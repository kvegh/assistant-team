"""Exercise recovery identity guards with the actual Ansible YAML loader."""

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

from ansible.errors import AnsibleFilterError
from ansible.parsing.dataloader import DataLoader


ROOT = Path(__file__).resolve().parents[1]


def plugin(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'src/filter_plugins' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RECOVERY = plugin('linux_vm_recovery')
REGISTRATION = plugin('inventory_registration')


class AnsibleIntegerGuardTests(unittest.TestCase):
    def setUp(self):
        self.values = DataLoader().load('''
pin:
  address: 192.0.2.10
  user: fixture
  port: 22
  machine_id: '11111111111111111111111111111111'
  host_keys: [ssh-ed25519 AAAA]
hosts:
  count: 1
  next: null
  results:
    - id: 19
      name: example-v16
      inventory: 3
      enabled: true
      variables: '{"assistant_vm_name":"example-v16","ansible_host":"198.51.100.60"}'
groups:
  count: 1
  next: null
  results:
    - id: 2
      name: assistant_team
      inventory: 3
''')

    def test_recovery_pin_accepts_the_native_loader_integer(self):
        pin = self.values['pin']
        self.assertIsInstance(pin['port'], int)
        self.assertNotIsInstance(pin['port'], bool)
        self.assertEqual(RECOVERY.recovery_pin(pin, '192.0.2.10'), pin)

    def test_recovery_port_still_refuses_booleans_strings_floats_and_invalid_ranges(self):
        for value in (True, False, '22', 22.0, 0, -1, 65536):
            with self.subTest(value=value), self.assertRaises(AnsibleFilterError):
                RECOVERY.recovery_pin(dict(self.values['pin'], port=value), '192.0.2.10')

    def test_registration_accepts_native_loader_host_and_group_ids(self):
        result = REGISTRATION.repair_binding(
            self.values['hosts'], self.values['groups'], '3', 'example-v16')
        self.assertEqual(result, {'host_id': 19, 'group_id': 2,
                                  'address': '198.51.100.60', 'name': 'example-v16'})

    def test_registration_ids_still_refuse_booleans_strings_floats_and_nonpositive_values(self):
        for field in ('hosts', 'groups'):
            for value in (True, False, '19', 19.0, 0, -1):
                values = deepcopy(self.values)
                values[field]['results'][0]['id'] = value
                with self.subTest(field=field, value=value), self.assertRaises(AnsibleFilterError):
                    REGISTRATION.repair_binding(values['hosts'], values['groups'], '3', 'example-v16')


if __name__ == '__main__':
    unittest.main()
