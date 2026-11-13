"""Validate coordinator-authored factual notes, not scientific classifications."""
import argparse, json
from pathlib import Path
import resume_screening as s

p=argparse.ArgumentParser();p.add_argument('batch');args=p.parse_args();batch=args.batch
folder=s.RUN/'paired'/batch;source={r['publication_id']:r for r in s.rd(folder/'source.csv')}
a={r['publication_id']:r for r in s.rd(folder/'pass-A.csv')};b={r['publication_id']:r for r in s.rd(folder/'pass-B.csv')}
selection=json.loads((folder/'audit-selection.json').read_text(encoding='utf-8'));sample=set(selection['sample_ids'])
required={i for i in source if a[i]['eligibility']==b[i]['eligibility']=='INCLUDE'}|sample
notes=[];inputs={};paths=sorted((s.RUN/'parent-validation').glob(batch+'-part*.json'))
for path in paths:
    j=json.loads(path.read_text(encoding='utf-8'));assert j['batch_id']==batch and j['source_packet_sha256']==s.sha(folder/'source.csv')
    assert j['reviewer']=='Coordinator_source_validator_resume' and j['model']=='coordinator_model_not_exposed' and j['human_verification']=='PENDING'
    for r in j['records']:
        i=r['publication_id'];assert i in required,('UNASSIGNED_ROUTINE_ID',i)
        assert s.norm(r['supporting_evidence']) in s.norm(source[i]['title']+' '+source[i]['abstract']),('QUOTE_NOT_LITERAL',i,r['supporting_evidence'])
        assert r['source_observation'] and r['routing_or_field_concern'];notes.append(r)
    inputs[path.as_posix()]=s.sha(path)
ids=[r['publication_id'] for r in notes];assert len(ids)==len(set(ids)) and set(ids)==required,('ROUTINE_COVERAGE',len(ids),len(required),required-set(ids))
dest=s.RUN/'parent-validation'/(batch+'-validation-receipt.json')
report={'batch_id':batch,'reviewer':'Coordinator_source_validator_resume','model':'coordinator_model_not_exposed','assessment_stage':'source_validation_after_both_initials','generated_at_utc':s.stamp(),'human_verification':'PENDING','source_packet_sha256':s.sha(folder/'source.csv'),'pass_A_sha256':s.sha(folder/'pass-A.csv'),'pass_B_sha256':s.sha(folder/'pass-B.csv'),'inputs':inputs,'ids':ids,'n':len(ids),'fixed_exclusion_sample':selection['sample_ids'],'agreed_inclusion_n':len(required-sample),'scope':'Parent personally read complete available frozen source text for every listed case and authored factual findings. Mechanical checks cover exact case set/quotes/source hashes only. Sol retains adjudication and independently assesses uncertainties/material conflicts. No new initial judgments or human validation.'}
s.js(dest,report,exclusive=True);print(json.dumps({'batch':batch,'validated_routine_n':len(ids),'receipt':dest.as_posix()}))
