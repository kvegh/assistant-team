"""Synthetic same-account recovery, including actual protected Ansible transport."""
import base64
import getpass
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

REPO = Path(__file__).parents[1]
SOURCE = REPO / 'src/roles/codex_auth_recovery/files/codex-auth-recovery.py'
spec = importlib.util.spec_from_file_location('recovery', SOURCE)
mod = importlib.util.module_from_spec(spec)
# The deployed helper dependency is adjacent; import from its existing source.
original = importlib.util.spec_from_file_location
def dependency(name, path, *args, **kwargs):
    if name == 'transfer':
        path = REPO / 'src/roles/native_auth_transfer/files/native-auth-transfer.py'
    return original(name, path, *args, **kwargs)
with mock.patch.object(importlib.util, 'spec_from_file_location', side_effect=dependency):
    spec.loader.exec_module(mod)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.role = self.root / 'archive/sample/profiles/builder'
        self.home = self.role / 'accounts/codex-priv/home'
        self.target = self.root / 'models'
        self.config = self.root / 'environment.conf'
        self.write(self.role / 'profile.json', {'flavour': 'codex', 'auth_directory': 'codex-priv', 'account_profile': 'codex-priv'})
        self.write(self.home / '.codex/auth.json', self.auth('synthetic-account', 'new'))
        self.write(self.target / 'codex-priv/.native-install.json', {'directory': 'codex-priv', 'flavour': 'codex'})
        self.write(self.target / 'codex-priv/.codex/auth.json', self.auth('synthetic-account', 'old'))
        self.write(self.config, {'version': 1, 'profiles': {p: {'enabled': p == 'codex-priv'} for p in mod.transfer.PROFILES}})
        self.guard = mock.patch.object(mod, 'stopped')
        self.guard.start()
        self.addCleanup(self.guard.stop)

    @staticmethod
    def write(path, data):
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # All credential-scope ancestors in this disposable fixture are private.
        for parent in path.parents:
            if parent.name in ['builder', 'accounts', 'home', 'codex-priv', '.codex']:
                parent.chmod(0o700)
        path.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())
        path.chmod(0o600)

    @staticmethod
    def auth(account, marker):
        claims = {'sub': 'synthetic-subject', 'iss': 'synthetic-issuer', 'exp': time.time() + 3600,
                  'https://api.openai.com/auth': {'chatgpt_account_id': account}}
        token = 'header.' + base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=') + '.' + marker
        return {'auth_mode': 'chatgpt', 'tokens': {'account_id': account, 'access_token': token, 'id_token': token, 'refresh_token': 'synthetic-refresh-' + marker}}

    def capture(self):
        return mod.capture(self.role, self.home)

    def replace(self, payload):
        return mod.replace(self.target, self.config, payload)

    def test_same_account_replace_preserves_source_and_rerun(self):
        before = (self.home / '.codex/auth.json').read_bytes()
        result = self.replace(self.capture())
        self.assertTrue(result['changed'])
        self.assertEqual((self.target / 'codex-priv/.codex/auth.json').read_bytes(), before)
        self.assertEqual((self.home / '.codex/auth.json').read_bytes(), before)
        self.assertFalse(self.replace(self.capture())['changed'])
        self.assertNotIn('synthetic-account', json.dumps(result))
        self.assertEqual((self.target / 'codex-priv/.codex/auth.json').stat().st_mode & 0o777, 0o600)

    def test_mismatch_refuses_without_changing_destination(self):
        self.write(self.home / '.codex/auth.json', self.auth('other-account', 'new'))
        before = (self.target / 'codex-priv/.codex/auth.json').read_bytes()
        with self.assertRaisesRegex(mod.Error, 'account_identity_mismatch'):
            self.replace(self.capture())
        self.assertEqual((self.target / 'codex-priv/.codex/auth.json').read_bytes(), before)

    def test_wrong_context_public_file_and_link_are_refused(self):
        metadata = self.role / 'profile.json'
        self.write(metadata, {'flavour': 'codex', 'auth_directory': 'codex-work', 'account_profile': 'codex-work'})
        with self.assertRaisesRegex(mod.Error, 'wrong_source_role_context'):
            self.capture()
        self.write(metadata, {'flavour': 'codex', 'auth_directory': 'codex-priv', 'account_profile': 'codex-priv'})
        credential = self.home / '.codex/auth.json'
        credential.chmod(0o644)
        with self.assertRaises(mod.Error):
            self.capture()
        credential.chmod(0o600)
        external = self.root / 'external'
        external.write_bytes(credential.read_bytes())
        credential.unlink()
        credential.symlink_to(external)
        with self.assertRaises(mod.Error):
            self.capture()

    def test_target_disabled_noncanonical_or_link_refuses_preserving_target(self):
        payload = self.capture()
        path = self.target / 'codex-priv/.codex/auth.json'
        before = path.read_bytes()
        cfg = json.loads(self.config.read_text())
        cfg['profiles']['codex-priv']['enabled'] = False
        self.write(self.config, cfg)
        with self.assertRaisesRegex(mod.Error, 'target_account_disabled'):
            self.replace(payload)
        cfg['profiles']['codex-priv']['enabled'] = True
        self.write(self.config, cfg)
        self.write(self.target / 'codex-priv/.native-install.json', {'directory': 'codex', 'flavour': 'codex'})
        with self.assertRaisesRegex(mod.Error, 'wrong_installed_profile'):
            self.replace(payload)
        self.assertEqual(path.read_bytes(), before)
        self.write(self.target / 'codex-priv/.native-install.json', {'directory': 'codex-priv', 'flavour': 'codex'})
        external = self.root / 'external'
        external.write_bytes(before)
        path.unlink()
        path.symlink_to(external)
        with self.assertRaises(mod.Error):
            self.replace(payload)
        self.assertEqual(external.read_bytes(), before)

    def test_writer_guard_refuses_running_container_mount(self):
        self.guard.stop()
        with mock.patch.object(mod.transfer, 'idle'), mock.patch.object(subprocess, 'run', side_effect=[
                subprocess.CompletedProcess([], 0, 'synthetic-container\n', ''),
                subprocess.CompletedProcess([], 0, json.dumps([{'Mounts': [{'Source': str(self.home)}]}]), '')]):
            with self.assertRaisesRegex(mod.Error, 'credential_container_writer_active'):
                mod.stopped(self.home)
        self.guard.start()

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
        variables = {'ansible_become': False, 'codex_auth_recovery_runtime_user': getpass.getuser(),
                     'codex_auth_recovery_source_host': 'source_fixture', 'codex_auth_recovery_source_role': str(self.role),
                     'codex_auth_recovery_source_home': str(self.home), 'codex_auth_recovery_destination_profiles_root': str(self.target),
                     'codex_auth_recovery_destination_environment_config': str(self.config),
                     'codex_auth_recovery_report_directory': str(self.root / 'reports')}
        env = dict(os.environ, PATH=str(fake) + os.pathsep + os.environ['PATH'], ANSIBLE_ROLES_PATH=str(REPO / 'src/roles'),
                   ANSIBLE_HOME=str(self.root / 'ansible'), ANSIBLE_LOCAL_TEMP=str(self.root / 'local'))
        play = self.root / 'play.json'
        def run(execute):
            variables['codex_auth_recovery_execute'] = execute
            play.write_text(json.dumps([{'name': 'Synthetic Codex recovery', 'hosts': 'destination_fixture', 'gather_facts': False,
                                         'vars': variables, 'environment': {'PATH': env['PATH']}, 'roles': ['codex_auth_recovery']}]))
            return subprocess.run(['ansible-playbook', '-i', str(inventory), str(play)], env=env, cwd=self.root,
                                  capture_output=True, text=True, timeout=90)
        source = (self.home / '.codex/auth.json').read_bytes()
        for execute, status in [(False, 'validated_same_account'), (True, 'replaced_same_account'), (True, 'unchanged_same_account')]:
            result = run(execute)
            self.assertEqual(result.returncode, 0, 'Synthetic Ansible recovery failed; protected output withheld')
            self.assertNotIn('synthetic-refresh', result.stdout + result.stderr)
            self.assertEqual(json.loads((self.root / 'reports/codex-priv.json').read_text())['status'], status)
        self.assertEqual(source, (self.home / '.codex/auth.json').read_bytes())
        self.write(self.home / '.codex/auth.json', self.auth('different-account', 'new'))
        before = (self.target / 'codex-priv/.codex/auth.json').read_bytes()
        self.assertNotEqual(run(True).returncode, 0)
        self.assertEqual((self.target / 'codex-priv/.codex/auth.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
