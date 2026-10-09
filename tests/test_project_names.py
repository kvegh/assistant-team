import importlib.util
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parents[1]/'src/lib/project-names.py'
spec=importlib.util.spec_from_file_location('names',SOURCE);names=importlib.util.module_from_spec(spec);spec.loader.exec_module(names)

class ProjectNameTests(unittest.TestCase):
    def test_timestamp_extensions_allow_long_original_base_without_arbitrary_long_names(self):
        self.assertEqual(names.validate('a'*40+'-0910260800'),'a'*40+'-0910260800')
        self.assertEqual(names.validate('a'*40+'-0910260800-1010261200'),'a'*40+'-0910260800-1010261200')
        for invalid in ['a'*41,'a'*40+'-9913260800','a'*40+'-0910260800x','../other','UPPER']:
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):names.validate(invalid)

    def test_actual_socket_length_limits_reject_long_name_or_multibyte_home(self):
        names.validate('demo-0910260800','/tmp/h')
        with self.assertRaisesRegex(ValueError,'socket path too long'):
            names.validate('a'*40+'-0910260800','/home/runtime-user')
        with self.assertRaisesRegex(ValueError,'socket path too long'):
            names.validate('demo','/'+('ü'*40))
