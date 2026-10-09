import contextlib
import datetime
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

BASE=Path(__file__).resolve().parents[1]
FRAMEWORK=BASE/'src/roles/project_framework/files/project-team.py'
HELPER=BASE/'src/roles/project_framework/files/unarchive-project.py'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class UnarchiveTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.home=Path(temp.name)
        self.framework=load('unarchive_framework',FRAMEWORK)
        self.framework.ACCOUNT_HOME=self.home;self.framework.PROJECTS=self.home/'projects'
        self.helper=load('unarchive_helper',HELPER)
        settings=load('unarchive_settings',BASE/'src/roles/project_framework/files/environment-config.py')
        self.framework.settings=lambda:settings
        self.name='sample-0910260800';self.archive=self.home/'project-archive'/self.name;self.archive.mkdir(parents=True)
        self.config={'version':1,'project':'sample','roles':{role:'claude-work' for role in self.framework.ROLES}}
        (self.archive/'projects.sample.config').write_text(json.dumps(self.config))
        (self.archive/'.assistant-archive.json').write_text(json.dumps({'version':1,'archived_at':'2026-10-09T08:00:00+00:00','timestamp_basis':'operation_start'}))
        (self.archive/'initialized').touch();(self.archive/'assistant-prompt.md').write_text('PRIVATE CUSTOM GOAL')
        with sqlite3.connect(self.archive/'db.sqlite') as db:db.execute('CREATE TABLE messages (text TEXT)');db.execute('INSERT INTO messages VALUES (?)',('PRESERVE CONVERSATION',));db.execute('CREATE TABLE agents (name TEXT)');db.execute('CREATE TABLE asks (text TEXT)');db.execute('CREATE TABLE replies (text TEXT)')
        (self.archive/'workspace').mkdir();(self.archive/'workspace/artifact').write_text('USER DATA')
        for role in self.framework.ROLES:
            profile=self.archive/'profiles'/role;profile.mkdir(parents=True)
            (profile/'profile.json').write_text(json.dumps({'flavour':'claude'}))
            (profile/'workspace').mkdir();(profile/'workspace/CLAUDE.md').write_text('OLD GENERATED')
            (profile/'launched').touch()
        self.framework.loaded_project_units=lambda name:[]
        self.framework.project_container_state=lambda name,role:None
        def core(name):
            def render():
                for role in self.framework.ROLES:(self.home/'projects'/name/'profiles'/role/'workspace/CLAUDE.md').write_text('NEW '+name)
            return types.SimpleNamespace(apply_prompts=render)
        self.framework.load=core
        enabled={'value':False}
        def run(args,**kwargs):
            if 'enable' in args:
                self.assertEqual(args[-1],'assistant-connector@'+self.name+'.target')
                enabled['value']=True
            if 'disable' in args:enabled['value']=False
            if 'is-enabled' in args:return subprocess.CompletedProcess(args,0 if enabled['value'] else 1,'enabled\n' if enabled['value'] else 'disabled\n','')
            return subprocess.CompletedProcess(args,0,'','')
        self.run=run

    def restore(self):
        with patch.object(self.helper.subprocess,'run',side_effect=self.run),contextlib.redirect_stdout(io.StringIO()) as output:
            name=self.helper.restore(self.framework,self.name)
        return name,output.getvalue()

    def test_copy_retains_archive_and_rebases_only_generated_identity(self):
        before={str(p.relative_to(self.archive)):p.read_bytes() for p in self.archive.rglob('*') if p.is_file()}
        name,output=self.restore();destination=self.home/'projects'/name
        self.assertIn('Archive retained unchanged',output)
        self.assertTrue(self.archive.exists())
        self.assertEqual(before,{str(p.relative_to(self.archive)):p.read_bytes() for p in self.archive.rglob('*') if p.is_file()})
        self.assertEqual((destination/'assistant-prompt.md').read_text(),'PRIVATE CUSTOM GOAL')
        self.assertEqual((destination/'workspace/artifact').read_text(),'USER DATA')
        self.assertFalse((destination/'.assistant-archive.json').exists())
        self.assertFalse((destination/'projects.sample.config').exists())
        self.assertEqual(json.loads((self.home/('projects.'+name+'.config')).read_text())['project'],name)
        for role in self.framework.ROLES:
            self.assertFalse((destination/'profiles'/role/'launched').exists())
            self.assertIn(name,(destination/'profiles'/role/'workspace/CLAUDE.md').read_text())
        self.assertEqual(destination.stat().st_mode&0o777,0o700)
        self.assertEqual((self.home/('projects.'+name+'.config')).stat().st_mode&0o777,0o600)
        with sqlite3.connect(destination/'db.sqlite') as db:self.assertEqual(db.execute('SELECT text FROM messages').fetchone()[0],'PRESERVE CONVERSATION')

    def test_legacy_plain_archive_gets_recorded_timestamp_name(self):
        plain=self.archive.with_name('sample');self.archive.rename(plain);self.archive=plain;self.name='sample'
        name,_=self.restore();self.assertEqual(name,'sample-0910260800');self.assertTrue(plain.exists())

    def test_conflict_or_symlink_fails_without_copy_or_enable(self):
        self.home.joinpath('projects').mkdir();self.home.joinpath('projects',self.name).mkdir()
        with patch.object(self.helper.subprocess,'run') as run:
            with self.assertRaises(ValueError):self.helper.restore(self.framework,self.name)
        run.assert_not_called()
        self.home.joinpath('projects',self.name).rmdir();(self.archive/'workspace/link').symlink_to('/outside/private')
        with patch.object(self.helper.subprocess,'run') as run:
            with self.assertRaises(ValueError):self.helper.restore(self.framework,self.name)
        run.assert_not_called();self.assertTrue(self.archive.exists())

    def test_relative_native_file_and_directory_links_are_preserved_without_following(self):
        native=self.archive/'profiles/builder/home/native'
        native.mkdir(parents=True);(native/'cache').mkdir();(native/'cache/state').write_text('fixture state')
        (native/'state-link').symlink_to('cache/state')
        (native/'cache-link').symlink_to('cache',target_is_directory=True)
        before=(native/'cache/state').read_bytes()
        name,_=self.restore();restored=self.home/'projects'/name/'profiles/builder/home/native'
        self.assertTrue((restored/'state-link').is_symlink())
        self.assertTrue((restored/'cache-link').is_symlink())
        self.assertEqual((restored/'state-link').read_bytes(),before)
        self.assertEqual((native/'cache/state').read_bytes(),before)

    def test_escaping_absolute_dangling_and_cyclic_links_fail_before_copy_or_enable(self):
        for target in ['../../outside','/outside/private','missing','link']:
            with self.subTest(target=target):
                link=self.archive/'workspace/link';link.symlink_to(target)
                with patch.object(self.helper.subprocess,'run') as run:
                    with self.assertRaises(ValueError):self.helper.restore(self.framework,self.name)
                run.assert_not_called();self.assertTrue(self.archive.exists())
                self.assertFalse((self.home/'projects').exists());link.unlink()

    def test_codex_cache_rewrites_only_own_current_and_omits_regenerated_state(self):
        profile=self.archive/'profiles/builder';(profile/'profile.json').write_text('{"flavour":"codex"}')
        home=profile/'accounts/codex-priv/home';cache=home/'.codex/packages/app-server-daemon'
        release=cache/'releases/fixture-release';release.mkdir(parents=True)
        (release/'real-codex').write_text('fixture executable');(release/'codex').symlink_to('real-codex')
        (cache/'current').symlink_to('/home/agent/.codex/packages/app-server-daemon/releases/fixture-release')
        arg0=home/'.codex/tmp/arg0';arg0.mkdir(parents=True);(arg0/'apply_patch').symlink_to('/container-only/tool')
        control=home/'.codex/app-server-control';control.mkdir();(control/'control.sock').symlink_to('/container-only/socket')
        before={str(p.relative_to(self.archive)):os.readlink(p) for p in self.archive.rglob('*') if p.is_symlink()}
        name,_=self.restore();restored=self.home/'projects'/name/home.relative_to(self.archive)
        current=restored/'.codex/packages/app-server-daemon/current'
        self.assertEqual(os.readlink(current),'releases/fixture-release')
        self.assertTrue(current.resolve().is_relative_to(restored))
        self.assertEqual((current/'codex').read_text(),'fixture executable')
        self.assertFalse((restored/'.codex/tmp/arg0').exists());self.assertFalse((restored/'.codex/app-server-control').exists())
        self.assertEqual(before,{str(p.relative_to(self.archive)):os.readlink(p) for p in self.archive.rglob('*') if p.is_symlink()})

    def test_codex_current_cannot_map_to_credentials_or_other_homes(self):
        profile=self.archive/'profiles/builder';(profile/'profile.json').write_text('{"flavour":"codex"}')
        home=profile/'accounts/codex-priv/home';cache=home/'.codex/packages/app-server-daemon';cache.mkdir(parents=True)
        (home/'private').mkdir();(home/'private/auth.json').write_text('fixture credentials')
        (cache/'current').symlink_to('/home/agent/private')
        with patch.object(self.helper.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'own retained release cache'):self.helper.restore(self.framework,self.name)
        run.assert_not_called();self.assertFalse((self.home/'projects').exists())

    def test_enable_failure_rolls_back_new_files_and_keeps_archive(self):
        commands=[]
        def run(args,**kwargs):
            commands.append(args)
            if 'enable' in args:raise subprocess.CalledProcessError(1,args)
            return self.run(args,**kwargs)
        with patch.object(self.helper.subprocess,'run',side_effect=run):
            with self.assertRaises(subprocess.CalledProcessError):self.helper.restore(self.framework,self.name)
        self.assertTrue(self.archive.exists());self.assertFalse(self.home.joinpath('projects',self.name).exists())
        self.assertFalse(self.home.joinpath('projects.'+self.name+'.config').exists())
        self.assertTrue(any('disable' in cmd for cmd in commands));self.assertFalse(any('start' in cmd for cmd in commands))

    def test_mismatched_identity_and_loaded_units_refuse_before_changes(self):
        self.config['project']='different';(self.archive/'projects.sample.config').write_text(json.dumps(self.config))
        with self.assertRaises(ValueError):self.restore()
        self.config['project']='sample';(self.archive/'projects.sample.config').write_text(json.dumps(self.config))
        self.framework.loaded_project_units=lambda name:['existing']
        with self.assertRaises(ValueError):self.restore()
        self.assertTrue(self.archive.exists())

    def test_malformed_database_is_rejected_before_destination_creation(self):
        (self.archive/'db.sqlite').write_text('NOT A DATABASE')
        with self.assertRaisesRegex(ValueError,'database is invalid'):self.restore()
        self.assertFalse(self.home.joinpath('projects',self.name).exists())
        self.assertEqual((self.archive/'db.sqlite').read_text(),'NOT A DATABASE')

    def test_restored_archive_identity_requires_rename_before_rearchive(self):
        name,_=self.restore()
        with self.assertRaisesRegex(ValueError,'rename-project'):
            self.framework.lifecycle_paths(name,archive=True)
        self.assertTrue(self.archive.exists())
        self.assertTrue(self.home.joinpath('projects',name).exists())
