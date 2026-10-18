import importlib.util
import pathlib
import subprocess
import unittest
from unittest.mock import Mock, patch

SOURCE = pathlib.Path(__file__).parents[1]/'src/roles/project_framework/files/project-team.py'
spec = importlib.util.spec_from_file_location('project_control_test',SOURCE)
team = importlib.util.module_from_spec(spec)
spec.loader.exec_module(team)


class ProjectControlTests(unittest.TestCase):
    def test_stop_blocks_on_all_exact_units_before_container_verification(self):
        events=[]
        with patch.object(team,'control_command',side_effect=lambda cmd,deadline:events.append(cmd)), patch.object(team,'container_phase',return_value='exited'), patch.object(team,'wait_project_stopped',side_effect=lambda *args:events.append('verified')):
            team.control('stop','fixture')
        self.assertEqual(events,[['systemctl','--user','stop',*team.project_units('fixture')],'verified'])

    def test_orphan_container_is_stopped_without_removal_or_disabling(self):
        with patch.object(team,'load') as load, patch.object(team,'control_command') as command, patch.object(team,'container_phase',side_effect=lambda name,role:'running' if role=='builder' else 'absent'), patch.object(team,'wait_project_stopped'):
            team.control('stop','fixture')
        load.return_value.capture_sessions.assert_called_once_with()
        self.assertEqual(command.call_args_list[1].args[0],['podman','stop','--time','10','acp-fixture-builder'])
        self.assertEqual(len(command.call_args_list),2)

    def test_ambiguous_conversation_refuses_stop_before_systemd_teardown(self):
        core=Mock();core.capture_sessions.side_effect=ValueError('Multiple native conversations')
        with patch.object(team,'load',return_value=core), patch.object(team,'container_phase',return_value='running'), patch.object(team,'control_command') as command:
            with self.assertRaisesRegex(ValueError,'Multiple native'):
                team.stop_project('fixture',10)
        command.assert_not_called()

    def test_start_waits_for_shutdown_before_submitting_start(self):
        events=[]
        with patch.object(team,'pending_project_stop',return_value=True), patch.object(team,'wait_project_stopped',side_effect=lambda *args:events.append('waited')), patch.object(team,'control_command',side_effect=lambda cmd,*args:events.append(cmd)):
            team.control('start','fixture')
        self.assertEqual(events,['waited',['systemctl','--user','start','assistant-connector@fixture.target']])

    def test_shutdown_timeout_never_submits_start(self):
        with patch.object(team,'pending_project_stop',return_value=True), patch.object(team,'wait_project_stopped',side_effect=ValueError('shutdown incomplete')), patch.object(team,'control_command') as command:
            with self.assertRaisesRegex(ValueError,'incomplete'):team.control('start','fixture')
        command.assert_not_called()

    def test_restart_is_explicit_stop_completion_then_start_not_restart_job(self):
        events=[]
        with patch.object(team,'stop_project',side_effect=lambda *args:events.append('stopped')), patch.object(team,'control_command',side_effect=lambda cmd,*args:events.append(cmd)):
            team.control('restart','fixture')
        self.assertEqual(events,['stopped',['systemctl','--user','start','assistant-connector@fixture.target']])

    def test_stop_waits_until_service_container_jobs_and_listeners_finish(self):
        service_batches=iter(['deactivating','inactive','inactive'])
        current={'state':'deactivating','phase':'stopping'}
        def state(unit):
            if unit.endswith('.target'):
                current['state']=next(service_batches)
            return {'ActiveState':current['state']}
        listeners=Mock(side_effect=[team.ProjectStillListening('live'),None])
        with patch.object(team,'service_state',side_effect=state), patch.object(team,'container_phase',side_effect=lambda *args:'stopping' if current['state']=='deactivating' else 'exited'), patch.object(team,'pending_project_stop',return_value=False), patch.object(team,'verify_no_project_listener',listeners), patch.object(team,'project_path',return_value=pathlib.Path('/unused')), patch.object(team.time,'monotonic',return_value=1), patch.object(team.time,'sleep') as sleep:
            team.wait_project_stopped('fixture',10)
        self.assertEqual(sleep.call_count,2)
        self.assertEqual(listeners.call_count,2)

    def test_verification_failure_is_not_treated_as_stopped(self):
        with patch.object(team,'service_state',side_effect=ValueError('query failure')):
            with self.assertRaisesRegex(ValueError,'query failure'):team.wait_project_stopped('fixture',10)

    def test_pending_stop_only_considers_named_units_and_detects_container_stopping(self):
        result=subprocess.CompletedProcess([],0,'12 unrelated.service stop running\n13 assistant-connector@fixture.target start waiting\n','')
        with patch.object(team.subprocess,'run',return_value=result), patch.object(team,'service_state',return_value={'ActiveState':'inactive'}), patch.object(team,'container_phase',return_value='exited'):
            self.assertFalse(team.pending_project_stop('fixture'))
        result.stdout='14 assistant-connector-gateway@fixture.service stop waiting\n'
        with patch.object(team.subprocess,'run',return_value=result):
            self.assertTrue(team.pending_project_stop('fixture'))
        result.stdout=''
        with patch.object(team.subprocess,'run',return_value=result), patch.object(team,'service_state',return_value={'ActiveState':'inactive'}), patch.object(team,'container_phase',return_value='stopping'):
            self.assertTrue(team.pending_project_stop('fixture'))

    def test_control_command_timeout_does_not_claim_completed_shutdown(self):
        with patch.object(team.time,'monotonic',return_value=1), patch.object(team.subprocess,'run',side_effect=subprocess.TimeoutExpired('systemctl',1)):
            with self.assertRaisesRegex(ValueError,'may still be running'):team.control_command(['systemctl'],2)

    def test_status_reports_stopping_dependencies_instead_of_inactive_target(self):
        core=Mock();core.PROFILES=pathlib.Path('/nonexistent');core.container.side_effect=lambda role:'fixture-'+role
        with patch.object(team,'load',return_value=core), patch.object(team,'project_summary',return_value='stopping'), patch.object(team.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'stopping\n','')), patch('builtins.print') as output:
            team.status('fixture')
        self.assertEqual(output.call_args_list[0].args[0],'Project fixture: stopping')
