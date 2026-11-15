"""Offline regression tests; SC2 process and transport are mocked."""
import importlib.util
from pathlib import Path
import tempfile
import subprocess
import sys
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lan_patch', ROOT / 'patches/fix_pysc2_lan.py')
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)
STOCK = (ROOT / 'tests/fixtures/lan_sc2_env_4_0_0.py.txt').read_text()


class PatchTests(unittest.TestCase):
    def test_stock_and_idempotency(self):
        updated = patch.transform(STOCK)
        self.assertEqual(updated, patch.transform(updated))
        self.assertIn(patch.NEW, updated)

    def test_migrate_previous_patch(self):
        legacy = STOCK.replace(patch.OLD, patch.NEW).replace(
            '    self._action_delay_fns = [None]',
            '    self._action_delay_fns = [None]\n    self._requested_races = {0: int(race)}')
        self.assertEqual(patch.transform(STOCK), patch.transform(legacy))

    def test_unknown_source_rejected(self):
        for source in (STOCK.replace(patch.OLD, 'unknown=True)'),
                       STOCK.replace(patch.ANCHOR, ''),
                       STOCK.replace(patch.ANCHOR, patch.ANCHOR + '\n    self._requested_races = {}')):
            with self.subTest(source=source[-80:]), self.assertRaises(ValueError):
                patch.transform(source)

    def test_preview_backup_and_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'lan.py'
            path.write_text(STOCK)
            patch.patch_file(path)
            self.assertEqual(STOCK, path.read_text())
            patch.patch_file(path, apply=True)
            self.assertEqual(STOCK, path.with_suffix('.py.lan.bak').read_text())
            patch.patch_file(path, apply=True)
            self.assertEqual(patch.transform(STOCK), path.read_text())

    def test_cli_check_apply_and_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'lan.py'
            path.write_text(STOCK)
            command = [sys.executable, '-B', str(ROOT / 'patches/fix_pysc2_lan.py'),
                       '--target', str(path)]
            for mode, expected in [('--check', 1), ('--apply', 0),
                                   ('--check', 0), ('--apply', 0)]:
                result = subprocess.run(command + [mode], capture_output=True, text=True)
                self.assertEqual(expected, result.returncode, result.stderr)

    def test_conflicting_backup_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'lan.py'
            path.write_text(STOCK)
            path.with_suffix('.py.lan.bak').write_text('earlier backup')
            with self.assertRaises(ValueError):
                patch.patch_file(path, apply=True)
            self.assertEqual(STOCK, path.read_text())


class RuntimeTests(unittest.TestCase):
    @staticmethod
    def source():
        return STOCK

    @classmethod
    def setUpClass(cls):
        cls.lan = types.ModuleType('patched_lan')
        exec(compile(patch.transform(cls.source()), '<patched LAN>', 'exec'), cls.lan.__dict__)

    def test_join_reset_and_ports(self):
        lan = self.lan
        pb = lan.sc_pb
        info = pb.ResponseGameInfo(map_name='Simple64')
        info.player_info.add(player_id=1, type=pb.Participant, race_requested=1)
        info.player_info.add(player_id=2, type=pb.Participant, race_requested=4)
        info.player_info.add(player_id=3, type=pb.Observer)
        controller = mock.Mock()
        controller.game_info.return_value = info
        run_config = mock.Mock()
        run_config.start.return_value.controller = controller
        settings = dict(map_name='Simple64', map_path='Melee/Simple64.SC2Map',
                        map_data=b'map', game_version='5.0.17', remote=False,
                        ports={'server': {'game': 14381, 'base': 14382},
                               'client': {'game': 14383, 'base': 14384}})
        with mock.patch.object(lan, 'tcp_client', return_value=(mock.Mock(), settings)), \
             mock.patch.object(lan.run_configs, 'get', return_value=run_config), \
             mock.patch.object(lan.features, 'features_from_game_info', return_value=mock.Mock()), \
             mock.patch.object(lan.metrics if hasattr(lan, 'metrics') else lan.sc2_env.metrics, 'Metrics'), \
             mock.patch.object(lan.LanSC2Env, '_observe', return_value='observed'):
            for realtime in (False, True):
                with self.subTest(realtime=realtime):
                    env = lan.LanSC2Env(config_port=14380, race=lan.sc2_env.Race.random,
                                       realtime=realtime,
                                       agent_interface_format=pb.InterfaceOptions(raw=True))
                    try:
                        self.assertEqual({1: 1, 2: 4}, env._requested_races)
                        self.assertEqual('observed', env.reset())
                        with self.assertRaises(lan.RestartError):
                            env.reset()
                        join = controller.join_game.call_args.args[0]
                        self.assertEqual((14381, 14382), (join.server_ports.game_port, join.server_ports.base_port))
                        self.assertEqual((14383, 14384), (join.client_ports[0].game_port, join.client_ports[0].base_port))
                        self.assertEqual(4, join.race)
                        self.assertTrue(join.options.raw)
                    finally:
                        env.close()


class InstalledRuntimeTests(RuntimeTests):
    @staticmethod
    def source():
        package = Path(importlib.util.find_spec('pysc2').origin).parent
        return (package / 'env/lan_sc2_env.py').read_text()


if __name__ == '__main__':
    unittest.main()
