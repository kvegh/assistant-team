"""Exercise identity reset against a temporary filesystem tree."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class IdentityResetTests(unittest.TestCase):
    def test_handles_a_missing_dbus_directory_and_can_run_again(self):
        source = (ROOT / "src/reset_linux_identity.sh").read_text()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            etc = root / "etc"
            ssh = etc / "ssh"
            ssh.mkdir(parents=True)
            inherited_key = ssh / "ssh_host_example_key"
            inherited_key.write_text("example inherited key")
            machine_id = etc / "machine-id"
            machine_id.write_text("example inherited identity")
            dbus = root / "var/lib/dbus"
            script = source.replace("/etc/", str(etc) + "/").replace(
                "/var/lib/dbus", str(dbus)
            )
            for _ in range(2):
                subprocess.run(["sh"], input=script, text=True, check=True)
                self.assertFalse(inherited_key.exists())
                self.assertEqual(machine_id.read_text(), "")
                self.assertTrue((dbus / "machine-id").is_symlink())
                self.assertEqual((dbus / "machine-id").resolve(), machine_id)


if __name__ == "__main__":
    unittest.main()
