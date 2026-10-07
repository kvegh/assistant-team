"""Verify launch input validation without connecting to a hypervisor."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeploymentValidationTests(unittest.TestCase):
    def assert_rejected(self, overrides, inventory="hypervisor ansible_connection=local\n"):
        variables = {
            "vm_name": "example-vm",
            "provisioning": {
                "vm_name": "example-vm",
                "golden_image_path": "/example/image.qcow2",
                "vm_dir": "/example/vms",
                "vm_domain": "example.invalid",
                "vm_network": "example-network",
                "guest_ssh_user": "example-user",
            },
        }
        variables.update(overrides)
        with tempfile.TemporaryDirectory() as directory:
            inventory_file = Path(directory) / "inventory.ini"
            inventory_file.write_text(inventory)
            env = dict(os.environ, ANSIBLE_NOCOLOR="1")
            result = subprocess.run(
                [
                    "ansible-playbook", "--check", "-i", str(inventory_file),
                    "src/deploy_linux_vm.yml", "-e", json.dumps(variables),
                ],
                cwd=ROOT, env=env, text=True, capture_output=True, check=False,
            )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("TASK [Validate deployment inputs]", result.stdout)
        self.assertIn("failed=1", result.stdout)
        self.assertNotIn("TASK [Inspect existing VM names]", result.stdout)

    def test_rejects_vm_names_with_path_separators(self):
        self.assert_rejected({"vm_name": "../example"})

    def test_rejects_zero_cpus(self):
        self.assert_rejected({"vm_vcpus": 0})

    def test_rejects_memory_below_one_gib(self):
        self.assert_rejected({"vm_memory_mb": 512})

    def test_rejects_multiple_hypervisors(self):
        self.assert_rejected(
            {},
            "[hypervisor]\nexample-one ansible_connection=local\n"
            "example-two ansible_connection=local\n",
        )


if __name__ == "__main__":
    unittest.main()
