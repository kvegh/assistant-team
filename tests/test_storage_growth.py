import importlib.util
import pathlib
import types
import unittest
from unittest.mock import patch

SOURCE = pathlib.Path(__file__).parents[1] / 'src/roles/linux_root_growth/files/grow-root.py'
spec = importlib.util.spec_from_file_location('root_growth', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RootGrowthTests(unittest.TestCase):
    def test_already_grown_partition_is_idempotent_without_backup_or_partition_write(self):
        part = {'start': 100, 'size': 200, 'type': 'linux', 'uuid': 'fixture'}
        calls = []

        def command(*args, **kwargs):
            calls.append(args)
            return types.SimpleNamespace(returncode=1 if args[0] == 'growpart' else 0,
                                         stdout='NOCHANGE', stderr='')

        stat = types.SimpleNamespace(f_blocks=200, f_frsize=4096, f_bavail=150)
        with patch.object(module, 'inspect', return_value=('/dev/fixture', 4, part)), \
                patch.object(module, 'command', side_effect=command), \
                patch.object(module.os, 'statvfs', return_value=stat):
            result = module.grow()
        self.assertFalse(result['changed'])
        self.assertEqual(calls, [('growpart', '--dry-run', '/dev/fixture', '4'), ('xfs_growfs', '/')])

    def test_failed_partition_dry_run_stops_before_any_growth(self):
        part = {'start': 100, 'size': 200, 'type': 'linux', 'uuid': 'fixture'}
        stat = types.SimpleNamespace(f_blocks=200, f_frsize=4096)
        with patch.object(module, 'inspect', return_value=('/dev/fixture', 4, part)), \
                patch.object(module.os, 'statvfs', return_value=stat), \
                patch.object(module, 'command', return_value=types.SimpleNamespace(returncode=2, stdout='', stderr='')) as command:
            with self.assertRaises(ValueError):
                module.grow()
        self.assertEqual(command.call_count, 1)

    def test_identity_change_refuses_filesystem_growth(self):
        before = {'start': 100, 'size': 200, 'type': 'linux', 'uuid': 'fixture'}
        after = dict(before, start=101)
        stat = types.SimpleNamespace(f_blocks=200, f_frsize=4096)
        with patch.object(module, 'inspect', side_effect=[('/dev/fixture', 4, before), ('/dev/fixture', 4, after)]), \
                patch.object(module.os, 'statvfs', return_value=stat), \
                patch.object(module, 'command', return_value=types.SimpleNamespace(returncode=1, stdout='NOCHANGE', stderr='')) as command:
            with self.assertRaises(ValueError):
                module.grow()
        self.assertEqual(command.call_count, 1)
