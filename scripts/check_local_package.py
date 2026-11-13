"""Check the local import and unchanged copies; no screening or publication."""
import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--archive', type=Path, required=True)
    cli.add_argument('--write-receipt', action='store_true')
    args = cli.parse_args()
    inherited = load(ROOT / 'provenance/pre-adoption-import.json')
    manifest = ROOT / 'provenance/legacy-file-manifest.csv'
    assert sha(manifest) == inherited['file_manifest_sha256']
    with manifest.open(encoding='utf-8', newline='') as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len({row['path'] for row in rows}) == inherited['original_workspace_files']
    assert sum(int(row['bytes']) for row in rows) == inherited['original_workspace_bytes']
    assert all(not Path(row['path']).is_absolute() and '..' not in Path(row['path']).parts for row in rows)
    assert sha(args.archive) == inherited['archive_sha256']
    with zipfile.ZipFile(args.archive) as saved:
        assert set(saved.namelist()) == {row['path'] for row in rows}
        original_question = next(line[2:].strip() for line in saved.read('10 - Locked question and capability analysis.md').decode('utf-8-sig').splitlines() if line.startswith('> Since 2020'))
    current_question = next(line[2:].strip() for line in (ROOT / 'README.md').read_text(encoding='utf-8').splitlines() if line.startswith('> Since 2020'))
    assert original_question == current_question, 'LOCKED_QUESTION_CHANGED'
    bypath = {row['path']: row for row in rows}
    prefix = 'outputs/Medical-XR-Calibration-and-Full-Screening/'
    assert bypath[prefix + 'shared/snapshot/provisional_publications.csv']['sha256'] == inherited['frozen_inventory_sha256']
    for pas in 'AB':
        assert bypath[prefix + f'resume-20261112/canonical/pass-{pas}-original-initials.csv']['sha256'] == inherited[f'original_pass_{pas}_sha256']
    counts_path = ROOT / 'data/pause-counts.json'
    assert sha(counts_path) == bypath[prefix + 'resume-20261112/canonical/coverage-and-flow-current.json']['sha256']
    counts = load(counts_path)
    assert counts['pass_A_saved'] == counts['pass_B_saved'] == counts['both_initial_passes'] == 18976
    assert counts['adjudicated_n'] == 9226 and counts['adjudication_pending'] == 9750
    assert counts['required_audits_unperformed'] == 9464 and counts['mandatory_operational_audits_pending'] == 5
    assert counts['human_verified'] == 0 and not counts['goal_complete']
    copies = load(ROOT / 'provenance/unchanged-code-copies.json')
    for row in copies:
        assert sha(ROOT / row['candidate_path']) == row['sha256'] == bypath[row['original_path']]['sha256'], row['candidate_path']
    refs = load(ROOT / 'provenance/osri-guidance-sources.json')
    assert refs['baseline_commit'] == '8c39a0a36c0e962060659b1d51f666c367f9464a'
    assert refs['adoption_status'] == 'PROPOSED_PENDING_COLE_ACCEPTANCE'
    assert len(refs['sources']) == 31
    restored = load(ROOT / 'provenance/restore-validation.json')
    assert restored['result'] == 'PASS' and restored['restored_files_sha256_verified'] == len(rows)
    assert restored['restored_manifest_validation']['published_manifest_sha256'] == inherited['original_screening_manifest_sha256']
    files = {}
    for path in sorted(ROOT.rglob('*')):
        if path.is_file() and '.git' not in path.relative_to(ROOT).parts and path.name != 'local-package-check.json':
            files[path.relative_to(ROOT).as_posix()] = sha(path)
    result = {'checked_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'performed_by': 'Codex coordinator using this Python script', 'result': 'PASS', 'inherited_files_accounted': len(rows), 'inherited_bytes_accounted': inherited['original_workspace_bytes'], 'archive_sha256_matched': True, 'archive_member_set_matched': True, 'locked_question_matches_original': True, 'new_directory_restore_passed': True, 'unchanged_pipeline_copies_verified': len(copies), 'primary_guidance_records': len(refs['sources']), 'original_pass_and_inventory_hashes_matched': True, 'pause_counts_matched': True, 'file_sha256': files, 'human_acceptance': 'PENDING', 'not_checked': ['Fresh-environment or cross-machine reproduction', 'New scientific screening or publication commands', 'Public redistribution rights and licenses', 'Scientific correctness or full-text assessment', 'Human verification', 'OSRI acceptance or peer review'], 'scope': 'Mechanical preservation and local draft checks only. The archive save and separate restoration receipts record full per-file SHA-256 verification.'}
    if args.write_receipt:
        output = ROOT / 'provenance/local-package-check.json'
        with output.open('x', encoding='utf-8') as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'file_sha256'}))


if __name__ == '__main__':
    main()
