import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'src/roles/agents_connector/files/mcp-results.py'
spec = importlib.util.spec_from_file_location('mcp_results', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MCPResultsTests(unittest.TestCase):
    def result(self, value):
        return {'jsonrpc': '2.0', 'id': 7, 'result': {'content': [{'type': 'text', 'text': json.dumps(value)}], 'isError': False}}

    def test_array_envelope_preserves_original_text_and_id(self):
        response = self.result([{'name': 'peer'}])
        original = copy.deepcopy(response)
        actual = module.normalize(response)
        self.assertEqual(actual['result']['structuredContent'], {'items': [{'name': 'peer'}]})
        self.assertEqual(actual['result']['content'], original['result']['content'])
        self.assertEqual(actual['id'], 7)

    def test_empty_array_and_scalars_are_records_for_strict_clients(self):
        for value in ([], 12, 'value', False, None):
            with self.subTest(value=value):
                actual = module.normalize(self.result(value))['result']['structuredContent']
                self.assertIsInstance(actual, dict)
                self.assertEqual(actual, {'items': value} if isinstance(value, list) else {'value': value})

    def test_objects_errors_and_existing_structured_content_are_unchanged(self):
        samples = [self.result({'ok': True}), {'jsonrpc': '2.0', 'id': 7, 'error': {'code': -1}}]
        error = self.result([]); error['result']['isError'] = True; samples.append(error)
        structured = self.result([]); structured['result']['structuredContent'] = {'already': True}; samples.append(structured)
        for sample in samples:
            self.assertEqual(module.normalize(copy.deepcopy(sample)), sample)

    def test_nonjson_text_tool_definitions_and_notifications_are_unchanged(self):
        sample = self.result([]); sample['result']['content'][0]['text'] = 'ordinary text'
        for response in (sample, {'result': {'tools': []}}, {'method': 'notifications/initialized'}, [], {'result': {'content': []}}):
            self.assertEqual(module.normalize(copy.deepcopy(response)), response)

    def test_bidirectional_stdio_and_child_exit_code_are_preserved(self):
        request = {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call'}
        child = "import sys,json; r=json.loads(sys.stdin.readline()); print(json.dumps({'jsonrpc':'2.0','id':r['id'],'result':{'content':[{'type':'text','text':'[]'}]}}),flush=True);sys.exit(3)"
        actual = subprocess.run([sys.executable, str(SCRIPT), sys.executable, '-c', child], input=json.dumps(request)+'\n', text=True, capture_output=True, timeout=5)
        self.assertEqual(actual.returncode, 3)
        response = json.loads(actual.stdout)
        self.assertEqual(response['id'], 4)
        self.assertEqual(response['result']['structuredContent'], {'items': []})
        self.assertEqual(actual.stderr, '')

    def test_oversized_output_fails_without_echoing_payload(self):
        child = "print('x'*1048577)"
        actual = subprocess.run([sys.executable, str(SCRIPT), sys.executable, '-c', child], input='', text=True, capture_output=True, timeout=5)
        self.assertNotEqual(actual.returncode, 0)
        self.assertEqual(actual.stdout, '')
        self.assertLess(len(actual.stderr), 100)


if __name__ == '__main__':
    unittest.main()
