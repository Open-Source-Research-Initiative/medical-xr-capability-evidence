"""Check that each ID in a fixed routine audit bundle is mentioned in its note.

This is a coverage check, not a judgment of whether source review was adequate.
"""
import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('bundle', type=Path)
p.add_argument('note', type=Path)
p.add_argument('--output', type=Path)
args = p.parse_args()
data = json.loads(args.bundle.read_text(encoding='utf-8'))
text = args.note.read_text(encoding='utf-8')
groups = {}
for group in ('agreed_inclusions', 'sampled_agreed_exclusions'):
    ids = [row['publication_id'] for row in data[group]]
    groups[group] = {'total': len(ids), 'missing_from_note': [ident for ident in ids if ident not in text]}
result = {'batch': data['batch'], 'note': str(args.note), 'groups': groups,
          'limitation': 'Mentions alone do not establish accurate or independent source review.'}
if args.output:
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
if any(v['missing_from_note'] for v in groups.values()):
    raise SystemExit(1)
