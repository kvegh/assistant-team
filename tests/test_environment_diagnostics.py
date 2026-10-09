import importlib.util
import json
import pathlib
import tarfile
import tempfile
import unittest

SOURCE=pathlib.Path(__file__).parents[1]/'src/roles/project_framework/files/environment-diagnostics.py'
spec=importlib.util.spec_from_file_location('diagnostics',SOURCE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class DiagnosticTests(unittest.TestCase):
    def test_metadata_export_has_no_auth_project_or_chat_content(self):
        with tempfile.TemporaryDirectory() as home:
            module.record(home,'login','failed',1)
            directory=pathlib.Path(home)/'environment-logs'
            (directory/'credential.json').write_text('DO_NOT_EXPORT')
            archive=pathlib.Path(home)/'metadata.tar.gz';module.export(home,archive)
            with tarfile.open(archive) as bundle:
                self.assertEqual(bundle.getnames(),['events.jsonl'])
                data=bundle.extractfile('events.jsonl').read().decode()
            self.assertNotIn('DO_NOT_EXPORT',data)
            self.assertEqual(json.loads(data)['exit_code'],1)
            self.assertEqual((directory.stat().st_mode & 0o777),0o700)

    def test_export_rejects_unknown_fields_and_symlink(self):
        with tempfile.TemporaryDirectory() as home:
            module.record(home,'start','failed',1)
            path=pathlib.Path(home)/'environment-logs/events.jsonl'
            value=json.loads(path.read_text());value['token']='fixture'
            path.write_text(json.dumps(value)+'\n')
            with self.assertRaises(ValueError):module.export(home,pathlib.Path(home)/'bad.tar.gz')
            path.unlink();path.symlink_to(pathlib.Path(home)/'private')
            with self.assertRaises(ValueError):module.export(home,pathlib.Path(home)/'bad.tar.gz')

    def test_text_log_correlates_and_explains_failure_without_arbitrary_text(self):
        with tempfile.TemporaryDirectory() as home:
            module.record(home,'start','failed',1)
            directory=pathlib.Path(home)/'environment-logs'
            event=json.loads((directory/'events.jsonl').read_text())
            text=(directory/'events.log').read_text()
            self.assertIn('start | failed | exit 1',text)
            self.assertIn(event['correlation_id'],text)
            self.assertIn('Inspect systemctl --user status',text)
            self.assertEqual((directory/'events.log').stat().st_mode & 0o777,0o600)

    def test_both_log_formats_rotate_and_reject_symlinks(self):
        with tempfile.TemporaryDirectory() as home:
            module.record(home,'status','completed',0)
            directory=pathlib.Path(home)/'environment-logs'
            for name in ['events.log','events.jsonl']:
                (directory/name).write_text('x'*1048577)
            module.record(home,'status','completed',0)
            self.assertTrue((directory/'events.log.1').exists())
            self.assertTrue((directory/'events.jsonl.1').exists())
            (directory/'events.log').unlink()
            (directory/'events.log').symlink_to(directory/'private')
            with self.assertRaises(ValueError):module.record(home,'status','completed',0)

    def test_unknown_failure_text_cannot_be_logged(self):
        with tempfile.TemporaryDirectory() as home:
            with self.assertRaises(ValueError):module.record(home,'start','exception containing fixture secret')

    def test_archive_collision_is_specific_safe_and_exportable(self):
        with tempfile.TemporaryDirectory() as home:
            module.record(home,'archive','archive_collision',1)
            directory=pathlib.Path(home)/'environment-logs'
            event=json.loads((directory/'events.jsonl').read_text())
            self.assertEqual(event['result'],'archive_collision')
            text=(directory/'events.log').read_text()
            self.assertIn('without shutdown',text)
            self.assertIn('rename-project OLD NEW',text)
            module.export(home,pathlib.Path(home)/'metadata.tar.gz')
