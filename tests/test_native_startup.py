"""Project-only onboarding defaults must preserve security and existing state."""
import importlib.util
import json
import pathlib
import copy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = pathlib.Path(__file__).parents[1] / 'src/roles/agents_connector/files/connector-team.py'
spec = importlib.util.spec_from_file_location('native_startup_team', SOURCE)
team = importlib.util.module_from_spec(spec)
spec.loader.exec_module(team)


class NativeStartupTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = pathlib.Path(directory.name)
        self.profiles = self.root / 'projects/example/profiles'
        self.role = self.profiles / 'orchestrator'
        self.role.mkdir(parents=True)
        self.home = self.role / 'home'
        self.home.mkdir()
        patcher = patch.multiple(team, PROJECT='example', ACCOUNT_HOME=self.root, PROFILES=self.profiles)
        patcher.start()
        self.addCleanup(patcher.stop)

    def profile(self, vendor, account):
        (self.role / 'profile.json').write_text(json.dumps({'flavour': vendor, 'auth_directory': account}))

    def write(self, relative, value):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return path

    def test_claude_new_home_gets_setup_and_only_exact_workspace_trust(self):
        self.profile('claude', 'claude-work')
        team.prepare_native_startup('orchestrator')
        path = self.home / '.claude.json'
        data = json.loads(path.read_text())
        self.assertTrue(data['hasCompletedOnboarding'])
        self.assertEqual(data['theme'], 'dark')
        self.assertEqual(data['projects'], {'/workspace': {'hasTrustDialogAccepted': True}})
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('permissions', data)
        self.assertNotIn('oauthAccount', data)

    def test_preserves_claude_account_preferences_and_explicit_distrust(self):
        self.profile('claude', 'claude-priv')
        original = {'theme': 'light', 'hasCompletedOnboarding': False,
                    'oauthAccount': {'fixture': 'private-account'},
                    'projects': {'/workspace': {'hasTrustDialogAccepted': False}, '/elsewhere': {'custom': 1}},
                    'permissions': {'ask': ['Bash(*)']}}
        path = self.write('.claude.json', original)
        team.prepare_native_startup('orchestrator')
        data = json.loads(path.read_text())
        for key, value in original.items():
            self.assertEqual(data[key], value)
        first = path.stat().st_mtime_ns
        team.prepare_native_startup('orchestrator')
        self.assertEqual(path.stat().st_mtime_ns, first)

    def test_gemini_trust_is_scoped_and_update_policy_preserves_other_settings(self):
        self.profile('gemini', 'gemini-work')
        path = self.write('.gemini/settings.json', {'security': {'auth': {'selectedType': 'vertex-ai'}},
                                                   'model': {'name': 'fixture-model'}})
        team.prepare_native_startup('orchestrator')
        data = json.loads(path.read_text())
        self.assertEqual(data['security']['auth']['selectedType'], 'vertex-ai')
        self.assertEqual(data['model']['name'], 'fixture-model')
        self.assertEqual(data['general'], {'enableAutoUpdate': False, 'enableAutoUpdateNotification': False})
        self.assertEqual(json.loads((self.home / '.gemini/trustedFolders.json').read_text()),
                         {'/workspace': 'TRUST_FOLDER'})
        self.assertNotIn('approvalMode', data)

    def test_explicit_gemini_distrust_is_not_overridden(self):
        self.profile('gemini', 'gemini-work')
        path = self.write('.gemini/trustedFolders.json', {'/workspace': 'DO_NOT_TRUST'})
        team.prepare_native_startup('orchestrator')
        self.assertEqual(json.loads(path.read_text()), {'/workspace': 'DO_NOT_TRUST'})

    def test_antigravity_does_not_receive_gemini_cli_configuration(self):
        self.profile('gemini', 'gemini-priv')
        team.prepare_native_startup('orchestrator')
        self.assertFalse((self.home / '.gemini/settings.json').exists())

    def test_malformed_json_is_preserved_and_refused(self):
        self.profile('claude', 'claude-work')
        path = self.home / '.claude.json'
        path.write_text('{broken')
        with self.assertRaisesRegex(ValueError, 'Invalid native startup JSON'):
            team.prepare_native_startup('orchestrator')
        self.assertEqual(path.read_text(), '{broken')

    def test_symlinked_config_or_parent_is_refused(self):
        self.profile('claude', 'claude-work')
        external = self.root / 'other.json'
        external.write_text('{}')
        path = self.home / '.claude.json'
        path.symlink_to(external)
        with self.assertRaises(ValueError):
            team.prepare_native_startup('orchestrator')
        self.assertEqual(external.read_text(), '{}')
        path.unlink()
        self.profile('gemini', 'gemini-work')
        (self.home / '.gemini').symlink_to(self.root)
        with self.assertRaises(ValueError):
            team.prepare_native_startup('orchestrator')

    def test_legacy_environment_is_not_changed(self):
        self.profile('claude', 'claude-work')
        with patch.object(team, 'PROJECT', None):
            team.prepare_native_startup('orchestrator')
        self.assertFalse((self.home / '.claude.json').exists())

    def native_hooks(self):
        hooks = []
        for event, kind in [('userPromptSubmit', 'user_prompt_submit'), ('postToolUse', 'post_tool_use'), ('stop', 'stop')]:
            hooks.append({'key': '/home/agent/.codex/config.toml:' + kind + ':0:0',
                          'currentHash': 'sha256:' + 'a' * 64, 'eventName': event,
                          'sourcePath': '/home/agent/.codex/config.toml', 'handlerType': 'command',
                          'command': '/opt/connector/bin/agents-connector hook --socket /ipc/agent.sock '
                                     '--agent-token fixture-token --event ' + kind + ' --cli-kind codex',
                          'matcher': None, 'timeoutSec': 600, 'async': False, 'isManaged': False,
                          'enabled': True, 'trustStatus': 'untrusted'})
        return {'data': [{'cwd': '/workspace', 'hooks': hooks, 'errors': [], 'warnings': []}]}

    def test_only_current_exact_generated_hook_definitions_are_accepted(self):
        result = self.native_hooks()
        self.assertEqual(len(team.managed_codex_hooks(result, 'fixture-token')), 3)
        mutations = [('command', 'sh -c dangerous'), ('sourcePath', '/workspace/hooks.json'),
                     ('matcher', '*'), ('async', True), ('timeoutSec', 1),
                     ('currentHash', 'invented'), ('isManaged', True)]
        for key, value in mutations:
            changed = copy.deepcopy(result)
            changed['data'][0]['hooks'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                team.managed_codex_hooks(changed, 'fixture-token')
        with self.assertRaises(ValueError):
            team.managed_codex_hooks(result, 'different-project-token')
        result['data'][0]['hooks'].append(copy.deepcopy(result['data'][0]['hooks'][0]))
        with self.assertRaises(ValueError):
            team.managed_codex_hooks(result, 'fixture-token')

    def test_native_stdio_hash_roundtrip_is_bounded_to_managed_trust_edits(self):
        self.profile('codex', 'codex-priv')
        (self.role / 'token').write_text('fixture-token')
        fixture = self.root / 'server.py'
        fixture.write_text('''import json,sys
result=json.loads(sys.argv[1]); edited=False
for line in sys.stdin:
 request=json.loads(line)
 if 'id' not in request:continue
 method=request['method']
 if method=='initialize':answer={}
 elif method=='hooks/list':answer=result
 elif method=='config/batchWrite':
  params=request['params'];assert params['filePath']=='/home/agent/.codex/config.toml'
  assert params['reloadUserConfig'] is True and len(params['edits'])==3
  for edit in params['edits']:
   assert edit['keyPath'].startswith('hooks.state."/home/agent/.codex/config.toml:')
   assert edit['keyPath'].endswith('".trusted_hash')
   assert edit['mergeStrategy']=='replace' and edit['value']=='sha256:'+'a'*64
  for hook in result['data'][0]['hooks']:hook['trustStatus']='trusted'
  edited=True;answer={}
 else:raise AssertionError('Unexpected native method')
 print(json.dumps({'id':request['id'],'result':answer}),flush=True)
assert edited
''')
        original = subprocess.Popen
        with patch.object(team.subprocess, 'Popen', side_effect=lambda args, **kw:
                          original([sys.executable, str(fixture), json.dumps(self.native_hooks())], **kw)) as start:
            team.prepare_codex_hooks('orchestrator')
        self.assertEqual(start.call_args.args[0],
                         ['podman', 'exec', '-i', 'acp-example-orchestrator', 'codex', 'app-server', '--stdio'])


if __name__ == '__main__':
    unittest.main()
