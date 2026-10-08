import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPOSITORY = Path(__file__).resolve().parents[1]
FRAMEWORK = REPOSITORY / 'src/roles/project_framework/files/project-team.py'
ROUTER = REPOSITORY / 'src/roles/agents_connector/files/connector-team.py'


class ProjectListingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.projects = self.home / 'projects'
        specification = importlib.util.spec_from_file_location('project_listing', FRAMEWORK)
        self.framework = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(self.framework)
        self.framework.PROJECTS = self.projects

    def create_fixture(self, name):
        path = self.projects / name
        path.mkdir(parents=True)
        for filename in ('initialized', 'db.sqlite', 'assistant-prompt.md'):
            (path / filename).write_text('private-content-must-not-be-read')
        (path / 'workspace').mkdir()
        return path

    def output(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.framework.list_projects()
        return output.getvalue()

    def test_empty_listing_does_not_create_project_directory(self):
        self.assertIn('No initialized projects', self.output())
        self.assertFalse(self.projects.exists())

    def test_sorted_listing_excludes_partial_invalid_and_symlink_projects(self):
        for name in ('zeta', 'alpha'):
            self.create_fixture(name)
        incomplete = self.create_fixture('partial')
        (incomplete / 'initialized').unlink()
        self.create_fixture('UPPER')
        self.create_fixture('missing-workspace').joinpath('workspace').rmdir()
        self.projects.joinpath('alias').symlink_to(self.projects / 'alpha', target_is_directory=True)
        linked_marker = self.create_fixture('linked-marker')
        linked_marker.joinpath('initialized').unlink()
        linked_marker.joinpath('initialized').symlink_to(self.projects / 'alpha' / 'initialized')
        with patch.object(Path, 'read_text', side_effect=AssertionError('private content read')):
            self.assertEqual(self.output(), 'alpha\nzeta\n')

    def test_project_parent_symlink_is_rejected(self):
        self.projects.symlink_to(self.home, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            self.framework.list_projects()

    def test_both_aliases_skip_auth_and_service_operations(self):
        self.create_fixture('alpha')
        for action in ('--list', 'list-projects'):
            with self.subTest(action=action), patch.object(sys, 'argv', ['team', action]), \
                    patch.object(self.framework, 'settings', side_effect=AssertionError('auth read')), \
                    patch.object(self.framework, 'load', side_effect=AssertionError('broker loaded')), \
                    patch.object(self.framework.subprocess, 'run', side_effect=AssertionError('service command')):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.framework.main()
                self.assertEqual(output.getvalue(), 'alpha\n')

    def test_installed_router_executes_listing_without_project_or_private_helpers(self):
        routing = self.home / 'agents-connector' / 'routing'
        routing.mkdir(parents=True)
        shutil.copyfile(FRAMEWORK, routing / 'project-team.py')
        shutil.copyfile(ROUTER, routing / 'connector-team.py')
        self.home.joinpath('team').symlink_to(routing / 'connector-team.py')
        self.create_fixture('alpha')
        # No config/diagnostics/auth helpers are installed: listing must not import them.
        environment = os.environ.copy()
        for project in (None, 'alpha'):
            if project is None:
                environment.pop('ASSISTANT_PROJECT', None)
            else:
                environment['ASSISTANT_PROJECT'] = project
            for action in ('--list', 'list-projects'):
                with self.subTest(project=project, action=action):
                    result = subprocess.run([sys.executable, str(self.home / 'team'), action],
                                            capture_output=True, text=True, env=environment, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, 'alpha\n')

    def test_listing_rejects_extra_arguments(self):
        with patch.object(sys, 'argv', ['team', '--list', 'alpha']):
            with self.assertRaisesRegex(ValueError, 'without a project name'):
                self.framework.main()


if __name__ == '__main__':
    unittest.main()
