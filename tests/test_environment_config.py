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
        module.atomic(pathlib.Path(home)/'conf/environment.conf',{'version':1,'profiles':{p:{'enabled':p in enabled} for p in module.PROFILES}})

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
            path=pathlib.Path(home)/'conf/environment.conf';value=json.loads(path.read_text())
            value['profiles']['claude-priv']['token']='fixture'
            module.atomic(path,value)
            with self.assertRaises(ValueError):module.environment(home)

    def test_project_config_is_authoritative_and_separate(self):
        with tempfile.TemporaryDirectory() as home:
            self.environment(home,module.PROFILES)
            first=module.project(home,'one');second=module.project(home,'two')
            first['roles']['challenger']='gemini-priv'
            module.atomic(pathlib.Path(home)/'projects/one/project.one.config',first)
            self.assertEqual(module.project(home,'one')['roles']['challenger'],'gemini-priv')
            self.assertEqual(module.project(home,'two')['roles']['challenger'],'gemini-work')

    def test_antigravity_private_profile_can_select_native_team_adapter(self):
        with tempfile.TemporaryDirectory() as home:
            self.environment(home,module.PROFILES)
            value=module.project(home,'one');value['roles']['challenger']='gemini-priv'
            module.atomic(pathlib.Path(home)/'projects/one/project.one.config',value)
            self.assertEqual(module.assignments(home,'one')['challenger'],'gemini-priv')

    def test_mistral_work_and_private_can_be_assigned_to_visible_team_roles(self):
        with tempfile.TemporaryDirectory() as home:
            self.environment(home,module.PROFILES)
            for profile in ['mistral-work','mistral-priv']:
                value=module.project(home,'one')
                for role in ['orchestrator','builder','investigator','challenger']:value['roles'][role]=profile
                module.atomic(pathlib.Path(home)/'projects/one/project.one.config',value)
                self.assertEqual(module.assignments(home,'one'),value['roles'])

    def test_mistral_cannot_replace_private_readers_or_restricted_connectors(self):
        with tempfile.TemporaryDirectory() as home:
            self.environment(home,module.PROFILES)
            for role in ['summarizer','observer','private-connector','corporate-connector']:
                value=module.project(home,'one');value['roles'][role]='mistral-priv'
                module.atomic(pathlib.Path(home)/'projects/one/project.one.config',value)
                with self.assertRaisesRegex(ValueError,'restricted role requires Claude'):module.assignments(home,'one')
                value['roles'][role]=module.DEFAULTS[role]
                module.atomic(pathlib.Path(home)/'projects/one/project.one.config',value)
