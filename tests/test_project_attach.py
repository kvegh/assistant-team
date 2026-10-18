"""Attach failures should explain the required action without launching work."""
import importlib.util
import pathlib
import subprocess
import unittest
from unittest.mock import Mock, patch

SOURCE=pathlib.Path(__file__).parents[1]/'src/roles/project_framework/files/project-team.py'
spec=importlib.util.spec_from_file_location('project_attach',SOURCE)
team=importlib.util.module_from_spec(spec)
spec.loader.exec_module(team)


class ProjectAttachTests(unittest.TestCase):
    def setUp(self):
        self.core=Mock()
        self.core.container.return_value='acp-example-orchestrator'

    def test_created_or_stopped_project_explains_start_and_never_executes_attach(self):
        for phase in ['absent','created','exited','stopped']:
            with self.subTest(phase=phase),patch.object(team,'container_phase',return_value=phase),patch.object(team,'project_summary',return_value='stopped'),patch.object(team.subprocess,'run') as run:
                with self.assertRaisesRegex(ValueError,'not running.*team start example'):
                    team.attach_role('example','orchestrator',self.core)
                run.assert_not_called()
        self.core.run.assert_not_called()

    def test_missing_role_in_running_project_explains_role_launch(self):
        with patch.object(team,'container_phase',return_value='absent'),patch.object(team,'project_summary',return_value='running'):
            with self.assertRaisesRegex(ValueError,'team launch example orchestrator'):
                team.attach_role('example','orchestrator',self.core)
        self.core.run.assert_not_called()

    def test_transitional_paused_failed_and_unknown_states_recommend_status(self):
        for phase,state in [('stopping','stopping'),('paused','running'),('absent','starting'),('exited','failed'),('absent','unknown')]:
            with self.subTest(phase=phase,state=state),patch.object(team,'container_phase',return_value=phase),patch.object(team,'project_summary',return_value=state):
                with self.assertRaisesRegex(ValueError,'team status example'):
                    team.attach_role('example','orchestrator',self.core)
        self.core.run.assert_not_called()

    def test_running_container_without_tmux_session_gets_clear_diagnostic(self):
        with patch.object(team,'container_phase',return_value='running'),patch.object(team.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','')):
            with self.assertRaisesRegex(ValueError,'no available native tmux session'):
                team.attach_role('example','orchestrator',self.core)
        self.core.run.assert_not_called()

    def test_dead_native_pane_recommends_launch_without_attaching(self):
        replies=[subprocess.CompletedProcess([],0,'',''),subprocess.CompletedProcess([],0,'1\n','')]
        with patch.object(team,'container_phase',return_value='running'),patch.object(team.subprocess,'run',side_effect=replies):
            with self.assertRaisesRegex(ValueError,'has exited.*team launch example orchestrator'):
                team.attach_role('example','orchestrator',self.core)
        self.core.run.assert_not_called()

    def test_live_native_pane_attaches_without_requiring_other_roles_to_be_healthy(self):
        replies=[subprocess.CompletedProcess([],0,'',''),subprocess.CompletedProcess([],0,'0\n','')]
        with patch.object(team,'container_phase',return_value='running'),patch.object(team,'project_summary') as summary,patch.object(team.subprocess,'run',side_effect=replies):
            team.attach_role('example','orchestrator',self.core)
        summary.assert_not_called()
        self.core.run.assert_called_once_with(['podman','exec','-it','acp-example-orchestrator','tmux','attach-session','-t','native'])

    def test_race_after_preflight_has_readable_failure(self):
        self.core.run.side_effect=subprocess.CalledProcessError(125,['podman','exec'])
        replies=[subprocess.CompletedProcess([],0,'',''),subprocess.CompletedProcess([],0,'0\n','')]
        with patch.object(team,'container_phase',return_value='running'),patch.object(team.subprocess,'run',side_effect=replies):
            with self.assertRaisesRegex(ValueError,'session may have stopped.*team status example'):
                team.attach_role('example','orchestrator',self.core)
