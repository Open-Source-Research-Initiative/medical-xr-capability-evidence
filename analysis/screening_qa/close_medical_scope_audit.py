"""Exact final scope accounting only; never supplies scientific classifications."""
import argparse,json
from pathlib import Path
import resume_screening as s
import publish_resume_review as p

cli=argparse.ArgumentParser();cli.add_argument('--snapshot',required=True);cli.add_argument('--kind',choices=['medical','date-window','integrity'],default='medical');args=cli.parse_args()
assert args.snapshot.replace('-','').replace('_','').isalnum()
can=s.RUN/'canonical';counts=p.loadj(can/'coverage-and-flow-current.json')
assert counts['initial_assessments_remaining']==0,'INITIAL_ASSESSMENTS_STILL_UNPERFORMED_NO_AUDIT_CLOSURE'
inventory=s.inv();initial={pas:{r['publication_id']:r for r in s.rd(can/f'pass-{pas}-original-initials.csv')} for pas in 'AB'}
assert all(set(rows)==set(inventory) for rows in initial.values())
folder=s.RUN/{'medical':'medical-scope-audit','date-window':'date-window-audit','integrity':'integrity-disposition-audit'}[args.kind]/args.snapshot;receipt=p.loadj(folder/'receipt.json')
if args.kind=='date-window':assert receipt['legacy_unassigned_n']==receipt['deferred_flag_n']==0,'DATE_AUDIT_UNASSIGNED_OR_DEFERRED_SCOPE_REMAINS'
assert receipt['inventory_sha256']==s.EXPECTED_HASH
for pas in 'AB':
    path=can/f'pass-{pas}-original-initials.csv';assert receipt['input_snapshot_sha256'][path.as_posix()]==s.sha(path),'FINAL_LOCATOR_NOT_COMPLETE_CURRENT_INITIALS'
assert receipt['candidates_sha256']==s.sha(folder/'candidates.csv') and receipt['source_packet_sha256']==s.sha(folder/'source-only.csv')
candidates=s.rd(folder/'candidates.csv');keys={(r['pass_id'],r['publication_id']) for r in candidates}
assert len(keys)==len(candidates)==receipt['candidate_pass_id_n']
assert len({key for pas,key in keys})==receipt['candidate_publication_id_n']
notes=s.rd(can/'self-detected-recheck-queue.csv');adj={r['publication_id']:r for r in s.rd(can/'adjudicated-current.csv')}
registry=p.loadj(p.REG);receipts=[]
for entry in registry['entries'].values():receipts.append((Path(entry['receipt']),entry['receipt_sha256']))
for entry in registry.get('source_audit_reviews',[]):receipts.append((Path(entry['file']),entry['sha256']))
links={}
for path,digest in receipts:
    assert s.sha(path)==digest;raw=p.loadj(path)
    assert raw['reviewer']=='Adjudicator_Sol_resume' and raw['model']=='gpt-6.1-sol'
    ids=set(raw.get('ids',[r['publication_id'] for r in raw.get('entries',[])]))
    for name,sha in raw.get('inputs',{}).items():
        token=(Path(name).resolve(),sha)
        for key in ids:links.setdefault((token,key),[]).append({'file':path.as_posix(),'sha256':digest})
accounting=[];inputs={}
def note_matches_kind(row):
    name=Path(row['source_file']).name
    if args.kind in json.loads(row.get('author_declared_audit_kinds_json') or '[]'):return True
    if args.kind=='integrity':return bool(row.get('integrity_status_verbatim') or name.startswith(('prompted-integrity-','self-integrity-')))
    prefixes=('prompted-scope-recheck',) if args.kind=='medical' else ('prompted-date-','self-date-recheck')
    return name.startswith(prefixes)
for name in ['receipt.json','candidates.csv','source-only.csv']:
    path=folder/name;inputs[path.as_posix()]=s.sha(path)
