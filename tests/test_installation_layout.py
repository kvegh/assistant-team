"""Synthetic installation contract checks; no native tools or credentials used."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

BASE=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class InstallationLayoutTests(unittest.TestCase):
    def setUp(self):
        self.paths=load('layout_paths_test',BASE/'src/lib/install-paths.py')

    def test_all_mutable_paths_share_explicit_installation_root(self):
        with tempfile.TemporaryDirectory() as parent:
            root=Path(parent)/'ac-agents';paths=self.paths.Paths(root)
            self.assertEqual(paths.vendor,root/'agent-connector')
            self.assertEqual(paths.models,root/'model-environments')
            self.assertEqual(paths.environment,root/'conf/environment.conf')
            self.assertEqual(paths.template,root/'conf/templates/assistant.prompt.md.template')
            self.assertEqual(paths.team,root/'bin/team')
            self.assertEqual(paths.project_config('example'),root/'projects/example/project.example.config')
            self.assertEqual(paths.archives,root/'project-archive')
            self.assertEqual(paths.logs,root/'environment-logs')
            self.assertFalse(root.exists(),'Path inspection must not initialize the environment')

    def test_profile_discovery_supports_custom_prefix_and_rejects_legacy_home(self):
        with tempfile.TemporaryDirectory() as parent:
            root=Path(parent)/'custom/ac-agents'
            for vendor in ('claude','gemini','codex','mistral'):
                for context in ('work','priv'):
                    profile=root/'model-environments'/f'{vendor}-{context}'
                    self.assertEqual(self.paths.for_profile(profile).root,root)
            with self.assertRaises(ValueError):self.paths.for_profile(Path(parent)/'claude-priv')
            self.assertFalse(root.exists(),'Discovery must not migrate or create profiles')

    def test_socket_limit_includes_new_prefix_and_installation_directory(self):
        names=load('layout_names_test',BASE/'src/lib/project-names.py')
        short=Path('/tmp/ac-agents')
        names.validate('example',short)
        long=Path('/tmp')/('x'*70)/'ac-agents'
        with self.assertRaisesRegex(ValueError,'socket path'):
            names.validate('example',long)

    def test_default_home_child_depth_can_require_a_shorter_project_name(self):
        names=load('layout_default_names_test',BASE/'src/lib/project-names.py')
        home=Path('/home/operator')
        name='a'*37
        names.validate(name,home)
        with self.assertRaisesRegex(ValueError,'socket path'):
            names.validate(name,home/'ac-agents')
        names.validate('example',home/'ac-agents')

    def test_project_config_is_created_only_inside_named_project(self):
        config=load('layout_config_test',BASE/'src/roles/project_framework/files/environment-config.py')
        with tempfile.TemporaryDirectory() as parent:
            root=Path(parent)/'ac-agents'
            config.project(root,'example',create=True)
            self.assertTrue((root/'projects/example/project.example.config').is_file())
            self.assertTrue((root/'conf/environment.conf').is_file())
            self.assertFalse((root/'projects.example.config').exists())
            self.assertFalse((root/'environment.config').exists())
            self.assertFalse((Path(parent)/'environment.config').exists())
