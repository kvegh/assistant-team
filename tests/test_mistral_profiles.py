"""Mistral account isolation, preflight and native launch integration."""
import importlib.util
import json
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
core=load('mistral_profile_core','src/roles/agents_connector/files/connector-team.py')
project=load('mistral_profile_project','src/roles/project_framework/files/project-team.py')


class MistralProfileTests(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        self.home=Path(directory.name);self.profiles=self.home/'projects/example/profiles'
        context=patch.multiple(core,ACCOUNT_HOME=self.home,PROFILES=self.profiles,PROJECT='example')
        context.start();self.addCleanup(context.stop)
        context=patch.multiple(project,ACCOUNT_HOME=self.home)
        context.start();self.addCleanup(context.stop)
        for role in project.ROLES:
            path=self.profiles/role
            (path/'home/.codex').mkdir(parents=True)
            (path/'home/.codex/auth.json').write_text(json.dumps({'auth_mode':'chatgpt','tokens':{'access_token':'test-only'}}))
            (path/'profile.json').write_text(json.dumps({'flavour':'codex','auth_directory':'codex-priv'}))
        self.configure('mistral-priv')

    def configure(self,account):
        (self.profiles/'builder/profile.json').write_text(json.dumps({'flavour':'mistral','auth_directory':account}))

    def credential(self,account,value='test-only'):
        path=self.home/'model-environments'/account/'.vibe/.env'
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text('MISTRAL_API_KEY='+value+'\n');path.chmod(0o600)
        return path

    def preflight(self):
        with patch.object(project,'configure_roles'),patch.object(project,'load',return_value=core):
            return project.required_auth('example')

    def test_work_auth_never_falls_back_to_private(self):
        self.credential('mistral-priv');self.configure('mistral-work')
        with self.assertRaisesRegex(ValueError,'mistral-work'):self.preflight()
        self.credential('mistral-work');self.assertIs(self.preflight(),core)

    def test_empty_native_key_does_not_pass_auth_preflight(self):
        self.credential('mistral-priv','""')
        with self.assertRaisesRegex(ValueError,'mistral-priv'):self.preflight()

    def test_seeding_copies_only_selected_account_and_retains_existing_role_auth(self):
        self.credential('mistral-priv','private-test-only')
        self.credential('mistral-work','work-test-only');self.configure('mistral-work')
        core.seed_auth('builder')
        target=core.role_home('builder')/'.vibe/.env'
        self.assertEqual(target.read_text(),'MISTRAL_API_KEY=work-test-only\n')
        self.assertEqual(target.stat().st_mode&0o777,0o600)
        target.write_text('MISTRAL_API_KEY=role-refreshed-test-only\n')
        core.seed_auth('builder')
        self.assertIn('role-refreshed-test-only',target.read_text())

    def test_seeding_refuses_credential_symlink(self):
        source=self.credential('mistral-priv')
        target=core.role_home('builder')/'.vibe/.env'
        target.parent.mkdir();target.symlink_to(source)
        with self.assertRaises(ValueError):core.seed_auth('builder')

    def test_native_vibe_launch_keeps_approvals_and_exact_resume(self):
        with patch.object(core,'seed_auth'),patch.object(core,'prepare_native_startup'),patch.object(core,'start_container'),patch.object(core,'apply_prompts'),patch.object(core,'session_arguments',return_value=['--resume','saved-test-session']),patch.object(core,'token',return_value='test-only'),patch.object(core,'rpc',return_value={'kind':'ok'}) as broker,patch.object(core,'run') as execute:
            core.launch('builder')
        command=shlex.split(execute.call_args.args[0][-1])
        self.assertEqual(command[-3:],['vibe','--resume','saved-test-session'])
        self.assertIn('VIBE_HOME=/home/agent/.vibe',command)
        self.assertNotIn('--auto-approve',command)
        broker.assert_called_once_with({'kind':'set_agent_state','agent_token':'test-only','state':'idle'})

    def test_status_reports_native_mistral_account_and_selected_model(self):
        path=core.role_home('builder')/'.vibe/config.toml'
        path.parent.mkdir();path.write_text('active_model = "test-model"\n')
        self.assertEqual(project.role_model_metadata(core,'builder'),('mistral-priv','test-model (configured)'))

    def test_stopped_type_change_preserves_broker_token_and_message_history(self):
        import sqlite3
        database=self.profiles.parent/'db.sqlite'
        with sqlite3.connect(database) as db:
            db.execute('CREATE TABLE agents(name TEXT,cli_kind TEXT,token TEXT,removed_at TEXT)')
            db.execute("INSERT INTO agents VALUES('builder','codex','test-only',NULL)")
            db.execute('CREATE TABLE messages(text TEXT)')
            db.execute("INSERT INTO messages VALUES('retained fixture')")
        with patch.object(project,'verify_no_project_listener'),patch.object(project,'container_phase',return_value='exited'):
            project.reconcile_broker_types(self.profiles.parent,{'builder':'mistral'})
        with sqlite3.connect(database) as db:
            self.assertEqual(db.execute('SELECT cli_kind,token FROM agents').fetchone(),('mistral','test-only'))
            self.assertEqual(db.execute('SELECT text FROM messages').fetchone(),('retained fixture',))

    def test_live_type_change_never_edits_broker_metadata(self):
        import sqlite3
        database=self.profiles.parent/'db.sqlite'
        with sqlite3.connect(database) as db:
            db.execute('CREATE TABLE agents(name TEXT,cli_kind TEXT,token TEXT,removed_at TEXT)')
            db.execute("INSERT INTO agents VALUES('builder','codex','test-only',NULL)")
        with patch.object(project,'verify_no_project_listener'),patch.object(project,'container_phase',return_value='running'):
            with self.assertRaisesRegex(ValueError,'Stop the project'):
                project.reconcile_broker_types(self.profiles.parent,{'builder':'mistral'})
        with sqlite3.connect(database) as db:
            self.assertEqual(db.execute('SELECT cli_kind FROM agents').fetchone(),('codex',))
