import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).parents[1] / 'src/roles/agent_images/files/assistant-instance.py'
spec = importlib.util.spec_from_file_location('assistant_instance', MODULE)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class AssistantInstancesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.role = self.root / 'role.md'
        self.role.write_text('Summarize supplied materials and request approval before actions.')
        self.roster = self.root / 'participants.json'
        self.roster.write_text(json.dumps([{'role': 'reviewer', 'responsibility': 'Review summaries.', 'worker_visible': True}]))

    def init(self, name, flavour):
        return launcher.initialize(self.root / 'instances', name, flavour, self.role, self.roster)

    def test_native_instruction_files_include_participant_roles(self):
        for flavour, native in [('claude', 'workspace/CLAUDE.md'), ('codex', 'workspace/AGENTS.md'),
                                ('gemini', 'workspace/GEMINI.md'), ('vibe', 'home/.vibe/prompts/instance.md')]:
            instance = self.init(flavour, flavour)
            text = (instance / native).read_text()
            self.assertIn('reviewer: Review summaries.', text)
            self.assertIn('grants no access', text)

    def test_instances_do_not_share_authentication_or_workspace(self):
        one = self.init('one', 'claude')
        two = self.init('two', 'claude')
        (one / 'home/auth.json').write_text('test-only marker')
        self.assertFalse((two / 'home/auth.json').exists())
        (one / 'workspace/input.txt').write_text('test-only input')
        self.assertFalse((two / 'workspace/input.txt').exists())
        with self.assertRaises(ValueError):
            self.init('one', 'claude')

    def test_container_mounts_and_privileges_are_limited(self):
        instance = self.init('one', 'codex')
        command = launcher.podman_command(instance, 'one', 'codex', 'test', 'prompt', ['Summarize.'], False)
        mounts = [command[i + 1] for i, value in enumerate(command) if value == '--volume']
        self.assertEqual(len(mounts), 2)
        self.assertTrue(all(value.startswith(str(instance) + '/') for value in mounts))
        self.assertIn('--cap-drop=ALL', command)
        self.assertIn('--security-opt=no-new-privileges', command)
        self.assertIn('--read-only', command)
        self.assertNotIn('--privileged', command)
        (instance / 'workspace/AGENTS.md').unlink()
        (instance / 'workspace').rmdir()
        (instance / 'workspace').symlink_to(self.root)
        with self.assertRaises(ValueError):
            launcher.podman_command(instance, 'one', 'codex', 'test', 'prompt', ['Summarize.'], False)

    def test_programmatic_vibe_always_selects_constrained_agent(self):
        self.assertEqual(launcher.command_for('vibe', 'prompt', ['Summarize.'])[:3],
                         ['vibe', '--agent', 'instance'])
        instance = self.init('one', 'vibe')
        self.assertIn('enabled_tools = ["grep", "read_file"]',
                      (instance / 'home/.vibe/agents/instance.toml').read_text())

    def test_prompt_flags_are_passed_as_text(self):
        with self.assertRaises(ValueError):
            launcher.command_for('claude', 'prompt', ['--dangerously-skip-permissions'])
        with self.assertRaises(ValueError):
            launcher.command_for('codex', 'interactive', ['--yolo'])

    def test_observer_roles_are_not_rendered_into_worker_context(self):
        self.roster.write_text(json.dumps([
            {'role': 'reviewer', 'responsibility': 'Review summaries.', 'worker_visible': True},
            {'role': 'observer', 'responsibility': 'Evaluate verified outcomes.', 'worker_visible': False},
        ]))
        instance = self.init('one', 'codex')
        context = (instance / 'workspace/AGENTS.md').read_text()
        self.assertIn('reviewer: Review summaries.', context)
        self.assertNotIn('observer', context)
        self.assertNotIn('Evaluate verified outcomes.', context)
        self.assertNotIn('Workflow review', context)

    def test_roster_rejects_extra_access_metadata(self):
        self.roster.write_text(json.dumps([{'role': 'reviewer', 'responsibility': 'Review.', 'worker_visible': True, 'token': 'fake'}]))
        with self.assertRaises(ValueError):
            self.init('one', 'claude')
        self.assertFalse((self.root / 'instances/one').exists())


if __name__ == '__main__':
    unittest.main()
