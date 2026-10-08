import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'src/roles/agents_connector/files/connector-team.py'


class PromptFormatTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        specification = importlib.util.spec_from_file_location('prompt_format', SOURCE)
        self.core = importlib.util.module_from_spec(specification)
        with patch.dict(os.environ, {}, clear=True):
            specification.loader.exec_module(self.core)
        self.core.PROJECT = 'sample'
        self.core.ROOT = self.root
        self.core.PROFILES = self.root / 'profiles'
        for role in self.core.ALL:
            profile = self.core.PROFILES / role
            profile.joinpath('workspace').mkdir(parents=True)
            profile.joinpath('profile.json').write_text(json.dumps({'flavour': 'claude'}))

    def bracket_prompt(self):
        return ('[Project]\n# Human goal guidance\nACTIVE_GOAL\n' + ''.join(
            '[Role: ' + role.replace('-', ' ').title() + ']\n'
            '# Rough initial role prompt; refine through design.\n'
            '# Example: COMMENTED_' + role + '\nACTIVE_' + role + '\n'
            for role in self.core.ALL))

    def apply(self, text):
        self.root.joinpath('assistant-prompt.md').write_text(text)
        self.core.apply_prompts()

    def rendered(self, role):
        return self.core.PROFILES.joinpath(role, 'workspace', 'CLAUDE.md').read_text()

    def test_bracket_sections_and_comments_are_extracted_without_other_roles(self):
        self.apply(self.bracket_prompt())
        for role in self.core.ALL:
            with self.subTest(role=role):
                output = self.rendered(role)
                self.assertIn('ACTIVE_GOAL', output)
                self.assertIn('ACTIVE_' + role, output)
                self.assertNotIn('COMMENTED_', output)
                self.assertNotIn('Human goal guidance', output)
                self.assertNotIn('Rough initial', output)
                for other in self.core.ALL:
                    if other != role:
                        self.assertNotIn('ACTIVE_' + other, output)
        self.assertNotIn('observer', self.rendered('builder'))

    def test_examples_only_are_allowed_without_becoming_active_fallback(self):
        text = '[Project]\n# Example goal\n' + ''.join(
            '[Role: ' + role.replace('-', ' ').title() + ']\n# Example: NEVER_DELIVER\n'
            for role in self.core.ALL)
        self.apply(text)
        for role in self.core.ALL:
            self.assertNotIn('NEVER_DELIVER', self.rendered(role))
            self.assertNotIn('Example goal', self.rendered(role))

    def test_legacy_headers_and_markdown_instructions_remain_supported(self):
        text = '# Project goal\nLEGACY_GOAL\n' + ''.join(
            '# Role: ' + role + '\n# Real Markdown heading\n[Standalone legacy text]\nLEGACY_' + role + '\n'
            for role in self.core.ALL)
        self.apply(text)
        self.assertIn('LEGACY_GOAL', self.rendered('builder'))
        self.assertIn('# Real Markdown heading', self.rendered('builder'))
        self.assertIn('[Standalone legacy text]', self.rendered('builder'))
        self.assertIn('LEGACY_builder', self.rendered('builder'))
        self.assertNotIn('LEGACY_observer', self.rendered('builder'))

    def test_duplicate_missing_and_unknown_sections_fail_before_writing(self):
        text = self.bracket_prompt()
        invalid = [text + '[Role: Builder]\nextra',
                   text.replace('[Role: Builder]', '[Role: Unknown]'),
                   text.replace('[Role: Builder]', '[Role: Investigator]'),
                   text + '[Project]\nextra',
                   text.replace('[Role: Builder]', '[Unexpected]')]
        for candidate in invalid:
            with self.subTest(candidate=candidate[-50:]):
                with self.assertRaises(ValueError):
                    self.apply(candidate)
                self.assertFalse(self.core.PROFILES.joinpath('builder/workspace/CLAUDE.md').exists())

    def test_display_names_are_case_insensitive_with_spaces_or_hyphens(self):
        text = self.bracket_prompt().replace('[Role: Investigator]', '[role: INVESTIGATOR]')
        text = text.replace('[Role: Private Connector]', '[Role: private-connector]')
        text = text.replace('[Role: Corporate Connector]', '[Role: CorporateConnector]')
        self.apply(text)
        self.assertIn('ACTIVE_investigator', self.rendered('investigator'))

    def test_new_project_template_comments_legacy_examples_without_modifying_source(self):
        legacy = '# Template instructions\n' + ''.join(
            '# Role: ' + role + '\n# ' + role.title() + '\n'
            'Rough initial role prompt; refine through design.\nSAMPLE_' + role + '\n'
            for role in self.core.ALL)
        template = self.core.project_prompt_template(legacy)
        self.assertIn('[Project]', template)
        self.assertIn('[Role: Private Connector]', template)
        self.assertIn('# Example: SAMPLE_builder', template)
        self.assertNotIn('# Role:', template)
        self.apply(template)
        self.assertNotIn('SAMPLE_builder', self.rendered('builder'))
        self.assertIn('SAMPLE_builder', legacy)

    def test_modern_shared_template_preserves_operator_active_instructions(self):
        source = self.bracket_prompt()
        template = self.core.project_prompt_template(source)
        self.assertIn('# Example: COMMENTED_builder', template)
        self.assertIn('ACTIVE_builder', template)
        self.apply(template)
        self.assertIn('ACTIVE_builder', self.rendered('builder'))
        self.assertNotIn('COMMENTED_builder', self.rendered('builder'))


if __name__ == '__main__':
    unittest.main()
