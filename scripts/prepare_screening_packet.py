"""Copy one frozen batch into a new contributor packet; never screen a record."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / 'data/runs/2026-11-17/work-plan.json'
NAMES = {'source.csv', 'pass-A.csv', 'pass-B.csv', 'audit-selection.json', 'required-audit.csv'}


class PacketError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PacketError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def csv_rows(data):
    reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig'), newline=''), strict=True)
    fields = reader.fieldnames or []
    require(bool(fields) and all(fields) and len(fields) == len(set(fields)),
            'Missing or duplicate CSV headers')
    rows = list(reader)
    require(all(None not in row and all(value is not None for value in row.values()) for row in rows),
            'CSV row width differs from header')
    return rows


def safe_member(name):
    require(isinstance(name, str) and bool(name) and ':' not in name
            and all(ord(character) >= 32 and ord(character) != 127 for character in name),
            'Unsafe archive member path')
    path = PurePosixPath(name)
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in name,
            'Unsafe archive member path')
    require(path.as_posix() == name and bool(path.parts), 'Noncanonical archive member path')
    return path


def directory_reader(root):
    root = Path(root).resolve(strict=True)

    def read(name, expected_bytes):
        member = safe_member(name)
        target = (root / Path(*member.parts)).resolve(strict=True)
        require(target.is_relative_to(root) and target.is_file(), 'Input escaped the source directory')
        require(target.stat().st_size == expected_bytes, 'Input size differs from frozen manifest')
        return target.read_bytes()

    return read


def zip_reader(archive):
    names = archive.namelist()

    def read(name, expected_bytes):
        safe_member(name)
        require(names.count(name) == 1, 'Missing or duplicate ZIP member')
        require(archive.getinfo(name).file_size == expected_bytes, 'ZIP member size differs from frozen manifest')
        return archive.read(name)

    return read


def build_packet(plan, batch_id, legacy, read_member, output):
    require(plan.get('format') == 'medical-xr-issue-work-plan/1', 'Unknown work-plan format')
    matches = [item for item in plan['batches'] if item['batch_id'] == batch_id]
    require(len(matches) == 1, 'Batch is not uniquely assigned in this work plan')
    batch = matches[0]
    ids = batch['publication_ids']
    require(len(ids) == len(set(ids)) == batch['n'] and bool(ids), 'Invalid assigned ID set')
    inputs = batch['inputs']
    require(len(inputs) == len(NAMES) and {item['name'] for item in inputs} == NAMES,
            'Packet must contain exactly the five frozen inputs')
    require(all(type(item['bytes']) is int and item['bytes'] >= 0 for item in inputs),
            'Invalid batch input byte count')
    require(sum(item['bytes'] for item in inputs) <= 64 * 1024 * 1024, 'Batch input size exceeds packet bound')
    output = Path(output)
    require(not output.exists() and not output.is_symlink(), 'Output already exists; choose a new directory')
    payload = {}
    for item in inputs:
        name = item['archive_path']
        member = safe_member(name)
        require(member.name == item['name'] and member.parent.name == batch_id,
                'Frozen input path does not match the assigned batch and filename')
        require(name in legacy, 'Input is absent from the public frozen manifest')
        recorded = legacy[name]
        require(recorded['sha256'] == item['sha256'] and int(recorded['bytes']) == item['bytes'],
                'Work-plan input differs from the frozen public manifest')
        data = read_member(name, item['bytes'])
        require(len(data) == item['bytes'] and sha(data) == item['sha256'], 'Input hash or size mismatch')
        payload[item['name']] = data
    require(len({str(PurePosixPath(item['archive_path']).parent) for item in inputs}) == 1,
            'Frozen inputs must share the same batch directory')
    for name in ['source.csv', 'pass-A.csv', 'pass-B.csv']:
        actual = [row['publication_id'] for row in csv_rows(payload[name])]
        require(len(actual) == len(set(actual)) == len(ids) and set(actual) == set(ids),
                'Source/original-pass membership differs from assigned IDs')
    selection = json.loads(payload['audit-selection.json'].decode('utf-8-sig'))
    sample = selection['sample_ids']
    require(sample == batch['fixed_sample_ids'] and len(sample) == len(set(sample)),
            'Fixed audit sample changed')
    required = [row['publication_id'] for row in csv_rows(payload['required-audit.csv'])]
    require(len(required) == len(set(required)) and set(required) <= set(ids) and set(sample) <= set(required),
            'Required audit/sample membership is inconsistent')
    metadata = {
        'format': 'medical-xr-contributor-packet/1', 'batch_id': batch_id,
        'work_package': batch['work_package'], 'issue_url': batch.get('issue_url', ''),
        'publication_ids': ids, 'fixed_sample_ids': sample, 'inputs': inputs,
        'method': plan['method'], 'codebook': plan['codebook'],
        'stage': 'source_enriched_adjudication_after_both_original_passes',
        'human_verification': 'PENDING', 'source_reading_credit_from_packet_creation': 0,
        'limits': 'Selected frozen-input integrity only, not scientific assessment or whole-archive verification. Preserve original identities, models, records and samples. Record actual source reading and assistance in a separate contribution.'
    }
    output.mkdir(parents=True)
    for name, data in payload.items():
        with (output / name).open('xb') as handle:
            handle.write(data)
    with (output / 'packet.json').open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--source-root', type=Path)
    source.add_argument('--archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plan', type=Path, default=DEFAULT_PLAN)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding='utf-8'))
    manifest = ROOT / 'provenance/legacy-file-manifest.csv'
    require(sha(manifest.read_bytes()) == plan['frozen_file_manifest_sha256'], 'Frozen manifest changed')
    legacy = {row['path'].replace('\\', '/'): row for row in csv_rows(manifest.read_bytes())}
    if args.archive:
        with zipfile.ZipFile(args.archive) as archive:
            result = build_packet(plan, args.batch, legacy, zip_reader(archive), args.output)
    else:
        result = build_packet(plan, args.batch, legacy, directory_reader(args.source_root), args.output)
    print(json.dumps({'batch_id': result['batch_id'], 'records': len(result['publication_ids']),
                      'verified_input_members': len(result['inputs']), 'output': str(args.output),
                      'scientific_assessments_created': 0}))


if __name__ == '__main__':
    main()
