import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock

BASE = pathlib.Path(__file__).parents[1]/'src/roles/agents_connector/files'

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, BASE/file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

hook = load('antigravity_hook', 'antigravity-hook.py')
team = load('antigravity_team', 'connector-team.py')

class AntigravityHookTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.cursor=pathlib.Path(temporary.name)/'state/cursor'
        self.messages=[{'id':2,'from':'orchestrator','text':'readiness','ask_id':7}]

    def invoke(self,event,body,messages):
        frames=[]
        def rpc(_,request):
            frames.append(request)
            if request['kind']=='authenticate':return {'kind':'agent_info','name':'challenger'}
            if request['kind']=='read_messages':return {'kind':'messages','messages':messages}
            return {'kind':'ok'}
        with mock.patch.object(hook,'frame',side_effect=rpc):
            output=hook.handle(event,body,None,'fixture-token',self.cursor)
        return output,frames

    def test_preinvocation_injects_addressed_context_and_advances_cursor(self):
        output,frames=self.invoke('PreInvocation',{},self.messages)
        self.assertIn('ASK ask_id=7',output['injectSteps'][0]['ephemeralMessage'])
        self.assertEqual(self.cursor.read_text(),'2')
        self.assertEqual(self.cursor.stat().st_mode&0o777,0o600)
        self.assertEqual(frames[1]['state'],'busy')
        _,frames=self.invoke('PreInvocation',{},[])
        self.assertEqual(frames[2]['since'],2)

    def test_partial_stop_keeps_busy_and_does_not_consume_messages(self):
        output,frames=self.invoke('Stop',{'fullyIdle':False},self.messages)
        self.assertEqual(output,{})
        self.assertEqual(frames[1]['state'],'busy')
        self.assertEqual(len(frames),2)
        self.assertFalse(self.cursor.exists())

    def test_idle_stop_with_new_message_continues_scoped_turn(self):
        output,frames=self.invoke('Stop',{'fullyIdle':True},self.messages)
        self.assertEqual(output['decision'],'continue')
        self.assertIn('readiness',output['reason'])
        self.assertEqual(frames[-1]['state'],'busy')

    def test_idle_stop_without_context_allows_native_stop(self):
        output,frames=self.invoke('Stop',{'fullyIdle':True},[])
        self.assertEqual(output,{})
        self.assertEqual(frames[1]['state'],'idle')

    def test_auth_failure_never_reads_another_inbox(self):
        with mock.patch.object(hook,'frame',return_value={'kind':'error'}) as rpc:
            with self.assertRaisesRegex(ValueError,'authentication'):
                hook.handle('PreInvocation',{},None,'fixture',self.cursor)
        self.assertEqual(rpc.call_count,1)

class AntigravityProviderTests(unittest.TestCase):
    def test_pinned_provider_seed_preserves_role_refresh_and_excludes_vertex(self):
        with tempfile.TemporaryDirectory() as temporary:
            home=pathlib.Path(temporary);profiles=home/'project/profiles'
            source=home/'gemini-priv';binary=source/'.install/antigravity/1.3.1/antigravity'
            binary.parent.mkdir(parents=True);binary.write_text('fixture-binary')
            (source/'.native-install.json').write_text(json.dumps({'provider':'antigravity','version':'1.3.1','entrypoint':'antigravity/1.3.1/antigravity'}))
            relative=pathlib.Path('.gemini/antigravity-cli/antigravity-oauth-token')
            credential=source/relative;credential.parent.mkdir(parents=True);credential.write_text('private-fixture')
            (source/'.vertex.json').write_text('forbidden-fixture')
            profile=profiles/'challenger';(profile/'home').mkdir(parents=True)
            (profile/'profile.json').write_text(json.dumps({'flavour':'gemini','auth_directory':'gemini-priv'}))
            with mock.patch.multiple(team,ACCOUNT_HOME=home,PROFILES=profiles,ROOT=home/'project',PROJECT='fixture'):
                self.assertEqual(team.antigravity_executable('challenger'),binary)
                team.seed_auth('challenger')
                target=profile/'home'/relative
                self.assertEqual(target.read_text(),'private-fixture')
                target.write_text('refreshed-fixture');team.seed_auth('challenger')
                self.assertEqual(target.read_text(),'refreshed-fixture')
                self.assertFalse((profile/'home/.vertex.json').exists())
                self.assertFalse((profile/'home/.gemini/oauth_creds.json').exists())
                meta=json.loads((source/'.native-install.json').read_text());meta['version']='new-unknown'
                (source/'.native-install.json').write_text(json.dumps(meta))
                with self.assertRaisesRegex(ValueError,'pinned'):
                    team.antigravity_executable('challenger')
