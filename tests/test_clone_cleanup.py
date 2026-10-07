"""Verify that cleanup refuses protected accounts before deleting anything."""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CloneCleanupTests(unittest.TestCase):
    def assert_account_protected(self, account, automation_account, privileged=False):
        template = (ROOT / "src/roles/linux_vm/templates/clean_linux_clone.sh.j2").read_text()
        script = template.replace(
            "{{ provisioning.aap_service_user | quote }}", shlex.quote(account)
        ).replace(
            "{{ provisioning.guest_ssh_user | quote }}", shlex.quote(automation_account)
        )
        shell = shutil.which("sh")
        with tempfile.TemporaryDirectory() as directory:
            tools = Path(directory)
            marker = tools / "mutation-attempted"
            for name in ("rm", "find", "userdel", "dnf", "truncate"):
                tool = tools / name
                tool.write_text(
                    "#!/bin/sh\nprintf attempted > " + shlex.quote(str(marker)) + "\nexit 99\n"
                )
                tool.chmod(0o700)
            if privileged:
                for name, body in {
                    "getent": "printf '%s\\n' 'example-service:x:0:0::/home/example-service:/bin/sh'",
                    "id": "printf '0\\n'",
                }.items():
                    tool = tools / name
                    tool.write_text("#!/bin/sh\n" + body + "\n")
                    tool.chmod(0o700)
            env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ["PATH"])
            result = subprocess.run(
                [shell], input=script, env=env, text=True,
                capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertFalse(marker.exists(), "Cleanup attempted a mutation before validation")

    def test_preserves_root(self):
        self.assert_account_protected("root", "example-automation")

    def test_preserves_automation_access_account(self):
        self.assert_account_protected("example-automation", "example-automation")

    def test_preserves_any_account_with_uid_zero(self):
        self.assert_account_protected("example-service", "example-automation", privileged=True)


if __name__ == "__main__":
    unittest.main()
