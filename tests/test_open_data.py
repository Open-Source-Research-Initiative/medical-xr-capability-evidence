"""Archive corruption and unsafe-path regressions for the public data verifier."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location('open_data', Path(__file__).resolve().parents[1] / 'scripts/verify_open_data.py')
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class ArchiveChecks(unittest.TestCase):
    def fixture(self, directory, name='records.csv', body=b'publication_id\nP0000001\n'):
        path = Path(directory) / 'fixture.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr(name, body)
        return path, {name: {'bytes': str(len(body)), 'sha256': hashlib.sha256(body).hexdigest()}}

    def test_complete_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            path, manifest = self.fixture(directory)
            self.assertEqual(CHECK.verify_archive(path, manifest)['archive_files'], 1)

    def test_changed_member(self):
        with tempfile.TemporaryDirectory() as directory:
            path, manifest = self.fixture(directory)
            manifest['records.csv']['sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'hash differs'):
                CHECK.verify_archive(path, manifest)

    def test_missing_member(self):
        with tempfile.TemporaryDirectory() as directory:
            path, manifest = self.fixture(directory)
            manifest['missing.csv'] = manifest['records.csv']
            with self.assertRaisesRegex(ValueError, 'coverage differs'):
                CHECK.verify_archive(path, manifest)

    def test_unlisted_member(self):
        with tempfile.TemporaryDirectory() as directory:
            path, _ = self.fixture(directory)
            with self.assertRaisesRegex(ValueError, 'unlisted archive member'):
                CHECK.verify_archive(path, {})

    def test_parent_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            path, manifest = self.fixture(directory, '../outside.csv')
            with self.assertRaisesRegex(ValueError, 'Unsafe artifact path'):
                CHECK.verify_archive(path, manifest)

    def test_duplicate_id(self):
        with self.assertRaisesRegex(ValueError, 'duplicate publication ID'):
            CHECK.publication_ids([{'publication_id': 'P0000001'}, {'publication_id': 'P0000001'}])

    def test_short_csv_row(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'table.csv'
            path.write_text('publication_id,label\nP0000001\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'row width'):
                CHECK.read_table(path)


if __name__ == '__main__':
    unittest.main()
