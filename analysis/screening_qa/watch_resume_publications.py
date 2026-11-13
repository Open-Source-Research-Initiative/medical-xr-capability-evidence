"""Current-run coordinator publication loop; no screening/source judgments.

Calls the existing refresh/validator, saves immutable publication events, and
stops on an error or when source work is ready for final operational closures.
The coordinator must stop this loop before any manual canonical mutation.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import resume_screening as s


def source_signature():
    folder = s.RUN / 'adjudicator_sol'
    paths = set(folder.glob('source-audit-*-receipt.json'))
    for path in folder.glob('B*-adjudicated-resume-v0.4.6.csv'):
        receipt = path.with_name(path.stem + '-receipt.json')
        if receipt.is_file():
            paths.update([path, receipt])
    return tuple((path.as_posix(), path.stat().st_size, path.stat().st_mtime_ns) for path in sorted(paths))


def run_existing(script, *args):
    result = subprocess.run([sys.executable, str(Path(__file__).parent / script), *args], capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(json.dumps({'script': script, 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}))
    return result.stdout


def publish_event():
    refresh_output = run_existing('refresh_resume_run.py', '--skip-initial-refresh')
    validation = json.loads(run_existing('validate_resume_manifest.py'))
    can = s.RUN / 'canonical'
    counts = json.loads((can / 'coverage-and-flow-current.json').read_text(encoding='utf-8'))
    event = {'recorded_at_utc': s.stamp(), 'stage': 'COORDINATOR_MECHANICAL_PUBLICATION_VALIDATED', 'refresh_stdout': refresh_output, 'validation': validation, 'coverage_counts': counts, 'counts_file_sha256': s.sha(can / 'coverage-and-flow-current.json'), 'scope': 'Existing manually authored source work only. Mechanical publication/hash validation does not create classifications, resolve scientific evidence, perform human verification or complete the goal.'}
    folder = s.RUN / 'admin/coordinator-publication-events'
    name = event['recorded_at_utc'].replace(':', '').replace('-', '').replace('+0000', 'Z') + '.json'
    path = folder / name
    s.js(path, event, exclusive=True)
    print(json.dumps({'event': 'VALIDATED_PUBLICATION', 'generated_at_utc': counts['generated_at_utc'], 'adjudicated': counts['adjudicated_n'], 'adjudication_remaining': counts['adjudication_pending'], 'required_audits_unperformed': counts['required_audits_unperformed'], 'freshlegacy_considerations_pending': counts['fresh_legacy_rechecks_sol_consideration_pending'], 'postinitial_notes_pending': counts['self_detected_rechecks_pending'], 'operational_audits_pending': counts['mandatory_operational_audits_pending'], 'date_obligations': counts['independent_2020_date_obligations'], 'manifest_sha256': validation['published_manifest_sha256'], 'hashed_paths_verified': validation['hashed_paths_verified'], 'event_file': path.as_posix(), 'goal_complete': counts['goal_complete']}), flush=True)
    return counts


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--once', action='store_true')
    cli.add_argument('--min-gap-seconds', type=float, default=120)
    args = cli.parse_args()
    admin = s.RUN / 'admin'
    lock = admin / 'coordinator-publication-watch.lock.json'
    stop = admin / 'coordinator-publication-watch-stop.request'
    s.js(lock, {'pid': os.getpid(), 'started_at_utc': s.stamp(), 'script': str(Path(__file__)), 'scope': 'One coordinator publisher only. Stop and await exit before manual canonical mutations.'}, exclusive=True)
    previous = None
    published = None
    published_at = 0.0
    heartbeat_at = time.monotonic()
    counts = None
    try:
        while True:
            if stop.exists():
                print(json.dumps({'event': 'COORDINATOR_STOP_REQUEST_OBSERVED', 'goal_complete': False}), flush=True)
                return
            signature = source_signature()
            now = time.monotonic()
            if args.once or (signature != published and signature == previous and now - published_at >= args.min_gap_seconds):
                counts = publish_event()
                published = signature
                published_at = time.monotonic()
                heartbeat_at = published_at
                if args.once:
                    return
                if all(counts[key] == 0 for key in ['adjudication_pending', 'required_audits_unperformed', 'required_audits_scope_verification_pending', 'fresh_legacy_rechecks_sol_consideration_pending', 'self_detected_rechecks_pending']):
                    print(json.dumps({'event': 'READY_FOR_COORDINATOR_FINAL_OPERATIONAL_CLOSURES', 'goal_complete': False, 'scope': 'Loop stopping only; final named audits, exact consistency checks and review packet still require coordinator completion.'}), flush=True)
                    return
            previous = signature
            if time.monotonic() - heartbeat_at >= 50:
                print(json.dumps({'event': 'WAITING_FOR_SAVED_SOURCE_WORK', 'last_published_at_utc': counts['generated_at_utc'] if counts else None, 'new_source_inputs_waiting': signature != published, 'goal_complete': False}), flush=True)
                heartbeat_at = time.monotonic()
            time.sleep(5)
    finally:
        if lock.is_file() and json.loads(lock.read_text(encoding='utf-8'))['pid'] == os.getpid():
            lock.unlink()


if __name__ == '__main__':
    main()
