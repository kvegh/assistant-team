"""Exercise the live inventory guard with isolated controller HTTP fixtures."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InventoryVmGuardTests(unittest.TestCase):
    def run_guard(self, hosts, groups, *, operation="retire", existing=True, overrides=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugins = root / "plugins"
            plugins.mkdir()
            # Replace only the HTTP transport in this test process. Real role logic,
            # Jinja assertions and returned controller data remain exercised.
            (plugins / "uri.py").write_text(
                "from ansible.plugins.action import ActionBase\n"
                "import json, os\n"
                "class ActionModule(ActionBase):\n"
                " def run(self, tmp=None, task_vars=None):\n"
                "  source = 'GROUPS' if '/all_groups/' in self._task.args['url'] else 'HOSTS'\n"
                "  return {'changed': False, 'json': json.loads(os.environ['GUARD_TEST_' + source])}\n"
            )
            # An unqualified module name allows isolated transport substitution;
            # the copied role is otherwise byte-for-byte the shipped implementation.
            roles = root / "roles" / "inventory_vm_guard" / "tasks"
            roles.mkdir(parents=True)
            source = ROOT / "src/roles/inventory_vm_guard/tasks/main.yml"
            (roles / "main.yml").write_text(source.read_text().replace("ansible.builtin.uri:", "uri:"))
            play = root / "check.yml"
            play.write_text("- hosts: localhost\n  gather_facts: false\n  roles: [inventory_vm_guard]\n")
            variables = {
                "inventory_vm_guard_name": "example-5",
                "inventory_vm_guard_operation": operation,
                "inventory_vm_guard_require_existing": existing,
            }
            variables.update(overrides or {})
            result = subprocess.run(
                ["ansible-playbook", "-i", "localhost,", "-c", "local", str(play), "-e", json.dumps(variables)],
                cwd=ROOT, text=True, capture_output=True, check=False,
                env=dict(os.environ, ANSIBLE_NOCOLOR="1", ANSIBLE_LOCAL_TEMP=str(root / "tmp"),
                         ANSIBLE_ACTION_PLUGINS=str(plugins), ANSIBLE_ROLES_PATH=str(root / "roles"),
                         AC_AGENTS_CONTROLLER_HOST="https://controller.example.invalid",
                         AC_AGENTS_CONTROLLER_TOKEN="test-placeholder",
                         AC_AGENTS_CONTROLLER_INVENTORY_ID="7",
                         GUARD_TEST_HOSTS=json.dumps({"count": len(hosts), "results": hosts, "next": None}),
                         GUARD_TEST_GROUPS=json.dumps({"count": len(groups), "results": [{"name": g} for g in groups], "next": None})),
            )
            return result

    @staticmethod
    def host(identifier=1, binding="example-5", name="inventory-alias"):
        return {"id": identifier, "name": name, "variables": json.dumps({"assistant_vm_name": binding})}

    def assert_allowed(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_refused(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unprotected_managed_host_can_be_selected(self):
        self.assert_allowed(self.run_guard([self.host()], ["assistant_team"]))

    def test_production_membership_blocks_retirement(self):
        self.assert_refused(self.run_guard([self.host()], ["assistant_team", "prod"]))

    def test_inherited_production_membership_cannot_be_shadowed_by_inventory_variables(self):
        self.assert_refused(self.run_guard([self.host()], ["assistant_team", "prod"], overrides={
            "groups": {"assistant_team": ["inventory-alias"], "prod": []},
            "hostvars": {"inventory-alias": {"assistant_vm_name": "example-5", "group_names": ["assistant_team"]}},
        }))

    def test_shutdown_of_production_host_is_allowed(self):
        self.assert_allowed(self.run_guard([self.host()], ["assistant_team", "prod"], operation="shutdown"))

    def test_missing_target_refused(self):
        self.assert_refused(self.run_guard([], ["assistant_team"]))

    def test_ambiguous_explicit_bindings_refused(self):
        self.assert_refused(self.run_guard([self.host(), self.host(2)], ["assistant_team"]))

    def test_host_without_explicit_binding_refused(self):
        self.assert_refused(self.run_guard([{"id": 1, "name": "example-5", "variables": "{}"}], ["assistant_team"]))

    def test_unmanaged_host_refused(self):
        self.assert_refused(self.run_guard([self.host()], []))

    def test_fresh_target_must_be_absent(self):
        self.assert_allowed(self.run_guard([], [], existing=False))
        self.assert_refused(self.run_guard([self.host()], [], existing=False))

    def test_name_collision_without_binding_also_refused(self):
        self.assert_refused(self.run_guard([{"id": 1, "name": "example-5", "variables": "{}"}], [], existing=False))


if __name__ == "__main__":
    unittest.main()
