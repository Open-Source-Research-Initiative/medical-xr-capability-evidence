"""A lookup preserves original rows, distinguishes pending work, and catches ambiguous joins."""
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/lookup_publication.py'
SPEC = importlib.util.spec_from_file_location('lookup_publication', SCRIPT)
LOOKUP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LOOKUP)


class LookupTests(unittest.TestCase):
    def fixture(self, directory, adjudicated=True):
        root = Path(directory)
        tables = root / 'data/open/ledger-projections'
        tables.mkdir(parents=True)
        for key, (filename, fields) in LOOKUP.TABLES.items():
            fields = sorted(fields | {'year', 'model_version'})
            with (tables / filename).open('w', encoding='utf-8', newline='') as handle:
                writer = csv.DictWriter(handle, fields, lineterminator='\n')
                writer.writeheader()
                if key == 'adjudication' and not adjudicated:
                    continue
                row = {name: '' for name in fields}
                row.update({'publication_id': 'P0000001', 'year': '2020'})
                if 'eligibility' in fields:
                    row['eligibility'] = 'UNCERTAIN'
                if 'adjudicated_eligibility' in fields:
                    row['adjudicated_eligibility'] = 'EXCLUDE'
                writer.writerow(row)
        return root

    def test_preserves_strings_and_unknown_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            record = LOOKUP.lookup('P0000001', self.fixture(directory))
            self.assertEqual(record['records']['inventory']['year'], '2020')
            self.assertEqual(record['records']['pass_A']['model_version'], '')
            self.assertEqual(record['records']['pass_A']['eligibility'], 'UNCERTAIN')

    def test_missing_adjudication_is_null(self):
        with tempfile.TemporaryDirectory() as directory:
            record = LOOKUP.lookup('P0000001', self.fixture(directory, adjudicated=False))
            self.assertIsNone(record['records']['adjudication'])

    def test_unknown_inventory_id_is_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'absent from the frozen inventory'):
                LOOKUP.lookup('P0000002', self.fixture(directory))

    def test_short_id_is_not_silently_rewritten(self):
        with self.assertRaisesRegex(ValueError, 'full publication_id'):
            LOOKUP.lookup('P1')

    def test_duplicate_initial_is_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            path = root / 'data/open/ledger-projections/pass-A-original-initials.csv'
            lines = path.read_text(encoding='utf-8').splitlines()
            with path.open('a', encoding='utf-8') as handle:
                handle.write(lines[1] + '\n')
            with self.assertRaisesRegex(ValueError, 'Duplicate publication_id'):
                LOOKUP.lookup('P0000001', root)

    def test_missing_initial_is_not_pending_adjudication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            path = root / 'data/open/ledger-projections/pass-B-original-initials.csv'
            path.write_text(path.read_text(encoding='utf-8').splitlines()[0] + '\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Missing original initial assessment'):
                LOOKUP.lookup('P0000001', root)

    def test_truncated_matching_row_is_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            path = root / 'data/open/ledger-projections/pass-B-original-initials.csv'
            header = path.read_text(encoding='utf-8').splitlines()[0]
            fields = header.split(',')
            values = ['P0000001' if field == 'publication_id' else '' for field in fields[:-1]]
            path.write_text(header + '\n' + ','.join(values) + '\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'row width differs'):
                LOOKUP.lookup('P0000001', root)

    def test_json_cli_works_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPT), 'P0000314', '--json'],
                                    cwd=directory, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(result.stdout)
            self.assertEqual(record['publication_id'], 'P0000314')
            self.assertEqual(record['records']['pass_A']['publication_id'], 'P0000314')


if __name__ == '__main__':
    unittest.main()
