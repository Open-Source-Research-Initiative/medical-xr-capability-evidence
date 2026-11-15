"""Read one publication group's saved metadata and AI decisions; never screen or write data."""
import argparse
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TABLES = {
    'inventory': ('provisional_publications.csv', {'publication_id', 'doi', 'year'}),
    'pass_A': ('pass-A-original-initials.csv', {'publication_id', 'eligibility', 'reviewer', 'model'}),
    'pass_B': ('pass-B-original-initials.csv', {'publication_id', 'eligibility', 'reviewer', 'model'}),
    'adjudication': ('adjudicated-current.csv', {'publication_id', 'adjudicated_eligibility'}),
}


def lookup(publication_id, root=ROOT):
    if re.fullmatch(r'P[0-9]{7}', publication_id) is None:
        raise ValueError('Use the full publication_id from the inventory, for example P0000314; retain its leading zeros.')
    result = {'format': 'medical-xr-publication-lookup/1', 'publication_id': publication_id,
              'snapshot_date': '2026-11-13', 'records': {},
              'limits': 'Saved AI decisions, not new screening or human verification. Missing adjudication means not yet adjudicated in this snapshot.'}
    for key, (filename, required) in TABLES.items():
        path = Path(root) / 'data/open/ledger-projections' / filename
        with path.open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle, strict=True)
            fields = reader.fieldnames or []
            if len(fields) != len(set(fields)) or not required.issubset(fields):
                raise ValueError('Missing or duplicate required headers in ' + filename)
            matches = [row for row in reader if row.get('publication_id') == publication_id]
        if len(matches) > 1:
            raise ValueError('Duplicate publication_id in ' + filename + '; run scripts/verify_open_data.py.')
        if any(None in row or any(value is None for value in row.values()) for row in matches):
            raise ValueError('CSV row width differs from its header in ' + filename + '; run scripts/verify_open_data.py.')
        if key == 'inventory' and not matches:
            raise ValueError('publication_id is absent from the frozen inventory: ' + publication_id)
        if key in {'pass_A', 'pass_B'} and not matches:
            raise ValueError('Missing original initial assessment in ' + filename + '; run scripts/verify_open_data.py.')
        result['records'][key] = matches[0] if matches else None
    return result


def summary(record):
    rows = record['records']
    inventory = rows['inventory']
    print(record['publication_id'] + ' — saved snapshot ' + record['snapshot_date'])
    print('DOI: ' + (inventory['doi'] or '(not recorded; inspect dois_json in --json output)'))
    print('Inventory year: ' + (inventory['year'] or '(not recorded)'))
    for label, key in [('Pass A', 'pass_A'), ('Pass B', 'pass_B')]:
        row = rows[key]
        print(label + ': ' + row['eligibility'] + '; reviewer=' + (row['reviewer'] or '(not recorded)')
              + '; model=' + (row['model'] or '(not recorded)'))
        print('  Evidence stream: ' + (row.get('evidence_stream') or '(not recorded)')
              + '; modality: ' + (row.get('modality_stream') or '(not recorded)'))
    adjudication = rows['adjudication']
    if adjudication is None:
        print('Adjudication: not yet recorded in this snapshot (does not mean EXCLUDE).')
    else:
        print('Recorded adjudicated eligibility: ' + adjudication['adjudicated_eligibility'])
        print('  Reason code: ' + (adjudication.get('reason_code') or '(not recorded)'))
        print('  Human verification field: ' + (adjudication.get('human_verification') or '(not recorded)'))
        print('  Artifact: ' + (adjudication.get('adjudication_artifact') or '(not recorded)'))
    print('INCLUDE advances to later full-text assessment; it is not final study inclusion.')
    print('Use --json for complete CSV projection rows, provenance fields and original artifact references.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('publication_id', help='Full identifier, for example P0000314.')
    parser.add_argument('--json', action='store_true', help='Print the complete CSV projection rows as JSON; missing adjudication is null.')
    args = parser.parse_args(argv)
    try:
        record = lookup(args.publication_id)
    except (ValueError, OSError, csv.Error) as error:
        parser.exit(2, 'Lookup failed: ' + str(error) + '\n')
    sys.stdout.reconfigure(encoding='utf-8')
    if args.json:
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        print('Existing AI decisions follow. Disclose this exposure in any later source review.')
        summary(record)
    return 0


if __name__ == '__main__':
    sys.exit(main())
