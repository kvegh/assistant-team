import importlib.util
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'src/roles/agents_connector/files/connector-team.py'


class ContainerReadinessTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('container_readiness', SOURCE)
        self.core = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, {}, clear=True):
            spec.loader.exec_module(self.core)

    def result(self, code=0, stdout=''):
        return subprocess.CompletedProcess([], code, stdout, '')

    def test_detached_entrypoint_is_waited_for_without_launching_model(self):
        with patch.object(self.core.subprocess, 'run', side_effect=[
                self.result(1), self.result(stdout='true'), self.result()]) as execute, \
                patch.object(self.core.time, 'sleep') as sleep:
            self.core.wait_for_native_session('sample')
        sleep.assert_called_once_with(0.2)
        self.assertEqual(execute.call_count, 3)
        self.assertFalse(any('respawn-pane' in call.args[0] for call in execute.call_args_list))

    def test_exited_container_fails_immediately_without_recovery(self):
        with patch.object(self.core.subprocess, 'run', side_effect=[
                self.result(1), self.result(stdout='false')]), \
                patch.object(self.core.time, 'sleep') as sleep:
            with self.assertRaisesRegex(ValueError, 'Container stopped'):
                self.core.wait_for_native_session('sample', restore=True)
        sleep.assert_not_called()

    def test_unready_container_has_bounded_timeout(self):
        with patch.object(self.core.subprocess, 'run', side_effect=[
                self.result(1), self.result(stdout='true')]), \
                patch.object(self.core.time, 'monotonic', side_effect=[0, 16]):
            with self.assertRaisesRegex(ValueError, 'did not become ready'):
                self.core.wait_for_native_session('sample')

    def test_recovery_does_not_race_initializing_entrypoint(self):
        with patch.object(self.core.subprocess, 'run', side_effect=[
                self.result(1), self.result(stdout='true'), self.result(stdout='sh'),
                self.result()]) as execute, patch.object(self.core.time, 'sleep'):
            self.core.wait_for_native_session('sample', restore=True)
        self.assertFalse(any('new-session' in call.args[0] for call in execute.call_args_list))

    def test_finished_idle_entrypoint_can_restore_missing_session(self):
        with patch.object(self.core.subprocess, 'run', side_effect=[
                self.result(1), self.result(stdout='true'), self.result(stdout='sleep'),
                self.result(), self.result()]) as execute:
            self.core.wait_for_native_session('sample', restore=True)
        self.assertEqual(sum('new-session' in call.args[0] for call in execute.call_args_list), 1)
