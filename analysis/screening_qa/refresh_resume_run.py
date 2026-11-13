"""Single coordinator refresh using the validated reusable batch interfaces."""
import argparse, json, re
from pathlib import Path
import resume_screening as s
import publish_resume_review as p

parser=argparse.ArgumentParser();parser.add_argument('--skip-initial-refresh',action='store_true');args=parser.parse_args()
if not args.skip_initial_refresh:s.refresh()
else:
    counts=p.loadj(s.RUN/'canonical/current-counts.json')
    for pas in 'AB':assert len(s.rd(s.RUN/'canonical'/f'pass-{pas}-original-initials.csv'))==counts[f'pass_{pas}_saved'],'INITIAL_SNAPSHOT_COUNT_MISMATCH'
registry=p.loadj(p.REG) if p.REG.exists() else {'entries':{}}
folder=s.RUN/'adjudicator_sol'
for source in sorted(folder.glob('B*-adjudicated-resume-v0.4.6.csv')):
    batch=source.name[:5];receipt=source.with_name(source.stem+'-receipt.json')
    if not receipt.exists():continue
    existing=registry['entries'].get(batch)
    if existing:
        assert s.sha(source)==existing['sha256'],'IMMUTABLE_ADJUDICATION_BASE_DRIFT'
        assert s.sha(receipt)==existing['receipt_sha256'],'IMMUTABLE_ADJUDICATION_RECEIPT_DRIFT'
        for previous in existing['revisions']+existing.get('additional_source_receipts',[]):assert s.sha(Path(previous['file']))==previous['sha256'],('IMMUTABLE_SOURCE_REVISION_DRIFT',previous['file'])
    regular=sorted(folder.glob(batch+'-source-revision-*.json'),key=lambda x:int(re.search(r'revision-(\d+)',x.name)[1]))
    revisions=[Path(x['file']) for x in existing.get('revisions',[])] if existing else []
    integrity=sorted(folder.glob(batch+'-integrity-revision-*.json'),key=lambda x:int(re.search(r'revision-(\d+)',x.name)[1]))
    assert not (any(x not in revisions for x in regular) and any(x not in revisions for x in integrity)),('EXPLICIT_CROSS_CLASS_REVISION_ORDER_REQUIRED',batch)
    regular+=integrity
    for item in regular:
        if item not in revisions:revisions.append(item)
    extra=folder/(batch+'-source-access-exceptions.json')
    if not extra.exists():
        for candidate in p.source_attachments(folder,batch):
            if p.loadj(candidate).get('source_access_exceptions'):
                extra=candidate;break
    want=[{'file':x.as_posix(),'sha256':s.sha(x)} for x in revisions]
    attachments=[{'file':x.as_posix(),'sha256':s.sha(x)} for x in p.source_attachments(folder,batch)]
    old=[{'file':x['file'],'sha256':x['sha256']} for x in existing.get('revisions',[])] if existing else []
    if existing and existing['sha256']==s.sha(source) and old==want and existing.get('additional_source_receipts',[])==attachments:continue
    p.register(batch,source.as_posix(),receipt.as_posix(),[x.as_posix() for x in revisions],extra.as_posix() if extra.exists() else None)
for receipt in sorted(folder.glob('method-046-application-review-*-audit-receipt.json')):p.register_method_review(receipt.as_posix())
source_receipts=sorted(folder.glob('source-audit-*-receipt.json'))
frozen_for_packet_checks=None
for receipt in source_receipts:
    if receipt.name.endswith('-source-provenance-receipt.json'):
        packet=p.loadj(receipt)
        assert set(packet)=={'source_snapshot','source_snapshot_sha256','derived_packet','derived_packet_sha256','publication_ids','verification','linked_receipt','linked_receipt_sha256'},('UNKNOWN_SOURCE_PROVENANCE_SCHEMA',receipt)
        assert Path(packet['source_snapshot']).resolve()==s.INVENTORY.resolve() and packet['source_snapshot_sha256']==s.EXPECTED_HASH
        linked=folder/packet['linked_receipt'];assert s.sha(linked)==packet['linked_receipt_sha256']
        review=p.loadj(linked)
        assert review['reviewer']=='Adjudicator_Sol_resume' and review['model']=='gpt-6.1-sol' and review['human_verification']=='PENDING'
        derived=folder/packet['derived_packet'];assert s.sha(derived)==packet['derived_packet_sha256'] and review['inputs'][derived.as_posix()]==s.sha(derived)
        copied=s.rd(derived);ids=[row['publication_id'] for row in copied]
        assert len(ids)==len(set(ids)) and ids==packet['publication_ids'] and set(ids)=={row['publication_id'] for row in review['entries']}
        if frozen_for_packet_checks is None:frozen_for_packet_checks=s.inv()
        required_source_fields={'publication_id','title','abstract','abstract_record_id','year','year_candidates_json','doi','date_tags_json','journal','document_types_json','titles_json','title_conflict','year_conflict','doi_conflict'}
        assert all(required_source_fields<=set(row) for row in copied),('COPIED_PACKET_REQUIRED_SOURCE_FIELD_MISSING',receipt)
        assert all(all(field in frozen_for_packet_checks[row['publication_id']] and value==frozen_for_packet_checks[row['publication_id']][field] for field,value in row.items()) for row in copied),('COPIED_SOURCE_FIELD_DIFFERS_FROM_FROZEN',receipt)
        continue
    if receipt.name.endswith('-packet-receipt.json'):
        # A pinned copy-packet receipt is an input, not a source judgment.
        packet=p.loadj(receipt)
        assert set(packet)=={'scope','input_sha256','output_sha256'},('UNKNOWN_PACKET_RECEIPT_SCHEMA',receipt)
        for name,digest in packet['input_sha256'].items():assert s.sha(Path(name))==digest
        consumers=[p.loadj(path) for path in source_receipts if path!=receipt and not path.name.endswith('-packet-receipt.json')]
        consumers=[raw for raw in consumers if raw.get('inputs',{}).get(receipt.as_posix())==s.sha(receipt)]
        assert len(consumers)==1 and consumers[0].get('reviewer')=='Adjudicator_Sol_resume' and consumers[0].get('model')=='gpt-6.1-sol',('PACKET_NOT_LINKED_TO_ONE_ACTUAL_SOL_AUDIT',receipt)
        outputs=[Path(name) for name,digest in consumers[0]['inputs'].items() if digest==packet['output_sha256']]
        assert len(outputs)==1 and s.sha(outputs[0])==packet['output_sha256'],('PACKET_OUTPUT_NOT_PINNED',receipt)
        continue
    p.register_source_audit(receipt.as_posix())
for index in sorted(folder.glob('legacy-required-audit-scope-index-*.json')):p.register_source_audit_index(index.as_posix())
p.publish()
