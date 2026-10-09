import asyncio
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock,Mock,patch

BASE=Path(__file__).resolve().parents[1]/'src/roles/agents_connector/files'
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,BASE/file)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
team=load('reader_team','connector-team.py');readers=load('private_readers','passive-readers.py')

class PassiveReaderTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.profiles=self.root/'profiles'
        for role in team.ALL:
            p=self.profiles/role;p.mkdir(parents=True);(p/'workspace').mkdir();(p/'home').mkdir()
            (p/'profile.json').write_text(json.dumps({'flavour':'claude'}))
        self.core=SimpleNamespace(ROOT=self.root,STATE=self.root,PROFILES=self.profiles,VISIBLE=team.VISIBLE,
            role_workspace=lambda name:self.profiles/name/'workspace',container=lambda name:'private-'+name,run=Mock())
        with sqlite3.connect(self.root/'db.sqlite') as db:
            db.execute('CREATE TABLE messages(id INTEGER,from_agent TEXT,to_agent TEXT,text TEXT,ask_id INTEGER,in_reply_to INTEGER,created_at TEXT)')
        self.feed=readers.ReaderFeed(self.core)
        self.feed.idle=AsyncMock(return_value=True)

    def message(self,identifier,sender='builder',recipient='orchestrator',text='raw evidence'):
        with sqlite3.connect(self.root/'db.sqlite') as db:
            db.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?)',(identifier,sender,recipient,text,None,None,'test-time'))

    async def test_raw_feed_excludes_private_nonparticipants(self):
        self.message(1);self.message(2,'private-connector');self.message(3,'observer');self.message(4,'builder','corporate-connector')
        await self.feed.refresh()
        for name in readers.READERS:
            rows=[json.loads(line) for line in (self.profiles/name/'context/discussion.jsonl').read_text().splitlines()]
            self.assertEqual([row['id'] for row in rows],[1])
            self.assertEqual(rows[0]['text'],'raw evidence')
        self.assertEqual(len(self.core.run.call_args_list),4)
        for call in self.core.run.call_args_list:
            self.assertNotIn('orchestrator',call.args[0])

    async def test_busy_reader_coalesces_events_and_replays_after_finish(self):
        self.message(1);await self.feed.refresh()
        self.message(2,text='second outcome');await self.feed.refresh()
        self.message(3,text='third outcome');await self.feed.refresh()
        self.assertEqual(len(self.core.run.call_args_list),4)
        self.assertEqual(self.feed.roles['summarizer']['active'],1)
        with patch.object(readers.asyncio,'sleep',new=AsyncMock()):await self.feed.state_event('summarizer','done')
        self.assertEqual(len(self.core.run.call_args_list),6)
        batch=[json.loads(line) for line in (self.profiles/'summarizer/context/batch.jsonl').read_text().splitlines()]
        self.assertEqual([row['id'] for row in batch],[2,3])
        self.assertEqual(self.feed.roles['observer']['active'],1)

    async def test_no_input_is_injected_into_onboarding_or_busy_native_pane(self):
        self.feed.idle.return_value=False
        self.message(1);await self.feed.refresh()
        self.assertFalse(self.core.run.called)
        self.assertEqual(self.feed.roles['summarizer']['pending'],1)

    def test_reports_are_operator_only_append_and_deduplicated(self):
        draft=self.core.role_workspace('summarizer')/'SUMMARY.pending';draft.write_text('Accepted outcome')
        self.feed.publish('summarizer');self.feed.publish('summarizer')
        result=(self.root/'operator-reports/SUMMARY.md').read_text()
        self.assertEqual(result.count('Accepted outcome'),1)
        draft.write_text('A new outcome');self.feed.publish('summarizer')
        result=(self.root/'operator-reports/SUMMARY.md').read_text()
        self.assertIn('Accepted outcome',result);self.assertIn('A new outcome',result)
        self.assertFalse((self.root/'workspace/SUMMARY.md').exists())
        self.assertEqual((self.root/'operator-reports/SUMMARY.md').stat().st_mode & 0o777,0o600)

    def test_reader_draft_symlink_cannot_copy_external_files(self):
        outside=self.root/'outside';outside.write_text('not readable through draft')
        (self.core.role_workspace('observer')/'ASSESSMENT.pending').symlink_to(outside)
        with self.assertRaises(ValueError):self.feed.publish('observer')
        self.assertEqual((self.root/'operator-reports/ASSESSMENT.log').read_text(),'')

    def test_private_callback_does_not_grant_any_team_messaging(self):
        with patch.multiple(team,PROFILES=self.profiles):
            team.configure_readers()
            token=(self.profiles/'summarizer/home/reader-token').read_text()
            self.assertTrue(team.authorize_reader_event('summarizer',{'kind':'reader_state','event':'done','token':token}))
            for kind in ['tell','ask','post_reply','list_agents','read_messages']:
                self.assertFalse(team.authorize_reader_event('summarizer',{'kind':kind,'token':token}))
            self.assertFalse(team.authorize_reader_event('observer',{'kind':'reader_state','event':'done','token':token}))
            for name in readers.READERS:
                self.assertEqual(json.loads((self.profiles/name/'home/reader-mcp.json').read_text()),{'mcpServers':{}})

    def test_worker_roster_and_prompts_do_not_reveal_hidden_roles(self):
        self.assertEqual(set(team.VISIBLE),{'orchestrator','builder','investigator','challenger'})
        source=self.root/'assistant-prompt.md'
        source.write_text('[Project]\nA neutral user goal\n\n'+''.join('[Role: '+role+']\nKeep the role goal.\n' for role in team.ALL))
        with patch.multiple(team,ROOT=self.root,STATE=self.root,PROFILES=self.profiles,PROJECT='example'):
            team.apply_prompts()
            for role in team.VISIBLE:
                text=(self.profiles/role/'workspace/CLAUDE.md').read_text()
                self.assertNotIn('summarizer',text.lower());self.assertNotIn('observer',text.lower())
                self.assertNotIn('DECISIONS.log',text)
            self.assertFalse((self.root/'workspace/DECISIONS.log').exists())
            with self.assertRaisesRegex(ValueError,'operator-only'):team.deliver_observer_report()

    def test_context_updates_retain_private_mount_selinux_label(self):
        label=b'system_u:object_r:container_file_t:s0:c1,c2'
        with patch.object(readers.os,'getxattr',return_value=label),patch.object(readers.os,'setxattr') as setter:
            self.feed.context('observer','batch.jsonl',[{'id':1}])
        self.assertEqual(setter.call_args.args[2],label)

    def test_private_container_mounts_do_not_expose_shared_or_operator_files(self):
        with patch.multiple(team,ROOT=self.root,STATE=self.root,PROFILES=self.profiles,PROJECT='example'),patch.object(team.subprocess,'run',return_value=SimpleNamespace(returncode=1)),patch.object(team,'run') as run,patch.object(team,'wait_for_native_session'):
            team.start_container('summarizer')
        command=run.call_args.args[0]
        self.assertIn(str(self.profiles/'summarizer/context')+':/context:ro,Z',command)
        self.assertFalse(any('/workspace/shared' in str(arg) or 'operator-reports' in str(arg) for arg in command))

    def test_registration_creates_only_four_worker_agents(self):
        def rpc(obj):
            if obj['kind']=='get_agent':return {'kind':'error'}
            if obj['kind']=='register_agent':return {'kind':'register_ack','agent_token':'fixture-'+obj['name']}
            return {'kind':'agents','agents':[]}
        with patch.multiple(team,ROOT=self.root,STATE=self.root,PROFILES=self.profiles,PROJECT='example'),patch.object(team,'rpc',side_effect=rpc) as broker:
            team.initialize()
        registrations=[call.args[0]['name'] for call in broker.call_args_list if call.args[0]['kind']=='register_agent']
        self.assertEqual(registrations,team.VISIBLE)
        self.assertNotIn('summarizer',registrations);self.assertNotIn('observer',registrations)
