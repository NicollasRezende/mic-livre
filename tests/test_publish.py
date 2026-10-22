import contextlib
import importlib.util
import io
import hashlib
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('publish',Path(__file__).resolve().parents[1]/'scripts'/'publish.py')
publish=importlib.util.module_from_spec(spec);spec.loader.exec_module(publish)

class PublishTests(unittest.TestCase):
    def test_matching_release_hash_is_accepted_without_downloading(self):
        with tempfile.TemporaryDirectory() as directory:
            apk=Path(directory)/'mic-livre-0.2.1.apk';apk.write_bytes(b'official signed apk')
            data={'assets':[{'name':apk.name,'digest':'sha256:'+hashlib.sha256(apk.read_bytes()).hexdigest()}]}
            with patch.object(publish,'run',side_effect=AssertionError('unnecessary network')):
                publish.verify_asset('owner/repo',data,apk)

    def test_same_filename_with_different_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            apk=Path(directory)/'mic-livre-0.2.1.apk';apk.write_bytes(b'official signed apk')
            data={'assets':[{'name':apk.name,'digest':'sha256:'+'0'*64}]}
            with self.assertRaisesRegex(publish.PublishError,'SHA-256'):
                publish.verify_asset('owner/repo',data,apk)

    def test_missing_remote_digest_downloads_and_checks_actual_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            apk=Path(directory)/'mic-livre-0.2.1.apk';apk.write_bytes(b'official signed apk')
            data={'assets':[{'name':apk.name}]}
            for content in (apk.read_bytes(),b'different apk'):
                def download(*args,check=True):
                    target=Path(args[args.index('--dir')+1])/apk.name
                    target.write_bytes(content)
                with self.subTest(content=content),patch.object(publish,'run',side_effect=download):
                    if content==apk.read_bytes(): publish.verify_asset('owner/repo',data,apk)
                    else:
                        with self.assertRaisesRegex(publish.PublishError,'SHA-256'):
                            publish.verify_asset('owner/repo',data,apk)

    def test_dry_run_never_contacts_github_or_mutates_git(self):
        with patch.object(publish,'run',side_effect=AssertionError('unexpected subprocess')),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(publish.main(['--dry-run']),0)
        self.assertIn('Nenhuma chamada',output.getvalue())

    def test_invalid_destination_is_rejected_before_authenticated_call(self):
        with patch.object(publish,'run',side_effect=AssertionError('unexpected subprocess')):
            with self.assertRaises(publish.PublishError): publish.main(['--owner','bad/owner'])
            with self.assertRaises(publish.PublishError): publish.main(['--name','../other'])
