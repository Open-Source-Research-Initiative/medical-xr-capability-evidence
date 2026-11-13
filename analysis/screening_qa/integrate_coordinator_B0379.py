"""Validate and copy the coordinator's completed pass without overwriting.

Structural checks do not validate screening judgments or constitute an audit.
The source and destination remain byte-identical and reviewer identity remains
on every row. The independent Sol pass is not read by this script.
"""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path('outputs/Medical-XR-Calibration-and-Full-Screening')
source = root / 'shared/batches/B0379.csv'
original = root / 'terra_coordinator/B0379.csv'
destination = root / 'terra/B0379.csv'
receipt = Path('work/screening_qa/terra_coordinator-B0379-integration.json')

def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

if destination.exists() or receipt.exists():
    raise FileExistsError('A destination or receipt already exists; refusing overwrite')
base = rows(source)
assessed = rows(original)
source_ids = {r['publication_id']: r for r in base}
assert len(base) == len(source_ids) == len(assessed) == 50
assert len({r['publication_id'] for r in assessed}) == 50
assert {r['publication_id'] for r in assessed} == set(source_ids)
for row in assessed:
    ident = row['publication_id']
    assert row['reviewer'] == 'Coordinator_Terra_shard_3'
    assert row['batch_id'] == 'B0379'
    assert row['eligibility'] in {'INCLUDE', 'EXCLUDE', 'UNCERTAIN'}
    assert row['human_verification'] == 'PENDING'
    assert ident in row['source_coordinate']
    assert row['rationale'] and row['supporting_evidence'] and row['prior_exposure']
    for field in ('record_ids_json', 'source_memberships_json'):
        assert sorted(json.loads(row[field])) == sorted(json.loads(source_ids[ident][field]))
    assert row['supporting_evidence'].startswith('exact abstract excerpt: ')
    assert row['supporting_evidence'].split(': ', 1)[1] in source_ids[ident]['abstract']
content = original.read_bytes()
with destination.open('xb') as out:
    out.write(content)
digest = hashlib.sha256(content).hexdigest()
assert hashlib.sha256(destination.read_bytes()).hexdigest() == digest
record = {
    'created_utc': datetime.now(timezone.utc).isoformat(), 'batch': 'B0379',
    'source': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'original': str(original), 'integrated_copy': str(destination), 'sha256': digest,
    'count': len(assessed), 'ids': sorted(source_ids),
    'reviewer': 'Coordinator_Terra_shard_3',
    'limitations': 'Structural and literal-quotation validation only; classification requires independent Astra audit, and human verification remains pending.'}
with receipt.open('x', encoding='utf-8') as f:
    json.dump(record, f, indent=2)
    f.write('\n')
print(json.dumps(record, indent=2))
