import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'src/roles/agents_connector/files/repair-gemini-mcp.py'
spec = importlib.util.spec_from_file_location('gemini_mcp_repair', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class GeminiMCPRepairTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.home = Path(self.scratch.name)
        self.profile = self.home / 'projects/demo/profiles/challenger'
        self.profile.mkdir(parents=True)
        (self.profile/'profile.json').write_text(json.dumps({'flavour': 'gemini', 'account_profile': 'gemini-work'}))
        self.settings = self.profile / 'accounts/gemini-work/home/.gemini/settings.json'
        self.settings.parent.mkdir(parents=True)
        self.original = {'model': {'name': 'fixture-model'}, 'security': {'auth': {'selectedType': 'vertex-ai'}}, 'hooks': {'BeforeAgent': ['fixture-hook']}, 'mcpServers': {'unrelated': {'command': 'fixture'}, 'agents_connector': {'command': '/opt/connector/bin/agents-connector', 'args': ['mcp-shim', '--socket', '/ipc/agent.sock', '--agent-token', 'fixture-broker-token'], 'timeout': 30}}}
        self.settings.write_text(json.dumps(self.original)); self.settings.chmod(0o600)

    def test_changes_only_mcp_command_retains_settings_backup_and_idempotence(self):
        original_bytes = self.settings.read_bytes()
        self.assertTrue(module.configure(self.home, 'demo', 'challenger'))
        actual = json.loads(self.settings.read_text())
        server = actual['mcpServers']['agents_connector']
        self.assertEqual(server['command'], 'python3')
        self.assertEqual(server['args'][:2], ['/opt/connector/bin/mcp-results.py', '/opt/connector/bin/agents-connector'])
        self.assertEqual(server['timeout'], 30)
        actual['mcpServers']['agents_connector'] = self.original['mcpServers']['agents_connector']
        self.assertEqual(actual, self.original)
        backup = next(self.settings.parent.glob('.mcp-result-backup-*'))
        self.assertEqual(backup.read_bytes(), original_bytes)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertFalse(module.configure(self.home, 'demo', 'challenger'))
        self.assertEqual(len(list(self.settings.parent.glob('.mcp-result-backup-*'))), 1)

    def test_non_gemini_and_unknown_native_command_are_refused_without_changes(self):
        before = self.settings.read_bytes()
        (self.profile/'profile.json').write_text('{"flavour":"claude"}')
        with self.assertRaises(ValueError): module.configure(self.home, 'demo', 'challenger')
        self.assertEqual(self.settings.read_bytes(), before)
        (self.profile/'profile.json').write_text('{"flavour":"gemini","account_profile":"gemini-work"}')
        config = dict(self.original); config['mcpServers'] = {'agents_connector': {'command':'unrelated', 'args':[]}}
        self.settings.write_text(json.dumps(config)); before = self.settings.read_bytes()
        with self.assertRaises(ValueError): module.configure(self.home, 'demo', 'challenger')
        self.assertEqual(self.settings.read_bytes(), before)

    def test_symlink_settings_and_invalid_identity_refused(self):
        target = self.settings.parent/'actual.json'; self.settings.rename(target); self.settings.symlink_to(target.name)
        before = target.read_bytes()
        for project, role in [('demo','challenger'), ('../escape','challenger'), ('demo','observer')]:
            with self.assertRaises(ValueError): module.configure(self.home, project, role)
        self.assertEqual(target.read_bytes(), before)

    def test_failed_atomic_publish_preserves_settings(self):
        from unittest.mock import patch
        before = self.settings.read_bytes()
        with patch.object(Path, 'replace', side_effect=OSError('fixture publication failure')):
            with self.assertRaises(OSError): module.configure(self.home, 'demo', 'challenger')
        self.assertEqual(self.settings.read_bytes(), before)
        self.assertFalse(list(self.settings.parent.glob('.mcp-result-pending-*')))


if __name__ == '__main__': unittest.main()
