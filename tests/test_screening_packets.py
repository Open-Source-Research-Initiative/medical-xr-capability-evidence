"""Contributor packet integrity and public issue-map coverage; no scientific validation."""
import copy
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('screening_packet', ROOT / 'scripts/prepare_screening_packet.py')
PACKET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKET)
RUN = ROOT / 'data/runs/2026-11-17'


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


class WorkMapChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads((RUN / 'work-plan.json').read_text(encoding='utf-8'))
        cls.remaining = rows(RUN / 'remaining-publications.csv')
        cls.integrated = rows(RUN / 'integrated-publication-ids.csv')
        cls.issues = json.loads((RUN / 'issue-map.json').read_text(encoding='utf-8'))['issues']

    def test_exact_partition_of_frozen_public_inventory(self):
        inventory = [row['publication_id'] for row in rows(ROOT / 'data/open/ledger-projections/all-id-status-current.csv')]
        pending = [row['publication_id'] for row in self.remaining]
        integrated = [row['publication_id'] for row in self.integrated]
        self.assertEqual(len(inventory), len(set(inventory)))
        self.assertEqual(len(pending), len(set(pending)))
        self.assertEqual(len(integrated), len(set(integrated)))
        self.assertEqual((len(inventory), len(integrated), len(pending)), (18976, 11076, 7900))
        self.assertFalse(set(pending) & set(integrated))
        self.assertEqual(set(inventory), set(pending) | set(integrated))
        frozen_adjudicated = {row['publication_id'] for row in rows(ROOT / 'data/open/ledger-projections/adjudicated-current.csv')}
        self.assertTrue(frozen_adjudicated <= set(integrated))
        self.assertEqual((self.plan['inventory_n'], self.plan['integrated_n'], self.plan['remaining_n']),
                         (len(inventory), len(integrated), len(pending)))

    def test_every_pending_id_has_one_batch_package_and_public_issue(self):
        batches = self.plan['batches']
        packages = self.plan['packages']
        issue_map = {item['key']: item for item in self.issues}
        self.assertEqual(len(batches), 158)
        self.assertEqual(len(packages), 35)
        self.assertEqual(len(issue_map), len(self.issues))
        self.assertEqual(len(self.issues), 49)
        self.assertEqual(len({item['batch_id'] for item in batches}), len(batches))
        self.assertEqual(len({item['key'] for item in packages}), len(packages))
        assigned = {}
        package_map = {item['key']: item for item in packages}
        for batch in batches:
            with self.subTest(batch=batch['batch_id']):
                ids = batch['publication_ids']
                self.assertEqual(batch['n'], 50)
                self.assertEqual(len(ids), 50)
                self.assertEqual(len(set(ids)), 50)
                package = package_map[batch['work_package']]
                self.assertIn(batch['batch_id'], package['batches'])
                self.assertEqual(batch['issue_url'], package['issue_url'])
                self.assertEqual(batch['issue_url'], issue_map[package['key']]['url'])
                self.assertEqual(package['issue_number'], issue_map[package['key']]['number'])
                self.assertTrue(batch['issue_url'].endswith('/issues/' + str(package['issue_number'])))
                self.assertEqual(len(batch['fixed_sample_ids']), len(set(batch['fixed_sample_ids'])))
                self.assertTrue(set(batch['fixed_sample_ids']) <= set(ids))
                for publication_id in ids:
                    self.assertNotIn(publication_id, assigned)
                    assigned[publication_id] = (batch['batch_id'], batch['work_package'], batch['issue_url'])
        for package in packages:
            members = [item for item in batches if item['work_package'] == package['key']]
            self.assertEqual([item['batch_id'] for item in members], package['batches'])
            self.assertGreaterEqual(len(members), 1)
            self.assertLessEqual(len(members), 5)
            self.assertEqual(package['n'], sum(item['n'] for item in members))
            self.assertEqual((package['first_batch'], package['last_batch']),
                             (package['batches'][0], package['batches'][-1]))
        self.assertEqual(assigned, {row['publication_id']: (row['batch_id'], row['work_package'], row['issue_url'])
                                    for row in self.remaining})
        summary = rows(RUN / 'work-packages.csv')
        self.assertEqual(len(summary), 158)
        self.assertEqual(len({row['batch_id'] for row in summary}), 158)
        self.assertEqual({row['batch_id']: (row['work_package'], int(row['n']), row['issue_url'], int(row['fixed_sample_n']))
                          for row in summary},
                         {batch['batch_id']: (batch['work_package'], batch['n'], batch['issue_url'], len(batch['fixed_sample_ids']))
                          for batch in batches})

    def test_all_batch_inputs_are_bound_to_unchanged_frozen_manifest(self):
        manifest_data = (ROOT / 'provenance/legacy-file-manifest.csv').read_bytes()
        self.assertEqual(hashlib.sha256(manifest_data).hexdigest(), self.plan['frozen_file_manifest_sha256'])
        legacy_rows = PACKET.csv_rows(manifest_data)
        legacy = {item['path'].replace('\\', '/'): item for item in legacy_rows}
        self.assertEqual(len(legacy), len(legacy_rows))
        for batch in self.plan['batches']:
            with self.subTest(batch=batch['batch_id']):
                self.assertEqual({item['name'] for item in batch['inputs']}, PACKET.NAMES)
                self.assertEqual(len(batch['inputs']), 5)
                for item in batch['inputs']:
                    path = PACKET.safe_member(item['archive_path'])
                    self.assertEqual(path.name, item['name'])
                    self.assertEqual(path.parent.name, batch['batch_id'])
                    original = legacy[item['archive_path']]
                    self.assertEqual((item['sha256'], item['bytes']), (original['sha256'], int(original['bytes'])))
                    self.assertGreater(item['bytes'], 0)


class PacketChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / 'new-packet'
        self.ids = ['P0000001', 'P0000002']
        self.payload = {
            'source.csv': b'publication_id,title\r\nP0000001,First source\r\nP0000002,Second source\r\n',
            'pass-A.csv': b'publication_id,author,decision\nP0000001,Original_A,INCLUDE\nP0000002,Original_A,EXCLUDE\n',
            'pass-B.csv': b'publication_id,author,decision\nP0000002,Original_B,EXCLUDE\nP0000001,Original_B,UNCERTAIN\n',
            'audit-selection.json': b'{"sample_ids": ["P0000002"]}\n',
            'required-audit.csv': b'publication_id,reason\nP0000002,original fixed sample\n',
        }
        self.plan = {
            'format': 'medical-xr-issue-work-plan/1', 'method': '0.4.6 plus addenda01-04', 'codebook': '0.2',
            'batches': [{'batch_id': 'B0001', 'work_package': 'S01-01', 'n': 2,
                         'publication_ids': self.ids, 'fixed_sample_ids': ['P0000002'],
                         'issue_url': 'https://example.test/issues/1', 'inputs': []}],
        }
        self.legacy = {}
        self.rebind()

    def rebind(self):
        """Bind a synthetic frozen fixture; mutation tests exercise the later semantic checks."""
        self.plan['batches'][0]['inputs'] = []
        self.legacy = {}
        for name, data in self.payload.items():
            member = 'paired/B0001/' + name
            digest = hashlib.sha256(data).hexdigest()
            self.plan['batches'][0]['inputs'].append({'name': name, 'archive_path': member,
                                                    'sha256': digest, 'bytes': len(data)})
            self.legacy[member] = {'sha256': digest, 'bytes': str(len(data))}

    def memory_read(self, name, expected_bytes):
        return self.payload[Path(name).name]

    def build(self, reader=None):
        return PACKET.build_packet(self.plan, 'B0001', self.legacy, reader or self.memory_read, self.output)

    def assert_preserved(self, metadata):
        self.assertEqual({path.name for path in self.output.iterdir()}, PACKET.NAMES | {'packet.json'})
        for name, data in self.payload.items():
            self.assertEqual((self.output / name).read_bytes(), data)
        self.assertEqual(metadata['publication_ids'], self.ids)
        self.assertEqual(metadata['fixed_sample_ids'], ['P0000002'])
        self.assertEqual(metadata['source_reading_credit_from_packet_creation'], 0)
        self.assertEqual(metadata['human_verification'], 'PENDING')
        self.assertNotIn('decision', metadata)
        self.assertEqual(json.loads((self.output / 'packet.json').read_text(encoding='utf-8')), metadata)

    def test_directory_packet_preserves_every_byte_without_assessing_records(self):
        source = self.root / 'restored-archive'
        for name, data in self.payload.items():
            member = source / 'paired/B0001' / name
            member.parent.mkdir(parents=True, exist_ok=True)
            member.write_bytes(data)
        self.assert_preserved(self.build(PACKET.directory_reader(source)))

    def test_zip_packet_preserves_every_byte_without_extracting_other_members(self):
        archive_path = self.root / 'source.zip'
        with zipfile.ZipFile(archive_path, 'w') as archive:
            for name, data in self.payload.items():
                archive.writestr('paired/B0001/' + name, data)
            archive.writestr('unrelated.txt', 'not part of the selected packet')
        with zipfile.ZipFile(archive_path) as archive:
            self.assert_preserved(self.build(PACKET.zip_reader(archive)))

    def test_hash_mismatch_fails_before_creating_output(self):
        self.payload['source.csv'] = self.payload['source.csv'].replace(b'First', b'F1rst')
        with self.assertRaisesRegex(PACKET.PacketError, 'hash or size mismatch'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_plan_cannot_replace_frozen_hash(self):
        self.plan['batches'][0]['inputs'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(PACKET.PacketError, 'differs from the frozen public manifest'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_original_pass_must_have_exact_assigned_membership(self):
        self.payload['pass-B.csv'] = self.payload['pass-B.csv'].replace(b'P0000002', b'P0000003')
        self.rebind()
        with self.assertRaisesRegex(PACKET.PacketError, 'membership differs'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_duplicate_source_id_is_rejected(self):
        self.payload['source.csv'] = self.payload['source.csv'].replace(b'P0000002', b'P0000001')
        self.rebind()
        with self.assertRaisesRegex(PACKET.PacketError, 'membership differs'):
            self.build()

    def test_original_fixed_sample_cannot_be_redrawn(self):
        self.plan['batches'][0]['fixed_sample_ids'] = ['P0000001']
        with self.assertRaisesRegex(PACKET.PacketError, 'Fixed audit sample changed'):
            self.build()
        self.assertFalse(self.output.exists())

    def test_required_audit_must_include_original_sample(self):
        self.payload['required-audit.csv'] = b'publication_id,reason\nP0000001,other reason\n'
        self.rebind()
        with self.assertRaisesRegex(PACKET.PacketError, 'audit/sample membership is inconsistent'):
            self.build()

    def test_existing_output_is_preserved(self):
        self.output.mkdir()
        marker = self.output / 'existing.txt'
        marker.write_bytes(b'prior work')
        with self.assertRaisesRegex(PACKET.PacketError, 'Output already exists'):
            self.build()
        self.assertEqual(marker.read_bytes(), b'prior work')
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_negative_byte_counts_are_rejected(self):
        self.plan['batches'][0]['inputs'][0]['bytes'] = -1
        with self.assertRaisesRegex(PACKET.PacketError, 'Invalid batch input byte count'):
            self.build()

    def test_unsafe_member_paths_are_rejected(self):
        for member in ['', '../source.csv', '/source.csv', 'a/../../source.csv',
                       'C:/source.csv', 'C:source.csv', 'a\\source.csv', 'a/./source.csv',
                       'a//source.csv', 'a/source.csv:stream', 'a/line\nsource.csv', 'a/\x00source.csv']:
            with self.subTest(member=repr(member)):
                with self.assertRaises(PACKET.PacketError):
                    PACKET.safe_member(member)

    def test_duplicate_zip_member_is_rejected(self):
        buffer = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(buffer, 'w') as archive:
                archive.writestr('paired/B0001/source.csv', self.payload['source.csv'])
                archive.writestr('paired/B0001/source.csv', self.payload['source.csv'])
        with zipfile.ZipFile(buffer) as archive:
            with self.assertRaisesRegex(PACKET.PacketError, 'Missing or duplicate ZIP member'):
                PACKET.zip_reader(archive)('paired/B0001/source.csv', len(self.payload['source.csv']))

    def test_missing_zip_member_is_rejected(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w'):
            pass
        with zipfile.ZipFile(buffer) as archive:
            with self.assertRaisesRegex(PACKET.PacketError, 'Missing or duplicate ZIP member'):
                PACKET.zip_reader(archive)('paired/B0001/source.csv', 0)

    def test_swapped_filename_binding_is_rejected(self):
        item = self.plan['batches'][0]['inputs'][0]
        item['archive_path'] = 'paired/B0001/pass-A.csv'
        with self.assertRaisesRegex(PACKET.PacketError, 'assigned batch and filename'):
            self.build()

    def test_batch_must_be_uniquely_assigned(self):
        self.plan['batches'].append(copy.deepcopy(self.plan['batches'][0]))
        with self.assertRaisesRegex(PACKET.PacketError, 'not uniquely assigned'):
            self.build()

    def test_malformed_csv_headers_and_row_width_are_rejected(self):
        for data in [b'publication_id,publication_id\nP0000001,P0000002\n',
                     b'publication_id,label\nP0000001\n', b'publication_id\nP0000001,extra\n']:
            with self.subTest(data=data):
                with self.assertRaises(PACKET.PacketError):
                    PACKET.csv_rows(data)


if __name__ == '__main__':
    unittest.main()
