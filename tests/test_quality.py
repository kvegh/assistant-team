import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('quality', Path(__file__).parents[1] / 'src/check-quality.py')
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)

class QualityTests(unittest.TestCase):
    def test_test_failure_stops_before_lint_and_preserves_exit(self):
        with patch('sys.argv', ['quality']), patch.object(quality.shutil, 'which', return_value='/fixture/ansible'), patch.dict(quality.os.environ, {'ANSIBLE_VAULT_PASSWORD_FILE': '/fixture/vpf'}), patch.object(quality.subprocess, 'run', return_value=Mock(returncode=17)) as run:
            self.assertEqual(quality.main(), 17)
            self.assertEqual(run.call_count, 1)

    def test_missing_vault_input_runs_no_command(self):
        with patch('sys.argv', ['quality']), patch.object(quality.shutil, 'which', return_value='/fixture/ansible'), patch.dict(quality.os.environ, {}, clear=True), patch.object(quality.subprocess, 'run') as run:
            with self.assertRaises(SystemExit) as error:
                quality.main()
            self.assertEqual(error.exception.code, 2)
            run.assert_not_called()

    def test_tests_only_does_not_require_vault_or_install_tools(self):
        with patch('sys.argv', ['quality', '--tests-only']), patch.dict(quality.os.environ, {}, clear=True), patch.object(quality.subprocess, 'run', return_value=Mock(returncode=0)) as run:
            self.assertEqual(quality.main(), 0)
            self.assertEqual(run.call_count, 1)
            self.assertIn('unittest', run.call_args.args[0])
