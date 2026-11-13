"""Combine the coordinator's five immutable partials after exact-ID checks."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path('outputs/Medical-XR-Calibration-and-Full-Screening')
folder = root / 'terra_coordinator'
source = root / 'shared/batches/B0379.csv'
dest = folder / 'B0379.csv'
receipt = Path('work/screening_qa/terra_coordinator-B0379-merge.json')
if dest.exists() or receipt.exists():
    raise FileExistsError('Refusing to overwrite final batch or receipt')
with source.open(encoding='utf-8-sig', newline='') as f:
    frozen = list(csv.DictReader(f))
paths = [folder / f'B0379-partial-{i:03}.csv' for i in range(1, 6)]
rows = []
header = None
for i, path in enumerate(paths):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if header is None:
            header = reader.fieldnames
        if reader.fieldnames != header:
            raise ValueError(f'Incompatible columns: {path}')
        part = list(reader)
    if [r['publication_id'] for r in part] != [r['publication_id'] for r in frozen[i*10:(i+1)*10]]:
        raise ValueError(f'IDs or order differ from source: {path}')
    rows.extend(part)
if len(rows) != 50 or len({r['publication_id'] for r in rows}) != 50:
    raise ValueError('Expected fifty unique source IDs')
with dest.open('x', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=header, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    writer.writerows(rows)
out = {'created_utc': datetime.now(timezone.utc).isoformat(), 'batch': 'B0379',
       'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
       'partial_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
       'final_sha256': hashlib.sha256(dest.read_bytes()).hexdigest(), 'count': len(rows),
       'limitation': 'This preserves source-read decisions and validates ID structure; it is not an independent accuracy audit.'}
with receipt.open('x', encoding='utf-8') as f:
    json.dump(out, f, indent=2)
    f.write('\n')
print(json.dumps(out, indent=2))
