"""Account for existing I/U context-stream source audits; never classify sources."""
import argparse,json
from collections import Counter
from pathlib import Path
import resume_screening as s
import publish_resume_review as p

cli=argparse.ArgumentParser();cli.add_argument('--snapshot',required=True);cli.add_argument('--close-final',action='store_true');args=cli.parse_args()
assert args.snapshot.replace('-','').replace('_','').isalnum()
can=s.RUN/'canonical';counts=p.loadj(can/'coverage-and-flow-current.json');inventory=s.inv();inputs={}
initial={}
for pas in 'AB':
    path=can/f'pass-{pas}-original-initials.csv';inputs[path.as_posix()]=s.sha(path);initial[pas]=s.rd(path)
for name in ['coverage-and-flow-current.json','adjudicated-current.csv','required-audit-status-current.csv']:
    path=can/name;inputs[path.as_posix()]=s.sha(path)
adj={r['publication_id']:r for r in s.rd(can/'adjudicated-current.csv')}
required={r['publication_id']:r for r in s.rd(can/'required-audit-status-current.csv')}
calibration={r['publication_id'] for r in s.rd(s.ROOT/'sol/calibration-v0.3.csv')}
streams={'review_context','protocol','commercial_context','adjacent_context'}
matrix=Counter();candidates=[]
for pas,rows in initial.items():
    for row in rows:
        actor=row.get('worker_id') or row.get('reviewer','UNKNOWN');model=row.get('model') or 'unknown';version=row.get('screening_method_version') or 'not_recorded'
        matrix[(pas,actor,model,version,row['eligibility'],row.get('evidence_stream','MISSING'))]+=1
        if row['eligibility'] not in {'INCLUDE','UNCERTAIN'} or row.get('evidence_stream') not in streams:continue
        key=row['publication_id'];current=adj.get(key,{});audit=required.get(key,{})
        status=audit.get('status',current.get('audit_status',''))
        pending=not current or not status or status.upper().startswith('PENDING') or 'UNPERFORMED' in status.upper() or 'UNAUDIT' in status.upper() or 'NOT_AUDIT' in status.upper()
        if key in calibration and current and current.get('rationale') and status and not pending:pending=False
        candidates.append({'publication_id':key,'pass_id':pas,'original_reviewer':row.get('reviewer',''),'original_worker':row.get('worker_id',''),'original_model':model,'original_method_version':version,'original_eligibility':row['eligibility'],'original_evidence_stream':row['evidence_stream'],'original_evidence_type_verbatim':row.get('evidence_type',''),'original_reason':row.get('reason_code',''),'original_rationale_verbatim':row.get('rationale',''),'initial_artifact':row['initial_artifact'],'initial_artifact_sha256':row['initial_artifact_sha256'],'current_eligibility':current.get('eligibility',''),'current_stream':current.get('evidence_stream',''),'current_type':current.get('evidence_type',''),'current_source_status':status,'source_accounting_status':'PENDING_EXISTING_SOURCE_AUDIT' if pending else 'SOURCE_ASSESSMENT_RECORDED','source_extent':current.get('source_assessment_extent',current.get('assessment_stage','')),'source_actor':current.get('source_revision_reviewer',current.get('reviewer','')),'source_model':current.get('source_revision_model',current.get('model','')),'source_artifact':current.get('source_revision_artifact',current.get('adjudication_artifact','')),'is_calibration_record':key in calibration,'not_a_confirmed_error':'true','human_verification':'PENDING'})
keys={(r['pass_id'],r['publication_id']) for r in candidates};assert len(keys)==len(candidates)
current_include_context=[r for r in adj.values() if r['eligibility']=='INCLUDE' and r.get('evidence_stream') in streams]
pending=sum(r['source_accounting_status'].startswith('PENDING') for r in candidates)
if args.close_final:
    assert counts['initial_assessments_remaining']==0 and all(len(rows)==len({r['publication_id'] for r in rows})==len(inventory) for rows in initial.values()),'FINAL_COMPLETE_INITIAL_SCOPE_REQUIRED'
    assert pending==0,('EXISTING_SOURCE_AUDITS_STILL_PENDING',pending)
    assert not current_include_context,('CURRENT_INCLUDE_CONTEXT_COMBINATIONS_NEED_SOURCE_FIELD_CLARIFICATION',[r['publication_id'] for r in current_include_context])
    assert all(r['publication_id'] in required or r['publication_id'] in calibration for r in candidates),'FINAL_REQUIRED_AUDIT_SCOPE_LINK_MISSING'
folder=s.RUN/'label-stream-diagnostics'/args.snapshot;folder.mkdir(parents=True,exist_ok=False)
s.wr(folder/'candidate-source-accounting.csv',candidates,exclusive=True)
s.wr(folder/'original-label-stream-matrix.csv',[dict(zip(['pass_id','actor','model','method_version','original_eligibility','original_evidence_stream'],key))|{'pass_id_assessments':n} for key,n in sorted(matrix.items())],exclusive=True)
s.wr(folder/'current-include-context-candidates.csv',[{k:r.get(k,'') for k in ['publication_id','eligibility','evidence_stream','evidence_type','rationale','source_assessment_extent','adjudication_artifact','source_revision_artifact']} for r in current_include_context],exclusive=True)
for name in ['candidate-source-accounting.csv','original-label-stream-matrix.csv','current-include-context-candidates.csv']:inputs[(folder/name).as_posix()]=s.sha(folder/name)
receipt={'generated_at_utc':s.stamp(),'snapshot':args.snapshot,'reviewer':'Coordinator_source_accounting_resume','model':'coordinator_model_not_exposed','inventory_sha256':s.EXPECTED_HASH,'inputs':inputs,'candidate_pass_id_n':len(candidates),'candidate_publication_id_n':len({r['publication_id'] for r in candidates}),'existing_source_audits_pending':pending,'current_include_context_combinations_pending_clarification':len(current_include_context),'closed_final_scope':args.close_final,'classification_count_generated_by_script':0,'human_verification':'PENDING','scope':'Original non-excluded/context-stream combinations, including legitimate missing-text uncertainty and mixed original observations, are diagnostic candidates rather than confirmed errors. They already require source assessment as INCLUDE/UNCERTAIN records. All original labels/streams and original agreement remain unchanged. This only accounts for recorded source judgments; it is not an accuracy estimate, scientific validation or a new eligibility rule.'}
path=folder/('closure-index.json' if args.close_final else 'snapshot-receipt.json');s.js(path,receipt,exclusive=True)
if args.close_final:
    file=s.RUN/'mandatory-audit-obligations.json';items=p.loadj(file);target=next(r for r in items['obligations'] if r['obligation_id']=='initial-context-label-source-accounting')
    target.update(status='COMPLETE_SOURCE_ASSESSED',closure_index=path.as_posix(),closure_index_sha256=s.sha(path),source_accounted_pass_id_n=len(candidates),source_accounted_publication_id_n=receipt['candidate_publication_id_n'],closure_scope=receipt['scope'],human_verification='PENDING');s.js(file,items)
print(json.dumps({k:receipt[k] for k in ['snapshot','candidate_pass_id_n','candidate_publication_id_n','existing_source_audits_pending','current_include_context_combinations_pending_clarification','closed_final_scope','classification_count_generated_by_script']}))