for candidate in candidates:
    pas,key,worker=candidate['pass_id'],candidate['publication_id'],candidate['worker']
    original=initial[pas][key];assert original.get('worker_id')==worker and original['model']=='gpt-6.1-terra'
    matches=[r for r in notes if r['pass_id']==pas and r['publication_id']==key and r['worker']==worker and note_matches_kind(r)]
    assert matches,('OWN_SOURCE_SCOPE_RECHECK_UNPERFORMED',pas,key)
    assert key in adj,('CURRENT_SOURCE_ROUTING_NOT_YET_AVAILABLE',key)
    for row in matches:
        source=Path(row['source_file']);assert s.sha(source)==row['source_sha256']
        payload=json.loads(row['note_payload_json'])
        assert row.get('note_model')=='gpt-6.1-terra' and row.get('rationale_verbatim'),('SOURCE_RECHECK_AUTHOR_OR_RATIONALE_MISSING',pas,key)
        assert p.source_note_quotes(payload),('SOURCE_RECHECK_EXCERPT_MISSING',pas,key)
        assert any(row.get(field) for field in ['proposed_eligibility','rechecked_label_verbatim','recheck_outcome_verbatim']),('SOURCE_RECHECK_OUTCOME_MISSING',pas,key)
        assert row['adjudication_status']=='RECHECK_HASH_LINKED_IN_ADJUDICATION_RECEIPT',('SOL_CONSIDERATION_UNPERFORMED',pas,key)
        credit=links.get(((source.resolve(),row['source_sha256']),key),[]);assert credit,('SOL_HASH_AND_ID_LINK_NOT_FOUND',pas,key)
        inputs[source.as_posix()]=row['source_sha256']
        for item in credit:inputs[item['file']]=item['sha256']
        accounting.append(row|{'source_scope_snapshot':args.snapshot,'sol_receipts_json':json.dumps(credit,sort_keys=True),'current_source_routing_at_closure':adj[key]['eligibility'],'current_source_artifact_at_closure':adj[key].get('source_revision_artifact') or adj[key]['adjudication_artifact'],'scope':'Mechanical accounting of personally authored source rechecks and exact-ID/hash-linked Sol consideration. Copied routing is provisional source authorship, not a coordinator classification.'})
assert {(r['pass_id'],r['publication_id']) for r in accounting}==keys
s.wr(folder/'source-check-and-consideration-accounting.csv',accounting,exclusive=True)
path=folder/'source-check-and-consideration-accounting.csv';inputs[path.as_posix()]=s.sha(path)
index={'generated_at_utc':s.stamp(),'reviewer':'Coordinator_scope_accounting_resume','model':'coordinator_model_not_exposed','inventory_sha256':s.EXPECTED_HASH,'snapshot':args.snapshot,'candidate_pass_id_n':len(keys),'candidate_publication_id_n':len({key for pas,key in keys}),'own_source_checked_pass_id_n':len(keys),'sol_considered_pass_id_n':len(keys),'unperformed_n':0,'inputs':inputs,'human_verification':'PENDING','scope':'Final complete-initial locator scope only. All named candidates have actual own-source notes and hash/ID-linked Sol consideration. Source-limited outcomes, dissent and original initials remain preserved; this is not an exhaustive semantic error detector, scientific ground truth or human verification.'}
index_path=folder/'closure-index.json';s.js(index_path,index,exclusive=True)
obligations=p.loadj(s.RUN/'mandatory-audit-obligations.json');obligation_id={'medical':'fresh-pool-medical-scope-human-only-gate-review','date-window':'fresh-pool-date-window-upper-cutoff-review','integrity':'fresh-pool-integrity-disposition-application-review'}[args.kind];task=next(x for x in obligations['obligations'] if x['obligation_id']==obligation_id)
assert task['status']!='COMPLETE_SOURCE_ASSESSED','AUDIT_ALREADY_CLOSED_REVIEW_EXISTING_INDEX'
task.update(status='COMPLETE_SOURCE_ASSESSED',closure_index=index_path.as_posix(),closure_index_sha256=s.sha(index_path),source_checked_pass_id_n=len(keys),sol_considered_pass_id_n=len(keys),closure_scope=index['scope'],human_verification='PENDING')
s.js(s.RUN/'mandatory-audit-obligations.json',obligations)
print(json.dumps({'closed_named_source_scope_audit':args.kind,'snapshot':args.snapshot,'source_checked_pass_ids':len(keys),'sol_considered_pass_ids':len(keys),'unperformed':0,'human_verification':'PENDING'}))
