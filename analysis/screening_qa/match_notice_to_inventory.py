"""Locate possible frozen inventory IDs by exact publisher-notice DOI.

DOI matches are identity-verification candidates, not automatic decisions.
This script does not read any reviewer labels or mutate inventory records.
"""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

notice = Path('work/screening_qa/sage-2025-retraction-notice-dois.json')
inventory = Path('outputs/Medical-XR-Calibration-and-Full-Screening/shared/snapshot/provisional_publications.csv')
output = Path('work/screening_qa/sage-2025-notice-inventory-candidates.json')
if output.exists():
    raise FileExistsError(output)
source = json.loads(notice.read_text(encoding='utf-8'))
notice_dois = {x.strip().lower() for x in source['article_dois']}
matches = []
with inventory.open(encoding='utf-8-sig', newline='') as f:
    for row in csv.DictReader(f):
        candidates = {row.get('doi', '').strip().lower()}
        try:
            candidates.update(x.strip().lower() for x in json.loads(row.get('dois_json') or '[]') if isinstance(x, str))
        except (ValueError, TypeError):
            pass
        overlap = sorted(candidates & notice_dois)
        if overlap:
            matches.append({'publication_id': row['publication_id'], 'title': row['title'],
                            'matched_dois': overlap, 'record_ids_json': row['record_ids_json'],
                            'identity_status': 'CANDIDATE_REQUIRES_TITLE_AND_SOURCE_VERIFICATION',
                            'human_verification': 'PENDING'})
out = {'created_utc': datetime.now(timezone.utc).isoformat(),
       'notice': source['notice'], 'notice_sha256': hashlib.sha256(notice.read_bytes()).hexdigest(),
       'inventory_sha256': hashlib.sha256(inventory.read_bytes()).hexdigest(),
       'notice_doi_count': len(notice_dois), 'candidate_count': len(matches), 'candidates': matches,
       'limitation': 'Exact DOI candidates can include conflicting provisional groups. Verify each title and report identity; do not merge or transfer screening decisions.'}
output.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps(out, indent=2, ensure_ascii=True))
