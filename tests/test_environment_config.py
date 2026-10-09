import importlib.util
import json
import pathlib
import tempfile
import unittest

SOURCE=pathlib.Path(__file__).parents[1]/'src/roles/project_framework/files/environment-config.py'
spec=importlib.util.spec_from_file_location('environment_config',SOURCE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class EnvironmentConfigTests(unittest.TestCase):
    def environment(self, home, enabled):
        module.atomic(pathlib.Path(home)/'environment.config',{'version':1,'profiles':{p:{'enabled':p in enabled} for p in module.PROFILES}})

    def test_selected_subset_does_not_assign_disabled_accounts(self):
        with tempfile.TemporaryDirectory() as home:
            self.environment(home,['claude-work','gemini-priv','codex-priv'])
            config=module.project(home,'example')
            self.assertEqual(config['roles']['challenger'],'gemini-priv')
            self.assertIsNone(config['roles']['private-connector'])
            with self.assertRaisesRegex(ValueError,'private-connector'):
                module.assignments(home,'example')

    def test_custom_profile_and_secret_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as home:
            self.environment(home,[])
            path=pathlib.Path(home)/'environment.config';value=json.loads(path.read_text())
            value['profiles']['claude-priv']['token']='fixture'
            module.atomic(path,value)
            with self.assertRaises(ValueError):module.environment(home)

    def test_project_config_is_authoritative_and_separate(self):
        with tempfile.TemporaryDirectory() as home:
            self.environment(home,module.PROFILES)
            first=module.project(home,'one');second=module.project(home,'two')
            first['roles']['challenger']='gemini-priv'
            module.atomic(pathlib.Path(home)/'projects.one.config',first)
            self.assertEqual(module.project(home,'one')['roles']['challenger'],'gemini-priv')
            self.assertEqual(module.project(home,'two')['roles']['challenger'],'gemini-work')

    def test_antigravity_private_profile_can_select_native_team_adapter(self):
        with tempfile.TemporaryDirectory() as home:
            self.environment(home,module.PROFILES)
            value=module.project(home,'one');value['roles']['challenger']='gemini-priv'
            module.atomic(pathlib.Path(home)/'projects.one.config',value)
            self.assertEqual(module.assignments(home,'one')['challenger'],'gemini-priv')

    def test_mistral_profile_available_but_team_assignment_rejected(self):
        with tempfile.TemporaryDirectory() as home:
            self.environment(home,module.PROFILES)
            value=module.project(home,'one');value['roles']['builder']='mistral-priv'
            module.atomic(pathlib.Path(home)/'projects.one.config',value)
            with self.assertRaisesRegex(ValueError,'adapter'):module.assignments(home,'one')
