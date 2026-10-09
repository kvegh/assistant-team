import contextlib
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

SOURCE=Path(__file__).resolve().parents[1]/'src/roles/project_framework/files/project-rename.py'


class RenameProjectTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.home=Path(temp.name)
        spec=importlib.util.spec_from_file_location('rename_test',SOURCE)
        self.rename=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.rename)
        self.roles=['orchestrator','builder','investigator','challenger','summarizer','observer','private-connector','corporate-connector']
        self.path=self.home/'projects/old';self.path.mkdir(parents=True)
        (self.path/'initialized').touch();(self.path/'workspace').mkdir()
        (self.path/'workspace/artifact').write_text('old user text remains old')
        (self.path/'assistant-prompt.md').write_text('old original editable prompt')
        (self.path/'db.sqlite').write_bytes(b'old conversation unchanged')
        self.rendered=self.path/'profiles/builder/workspace/AGENTS.md';self.rendered.parent.mkdir(parents=True)
        self.rendered.write_text('generated old identity')
        (self.path/'profiles/builder/launched').touch()
        self.config=self.path/'project.old.config'
        self.original=json.dumps({'version':1,'project':'old','roles':dict.fromkeys(self.roles,'codex-priv')})
        self.config.write_text(self.original)
        self.calls=[]
        def project_path(name):
            if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,50}',name):raise ValueError('Invalid project name')
            return self.home/'projects'/name
        self.framework=types.SimpleNamespace(ACCOUNT_HOME=self.home,ROLES=self.roles,project_path=project_path,
            paths=lambda root:types.SimpleNamespace(project_config=lambda name:project_path(name)/('project.'+name+'.config')),
            lifecycle_paths=lambda name:(project_path(name),project_path(name)/('project.'+name+'.config'),None),
            loaded_project_units=lambda name:[],project_container_state=lambda name,role:None,
            service_state=lambda unit:{'UnitFileState':'enabled'},user_env=lambda:{},
            quiesce_project=lambda name,path:self.calls.append(('stop',name)),
            forget_project_units=lambda name:self.calls.append(('forget',name)))
        def snapshot(framework,path):return [(self.rendered,self.rendered.read_bytes())]
        def restore(records):
            for path,data in records:path.write_bytes(data)
        def rebase(framework,name,old_name=None):
            config=project_path(name)/('project.'+name+'.config');data=json.loads(config.read_text());data['project']=name
            config.write_text(json.dumps(data));(project_path(name)/self.rendered.relative_to(self.path)).write_text('generated '+name+' identity')
        self.helper=types.SimpleNamespace(snapshot_rendered=snapshot,restore_rendered=restore,rebase=rebase)

    def run_rename(self,new='new'):
        def command(args,**kwargs):self.calls.append(tuple(args));return subprocess.CompletedProcess(args,0)
        with patch.object(self.rename,'identity_helper',return_value=self.helper), \
                patch.object(self.rename.subprocess,'run',side_effect=command),contextlib.redirect_stdout(io.StringIO()):
            self.rename.rename_project(self.framework,'old',new)

    def test_rename_preserves_user_content_and_rebases_only_generated_identity(self):
        self.run_rename();new=self.home/'projects/new'
        self.assertFalse(self.path.exists());self.assertFalse(self.config.exists())
        self.assertEqual(json.loads((new/'project.new.config').read_text())['project'],'new')
        self.assertEqual((new/'workspace/artifact').read_text(),'old user text remains old')
        self.assertEqual((new/'assistant-prompt.md').read_text(),'old original editable prompt')
        self.assertEqual((new/'db.sqlite').read_bytes(),b'old conversation unchanged')
        self.assertEqual((new/'profiles/builder/workspace/AGENTS.md').read_text(),'generated new identity')
        self.assertFalse((new/'profiles/builder/launched').exists())
        self.assertIn(('stop','old'),self.calls);self.assertIn(('forget','old'),self.calls)
        self.assertIn(('systemctl','--user','enable','assistant-connector@new.target'),self.calls)
        self.assertFalse(any('start' in command for command in self.calls))

    def test_existing_new_project_config_or_units_do_not_stop_old(self):
        destination=self.home/'projects/new';destination.mkdir()
        with self.assertRaises(ValueError):self.run_rename()
        destination.rmdir()
        self.framework.loaded_project_units=lambda name:['assistant-connector@new.target']
        with self.assertRaises(ValueError):self.run_rename()
        self.assertEqual(self.calls,[])

    def test_container_conflict_and_long_socket_path_do_not_stop_old(self):
        self.framework.project_container_state=lambda name,role:False if role=='builder' else None
        with self.assertRaises(ValueError):self.run_rename()
        self.framework.project_container_state=lambda name,role:None
        with self.assertRaisesRegex(ValueError,'socket path'):self.run_rename('a'*51)
        self.assertEqual(self.calls,[])

    def test_runtime_enablement_is_preserved_and_disabled_target_not_enabled(self):
        self.framework.service_state=lambda unit:{'UnitFileState':'enabled-runtime'}
        self.run_rename()
        self.assertIn(('systemctl','--user','enable','--runtime','assistant-connector@new.target'),self.calls)

    def test_disabled_target_remains_disabled(self):
        self.framework.service_state=lambda unit:{'UnitFileState':'disabled'}
        self.run_rename()
        self.assertFalse(any('enable' in command for command in self.calls))

    def test_real_shared_identity_helper_rebases_generated_files_only(self):
        spec=importlib.util.spec_from_file_location('real_identity',SOURCE.with_name('project-identity.py'))
        identity=importlib.util.module_from_spec(spec);spec.loader.exec_module(identity)
        for role in self.roles:
            profile=self.path/'profiles'/role;profile.mkdir(exist_ok=True)
            (profile/'workspace').mkdir(exist_ok=True)
            (profile/'profile.json').write_text(json.dumps({'flavour':'codex'}))
        def atomic(path,data):path.write_text(json.dumps(data))
        self.framework.settings=lambda:types.SimpleNamespace(PROFILES={'codex-priv':{}},atomic=atomic)
        def load(name):
            def apply():
                for role in self.roles:
                    (self.home/'projects'/name/'profiles'/role/'workspace/AGENTS.md').write_text('generated '+name)
            return types.SimpleNamespace(apply_prompts=apply)
        self.framework.load=load;self.helper=identity
        self.run_rename()
        self.assertEqual((self.home/'projects/new/profiles/builder/workspace/AGENTS.md').read_text(),'generated new')
        self.assertEqual((self.home/'projects/new/assistant-prompt.md').read_text(),'old original editable prompt')

    def test_rebase_failure_restores_exact_config_and_rendered_instructions(self):
        original_rebase=self.helper.rebase
        def rebase(*args,**kwargs):original_rebase(*args,**kwargs);raise ValueError('fixture render failure')
        self.helper.rebase=rebase
        with self.assertRaisesRegex(ValueError,'render failure'):self.run_rename()
        self.assertTrue(self.path.exists());self.assertFalse((self.home/'projects/new').exists())
        self.assertEqual(self.config.read_text(),self.original)
        self.assertEqual(self.rendered.read_text(),'generated old identity')
        self.assertTrue((self.path/'profiles/builder/launched').exists())

    def test_unexpected_renderer_failure_or_interrupt_rolls_back_identity(self):
        for error in [RuntimeError('fixture unexpected error'),KeyboardInterrupt()]:
            with self.subTest(error=type(error).__name__):
                original_rebase=self.helper.rebase
                def fail(*args,**kwargs):
                    original_rebase(*args,**kwargs)
                    raise error
                self.helper.rebase=fail
                with self.assertRaisesRegex(ValueError,'identity was restored'):self.run_rename()
                self.assertTrue(self.path.exists());self.assertEqual(self.config.read_text(),self.original)
                self.assertEqual(self.rendered.read_text(),'generated old identity')
                self.helper.rebase=original_rebase

    def test_config_move_failure_rolls_directory_back(self):
        original_rename=Path.rename
        def rename(path,target):
            if path.name=='project.old.config':raise OSError('fixture config move')
            return original_rename(path,target)
        with patch.object(Path,'rename',rename),self.assertRaisesRegex(OSError,'config move'):self.run_rename()
        self.assertTrue(self.path.exists());self.assertEqual(self.config.read_text(),self.original)

    def test_new_enable_failure_restores_state_and_old_enablement(self):
        def command(args,**kwargs):
            self.calls.append(tuple(args))
            if args==['systemctl','--user','enable','assistant-connector@new.target']:
                raise subprocess.CalledProcessError(1,args)
            return subprocess.CompletedProcess(args,0)
        with patch.object(self.rename,'identity_helper',return_value=self.helper), \
                patch.object(self.rename.subprocess,'run',side_effect=command), \
                self.assertRaises(subprocess.CalledProcessError):
            self.rename.rename_project(self.framework,'old','new')
        self.assertEqual(self.config.read_text(),self.original);self.assertTrue(self.path.exists())
        self.assertTrue((self.path/'profiles/builder/launched').exists())
        self.assertIn(('systemctl','--user','disable','assistant-connector@new.target'),self.calls)
        self.assertIn(('systemctl','--user','enable','assistant-connector@old.target'),self.calls)

    def test_same_or_invalid_name_preserves_old(self):
        for new in ['old','../other','UPPER']:
            with self.subTest(new=new),self.assertRaises(ValueError):self.run_rename(new)
        self.assertEqual(self.calls,[])


if __name__=='__main__':unittest.main()
