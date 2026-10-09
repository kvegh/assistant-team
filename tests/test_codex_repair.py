import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'src/roles/agents_connector/files/connector-team.py'


class CodexRepairTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        spec = importlib.util.spec_from_file_location('codex_repair', SOURCE)
        self.core = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, {}, clear=True):
            spec.loader.exec_module(self.core)
        self.core.PROJECT = 'example'
        self.core.SESSION = 'example'
        self.core.PROFILES = self.root / 'profiles'
        self.builder = self.core.PROFILES / 'builder'
        self.builder.mkdir(parents=True)
        (self.builder / 'profile.json').write_text(json.dumps({'flavour': 'codex'}))
        (self.builder / 'launched').write_text('')
        (self.builder / 'private-state').write_text('preserve')

    def test_active_builder_is_never_replaced_or_launched(self):
        with patch.object(self.core.subprocess, 'check_output', return_value='0\n'), \
                patch.object(self.core, 'run') as run, patch.object(self.core, 'launch') as launch:
            with self.assertRaisesRegex(ValueError, 'active; preserved'):
                self.core.repair_failed_codex_builder()
        run.assert_not_called()
        launch.assert_not_called()
        self.assertTrue((self.builder / 'launched').exists())

    def test_dead_builder_only_is_replaced_and_private_state_preserved(self):
        with patch.object(self.core.subprocess, 'check_output', return_value='1\n'), \
                patch.object(self.core, 'run') as run, patch.object(self.core, 'launch') as launch:
            self.core.repair_failed_codex_builder()
        self.assertEqual(run.call_args.args[0], ['podman', 'rm', '--force', 'acp-example-builder'])
        launch.assert_called_once_with('builder')
        self.assertTrue((self.builder / 'launched').exists())
        self.assertEqual((self.builder / 'private-state').read_text(), 'preserve')

    def test_non_codex_builder_is_preserved_before_runtime_commands(self):
        (self.builder / 'profile.json').write_text(json.dumps({'flavour': 'claude'}))
        with patch.object(self.core.subprocess, 'check_output') as inspect:
            with self.assertRaisesRegex(ValueError, 'not a Codex'):
                self.core.repair_failed_codex_builder()
        inspect.assert_not_called()

    def test_missing_explicit_project_cannot_select_global_builder(self):
        self.core.PROJECT = None
        with self.assertRaisesRegex(ValueError, 'explicitly selected'):
            self.core.repair_failed_codex_builder()

    def test_failed_native_launch_never_restores_wake_marker(self):
        with patch.object(self.core.subprocess, 'check_output', return_value='1\n'), \
                patch.object(self.core, 'run'), \
                patch.object(self.core, 'launch', side_effect=RuntimeError('launch failed')):
            with self.assertRaisesRegex(RuntimeError, 'launch failed'):
                self.core.repair_failed_codex_builder()
        self.assertFalse((self.builder / 'launched').exists())

    def test_live_native_marker_restoration_never_launches_or_replaces(self):
        (self.builder / 'launched').unlink()
        with patch.object(self.core.subprocess, 'check_output', side_effect=['0\n', 'codex\n']), \
                patch.object(self.core, 'run') as run, patch.object(self.core, 'launch') as launch:
            self.core.restore_codex_builder_marker()
        self.assertTrue((self.builder / 'launched').exists())
        run.assert_not_called()
        launch.assert_not_called()

    def test_idle_or_dead_pane_cannot_claim_native_launch_marker(self):
        for dead, command in [('1', 'codex'), ('0', 'bash')]:
            with self.subTest(dead=dead, command=command):
                (self.builder / 'launched').unlink(missing_ok=True)
                with patch.object(self.core.subprocess, 'check_output', side_effect=[dead, command]):
                    with self.assertRaisesRegex(ValueError, 'live native Codex'):
                        self.core.restore_codex_builder_marker()
                self.assertFalse((self.builder / 'launched').exists())

    def test_repaired_builder_receives_fixed_event_notice(self):
        with patch.object(self.core.subprocess, 'check_output', return_value='1\n'), \
                patch.object(self.core, 'run'), patch.object(self.core, 'launch'):
            self.core.repair_failed_codex_builder()
        with patch.object(self.core, 'run') as send:
            self.core.wake(['send-keys', '-l', '-t', 'example:builder',
                            '[agents-connector] new message from orchestrator — see additionalContext for content'])
        self.assertEqual(send.call_args.args[0][:4], ['podman', 'exec', 'acp-example-builder', 'tmux'])
        self.assertIn('read your authenticated inbox', send.call_args.args[0][-1])
