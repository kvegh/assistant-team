"""Synthetic private Claude refresh-capable cache recovery without provider calls."""
import getpass
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).parents[1]
SOURCE = REPO / 'src/roles/claude_auth_recovery/files/claude-auth-recovery.py'
original = importlib.util.spec_from_file_location
def dependency(name, path, *args, **kwargs):
    if name == 'transfer':
        path = REPO / 'src/roles/native_auth_transfer/files/native-auth-transfer.py'
    elif name == 'codex_recovery_guard':
        path = REPO / 'src/roles/codex_auth_recovery/files/codex-auth-recovery.py'
    return original(name, path, *args, **kwargs)
spec = original('claude_recovery', SOURCE)
mod = importlib.util.module_from_spec(spec)
with mock.patch.object(importlib.util, 'spec_from_file_location', side_effect=dependency):
    spec.loader.exec_module(mod)


class ClaudeRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.role = self.root / 'archive/sample/profiles/private-connector'
        self.home = self.role / 'accounts/claude-priv/home'
        self.target = self.root / 'models'
        self.config = self.root / 'environment.conf'
        self.metadata = {'oauthAccount': {'accountUuid': 'synthetic-account', 'organizationUuid': 'synthetic-org'}}
        self.write(self.role / 'profile.json', {'flavour': 'claude', 'auth_directory': 'claude-priv', 'account_profile': 'claude-priv'})
        self.write(self.home / '.claude.json', self.metadata)
        self.write(self.home / '.claude/.credentials.json', {'claudeAiOauth': {'accessToken': 'synthetic-expired', 'refreshToken': 'synthetic-refresh', 'expiresAt': 1}})
        self.write(self.target / 'claude-priv/.native-install.json', {'directory': 'claude-priv', 'flavour': 'claude'})
        self.write(self.target / 'claude-priv/.claude/.claude.json', self.metadata)
        self.write(self.target / 'claude-priv/.claude/.credentials.json', {'claudeAiOauth': {'accessToken': 'synthetic-old', 'expiresAt': 1}})
        self.write(self.config, {'version': 1, 'profiles': {p: {'enabled': p == 'claude-priv'} for p in mod.transfer.PROFILES}})
        self.guard = mock.patch.object(mod.guard, 'stopped')
        self.guard.start()
        self.addCleanup(self.guard.stop)

    @staticmethod
    def write(path, data):
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        for parent in path.parents:
            if parent.name in ['private-connector', 'accounts', 'home', 'claude-priv', '.claude']:
                parent.chmod(0o700)
        path.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())
        path.chmod(0o600)

    def capture(self):
        return mod.capture(self.role, self.home, self.home / '.claude.json')

    def replace(self, payload, validate_only=False):
        return mod.replace(self.target, self.config, payload, validate_only)

    def test_same_account_expired_refresh_capable_recovery_preserves_metadata(self):
        before = {str(p): p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        metadata = (self.target / 'claude-priv/.claude/.claude.json').read_bytes()
        old = (self.target / 'claude-priv/.claude/.credentials.json').read_bytes()
        self.assertEqual(self.replace(self.capture(), True)['status'], 'validated_same_account')
        self.assertEqual((self.target / 'claude-priv/.claude/.credentials.json').read_bytes(), old)
        report = self.replace(self.capture())
        self.assertTrue(report['changed'])
        self.assertFalse(self.replace(self.capture())['changed'])
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.home.rglob('*') if p.is_file()})
        self.assertEqual((self.target / 'claude-priv/.claude/.claude.json').read_bytes(), metadata)
        self.assertNotIn('synthetic-account', json.dumps(report))

    def test_account_and_organization_mismatches_preserve_destination(self):
        old = (self.target / 'claude-priv/.claude/.credentials.json').read_bytes()
        for key in ['accountUuid', 'organizationUuid']:
            metadata = json.loads(json.dumps(self.metadata))
            metadata['oauthAccount'][key] = 'different'
            self.write(self.home / '.claude.json', metadata)
            with self.assertRaisesRegex(mod.Error, 'account_identity_mismatch'):
                self.replace(self.capture())
            self.assertEqual((self.target / 'claude-priv/.claude/.credentials.json').read_bytes(), old)

    def test_explicit_metadata_context_refresh_and_private_paths_required(self):
        with self.assertRaises(mod.Error):
            mod.capture(self.role, self.home, self.home / '.claude/.claude.json')
        self.write(self.role / 'profile.json', {'flavour': 'claude', 'auth_directory': 'claude-work', 'account_profile': 'claude-work'})
        with self.assertRaisesRegex(mod.Error, 'wrong_source_role_context'):
            self.capture()
        self.write(self.role / 'profile.json', {'flavour': 'claude', 'auth_directory': 'claude-priv', 'account_profile': 'claude-priv'})
        self.write(self.home / '.claude/.credentials.json', {'claudeAiOauth': {'accessToken': 'synthetic-expired'}})
        with self.assertRaisesRegex(mod.Error, 'candidate_refresh_missing'):
            self.capture()
        self.write(self.home / '.claude/.credentials.json', {'claudeAiOauth': {'refreshToken': 'synthetic-refresh'}})
        path = self.home / '.claude.json'
        path.chmod(0o644)
        with self.assertRaises(mod.Error):
            self.capture()
        path.chmod(0o600)
        external = self.root / 'external'
        external.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(external)
        with self.assertRaises(mod.Error):
            self.capture()

    @unittest.skipUnless(shutil.which('ansible-playbook'), 'Existing Ansible required')
    def test_actual_ansible_recovery_and_mismatch_refusal(self):
        fake = self.root / 'bin'
        fake.mkdir()
        podman = fake / 'podman'
        podman.write_text('#!/bin/sh\nexit 0\n')
        podman.chmod(0o700)
        inventory = self.root / 'inventory'
        inventory.write_text('\n'.join(n + ' ansible_connection=local ansible_python_interpreter=' + sys.executable +
                                      ' ansible_remote_tmp=' + str(self.root / 'remote') for n in ['source_fixture', 'destination_fixture']))
        variables = {'ansible_become': False, 'claude_auth_recovery_runtime_user': getpass.getuser(),
                     'claude_auth_recovery_source_host': 'source_fixture', 'claude_auth_recovery_source_role': str(self.role),
                     'claude_auth_recovery_source_home': str(self.home), 'claude_auth_recovery_source_metadata': str(self.home / '.claude.json'),
                     'claude_auth_recovery_destination_profiles_root': str(self.target),
                     'claude_auth_recovery_destination_environment_config': str(self.config),
                     'claude_auth_recovery_report_directory': str(self.root / 'reports')}
        env = dict(os.environ, PATH=str(fake) + os.pathsep + os.environ['PATH'], ANSIBLE_ROLES_PATH=str(REPO / 'src/roles'),
                   ANSIBLE_HOME=str(self.root / 'ansible'), ANSIBLE_LOCAL_TEMP=str(self.root / 'local'))
        play = self.root / 'play.json'
        def run(execute):
            variables['claude_auth_recovery_execute'] = execute
            play.write_text(json.dumps([{'name': 'Synthetic Claude recovery', 'hosts': 'destination_fixture', 'gather_facts': False,
                                         'vars': variables, 'environment': {'PATH': env['PATH']}, 'roles': ['claude_auth_recovery']}]))
            return subprocess.run(['ansible-playbook', '-i', str(inventory), str(play)], env=env, cwd=self.root,
                                  capture_output=True, text=True, timeout=90)
        source = (self.home / '.claude/.credentials.json').read_bytes()
        metadata = (self.target / 'claude-priv/.claude/.claude.json').read_bytes()
        for execute, status in [(False, 'validated_same_account'), (True, 'replaced_same_account'), (True, 'unchanged_same_account')]:
            result = run(execute)
            self.assertEqual(result.returncode, 0, 'Synthetic Ansible recovery failed; protected output withheld')
            self.assertNotIn('synthetic-refresh', result.stdout + result.stderr)
            self.assertEqual(json.loads((self.root / 'reports/claude-priv.json').read_text())['status'], status)
        self.assertEqual(source, (self.home / '.claude/.credentials.json').read_bytes())
        self.assertEqual(metadata, (self.target / 'claude-priv/.claude/.claude.json').read_bytes())
        self.write(self.home / '.claude.json', {'oauthAccount': {'accountUuid': 'different', 'organizationUuid': 'synthetic-org'}})
        before = (self.target / 'claude-priv/.claude/.credentials.json').read_bytes()
        self.assertNotEqual(run(True).returncode, 0)
        self.assertEqual((self.target / 'claude-priv/.claude/.credentials.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
