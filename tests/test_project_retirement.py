import importlib.util
import io
import contextlib
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE=Path(__file__).resolve().parents[1]/'src/roles/project_framework/files/project-team.py'


class ProjectRetirementTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.home=Path(temp.name)
        spec=importlib.util.spec_from_file_location('project_retirement',SOURCE)
        self.core=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.core)
        self.core.ACCOUNT_HOME=self.home;self.core.PROJECTS=self.home/'projects'
        self.project=self.fixture('example');self.other=self.fixture('other')
        self.config=self.home/'projects.example.config';self.config.write_text('fixture assignments')
        self.home.joinpath('projects.other.config').write_text('untouched')
        self.account=self.home/'codex-priv';self.account.mkdir();self.account.joinpath('state').write_text('untouched')

    def fixture(self,name):
        p=self.core.PROJECTS/name;p.mkdir(parents=True)
        for filename in ['initialized','db.sqlite','db.sqlite-wal','db.sqlite-shm','assistant-prompt.md']:
            (p/filename).write_text('fixture '+filename)
        (p/'workspace').mkdir();(p/'workspace/artifact').write_text('fixture artifact')
        return p

    def retire(self,archive=False):
        with patch.object(self.core,'quiesce_project') as stop,contextlib.redirect_stdout(io.StringIO()):
            self.core.retire_project('example',archive)
        return stop

    def test_destroy_removes_only_named_project_and_config(self):
        stop=self.retire()
        stop.assert_called_once_with('example',self.project)
        self.assertFalse(self.project.exists());self.assertFalse(self.config.exists())
        self.assertTrue(self.other.exists());self.assertTrue(self.account.joinpath('state').is_file())
        self.assertEqual(self.home.joinpath('projects.other.config').read_text(),'untouched')

    def test_archive_preserves_entire_project_and_external_config_privately(self):
        self.retire(True);destination=self.home/'project-archive/example'
        self.assertFalse(self.project.exists());self.assertFalse(self.config.exists())
        for filename in ['db.sqlite','db.sqlite-wal','db.sqlite-shm','assistant-prompt.md']:
            self.assertEqual((destination/filename).read_text(),'fixture '+filename)
        self.assertEqual((destination/'workspace/artifact').read_text(),'fixture artifact')
        self.assertEqual((destination/'projects.example.config').read_text(),'fixture assignments')
        self.assertEqual(destination.stat().st_mode&0o777,0o700)
        self.assertEqual(destination.parent.stat().st_mode&0o777,0o700)
        self.assertEqual((destination/'projects.example.config').stat().st_mode&0o777,0o600)
        self.assertTrue(self.other.exists());self.assertTrue(self.account.exists())

    def test_collision_and_symlink_preflight_never_stop_project(self):
        archive=self.home/'project-archive';archive.mkdir();(archive/'example').mkdir()
        with patch.object(self.core,'quiesce_project') as stop:
            with self.assertRaisesRegex(ValueError,'Archive already exists'):self.core.retire_project('example',True)
        stop.assert_not_called();self.assertTrue(self.project.exists());self.assertTrue(self.config.exists())
        (archive/'example').rmdir();(archive/'example').symlink_to(archive/'missing')
        with patch.object(self.core,'quiesce_project') as stop:
            with self.assertRaises(ValueError):self.core.retire_project('example',True)
        stop.assert_not_called()

    def test_invalid_names_and_config_symlink_fail_before_shutdown(self):
        with patch.object(self.core,'quiesce_project') as stop:
            for name in ['../other','*','UPPER','a/b','', 'x'*41]:
                with self.assertRaises(ValueError):self.core.retire_project(name)
            self.config.unlink();self.config.symlink_to(self.account/'state')
            with self.assertRaises(ValueError):self.core.retire_project('example')
        stop.assert_not_called();self.assertEqual(self.account.joinpath('state').read_text(),'untouched')

    def test_stop_failure_preserves_project_and_configuration(self):
        with patch.object(self.core,'quiesce_project',side_effect=subprocess.CalledProcessError(1,['systemctl'])):
            with self.assertRaises(subprocess.CalledProcessError):self.core.retire_project('example')
        self.assertTrue(self.project.exists());self.assertTrue(self.config.exists())

    def test_archive_move_failure_rolls_configuration_back(self):
        original=Path.rename
        def rename(path,target):
            if path==self.project:raise OSError('fixture move failure')
            return original(path,target)
        with patch.object(self.core,'quiesce_project'),patch.object(Path,'rename',rename):
            with self.assertRaises(OSError):self.core.retire_project('example',True)
        self.assertTrue(self.project.exists());self.assertEqual(self.config.read_text(),'fixture assignments')
        self.assertFalse(self.project.joinpath(self.config.name).exists())

    def test_archive_and_destroy_never_follow_internal_links(self):
        link=self.project/'workspace/external';link.symlink_to(self.account,target_is_directory=True)
        self.retire(True);archived=self.home/'project-archive/example/workspace/external'
        self.assertTrue(archived.is_symlink());self.assertTrue(self.account.joinpath('state').is_file())
        self.project=self.fixture('example');self.config.write_text('fixture assignments')
        self.project.joinpath('workspace/external').symlink_to(self.account,target_is_directory=True)
        self.retire();self.assertEqual(self.account.joinpath('state').read_text(),'untouched')

    def test_inactive_services_and_absent_containers_do_not_stop_anything(self):
        state={'ActiveState':'inactive','LoadState':'loaded','UnitFileState':'disabled'}
        with patch.object(self.core,'service_state',return_value=state), \
                patch.object(self.core,'project_container_state',return_value=None), \
                patch.object(self.core.subprocess,'run') as run:
            self.core.quiesce_project('example',self.project)
        run.assert_not_called()

    def test_orphan_service_and_container_are_stopped_with_exact_names(self):
        calls=[]
        def service(unit):
            active=unit=='assistant-connector-broker@example.service' and not calls
            return {'ActiveState':'active' if active else 'inactive','LoadState':'loaded','UnitFileState':'disabled'}
        checks={role:0 for role in self.core.ROLES}
        def container(name,role):
            checks[role]+=1
            return role=='builder' and checks[role]==1
        with patch.object(self.core,'service_state',side_effect=service), \
                patch.object(self.core,'project_container_state',side_effect=container), \
                patch.object(self.core.subprocess,'run',side_effect=lambda args,**kwargs:calls.append(args)):
            self.core.quiesce_project('example',self.project)
        self.assertEqual(calls[0],['systemctl','--user','stop','assistant-connector-broker@example.service'])
        self.assertEqual(calls[1],['podman','stop','--time','10','acp-example-builder'])
        self.assertEqual(calls[2],['podman','rm',*['acp-example-'+role for role in self.core.ROLES]])
        self.assertFalse(any('other' in arg for call in calls for arg in call))

    def test_bus_and_podman_errors_are_not_inactive(self):
        with patch.object(self.core.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','bus unavailable')):
            with self.assertRaises(ValueError):self.core.service_state('unit')
        with patch.object(self.core.subprocess,'run',return_value=subprocess.CompletedProcess([],125)):
            with self.assertRaises(ValueError):self.core.project_container_state('example','builder')

    def test_live_project_socket_blocks_cleanup(self):
        listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.addCleanup(listener.close);listener.bind(str(self.project/'broker.sock'));listener.listen(1)
        with self.assertRaisesRegex(ValueError,'still listening'):
            self.core.verify_no_project_listener(self.project)

    def test_embedded_configuration_collision_does_not_stop_or_overwrite(self):
        embedded=self.project/self.config.name;embedded.write_text('existing project content')
        with patch.object(self.core,'quiesce_project') as stop:
            with self.assertRaisesRegex(ValueError,'configuration destination already exists'):
                self.core.retire_project('example',True)
        stop.assert_not_called();self.assertEqual(embedded.read_text(),'existing project content')

    def test_service_remaining_active_prevents_container_removal(self):
        state={'ActiveState':'active','LoadState':'loaded','UnitFileState':'disabled'}
        with patch.object(self.core,'service_state',return_value=state), \
                patch.object(self.core,'project_container_state',return_value=None), \
                patch.object(self.core.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'services did not stop'):
                self.core.quiesce_project('example',self.project)
        self.assertEqual(run.call_count,1)
        self.assertEqual(run.call_args.args[0][:3],['systemctl','--user','stop'])
        self.assertTrue(self.project.exists());self.assertTrue(self.config.exists())

    def test_enabled_named_target_is_disabled_without_touching_shared_template(self):
        def service(unit):
            return {'ActiveState':'inactive','LoadState':'loaded',
                    'UnitFileState':'enabled' if unit.endswith('.target') else 'static'}
        with patch.object(self.core,'service_state',side_effect=service), \
                patch.object(self.core,'project_container_state',return_value=None), \
                patch.object(self.core.subprocess,'run') as run:
            self.core.quiesce_project('example',self.project)
        self.assertEqual(run.call_args.args[0],['systemctl','--user','disable','assistant-connector@example.target'])

    def test_project_parent_symlink_is_rejected_before_shutdown(self):
        alternate=self.home/'alternate';self.core.PROJECTS.rename(alternate)
        self.core.PROJECTS.symlink_to(alternate,target_is_directory=True)
        with patch.object(self.core,'quiesce_project') as stop:
            with self.assertRaises(ValueError):self.core.retire_project('example')
        stop.assert_not_called()
