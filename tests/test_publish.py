import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('publish',Path(__file__).resolve().parents[1]/'scripts'/'publish.py')
publish=importlib.util.module_from_spec(spec);spec.loader.exec_module(publish)

class PublishTests(unittest.TestCase):
    def test_dry_run_never_contacts_github_or_mutates_git(self):
        with patch.object(publish,'run',side_effect=AssertionError('unexpected subprocess')),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(publish.main(['--dry-run']),0)
        self.assertIn('Nenhuma chamada',output.getvalue())

    def test_invalid_destination_is_rejected_before_authenticated_call(self):
        with patch.object(publish,'run',side_effect=AssertionError('unexpected subprocess')):
            with self.assertRaises(publish.PublishError): publish.main(['--owner','bad/owner'])
            with self.assertRaises(publish.PublishError): publish.main(['--name','../other'])
