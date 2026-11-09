"""Exercise recovery identity refusal, strict SSH routing and protected bootstrap."""

from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml
from ansible.errors import AnsibleFilterError
from ansible.parsing.vault import VaultLib, VaultSecret
from ansible.parsing.yaml.dumper import AnsibleDumper
from ansible.parsing.yaml.objects import AnsibleVaultEncryptedUnicode

ROOT = Path(__file__).resolve().parents[1]
ROLE = ROOT / "src/roles/linux_vm"
spec = importlib.util.spec_from_file_location("linux_vm_recovery", ROOT / "src/filter_plugins/linux_vm_recovery.py")
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


def pin():
    return {"address": "192.0.2.10", "user": "fixture", "port": 22,
            "machine_id": "1" * 32, "host_keys": ["ssh-ed25519 AAAA"]}


class RecoveryConnectionTests(unittest.TestCase):
    def test_shared_release_and_retirement_refuse_a_different_saved_source_pin(self):
        role = ROOT / 'src/roles/linux_recovery_release'
        defaults = yaml.safe_load((role / 'defaults/main.yml').read_text())
        tasks = yaml.safe_load((role / 'tasks/main.yml').read_text())
        for operation in ['release_guest', 'retire_guest']:
            guard = next(task for task in tasks if task['name'].startswith(
                'Require a completed verified' if operation == 'release_guest' else
                'Require the exact persisted'))
            for revision, accepted in [(defaults['linux_recovery_release_revision'], True),
                    ('785e613f53036fae61bf3a63b994a83fbe68fcaf', False), ('b' * 40, False)]:
                with self.subTest(operation=operation, accepted=accepted), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    variables = dict(defaults, role_path=str(role),
                        aap_hactar_source_revision='a' * 40, hactar_source_public_ip='198.51.100.10',
                        linux_recovery_release_revision=revision, linux_recovery_release_operation=operation,
                        linux_recovery_release_retire_phase='plan',
                        linux_recovery_release_retire_guest_name='example-v16',
                        linux_recovery_release_retire_hypervisor=pin(),
                        deployment_vm_verified_provenance={'verified': True,
                            'hypervisor_machine_id': pin()['machine_id'], 'machine_id': '2' * 32, 'bridge': 'fixture0'},
                        deployment_vm_hypervisor_pin=pin(),
                        deployment_vm_trust_file='/tmp/linux-vm-recovery-known-hosts-fixture')
                    result = self.run_play([guard], variables, root)
                    self.assertEqual(result.returncode == 0, accepted, result.stdout + result.stderr)

    def test_recovery_launch_uses_encrypted_file_credentials_after_both_environment_loads(self):
        self.recovery_inputs(False)

    def test_recovery_launch_rejects_credential_overrides_before_using_them(self):
        self.recovery_inputs(True)

    def recovery_inputs(self, reject):
        source = yaml.safe_load((ROOT / 'src/deploy_linux_vm.yml').read_text())
        with tempfile.TemporaryDirectory(prefix='recovery-input-contract-') as directory:
            root = Path(directory)
            secret = VaultSecret(b'synthetic-vault-password')
            configuration = {'hactar_source_git_token': 'synthetic-source-reader-canary',
                'provisioning': {'vm_name': 'legacy-placeholder',
                'golden_image_path': '/legacy/image.qcow2', 'vm_dir': '/legacy/vms',
                'vm_domain': 'example.invalid', 'vm_network': 'legacy-network',
                'guest_ssh_user': 'fixture', 'guest_ssh_password': 'synthetic-protected-password',
                'guest_become_password': 'synthetic-protected-password'}}
            encrypted = root / 'environment_vault.yml'
            encrypted.write_bytes(VaultLib([('default', secret)]).encrypt(yaml.safe_dump(configuration)))
            key = root / 'vault-password'; key.write_text('synthetic-vault-password'); key.chmod(0o600)
            recovery = {'vm_name': 'fixture-v07', 'golden_image_path': '/verified/upstream.qcow2',
                'vm_dir': '/verified/vms', 'vm_domain': 'example.invalid', 'vm_network': 'isolated',
                'generic_image': True, 'update_packages': False, 'hypervisor_pin': pin(),
                'isolation_policy': {'bridges': ['fixture0']}}
            if reject:
                recovery['guest_ssh_password'] = 'rejected-plaintext-secret-canary'
            variables = {'secret_config_file': str(encrypted), 'vm_name': 'fixture-v07',
                         'linux_vm_recovery': recovery}
            plays = []
            for index, original in enumerate(source):
                tasks = deepcopy(original['pre_tasks'])
                for task in tasks:
                    if 'ansible.builtin.include_tasks' in task:
                        task['ansible.builtin.include_tasks']['file'] = str(ROOT / 'src/tasks/linux_vm_recovery_inputs.yml')
                tasks.append({'name': 'Verify protected login and recovery inputs survive this load', 'no_log': True,
                    'ansible.builtin.assert': {'that': [
                        "provisioning.guest_ssh_user == 'fixture'",
                        "provisioning.guest_ssh_password == 'synthetic-protected-password'",
                        "provisioning.vm_name == 'fixture-v07'",
                        "provisioning.golden_image_path == '/verified/upstream.qcow2'",
                        "hactar_source_git_token == 'synthetic-source-reader-canary'",
                        'provisioning.generic_image', 'not provisioning.update_packages']}})
                plays.append({'name': 'Exercise actual environment load ' + str(index), 'hosts': 'localhost',
                    'connection': 'local', 'gather_facts': False, 'vars': variables, 'tasks': tasks})
            play = root / 'fixture.yml'; play.write_text(yaml.safe_dump(plays, sort_keys=False))
            environment = dict(os.environ, ANSIBLE_NOCOLOR='1', ANSIBLE_LOCAL_TEMP=str(root / 'local'),
                               ANSIBLE_REMOTE_TEMP=str(root / 'remote'),
                               ANSIBLE_ROLES_PATH=str(ROOT / 'src/roles'))
            outcome = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,',
                str(play), '--vault-password-file', str(key)], cwd=ROOT, env=environment,
                text=True, capture_output=True, timeout=60)
            self.assertEqual(outcome.returncode == 0, not reject, outcome.stdout + outcome.stderr)
            self.assertIn('Require a complete nonsecret recovery override', outcome.stdout)
            if reject:
                self.assertNotIn('TASK [Merge declared recovery values', outcome.stdout)
            self.assertNotIn('synthetic-protected-password', outcome.stdout + outcome.stderr)
            self.assertNotIn('synthetic-source-reader-canary', outcome.stdout + outcome.stderr)
            self.assertNotIn('rejected-plaintext-secret-canary', outcome.stdout + outcome.stderr)

    def test_invalid_or_wrong_recovery_identity_is_rejected(self):
        original = pin()
        self.assertEqual(recovery.recovery_pin(original, "192.0.2.10"), original)
        for changes, address in (({}, "192.0.2.11"), ({"user": "root"}, "192.0.2.10"),
                                 ({"machine_id": "unverified"}, "192.0.2.10"),
                                 ({"host_keys": ["ssh-ed25519 untrusted;command"]}, "192.0.2.10")):
            with self.assertRaises(AnsibleFilterError):
                recovery.recovery_pin(dict(original, **changes), address)

    def test_release_bridge_comes_from_the_actual_selected_network(self):
        xml = '<network><name>isolated</name><bridge name="fixture0"/></network>'
        self.assertEqual(recovery.network_bridge(xml, 'isolated', ['fixture0']), 'fixture0')
        for candidate, network, bridges in ((xml, 'foreign', ['fixture0']),
                (xml, 'isolated', ['foreign0']), ('<invalid', 'isolated', ['fixture0']),
                ('<network><name>isolated</name></network>', 'isolated', ['fixture0'])):
            with self.assertRaises(AnsibleFilterError):
                recovery.network_bridge(candidate, network, bridges)

    def test_guest_private_address_always_crosses_pinned_hypervisor_with_two_key_checks(self):
        args = recovery.guest_ssh(pin(), "/tmp/synthetic trust", "fixture-v07")
        self.assertIn("ProxyCommand=", args)
        self.assertIn("fixture@192.0.2.10", args)
        self.assertEqual(args.count("StrictHostKeyChecking=yes"), 2)
        self.assertIn("HostKeyAlias=fixture-v07", args)
        self.assertIn("PasswordAuthentication=no", args)
        self.assertNotIn("StrictHostKeyChecking=no", args)
        with self.assertRaises(AnsibleFilterError):
            recovery.guest_ssh(pin(), "/tmp/trust", "fixture; command")

    def test_resumed_guest_keys_require_the_same_domain_and_image_provenance(self):
        data = {"schema_version": 1, "deployment_type": "generic-recovery", "vm_name": "fixture-v07",
                "uuid": "synthetic-uuid", "hypervisor_machine_id": "1" * 32,
                "source_image_sha256": "a" * 64, "host_keys": ["ssh-ed25519 AAAA"]}
        self.assertEqual(recovery.saved_keys(data, "fixture-v07", "synthetic-uuid", "1" * 32, "a" * 64),
                         ["ssh-ed25519 AAAA"])
        for key in ("vm_name", "uuid", "hypervisor_machine_id", "source_image_sha256"):
            with self.assertRaises(AnsibleFilterError):
                recovery.saved_keys(dict(data, **{key: "changed"}), "fixture-v07", "synthetic-uuid", "1" * 32, "a" * 64)

    def run_play(self, tasks, variables, root):
        play = root / "fixture.yml"
        play.write_text(yaml.dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
                                  "vars": variables, "tasks": tasks}], Dumper=AnsibleDumper, sort_keys=False))
        environment = dict(os.environ, ANSIBLE_NOCOLOR="1", ANSIBLE_LOCAL_TEMP=str(root / "local"),
                           ANSIBLE_REMOTE_TEMP=str(root / "remote"),
                           ANSIBLE_FILTER_PLUGINS=str(ROOT / "src/filter_plugins"))
        options = ["--vault-password-file", str(root / "vault-password")] if (root / "vault-password").exists() else []
        return subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(play), *options],
                              env=environment, cwd=ROOT, text=True, capture_output=True, timeout=90)

    def test_actual_preflight_stops_before_storage_when_remote_machine_id_is_wrong(self):
        tasks = yaml.safe_load((ROLE / "tasks/recovery-preflight.yml").read_text())
        with tempfile.TemporaryDirectory(prefix="recovery-hypervisor-test-") as directory:
            root = Path(directory)
            (root / "vault-password").write_text("synthetic-vault-password")
            secret = VaultSecret(b"synthetic-vault-password")
            password = AnsibleVaultEncryptedUnicode(VaultLib([("default", secret)]).encrypt("synthetic-bootstrap-canary"))
            for task in tasks:
                if task["name"].startswith("Verify the actual"):
                    task["ansible.builtin.command"]["argv"] = [sys.executable, "-c", "print('2' * 32)"]
                if task["name"].startswith("Require the existing persistent"):
                    task["ansible.builtin.command"]["argv"] = [sys.executable, "-c", "raise SystemExit(99)"]
            variables = {"ansible_host": "192.0.2.10",
                "aap_hactar_source_revision": "a" * 40,
                "hactar_source_public_ip": "198.51.100.10", "provisioning": {
                "hypervisor_pin": pin(), "generic_image": True,
                "isolation_policy": {"bridges": ["fixture0"]}, "guest_ssh_user": "fixture",
                "guest_ssh_password": password, "guest_become_password": password}}
            outcome = self.run_play(tasks, variables, root)
            self.assertNotEqual(outcome.returncode, 0)
            self.assertIn("Verify the actual recovery hypervisor identity", outcome.stdout)
            self.assertNotIn("TASK [Require the existing persistent isolation", outcome.stdout)
            self.assertNotIn("synthetic-bootstrap-canary", outcome.stdout + outcome.stderr)

    def test_native_policy_readback_is_read_only_and_blocks_storage_on_drift(self):
        source = yaml.safe_load((ROLE / "tasks/recovery-preflight.yml").read_text())
        boundary = next(i for i, task in enumerate(source)
                        if task["name"] == "Inspect the generic source without following symlinks")
        for matches in [True, False]:
            with self.subTest(matches=matches), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                shared = root / 'shared/tasks'
                shared.mkdir(parents=True)
                (shared / 'aap-isolation-prepare.yml').write_text(yaml.safe_dump([
                    {'name': 'Fixture native transaction', 'ansible.builtin.set_fact': {
                        'fixture_lock': True, 'aap_isolation_autodeploy_root': '/wrong-caller-project'}},
                    {'name': 'Fixture uses the actual common source inside prepare', 'ansible.builtin.assert': {'that': [
                        "aap_isolation_autodeploy_root == __linux_vm_firewall_source.path ~ '/source'"]}}]))
                (shared / 'aap-isolation-observe.yml').write_text(yaml.safe_dump([
                    {'name': 'Fixture native readback', 'ansible.builtin.assert': {'that': [
                        'fixture_lock', 'aap_isolation_require_match', 'fixture_native_matches']}}]))
                (shared / 'aap-isolation-finish.yml').write_text(yaml.safe_dump([
                    {'name': 'Fixture cleanup', 'ansible.builtin.file': {
                        'path': str(root / 'cleaned'), 'state': 'touch'}}]))
                tasks = deepcopy(source[:boundary])
                for task in tasks:
                    if task['name'].startswith('Verify the actual'):
                        task['ansible.builtin.command']['argv'] = [sys.executable, '-c', "print('1' * 32)"]
                    if task['name'].startswith('Verify current native firewall'):
                        fetch = task['block'][0]
                        fetch.pop('ansible.builtin.git')
                        fetch['ansible.builtin.copy'] = {
                            'src': str(root / 'shared') + '/',
                            'dest': '{{ __linux_vm_firewall_source.path }}/source/'}
                tasks.append({'name': 'Fixture first storage operation', 'ansible.builtin.file': {
                    'path': str(root / 'storage'), 'state': 'touch'}})
                variables = {'role_path': str(ROLE), 'ansible_host': '192.0.2.10',
                    'aap_hactar_source_revision': 'a' * 40,
                    'hactar_source_public_ip': '198.51.100.10', 'fixture_native_matches': matches,
                    'provisioning': {'hypervisor_pin': pin(), 'generic_image': True,
                        'isolation_policy': {'bridges': ['fixture0']}, 'guest_ssh_user': 'fixture',
                        'guest_ssh_password': 'synthetic-secret-canary',
                        'guest_become_password': 'synthetic-secret-canary'}}
                result = self.run_play(tasks, variables, root)
                self.assertEqual(result.returncode == 0, matches, result.stdout + result.stderr)
                self.assertEqual((root / 'storage').exists(), matches)
                self.assertTrue((root / 'cleaned').exists())
                self.assertNotIn('synthetic-secret-canary', result.stdout + result.stderr)

    def bootstrap(self, reject):
        tasks = deepcopy(yaml.safe_load((ROLE / "tasks/generic-bootstrap.yml").read_text()))
        with tempfile.TemporaryDirectory(prefix="recovery-bootstrap-test-") as directory:
            root = Path(directory)
            proof = root / "proof.json"
            stub = root / "customize.py"
            stub.write_text(
                "import json,pathlib,sys\n"
                "args=sys.argv[1:]; selected=args[args.index('--password')+1]; user,kind,path=selected.split(':',2)\n"
                "assert kind=='file' and pathlib.Path(path).read_text().strip()=='synthetic-bootstrap-canary'\n"
                "assert 'synthetic-bootstrap-canary' not in ' '.join(args)\n"
                "assert '--no-network' in args\n"
                "pathlib.Path(" + repr(str(proof)) + ").write_text(json.dumps({'workspace':str(pathlib.Path(path).parent),'password_file_mode':pathlib.Path(path).stat().st_mode & 511}))\n"
                "raise SystemExit(" + ("1" if reject else "0") + ")\n")
            for task in tasks[1]["block"]:
                if task["name"].startswith("Customize the new generic clone"):
                    argv = task["ansible.builtin.command"]["argv"]
                    task["ansible.builtin.command"]["argv"] = [sys.executable, str(stub)] + argv[1:]
            variables = {"role_path": str(ROLE), "linux_vm_deployment_name": "fixture-v07",
                         "linux_vm_deployment_disk": str(root / "new-clone.qcow2"),
                         "provisioning": {"guest_ssh_user": "fixture", "guest_ssh_password": "synthetic-bootstrap-canary",
                                          "vm_domain": "example.invalid"}}
            outcome = self.run_play(tasks, variables, root)
            self.assertEqual(outcome.returncode == 0, not reject, outcome.stdout + outcome.stderr)
            data = json.loads(proof.read_text())
            self.assertEqual(data["password_file_mode"], 0o600)
            self.assertFalse(Path(data["workspace"]).exists(), "Private bootstrap workspace must be removed on success and failure")
            self.assertNotIn("synthetic-bootstrap-canary", outcome.stdout + outcome.stderr)

    def test_real_bootstrap_uses_file_password_and_cleans_temporary_private_keys(self):
        self.bootstrap(False)

    def test_failed_customization_also_removes_private_bootstrap_files(self):
        self.bootstrap(True)


if __name__ == "__main__":
    unittest.main()
