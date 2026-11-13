"""Save a manually source-read coordinator screening shard without overwriting.

The JSON input contains the coordinator's record-level judgments; this program
does not infer eligibility. It reads no Sol, Terra or legacy decision file.
"""
import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('outputs/Medical-XR-Calibration-and-Full-Screening')
FIELDS = ['publication_id','reviewer','model','model_version','capability_codebook_version',
 'screening_method_version','prompt_version','batch_id','eligibility','reason_code','rationale',
 'supporting_evidence','source_coordinate','medical_task','modality_stream','modality_components',
 'evidence_stream','evidence_type','evidence_type_basis','evidence_type_check_status',
 'date_status','access_status','source_url','assessed_extent','report_disposition','review_role',
 'prior_exposure','human_verification','screened_at','source_memberships_json','record_ids_json']

p = argparse.ArgumentParser()
p.add_argument('batch')
p.add_argument('chunk', type=int, choices=range(1, 6))
p.add_argument('decisions', type=Path)
args = p.parse_args()
if not re.fullmatch(r'B\d{4}', args.batch) or not 351 <= int(args.batch[1:]) <= 379:
    raise ValueError('Coordinator partials are restricted to batches B0351–B0379')
with (ROOT / 'shared/batches' / f'{args.batch}.csv').open(encoding='utf-8-sig', newline='') as f:
    source = list(csv.DictReader(f))
data = json.loads(args.decisions.read_text(encoding='utf-8'))
source = source[(args.chunk-1)*10:args.chunk*10]
if len(source) != 10 or len(data) != 10 or {r['publication_id'] for r in source} != set(data):
    raise ValueError('Manual decisions must cover exactly the ten specified frozen source IDs')
dest = ROOT / 'terra_coordinator' / f'{args.batch}-partial-{args.chunk:03}.csv'
if dest.exists():
    raise FileExistsError(dest)
now = datetime.now(timezone.utc).isoformat()
output = []
for src in source:
    ident = src['publication_id']
    d = data[ident]
    excerpt_field = d.get('excerpt_field', 'abstract')
    if excerpt_field not in {'title', 'abstract'} or d['excerpt'] not in src[excerpt_field]:
        raise ValueError(f'{ident}: labeled excerpt absent from specified frozen source field')
    if excerpt_field == 'title' and src['abstract'].strip():
        raise ValueError(f'{ident}: title-only decision requested despite available abstract')
    if d['eligibility'] not in {'INCLUDE','EXCLUDE','UNCERTAIN'}:
        raise ValueError(f'{ident}: invalid eligibility')
    for key in ('rationale','reason','task','modality','stream','type'):
        if not d[key].strip():
            raise ValueError(f'{ident}: missing {key}')
    output.append({
      'publication_id': ident, 'reviewer': 'Coordinator_Terra_shard_3', 'model': 'unknown',
      'model_version': 'runtime_version_not_exposed', 'capability_codebook_version': '0.2',
      'screening_method_version': '0.4.6 plus addenda 01-04',
      'prompt_version': '11-2026-11-11 coordinator shard', 'batch_id': args.batch,
      'eligibility': d['eligibility'], 'reason_code': d['reason'], 'rationale': d['rationale'],
      'supporting_evidence': f'exact {excerpt_field} excerpt: ' + d['excerpt'],
      'source_coordinate': (f"{ident} / {src['abstract_record_id']} / title and abstract"
                            if excerpt_field == 'abstract' else f'{ident} / frozen title only'),
      'medical_task': d['task'], 'modality_stream': d['modality'], 'modality_components': d.get('components', 'UNASSESSED'),
      'evidence_stream': d['stream'], 'evidence_type': d['type'],
      'evidence_type_basis': ('frozen title and complete available abstract' if excerpt_field == 'abstract'
                              else 'frozen title only; substantive text not available'),
      'evidence_type_check_status': d.get('type_status','CHECKED_CLEAR'),
      'date_status': ('export year 2020; earliest journal publication month/day unverified; June boundary pending'
                      if src['year'] == '2020' else
                      f"export year {src['year']}; earliest journal publication not independently verified"),
      'access_status': ('title_abstract' if excerpt_field == 'abstract' else 'title_only'), 'source_url': '',
      'assessed_extent': ('frozen title and complete available abstract' if excerpt_field == 'abstract'
                          else 'frozen title only; abstract absent'),
      'report_disposition': 'UNASSESSED', 'review_role': 'UNASSESSED',
      'prior_exposure': 'Coordinator saw calibration and earlier adjudications; no known prior exposure to this report and no other reviewer decisions for this batch read before screening',
      'human_verification': 'PENDING', 'screened_at': now,
      'source_memberships_json': src['source_memberships_json'], 'record_ids_json': src['record_ids_json'],
    })
with dest.open('x', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
    w.writeheader()
    w.writerows(output)
print(f'Saved {len(output)} source-read decisions to {dest}')
