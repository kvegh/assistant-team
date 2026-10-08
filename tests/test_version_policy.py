import importlib.util
import pathlib
import unittest
spec=importlib.util.spec_from_file_location('versions',pathlib.Path(__file__).parents[1]/'src/bump-version.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class VersionPolicyTests(unittest.TestCase):
    def test_documentation_and_other_commits_increment_patch(self):self.assertEqual(module.next_version('0.0.1'),'0.0.2')
    def test_feature_commit_increments_minor_and_resets_patch(self):self.assertEqual(module.next_version('0.0.7',True),'0.1.0')
