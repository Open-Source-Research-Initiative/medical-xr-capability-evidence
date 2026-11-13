"""Read-only integrity and coverage check of one published snapshot."""
import json
from pathlib import Path
import resume_screening as s

folder=s.RUN/'canonical';path=folder/'provenance-manifest-current.json'
manifest=json.loads(path.read_text(encoding='utf-8'));errors=[]
for name,digest in manifest['input_and_output_sha256'].items():
    source=Path(name)
    if not source.is_file():errors.append({'path':name,'error':'MISSING'})
    elif s.sha(source)!=digest:errors.append({'path':name,'error':'HASH_MISMATCH'})
assert not errors,errors
counts=json.loads((folder/'coverage-and-flow-current.json').read_text(encoding='utf-8'))
initial={pas:s.rd(folder/f'pass-{pas}-original-initials.csv') for pas in 'AB'}
ids={pas:{x['publication_id'] for x in rows} for pas,rows in initial.items()}
for pas in 'AB':assert len(ids[pas])==len(initial[pas])==counts[f'pass_{pas}_saved']
worker_counts={worker:sum(row.get('worker_id')==worker for row in initial[worker[0]]) for worker in s.WORKERS}
assert counts['by_worker']==worker_counts,('WORKER_BREAKDOWN_NOT_SAME_INITIAL_SNAPSHOT',counts['by_worker'],worker_counts)
assert sum(worker_counts.values())==counts['new_validated_assessments'],'NEW_ASSESSMENT_WORKER_TOTAL_MISMATCH'
assert len(ids['A']&ids['B'])==counts['both_initial_passes']
assert len(ids['A']|ids['B'])==counts['at_least_one_initial_pass']
assert 2*18976-sum(len(x) for x in ids.values())==counts['initial_assessments_remaining']
allids=s.rd(folder/'all-id-status-current.csv');assert len(allids)==len({x['publication_id'] for x in allids})==18976
adjudications=s.rd(folder/'adjudicated-current.csv');assert len(adjudications)==len({x['publication_id'] for x in adjudications})==counts['adjudicated_n']
assert all(x['human_verification']=='PENDING' for x in allids)
print(json.dumps({'published_manifest_sha256':s.sha(path),'hashed_paths_verified':len(manifest['input_and_output_sha256']),'frozen_ids':len(allids),'pass_A':len(ids['A']),'pass_B':len(ids['B']),'both':len(ids['A']&ids['B']),'adjudicated':len(adjudications),'initial_assessments_remaining':counts['initial_assessments_remaining'],'goal_complete':counts['goal_complete'],'errors':errors,'scope':'Mechanical snapshot integrity and exact coverage only; scientific correctness, source limitations and human verification remain separate.'}))
