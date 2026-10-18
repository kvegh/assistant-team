"""Native session continuity must not weaken launch permissions or stop ordering."""
import importlib.util
import json
import pathlib
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = pathlib.Path(__file__).parents[1]/'src/roles/agents_connector/files/connector-team.py'
spec = importlib.util.spec_from_file_location('session_lifecycle_core', SOURCE)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
SESSION = '11111111-1111-4111-8111-111111111111'


class SessionLifecycleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = pathlib.Path(temporary.name)
        self.profiles = self.root/'projects/example/profiles'
        self.profiles.mkdir(parents=True)
        context = patch.multiple(core, PROJECT='example', ACCOUNT_HOME=self.root, PROFILES=self.profiles)
        context.start(); self.addCleanup(context.stop)

    def profile(self, role, vendor):
        path = self.profiles/role
        (path/'home').mkdir(parents=True)
        (path/'profile.json').write_text(json.dumps({'flavour':vendor,'auth_directory':vendor+'-priv'}))

    def launch(self, role, vendor, suffix):
        self.profile(role, vendor)
        with patch.object(core,'seed_auth'), patch.object(core,'prepare_native_startup'), \
                patch.object(core,'start_container'), patch.object(core,'prepare_codex_hooks'), \
                patch.object(core,'apply_prompts'), patch.object(core,'session_arguments',return_value=suffix), \
                patch.object(core,'run') as execute:
            core.launch(role)
        return shlex.split(execute.call_args.args[0][-1])

    def test_codex_resume_retains_sandbox_and_approval_settings_without_task_prompt(self):
        command = self.launch('builder','codex',['resume',SESSION])
        self.assertEqual(command[-2:],['resume',SESSION])
        self.assertEqual(command[command.index('--sandbox')+1],'workspace-write')
        self.assertEqual(command[command.index('--ask-for-approval')+1],'on-request')
        self.assertIn('--no-daemon',command)
        self.assertNotIn('--last',command)

    def test_private_reader_resume_keeps_tools_and_mcp_isolation(self):
        command = self.launch('observer','claude',['--resume',SESSION])
        self.assertEqual(command[-2:],['--resume',SESSION])
        self.assertIn('--strict-mcp-config',command)
        self.assertEqual(command[command.index('--tools')+1],'Read,Grep,Glob,Write')

    def test_capture_failure_is_reported_without_stopping_containers(self):
        self.profile('builder','codex')
        result = subprocess.CompletedProcess([],0,'true\n','')
        failure = subprocess.CompletedProcess([],1,'','Ambiguous native history')
        with patch.object(core,'ALL',['builder']), patch.object(core.subprocess,'run',side_effect=[result,failure]) as execute:
            with self.assertRaisesRegex(ValueError,'builder: Ambiguous'):
                core.capture_sessions()
        self.assertFalse(any('stop' in item.args[0] for item in execute.call_args_list))

    def test_stopped_container_never_runs_identity_probe(self):
        result = subprocess.CompletedProcess([],0,'false\n','')
        with patch.object(core,'ALL',['builder']), patch.object(core.subprocess,'run',return_value=result) as execute:
            core.capture_sessions()
        self.assertEqual(execute.call_count,1)

    def test_gemini_session_hook_is_idempotent_and_preserves_other_hooks(self):
        self.profile('challenger','gemini')
        path = self.profiles/'challenger/profile.json'
        path.write_text(json.dumps({'flavour':'gemini','auth_directory':'gemini-work'}))
        home = self.profiles/'challenger/home'
        (home/'.gemini').mkdir()
        settings = home/'.gemini/settings.json'
        existing = {'hooks':{'BeforeAgent':[{'operator':'kept'}]},'security':{'auth':{'selectedType':'vertex-ai'}}}
        settings.write_text(json.dumps(existing))
        core.prepare_native_startup('challenger');core.prepare_native_startup('challenger')
        value = json.loads(settings.read_text())
        self.assertEqual(value['hooks']['BeforeAgent'],existing['hooks']['BeforeAgent'])
        self.assertEqual(len(value['hooks']['SessionStart']),1)
        command = shlex.split(value['hooks']['SessionStart'][0]['hooks'][0]['command'])
        self.assertEqual(command[-4:],['record-hook','gemini','gemini-work','challenger'])
        self.assertEqual(value['security'],existing['security'])
