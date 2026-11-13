"""Finalize a coordinator Terra shard from five manually reviewed partials.

Keep all five originals. Validate source IDs, exact support and source
memberships before writing an original merged CSV and byte-identical pass copy.
No Sol or other reviewer's decisions are read.
"""
import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('batch')
args = p.parse_args()
if not re.fullmatch(r'B\d{4}', args.batch) or not 351 <= int(args.batch[1:]) <= 378:
    raise ValueError('Coordinator finalization is restricted to B0351–B0378')
root = Path('outputs/Medical-XR-Calibration-and-Full-Screening')
folder = root / 'terra_coordinator'
source = root / 'shared/batches' / f'{args.batch}.csv'
original = folder / f'{args.batch}.csv'
destination = root / 'terra' / f'{args.batch}.csv'
receipt = Path('work/screening_qa') / f'terra_coordinator-{args.batch}-integration.json'
if any(p.exists() for p in (original, destination, receipt)):
    raise FileExistsError('Refusing to overwrite an original, integrated copy or receipt')
with source.open(encoding='utf-8-sig', newline='') as f:
    frozen = list(csv.DictReader(f))
paths = [folder / f'{args.batch}-partial-{i:03}.csv' for i in range(1, 6)]
records = []
header = None
for i, path in enumerate(paths):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if header is None:
            header = reader.fieldnames
        if reader.fieldnames != header:
            raise ValueError(f'Incompatible columns: {path}')
        part = list(reader)
    src = frozen[i*10:(i+1)*10]
    if len(part) != 10 or [r['publication_id'] for r in part] != [r['publication_id'] for r in src]:
        raise ValueError(f'Frozen IDs or order differ: {path}')
    for row, base in zip(part, src):
        if row['reviewer'] != 'Coordinator_Terra_shard_3' or row['human_verification'] != 'PENDING':
            raise ValueError(f"Incorrect provenance: {row['publication_id']}")
        if row['batch_id'] != args.batch or row['eligibility'] not in {'INCLUDE','EXCLUDE','UNCERTAIN'}:
            raise ValueError(f"Invalid classification fields: {row['publication_id']}")
        support = row['supporting_evidence']
        match = re.match(r'^exact (abstract|title) excerpt: (.+)$', support, re.S)
        if not match or match.group(2) not in base[match.group(1)]:
            raise ValueError(f"Inexact source excerpt: {row['publication_id']}")
        for field in ('source_memberships_json','record_ids_json'):
            if sorted(json.loads(row[field])) != sorted(json.loads(base[field])):
                raise ValueError(f"Source membership differs: {row['publication_id']}")
    records.extend(part)
if len(frozen) != 50 or len(records) != 50 or len({r['publication_id'] for r in records}) != 50:
    raise ValueError('Expected 50 unique source IDs')
with original.open('x', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=header, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(records)
content = original.read_bytes()
with destination.open('xb') as f:
    f.write(content)
sha = hashlib.sha256(content).hexdigest()
if hashlib.sha256(destination.read_bytes()).hexdigest() != sha:
    raise RuntimeError('Integrated bytes differ')
result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'batch': args.batch,
          'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'partial_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
          'original': str(original), 'integrated_copy': str(destination), 'sha256': sha,
          'count': len(records), 'reviewer': 'Coordinator_Terra_shard_3',
          'limitations': 'Structure and literal quotations only; independent Astra audit and human verification are pending.'}
with receipt.open('x', encoding='utf-8') as f:
    json.dump(result, f, indent=2)
    f.write('\n')
print(json.dumps(result, indent=2))
