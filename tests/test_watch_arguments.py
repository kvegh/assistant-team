import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('watch_arguments',ROOT/'src/roles/project_framework/files/project-team.py')
framework=importlib.util.module_from_spec(spec);spec.loader.exec_module(framework)
spec=importlib.util.spec_from_file_location('watch_argument_core',ROOT/'src/roles/agents_connector/files/connector-team.py')
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)

class WatchArgumentTests(unittest.TestCase):
    def test_project_position_and_compact_options_dispatch_identically(self):
        for arguments,expected in [
            (['example'],(50,False)),(['-f','example'],(0,True)),
            (['-200f','example'],(200,True)),(['-200','-f','example'],(200,True)),
            (['example','-200f'],(200,True)),(['-f','example','-200'],(200,True)),
            (['-200','example','-f'],(200,True)),(['example','-200','-f'],(200,True)),
            (['-0f','example'],(0,True)),(['-0','example'],(0,False))]:
            with self.subTest(arguments=arguments):
                fake=Mock();fake.watch_history_limit=core.watch_history_limit
                with patch.object(sys,'argv',['team','watch']+arguments),patch.object(framework,'load',return_value=fake) as load,patch.object(framework,'verify_project') as verify:
                    framework.main()
                load.assert_called_once_with('example');verify.assert_called_once_with('example')
                fake.watch.assert_called_once_with(limit=expected[0],follow=expected[1])

    def test_missing_extra_project_and_invalid_options_fail_before_watch(self):
        for arguments in [[],['-f'],['example','other'],['-200f','-f','example'],['-f','example','-200f'],['--unknown','example'],['-200','example','-20']]:
            with self.subTest(arguments=arguments):
                fake=Mock();fake.watch_history_limit=core.watch_history_limit
                with patch.object(sys,'argv',['team','watch']+arguments),patch.object(framework,'load',return_value=fake),patch.object(framework,'verify_project') as verify,self.assertRaisesRegex(ValueError,'watch|Use team'):
                    framework.main()
                fake.watch.assert_not_called();verify.assert_not_called()
