"""Validate the public record and Git boundary without reading restricted evidence."""
import argparse
import ast
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SAFE_IMPORT = 'aae894e2284b89d9a1b48b50582a43798c6280c3'
BLOCKED_COMMITS = {'2515272b6feb75854082fc14344fe06d5fcfc822', 'd7d11a583c5594acbc67d5af96758b4ac8b01d5a'}
BLOCKED_BLOB = 'cc8e20c3a1b5115e05935ead3af281a28d396812'
WITHHELD_PATH = 'analysis/screening_qa/coordinator_screen_B0380.py'


def git(*args):
    result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace'))
    return result.stdout


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def check_name(name):
    path = Path(name)
    assert not path.is_absolute() and '..' not in path.parts, name
    assert name != WITHHELD_PATH, name
    assert not any(part in {'outputs', 'restricted', 'supporting-context', 'source-review', 'Meta Analysis Exports'} for part in path.parts), name
    assert path.suffix.lower() not in {'.pdf', '.ris', '.zip', '.bundle', '.jsonl'}, name
    assert 'private-access' not in path.name.lower(), name


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--staged', action='store_true', help='Inspect the staged tree before the publication commit.')
    cli.add_argument('--write-receipt', action='store_true')
    args = cli.parse_args()
    tree = git('write-tree').decode().strip() if args.staged else 'HEAD'
    entries = git('ls-tree', '-r', '-z', tree).split(b'\0')
    files = {}
    secrets = [re.compile(rb'(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}'), re.compile(rb'sk-proj-[A-Za-z0-9_-]{20,}'), re.compile(rb'AKIA[0-9A-Z]{16}'), re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]
    for entry in filter(None, entries):
        metadata, raw_name = entry.split(b'\t', 1)
        name = raw_name.decode('utf-8'); check_name(name)
        blob = metadata.split()[2].decode(); assert blob != BLOCKED_BLOB
        body = git('cat-file', 'blob', blob)
        assert not any(pattern.search(body) for pattern in secrets), ('CREDENTIAL_PATTERN', name)
        assert not re.search(rb'[A-Za-z]:[/\\]Users[/\\]', body), ('PRIVATE_USER_PATH', name)
        if name.endswith('.py'):
            ast.parse(body.decode('utf-8-sig'), filename=name)
        assert (ROOT / name).read_bytes() == body, ('WORKTREE_DIFFERS', name)
        files[name] = hashlib.sha256(body).hexdigest()
    copies = load('provenance/public-code-copies.json')['files']; assert len(copies) == 51
    for row in copies:
        assert files[row['candidate_path']] == row['sha256'], row['candidate_path']
    imported = load('provenance/pre-adoption-import.json')
    assert sha(ROOT / 'provenance/legacy-file-manifest.csv') == imported['file_manifest_sha256']
    with (ROOT / 'provenance/legacy-file-manifest.csv').open(encoding='utf-8', newline='') as handle:
        manifest = list(csv.DictReader(handle))
    assert len(manifest) == len({row['path'] for row in manifest}) == 36839
    assert sum(int(row['bytes']) for row in manifest) == imported['original_workspace_bytes']
    counts = load('data/pause-counts.json'); pause = load('data/pause-state.json')
    assert counts['pass_A_saved'] == counts['pass_B_saved'] == 18976
    assert counts['adjudicated_n'] == pause['adjudicated_n'] == 9226
    assert counts['adjudication_pending'] == pause['adjudication_remaining'] == 9750
    assert pause['state'] == 'PAUSED_BY_HUMAN' and not pause['screening_goal_complete']
    assert pause['next_batch'] == 'B0183' and pause['human_verified'] == 0
    authorization = load('provenance/publication-authorization.json')
    assert authorization['repository_publication_authorized'] and not authorization['scientific_screening_resume_authorized']
    commits = set(git('rev-list', '--all').decode().splitlines())
    assert SAFE_IMPORT in commits and not (commits & BLOCKED_COMMITS)
    objects = {line.split()[0] for line in git('rev-list', '--objects', '--all').decode().splitlines()}
    assert BLOCKED_BLOB not in objects
    assert subprocess.run(['git', 'cat-file', '-e', BLOCKED_BLOB], cwd=ROOT, capture_output=True).returncode != 0
    # Every reachable historical filename must obey the same public boundary.
    for commit in commits:
        for raw in filter(None, git('ls-tree', '-r', '--name-only', '-z', commit).split(b'\0')):
            check_name(raw.decode('utf-8'))
    result = {'checked_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'performed_by': 'Codex coordinator using this Python script', 'result': 'PASS', 'scope': 'Public tree and reachable Git history; no restricted artifact access or scientific execution.', 'inspected_tree': tree, 'public_files': len(files), 'public_unchanged_code_copies': len(copies), 'inherited_manifest_files': len(manifest), 'reachable_commits': len(commits), 'original_safe_import_preserved': True, 'excerpt_bearing_blob_absent': True, 'controlled_draft_commits_absent': True, 'screening_state': 'PAUSED', 'human_verification': 'PENDING', 'file_sha256': {k: v for k, v in files.items() if k != 'provenance/publication-check.json'}, 'limits': 'Bounded content and provenance checks; not scientific correctness, blanket rights clearance, human verification or external peer review.'}
    if args.write_receipt:
        with (ROOT / 'provenance/publication-check.json').open('x', encoding='utf-8', newline='\n') as handle:
            json.dump(result, handle, indent=2); handle.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'file_sha256'}))


if __name__ == '__main__':
    main()
