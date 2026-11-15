"""Verify open metadata and, optionally, every file in the frozen evidence ZIP."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read_table(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle, strict=True)
        fields = reader.fieldnames or []
        require(fields and len(fields) == len(set(fields)), 'Missing or duplicate CSV headers')
        rows = list(reader)
    require(all(None not in row and all(value is not None for value in row.values()) for row in rows),
            'CSV row width differs from header')
    return fields, rows


def publication_ids(rows):
    values = [row['publication_id'] for row in rows]
    require(all(values) and len(values) == len(set(values)), 'Empty or duplicate publication ID')
    return set(values)


def safe_path(root, name):
    require(isinstance(name, str) and name and '\\' not in name, 'Unsafe artifact path')
    relative = PurePosixPath(name)
    require(not relative.is_absolute() and ':' not in name and all(p not in {'.', '..'} for p in name.split('/')),
            'Unsafe artifact path')
    target = root / name
    require(target.resolve().is_relative_to(root.resolve()) and not target.is_symlink(), 'Unsafe artifact path')
    return target


def verify_metadata(root):
    root = Path(root).resolve()
    base = root / 'data/open'
    record = json.loads((root / 'provenance/open-data-publication.json').read_text(encoding='utf-8'))
    manifest_path = base / 'derivation-manifest.json'
    require(digest(manifest_path) == record['open_metadata_manifest_sha256'], 'Derivation manifest hash differs')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    legacy_path = root / 'provenance/legacy-file-manifest.csv'
    imported = json.loads((root / 'provenance/pre-adoption-import.json').read_text(encoding='utf-8'))
    require(digest(legacy_path) == imported['file_manifest_sha256'] == record['file_manifest_sha256'],
            'Original file manifest hash differs')
    _, legacy_rows = read_table(legacy_path)
    legacy = {row['path']: row for row in legacy_rows}
    require(len(legacy) == len(legacy_rows) == 36839, 'Original manifest coverage differs')
    _, catalog_rows = read_table(base / 'catalog.csv')
    catalog = {row['path']: row for row in catalog_rows}
    require(len(catalog) == len(catalog_rows) == 43, 'Catalog coverage differs')
    table_paths = set()
    source_paths = set()
    major = {}
    for entry in manifest['sources']:
        source = entry['source_path']
        require(source not in source_paths and source in legacy, 'Missing or duplicate original source')
        source_paths.add(source)
        require(entry['source_sha256'] == legacy[source]['sha256'], 'Original table binding differs')
        if 'output_path' not in entry:
            continue
        name = entry['output_path']
        require(name not in table_paths and name in catalog, 'Missing or duplicate output mapping')
        table_paths.add(name)
        path = safe_path(base, name)
        require(digest(path) == entry['output_sha256'] == catalog[name]['sha256'], 'Data table hash differs')
        require(path.stat().st_size == int(catalog[name]['bytes']), 'Data table size differs')
        require(catalog[name]['source_path'] == source and catalog[name]['source_sha256'] == entry['source_sha256'],
                'Catalog original-source mapping differs')
        fields, rows = read_table(path)
        require(fields == entry['retained_fields'], 'Data table schema differs')
        require(len(rows) == entry['source_rows'] == int(catalog[name]['rows']), 'Data table row count differs')
        require(not {'abstract', 'title', 'rationale', 'supporting_evidence', 'exact_quote'} & set(fields),
                'Projection unexpectedly includes a source-text field')
        if path.name in {'provisional_publications.csv', 'pass-A-original-initials.csv',
                         'pass-B-original-initials.csv', 'adjudicated-current.csv'}:
            major[path.name] = rows
    require(len(source_paths) == 45 and len(table_paths) == 43, 'Derivation coverage differs')
    require(table_paths == set(catalog), 'Catalog contains unmapped tables')
    actual_paths = {path.relative_to(base).as_posix() for path in (base / 'ledger-projections').rglob('*') if path.is_file()}
    require(actual_paths == table_paths, 'Unmapped or missing projection file')
    frozen = publication_ids(major['provisional_publications.csv'])
    require(len(frozen) == 18976, 'Frozen ID count differs')
    for name in ['pass-A-original-initials.csv', 'pass-B-original-initials.csv']:
        require(publication_ids(major[name]) == frozen, 'Initial pass ID coverage differs')
    adjudicated = major['adjudicated-current.csv']
    require(len(adjudicated) == 9226 and publication_ids(adjudicated).issubset(frozen), 'Adjudication coverage differs')
    counts = json.loads((root / 'data/pause-counts.json').read_text(encoding='utf-8'))
    require(dict(Counter(row['adjudicated_eligibility'] for row in adjudicated)) == counts['adjudicated_eligibility_counts'],
            'Adjudication label distribution differs')
    _, human = read_table(root / 'data/human-verification-template.csv')
    require(not human and counts['human_verified'] == record['human_verified'] == 0, 'Human verification state differs')
    require(record['scientific_mutation'] is False and record['screening_state'] == 'PAUSED_BY_HUMAN',
            'Scientific pause state differs')
    return {'metadata_tables': len(table_paths), 'original_inputs': len(source_paths),
            'frozen_IDs': len(frozen), 'pass_A': len(frozen), 'pass_B': len(frozen), 'adjudicated': len(adjudicated)}


def verify_archive(path, manifest, expected_digest=None):
    path = Path(path)
    if expected_digest is not None:
        require(digest(path) == expected_digest, 'Evidence ZIP hash differs')
    seen = set()
    total = 0
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            name = member.filename
            safe_path(Path.cwd(), name)
            require(name not in seen and name in manifest, 'Duplicate or unlisted archive member')
            seen.add(name)
            expected = manifest[name]
            require(member.file_size == int(expected['bytes']), 'Archived file size differs')
            with archive.open(member) as handle:
                require(hashlib.file_digest(handle, 'sha256').hexdigest() == expected['sha256'], 'Archived file hash differs')
            total += member.file_size
    require(seen == set(manifest), 'Archive file coverage differs')
    return {'archive_files': len(seen), 'uncompressed_bytes': total}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Additionally verify a downloaded workspace.zip without extracting it.')
    args = parser.parse_args()
    result = verify_metadata(ROOT)
    if args.archive:
        record = json.loads((ROOT / 'provenance/open-data-publication.json').read_text(encoding='utf-8'))
        _, rows = read_table(ROOT / 'provenance/legacy-file-manifest.csv')
        result.update(verify_archive(args.archive, {row['path']: row for row in rows}, record['archive_sha256']))
    print(json.dumps({'result': 'PASS', **result, 'human_verified': 0, 'screening_state': 'PAUSED',
                      'limits': 'Integrity, schema and coverage checks; not scientific validation.'}))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, csv.Error, zipfile.BadZipFile) as error:
        raise SystemExit('Open data verification failed: ' + str(error)) from None
