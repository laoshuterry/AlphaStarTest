#!/usr/bin/env python3
"""Start/status/stop the two local PySC2 LAN clients (macOS/Linux)."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from datetime import datetime


def process_table():
    result = subprocess.run(
        ['ps', '-ww', '-axo', 'pid=,ppid=,pgid=,stat=,lstart=,command='],
        capture_output=True, text=True, env=dict(os.environ, LC_ALL='C'))
    if result.returncode:
        raise RuntimeError('Cannot inspect processes: ' + result.stderr.strip())
    table = {}
    for line in result.stdout.splitlines():
        fields = line.split(None, 9)
        if len(fields) != 10:
            continue
        pid, ppid, pgid = map(int, fields[:3])
        if fields[3].startswith('Z'):
            continue
        table[pid] = dict(pid=pid, ppid=ppid, pgid=pgid,
                          started=' '.join(fields[4:9]), command=fields[9])
    return table


def identity(pid):
    process = process_table().get(pid)
    return process['started'] if process else None


def same_process(record, process):
    # Accept old state files that included the command after the start time.
    stamp = ' '.join(record.get('identity', '').split()[:5])
    return bool(process and stamp and process['started'] == stamp)


def targets(record, table):
    if not record:
        return {}
    pid = record['pid']
    root = table.get(pid)
    found = {}
    if same_process(record, root):
        found[pid] = root
        if root['pgid'] == pid:
            found.update({p: info for p, info in table.items() if info['pgid'] == pid})
    # Recover SC2 left behind by an earlier launcher, using this run's unique
    # temporary directory from its log, never a broad SC2 name match.
    log = Path(record['log'])
    if log.is_file():
        import re
        markers = re.findall(r'Launching SC2: .*? -tempDir (\S+)',
                             log.read_text(errors='replace'))
        for p, info in table.items():
            if '/SC2.app/Contents/MacOS/SC2 ' in info['command'] and any(
                    f' -tempDir {marker} ' in info['command'] for marker in markers):
                found[p] = info
    # Include descendants even if they use a different process group.
    while True:
        additions = {p: info for p, info in table.items()
                     if info['ppid'] in found and p not in found}
        if not additions:
            break
        found.update(additions)
    return found


def alive(record):
    return bool(targets(record, process_table()))


def stop_process(record):
    tracked = targets(record, process_table())
    for sig, seconds in ((signal.SIGINT, 5), (signal.SIGTERM, 3), (signal.SIGKILL, 2)):
        if not tracked:
            return
        table = process_table()
        # Refresh descendants before their parent disappears.
        tracked.update(targets(record, table))
        for pid, expected in list(tracked.items()):
            current = table.get(pid)
            if not current or current['started'] != expected['started']:
                tracked.pop(pid)
                continue
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                tracked.pop(pid, None)
        deadline = time.monotonic() + seconds
        while tracked and time.monotonic() < deadline:
            table = process_table()
            tracked = {p: info for p, info in tracked.items()
                       if p in table and table[p]['started'] == info['started']}
            if tracked:
                time.sleep(0.1)
    if tracked:
        raise RuntimeError(f'Processes still running: {sorted(tracked)}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', choices=['start', 'status', 'stop'], default='start')
    parser.add_argument('--project', type=Path, default=Path('/Volumes/MacExt/Developer/sc2-coach'))
    parser.add_argument('--sc2path', default=os.environ.get('SC2PATH', '/Volumes/MacExt/BattleNet/StarCraft II'))
    parser.add_argument('--python', type=Path, help='Defaults to PROJECT/.venv-pysc2/bin/python')
    parser.add_argument('--map', default='Simple64')
    parser.add_argument('--port', type=int, default=14380)
    parser.add_argument('--agent', default='pysc2.agents.random_agent.RandomAgent')
    parser.add_argument('--startup-timeout', type=float, default=180)
    args = parser.parse_args()
    project = args.project.resolve()
    if not project.is_dir():
        parser.error(f'Project does not exist: {project}')
    if not 1 <= args.port <= 65531 or args.startup_timeout <= 0:
        parser.error('Invalid port range or startup timeout')
    runtime = project / 'logs' / '.lan-run'
    runtime.mkdir(parents=True, exist_ok=True)
    with (runtime / 'lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error('Another launcher operation is in progress')
        state_path = runtime / 'state.json'
        state = json.loads(state_path.read_text()) if state_path.exists() else {}

        def save():
            temp = runtime / 'state.tmp'
            temp.write_text(json.dumps(state, indent=2))
            temp.replace(state_path)

        if args.action == 'status':
            for role in ('human', 'agent'):
                record = state.get(role)
                print(f'{role}: {"RUNNING" if alive(record) else "STOPPED"}; log: {record["log"] if record else "-"}')
            return
        if args.action == 'stop':
            for role in ('agent', 'human'):
                stop_process(state.get(role))
            if any(alive(state.get(role)) for role in ('human', 'agent')):
                raise RuntimeError('A client is still running; stop did not complete')
            print('Both clients stopped (logs retained).')
            return
        if any(alive(state.get(role)) for role in ('human', 'agent')):
            parser.error('A client is already running. Use status or stop first.')
        python = args.python or project / '.venv-pysc2/bin/python'
        python = python.absolute()
        if not python.is_file():
            parser.error(f'Python not found: {python}')
        if not Path(args.sc2path).is_dir():
            parser.error(f'SC2PATH does not exist: {args.sc2path}')
        log_dir = project / 'logs' / datetime.now().strftime('lan-%Y%m%d-%H%M%S-%f')
        log_dir.mkdir()
        env = dict(os.environ, SC2PATH=args.sc2path, PYTHONUNBUFFERED='1')
        common = [str(python), '-u', '-m', 'pysc2.bin.play_vs_agent',
                  '--host', '127.0.0.1', '--config_port', str(args.port),
                  '--realtime', '--rgb_screen_size', '0', '--rgb_minimap_size', '0']
        state = {}
        children = []

        def spawn(role, extra):
            log_path = log_dir / f'{role}.log'
            with log_path.open('w') as log:
                process = subprocess.Popen(common + extra, cwd=project, env=env,
                                           stdin=subprocess.DEVNULL, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
            children.append(process)
            stamp = identity(process.pid)
            if not stamp:
                raise RuntimeError(f'{role} exited immediately; see {log_path}')
            state[role] = dict(pid=process.pid, identity=stamp, log=str(log_path))
            save()
            return process, log_path

        try:
            human, human_log = spawn('human', ['--human', '--map', args.map, '--render'])
            print(f'Human started; waiting for Join: {human_log}', flush=True)
            deadline = time.monotonic() + args.startup_timeout
            while True:
                if human.poll() is not None:
                    raise RuntimeError(f'Human exited ({human.returncode}); see {human_log}')
                if 'Join: play_vs_agent' in human_log.read_text(errors='replace'):
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError(f'Human startup timed out; see {human_log}')
                time.sleep(0.25)
            agent, agent_log = spawn('agent', ['--norender', '--agent', args.agent])
            print(f'Agent started: {agent_log}', flush=True)
            deadline = time.monotonic() + args.startup_timeout
            while True:
                if human.poll() is not None or agent.poll() is not None:
                    raise RuntimeError(f'A client exited during join; inspect {log_dir}')
                if 'Connected, starting run_loop.' in agent_log.read_text(errors='replace'):
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError(f'Agent join timed out; see {agent_log}')
                time.sleep(0.25)
            print('LAN connected. Both clients remain in the background; use status/stop.')
        except BaseException:
            for process in reversed(children):
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    except ProcessLookupError:
                        pass
            raise


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError) as error:
        raise SystemExit(str(error))
