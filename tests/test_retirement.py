"""Ensure unsafe retirement requests stop before any hypervisor command."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RetirementSafetyTests(unittest.TestCase):
    def assert_rejected(self, name, disk="/example/vms/example-2.disk.qcow2", check=False):
        variables = {
            "__inventory_vm_guard_matches": [{"id": 1, "variables": json.dumps({"assistant_vm_name": "example-3"})}],
            "__inventory_vm_guard_groups": ["assistant_team"],
            "linux_vm_retire_definition": {
                "vm_name": name,
                "vm_dir": "/example/vms",
                "golden_image_path": "/example/golden.qcow2",
            },
            "linux_vm_retire_disk": disk,
            "linux_vm_retire_execute": True,
        }
        with tempfile.TemporaryDirectory() as directory:
            play = Path(directory) / "retire.yml"
            play.write_text("- hosts: localhost\n  gather_facts: false\n  roles: [linux_vm_retire]\n")
            command = ["ansible-playbook", "-i", "localhost,", "-c", "local", str(play),
                       "-e", json.dumps(variables)]
            if check:
                command.append("--check")
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                    env=dict(os.environ, ANSIBLE_NOCOLOR="1",
                                             ANSIBLE_ROLES_PATH=str(ROOT / "src/roles")),
                                    check=False)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("failed=1", result.stdout)
        self.assertNotIn("TASK [linux_vm_retire : Inspect all defined domains]", result.stdout)

    def test_original_clone_cannot_be_retired(self):
        self.assert_rejected("example-1")

    def test_other_test_clone_cannot_be_retired(self):
        self.assert_rejected("example-4")

    def test_source_image_cannot_be_removed(self):
        self.assert_rejected("example-3", disk="/example/golden.qcow2")

    def test_check_mode_cannot_bypass_live_preflight(self):
        self.assert_rejected("example-3", check=True)
