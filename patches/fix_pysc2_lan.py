"""Reproducible LAN compatibility patch for PySC2 4.0.0 (no SC2 required).

Default: preview diff. --apply: backup then replace. --check: CI verification.
Unknown source layouts fail before writing. Importing this module never patches.
"""
import argparse
import difflib
import importlib.metadata
import importlib.util
from pathlib import Path
import re

OLD = 'agent_interface_format=agent_interface_format, require_raw=visualize)'
NEW = 'interface_format=agent_interface_format, require_raw=visualize)'
ANCHOR = '    self._game_info = [self._controllers[0].game_info()]'
RACES = '''
    self._requested_races = {
        info.player_id: info.race_requested
        for info in self._game_info[0].player_info
        if info.type != sc_pb.Observer
    }'''


def transform(source):
    """Accept stock 4.0.0, the previous local patch, or this patch."""
    compile(source, '<original LAN>', 'exec')
    if source.count('        ' + OLD) + source.count('        ' + NEW) != 1:
        raise ValueError('Unexpected _get_interface call; no changes written')
    source = source.replace(OLD, NEW)
    # Retire the old placeholder player ID. Keep unrelated local edits.
    source = re.sub(r'^    self\._requested_races = \{0: int\(race\)\}\n', '',
                    source, flags=re.MULTILINE)
    if source.count(ANCHOR) != 1:
        raise ValueError('Unexpected game_info layout; no changes written')
    if ANCHOR + RACES not in source:
        if 'self._requested_races =' in source:
            raise ValueError('Unknown race mapping; no changes written')
        source = source.replace(ANCHOR, ANCHOR + RACES)
    if source.count('self._requested_races =') != 1:
        raise ValueError('Ambiguous race mapping; no changes written')
    compile(source, '<patched LAN>', 'exec')
    return source


def patch_file(path, apply=False):
    original = path.read_text(encoding='utf-8')
    updated = transform(original)
    if apply and updated != original:
        backup = path.with_suffix(path.suffix + '.lan.bak')
        # Never overwrite a previous backup of different contents.
        if backup.exists() and backup.read_text(encoding='utf-8') != original:
            raise ValueError(f'Backup already exists: {backup}; inspect it first')
        if not backup.exists():
            with backup.open('x', encoding='utf-8') as out:
                out.write(original)
        path.write_text(updated, encoding='utf-8')
    return original, updated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, help='Explicit lan_sc2_env.py copy')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--check', action='store_true')
    args = parser.parse_args()
    path = args.target
    if path is None:
        if importlib.metadata.version('PySC2') != '4.0.0':
            parser.error('Only installed PySC2 4.0.0 is supported')
        path = Path(importlib.util.find_spec('pysc2').origin).parent / 'env/lan_sc2_env.py'
    original, updated = patch_file(path, apply=args.apply)
    if original == updated:
        print(f'Already patched: {path}')
        return 0
    print(''.join(difflib.unified_diff(original.splitlines(True),
                                      updated.splitlines(True),
                                      fromfile=str(path), tofile=str(path))), end='')
    print('Applied (backup: .py.lan.bak)' if args.apply else 'Patch required (preview only)')
    return 1 if args.check else 0


if __name__ == '__main__':
    raise SystemExit(main())
