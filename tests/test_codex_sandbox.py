import importlib.util
import json
import pathlib
import runpy
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock


SOURCE = pathlib.Path(__file__).parents[1] / 'src/roles/agents_connector/files/connector-team.py'
spec = importlib.util.spec_from_file_location('codex_sandbox_team', SOURCE)
team = importlib.util.module_from_spec(spec)
spec.loader.exec_module(team)


class CodexSandboxContainerTests(unittest.TestCase):
    def test_only_codex_uses_dedicated_domain_and_all_keep_confinement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            profiles = root / 'profiles'
            for flavour in ['codex', 'claude', 'gemini']:
                profile = profiles / 'builder'
                profile.mkdir(parents=True, exist_ok=True)
                (profile / 'profile.json').write_text(json.dumps({'flavour': flavour}))
                calls = []
                with mock.patch.multiple(team, ROOT=root, PROFILES=profiles, INSTALL_ROOT=root, PROJECT=None), \
                     mock.patch.object(team.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)), \
                     mock.patch.object(team, 'run', side_effect=lambda cmd, **kwargs: calls.append(cmd)), \
                     mock.patch.object(team, 'wait_for_native_session'):
                    team.start_container('builder')
                command = calls[0]
                self.assertEqual('--security-opt=label=type:ac_agents_codex.process' in command, flavour == 'codex')
                for flag in ['--read-only', '--cap-drop=all', '--security-opt=no-new-privileges', '--userns=keep-id:uid=1000,gid=1000']:
                    self.assertIn(flag, command)
                self.assertNotIn('--privileged', command)
                self.assertNotIn('--security-opt=label=disable', command)

    def run_repair(self, core, label):
        loader = mock.Mock()
        repair = SOURCE.with_name('repair-codex-sandbox.py')
        with mock.patch.object(importlib.util, 'spec_from_file_location', return_value=types.SimpleNamespace(loader=loader)), \
             mock.patch.object(importlib.util, 'module_from_spec', return_value=core), \
             mock.patch.object(sys, 'argv', [str(repair), '--session-id', '12345678-1234-1234-1234-123456789abc']), \
             mock.patch.object(subprocess, 'check_output', return_value=json.dumps([{'ProcessLabel': label}])):
            runpy.run_path(str(repair), run_name='__main__')

    def test_already_migrated_builder_does_not_restart_saved_session(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            profile = root / 'builder'
            profile.mkdir()
            (profile / 'profile.json').write_text('{"flavour":"codex"}')
            core = types.SimpleNamespace(PROJECT='example', PROFILES=root, container=lambda role: 'fixture', run=mock.Mock())
            with self.assertRaises(SystemExit) as caught:
                self.run_repair(core, 'system_u:system_r:ac_agents_codex.process:s0:c1,c2')
            self.assertEqual(caught.exception.code, 0)
            core.run.assert_not_called()

    def test_missing_saved_conversation_refuses_before_container_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            profile = root / 'builder'
            profile.mkdir()
            (profile / 'profile.json').write_text('{"flavour":"codex"}')
            core = types.SimpleNamespace(PROJECT='example', PROFILES=root, container=lambda role: 'fixture', role_home=lambda role: root, run=mock.Mock())
            with self.assertRaisesRegex(ValueError, 'saved conversation'):
                self.run_repair(core, 'system_u:system_r:container_t:s0:c1,c2')
            core.run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
