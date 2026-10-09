"""Synthetic-only bootstrap transfer tests; no provider calls or real auth reads."""
import base64
import copy
import importlib.util
import json
import getpass
import shutil
import subprocess
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).parents[1] / 'src/roles/native_auth_transfer/files/native-auth-transfer.py'
spec = importlib.util.spec_from_file_location('native_auth_transfer', SOURCE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name) / 'legacy'
        self.target = Path(self.tmp.name) / 'ac-agents/model-environments'
        self.source.mkdir()
        self.target.mkdir(parents=True)
        self.idle = mock.patch.object(mod, 'idle')
        self.idle.start()
        self.addCleanup(self.idle.stop)
        self.selected = ['claude-priv', 'claude-work', 'gemini-work', 'gemini-priv', 'codex-priv', 'mistral-priv']
        self.configs = []
        for root in [self.source, self.target]:
            config = root.parent / (root.name + '.conf')
            self.write(config, {'version': 1, 'profiles': {p: {'enabled': p in self.selected} for p in mod.PROFILES}})
            self.configs.append(config)
            for p in self.selected:
                self.write(root / p / '.native-install.json', {'directory': p, 'flavour': 'vibe' if p.startswith('mistral-') else p.split('-')[0], 'provider': mod.provider(p)})
        for p in self.selected:
            kind = mod.provider(p)
            data = ({'type': 'authorized_user', 'client_id': 'synthetic-client', 'client_secret': 'synthetic-secret', 'refresh_token': 'synthetic-refresh'} if kind == 'vertex' else
                    {'claudeAiOauth': {'accessToken': 'synthetic-access', 'refreshToken': 'synthetic-refresh'}} if kind == 'claude' else
                    {'tokens': {'access_token': 'synthetic-access', 'refresh_token': 'synthetic-refresh'}} if kind == 'codex' else
                    {'token': {'access_token': 'synthetic-access', 'refresh_token': 'synthetic-refresh'}})
            self.write(self.source / p / mod.credential_path(p), b'OTHER_SECRET="excluded"\nMISTRAL_API_KEY="synthetic-key"\n' if kind == 'mistral' else data)
            if kind == 'vertex':
                cfg = ({k: 'claude-synthetic-model' for k in mod.VERTEX_KEYS[p]} if p == 'claude-work' else {'GOOGLE_GENAI_USE_VERTEXAI': 'true', 'GOOGLE_CLOUD_PROJECT': 'synthetic-project', 'GOOGLE_CLOUD_LOCATION': 'global', 'GEMINI_MODEL': 'synthetic-model'})
                if p == 'claude-work':
                    cfg.update(CLAUDE_CODE_USE_VERTEX='1', CLOUD_ML_REGION='global', ANTHROPIC_VERTEX_PROJECT_ID='synthetic-project')
                self.write(self.source / p / '.vertex.json', cfg)
        self.write(self.source / 'claude-priv/.claude.json', {'oauthAccount': {'accountUuid': 'synthetic-id', 'emailAddress': 'synthetic@example.invalid'}, 'hasCompletedOnboarding': True, 'permissions': {'dangerous': True}, 'hooks': {'excluded': True}})

    @staticmethod
    def write(path, data):
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else (json.dumps(data) + '\n').encode())
        path.chmod(0o600)

    def capture(self):
        return mod.capture(self.source, self.configs[0])

    def restore(self, payload):
        return mod.restore(self.target, self.configs[1], payload)

    def test_roundtrip_contexts_allowlists_and_manifest(self):
        before = {str(p.relative_to(self.source)): p.read_bytes() for p in self.source.rglob('*') if p.is_file()}
        result = self.restore(self.capture())
        self.assertEqual(sum(r['status'] == 'restored' for r in result['report']), 6)
        self.assertEqual(before, {str(p.relative_to(self.source)): p.read_bytes() for p in self.source.rglob('*') if p.is_file()})
        mistral = (self.target / 'mistral-priv/.vibe/.env').read_text()
        self.assertNotIn('OTHER_SECRET', mistral)
        metadata = json.loads((self.target / 'claude-priv/.claude/.claude.json').read_text())
        self.assertNotIn('permissions', metadata)
        self.assertNotIn('hooks', metadata)
        self.assertEqual(len(result['vault_material_manifest']), 9)
        self.assertNotIn('synthetic-access', json.dumps(result))
        self.assertNotIn('synthetic@example', json.dumps(result))
        for path in self.target.rglob('*'):
            if path.is_file():
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads((self.target / 'gemini-work/.gemini/settings.json').read_text())['security']['auth']['selectedType'], 'vertex-ai')
        self.assertIn('cli_auth_credentials_store = "file"', (self.target / 'codex-priv/.codex/config.toml').read_text())

    def test_newer_existing_credentials_are_never_overwritten(self):
        path = self.target / 'claude-work/.config/gcloud/application_default_credentials.json'
        self.write(path, b'newer-existing-credentials')
        result = self.restore(self.capture())
        self.assertEqual(path.read_bytes(), b'newer-existing-credentials')
        self.assertFalse((self.target / 'claude-work/.vertex.json').exists())
        self.assertEqual(next(r['status'] for r in result['report'] if r['profile'] == 'claude-work'), 'skipped_existing')

    def test_metadata_preflight_never_reads_credential_bytes(self):
        original = mod.read_file
        def read(root, relative, private=True):
            self.assertNotIn(relative, [mod.credential_path(p) for p in mod.PROFILES])
            return original(root, relative, private)
        with mock.patch.object(mod, 'read_file', side_effect=read):
            result = mod.capture(self.source, self.configs[0], metadata_only=True)
        self.assertEqual(result['entries'], [])
        self.assertEqual(sum(r['status'] == 'present_unverified' for r in result['report']), 6)

    def test_source_file_symlink_cannot_capture_external_content(self):
        path = self.source / 'codex-priv/.codex/auth.json'
        path.unlink()
        external = Path(self.tmp.name) / 'external'
        self.write(external, {'tokens': {'access_token': 'excluded'}})
        path.symlink_to(external)
        result = self.capture()
        self.assertNotIn('codex-priv', [e['profile'] for e in result['entries']])
        self.assertNotIn('excluded', json.dumps(result))

    def test_destination_parent_symlink_refuses_before_any_secret_publication(self):
        (self.target / 'codex-priv/.codex').symlink_to(self.source / 'codex-priv/.codex')
        with self.assertRaises(mod.TransferError):
            self.restore(self.capture())
        self.assertFalse((self.target / 'claude-priv/.claude/.credentials.json').exists())

    def test_destination_file_symlink_refuses_without_external_write(self):
        external = Path(self.tmp.name) / 'external'
        self.write(external, b'preserved')
        (self.target / 'claude-priv/.claude').mkdir()
        (self.target / 'claude-priv/.claude/.claude.json').symlink_to(external)
        with self.assertRaises(mod.TransferError):
            self.restore(self.capture())
        self.assertEqual(external.read_bytes(), b'preserved')

    def test_unknown_file_or_public_manifest_field_is_rejected_before_copy(self):
        for field in ['path', 'allowlisted_fields']:
            payload = self.capture()
            payload['entries'][-1]['files'][0][field] = 'outside' if field == 'path' else ['SECRET-VALUE']
            with self.assertRaises(mod.TransferError):
                self.restore(payload)
            self.assertFalse((self.target / 'claude-priv/.claude/.credentials.json').exists())

    def test_partial_profile_write_rolls_back_on_filesystem_error(self):
        payload = self.capture()
        payload['entries'] = [e for e in payload['entries'] if e['profile'] == 'claude-priv']
        original = mod.publish
        def publish(root, path, raw):
            if path == '.claude/.credentials.json':
                raise OSError('synthetic disk failure')
            return original(root, path, raw)
        with mock.patch.object(mod, 'publish', side_effect=publish), self.assertRaises(OSError):
            self.restore(payload)
        self.assertFalse((self.target / 'claude-priv/.claude/.claude.json').exists())
        self.assertEqual(list(self.target.rglob('.auth-transfer-*')), [])

    def test_wrong_destination_provider_is_rejected(self):
        self.write(self.target / 'gemini-work/.native-install.json', {'directory': 'gemini-work', 'flavour': 'gemini', 'provider': 'antigravity'})
        with self.assertRaises(mod.TransferError):
            self.restore(self.capture())
        self.assertFalse((self.target / 'claude-priv/.claude/.credentials.json').exists())

    def test_mistral_duplicate_and_interpolation_never_execute(self):
        for data in [b'MISTRAL_API_KEY=a\nMISTRAL_API_KEY=b\n', b'MISTRAL_API_KEY=$(echo leak)\n']:
            with self.assertRaises(mod.TransferError):
                mod.native_credentials('mistral-priv', data)

    def test_unknown_claude_setting_is_not_restorable(self):
        payload = self.capture()
        entry = next(e for e in payload['entries'] if e['profile'] == 'claude-priv')
        item = next(f for f in entry['files'] if f['path'].endswith('.claude.json'))
        item['content_b64'] = base64.b64encode(b'{"permissions": {"allow": ["*"]}}').decode()
        with self.assertRaises(mod.TransferError):
            self.restore(payload)

    def test_safe_report_ignores_untrusted_reason_values(self):
        payload = self.capture()
        payload['report'][6]['reason'] = 'SECRET-VALUE'
        result = self.restore(payload)
        self.assertNotIn('SECRET-VALUE', json.dumps(result))

    def test_active_bootstrap_writer_blocks_capture_and_restore(self):
        with mock.patch.object(mod, 'idle', side_effect=mod.TransferError('bootstrap_writer_active')):
            with self.assertRaises(mod.TransferError):
                self.capture()

    @unittest.skipUnless(shutil.which('ansible-playbook'), 'Existing Ansible is needed for local transport acceptance')
    def test_ansible_transport_preflight_restore_and_idempotence(self):
        root = SOURCE.parents[4]
        fixture = Path(self.tmp.name)
        inventory = fixture / 'inventory'
        inventory.write_text('\n'.join(name + ' ansible_connection=local ansible_python_interpreter=' + os.sys.executable +
                                      ' ansible_remote_tmp=' + str(fixture / 'remote-tmp')
                                      for name in ['source_fixture', 'destination_fixture']) + '\n')
        variables = {'ansible_become': False, 'native_auth_transfer_runtime_user': getpass.getuser(),
                     'native_auth_transfer_source_host': 'source_fixture',
                     'native_auth_transfer_source_profiles_root': str(self.source),
                     'native_auth_transfer_source_environment_config': str(self.configs[0]),
                     'native_auth_transfer_destination_profiles_root': str(self.target),
                     'native_auth_transfer_destination_environment_config': str(self.configs[1]),
                     'native_auth_transfer_report_directory': str(fixture / 'reports')}
        environment = os.environ.copy()
        environment.update(ANSIBLE_ROLES_PATH=str(root / 'src/roles'), ANSIBLE_LOCAL_TEMP=str(fixture / 'ansible-tmp'))
        play = fixture / 'play.json'
        for execute, expected in [(False, 'present_unverified'), (True, 'restored'), (True, 'skipped_existing')]:
            variables['native_auth_transfer_execute'] = execute
            play.write_text(json.dumps([{'name': 'Synthetic native auth transport', 'hosts': 'destination_fixture',
                                         'gather_facts': False, 'vars': variables, 'roles': ['native_auth_transfer']}]))
            result = subprocess.run(['ansible-playbook', '-i', str(inventory), str(play)], env=environment,
                                    cwd=root, capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, 'Synthetic Ansible transfer failed; no secret-bearing output is displayed')
            report = json.loads((fixture / 'reports/latest.json').read_text())
            self.assertEqual(sum(row['status'] == expected for row in report['report']), 6)
            self.assertNotIn('synthetic-access', json.dumps(report))

    def test_writer_guard_distinguishes_bootstrap_and_project_container_streams(self):
        procroot = Path(self.tmp.name) / 'proc'
        process = procroot / '123456789'
        process.mkdir(parents=True)
        (process / 'comm').write_text('codex')
        (process / 'cmdline').write_bytes(b'codex\x00')
        (process / 'cgroup').write_text('0::/user.slice/native')
        (process / 'cwd').symlink_to(self.source / 'codex-priv')
        (process / 'environ').write_bytes(('HOME=' + str(self.source / 'codex-priv')).encode())
        real_path = Path
        def path(value):
            return procroot if value == '/proc' else real_path(value)
        self.idle.stop()
        with mock.patch.object(mod, 'Path', side_effect=path):
            with self.assertRaisesRegex(mod.TransferError, 'bootstrap_writer_active'):
                mod.idle(self.source, self.selected)
            (process / 'cgroup').write_text('0::/user.slice/libpod-independent-role')
            mod.idle(self.source, self.selected)
        self.idle.start()


if __name__ == '__main__':
    unittest.main()
