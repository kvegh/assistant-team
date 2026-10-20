"""Verify graceful shutdown preserves domain definitions and never force-stops."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VmShutdownTests(unittest.TestCase):
    def test_shutdown_changes_only_selected_domain_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "state.json"
            fixture.write_text(json.dumps({"example-1": "running", "example-5": "running"}))
            calls = root / "calls.jsonl"
            virsh = root / "virsh"
            virsh.write_text("""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
statefile = Path(os.environ['SHUTDOWN_TEST_STATE'])
state = json.loads(statefile.read_text())
args = sys.argv[1:]
with open(os.environ['SHUTDOWN_TEST_CALLS'], 'a') as log:
    log.write(json.dumps(args) + '\\n')
if args == ['list', '--all', '--name']:
    print('\\n'.join(state))
elif args[0] == 'domstate':
    print(state[args[1]])
elif args == ['shutdown', 'example-1']:
    state['example-1'] = 'shut off'
    statefile.write_text(json.dumps(state))
else:
    raise SystemExit('Forbidden virsh operation')
""")
            virsh.chmod(0o700)
            play = root / "shutdown.yml"
            play.write_text("- hosts: localhost\n  gather_facts: false\n  roles: [linux_vm_shutdown]\n")
            result = subprocess.run(
                ["ansible-playbook", "-i", "localhost,", "-c", "local", str(play), "-e", json.dumps({
                    "shutdown_vm_name": "example-1", "__inventory_vm_guard_matches": [{"id": 1}],
                })], cwd=ROOT, text=True, capture_output=True, check=False,
                env=dict(os.environ, PATH=directory + os.pathsep + os.environ["PATH"],
                         ANSIBLE_LOCAL_TEMP=str(root / "tmp"), ANSIBLE_REMOTE_TEMP=str(root / "remote"), ANSIBLE_NOCOLOR="1",
                         ANSIBLE_ROLES_PATH=str(ROOT / "src/roles"), SHUTDOWN_TEST_STATE=str(fixture),
                         SHUTDOWN_TEST_CALLS=str(calls)),
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(fixture.read_text()), {"example-1": "shut off", "example-5": "running"})
            commands = [json.loads(line) for line in calls.read_text().splitlines()]
            self.assertEqual([args for args in commands if args[0] == "shutdown"], [["shutdown", "example-1"]])
            self.assertTrue(all(args[0] in {"list", "domstate", "shutdown"} for args in commands))


if __name__ == "__main__":
    unittest.main()
