"""Locate, without reclassifying, shared advances for medical-task recheck.

This high-recall lexical search cannot establish relevance or completeness.
It only reads batches already initially assessed by both reviewers.
"""
import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--output', type=Path, default=Path('work/screening_qa/wellness-boundary-candidates.json'))
args = p.parse_args()
root = Path('outputs/Medical-XR-Calibration-and-Full-Screening')
def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))
out = []
inputs = []
for sol_file in sorted((root / 'sol').glob('B[0-9][0-9][0-9][0-9].csv')):
    terra_file = root / 'terra' / sol_file.name
    batch = root / 'shared/batches' / sol_file.name
    if not terra_file.exists() or not batch.exists():
        continue
    inputs.append({'batch': sol_file.stem, 'files': {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (sol_file, terra_file, batch)}})
    sol = {r['publication_id']: r for r in read(sol_file)}
    terra = {r['publication_id']: r for r in read(terra_file)}
    for row in read(batch):
        ident = row['publication_id']
        if ident not in sol or ident not in terra or sol[ident]['eligibility'] != 'INCLUDE' or terra[ident]['eligibility'] != 'INCLUDE':
            continue
        text = (row['title'] + ' ' + row['abstract']).lower()
        pop = re.search(r'healthy|non[- ]clinical|nonclinical|general population', text)
        topic = re.search(r'relax|mindful|well[- ]?being|mood|wellness|exercis|stress', text)
        if pop and topic:
            out.append({'publication_id': ident, 'batch': sol_file.stem, 'title': row['title'],
                        'population_term': pop.group(), 'topic_term': topic.group(),
                        'status': 'CANDIDATE_ONLY_NOT_RECLASSIFIED'})
path = args.output
if path.exists():
    raise FileExistsError('Preserve earlier candidate snapshots rather than overwrite')
payload = {'created_utc': datetime.now(timezone.utc).isoformat(), 'inputs': inputs,
           'candidate_count': len(out), 'candidates': out,
           'limitation': 'Keyword locator only; neither a classification nor a complete medical-task audit.'}
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(payload, ensure_ascii=True, indent=2))
