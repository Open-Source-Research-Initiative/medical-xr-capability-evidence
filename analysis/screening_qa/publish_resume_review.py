"""Coordinator-only validation, routing views and review packet; no source labels invented."""
import argparse, csv, hashlib, json, re
from collections import Counter, defaultdict
from datetime import datetime,timezone
from pathlib import Path
import resume_screening as s
import resume_rechecks as rr

ROOT=s.ROOT;RUN=s.RUN;CANON=RUN/'canonical';REG=RUN/'adjudication-registry.json'
DATEREG=RUN/'date-recheck-registry.json'
def loadj(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def source_note_quotes(item):
    fields=['quote','source_quote','source_excerpt','supporting_evidence','exact_excerpt','exact_quote','exact_source_quote','additional_excerpt','excerpt','literal_excerpt','literal_source_excerpt','frozen_quote','frozen_source_quote','notice_excerpt']
    quotes=[item[field] for field in fields if item.get(field)]
    if item.get('source_evidence'):
        assert isinstance(item['source_evidence'],list),'SOURCE_EVIDENCE_ARRAY_REQUIRED'
        quotes.extend(item['source_evidence'])
    assert all(isinstance(quote,str) and quote.strip() for quote in quotes),'INVALID_SOURCE_NOTE_QUOTE'
    return quotes

def worker_note_paths(worker):
    """Own post-initial notes only; never descend into legacy recheck drafts."""
    root=RUN/'workers'/worker
    patterns=['self-*recheck*.json','self-correction-*.json','self-integrity-*.json','identity-issues-*.json','prompted-*-recheck*.json','prompted-integrity-locator-sweep-[0-9]*.json']
    paths={p for pattern in patterns for p in root.glob(pattern)}
    for name in ['date-window-audit','medical-scope-audit','integrity-disposition-audit']:
        folder=root/name
        paths.update(p for pattern in patterns for p in folder.rglob(pattern))
    return paths

def receipt_input_path(name,base):
    p=Path(name);candidates=[p] if p.is_absolute() else [p,base/p]
    found={candidate.resolve() for candidate in candidates if candidate.is_file()}
    assert len(found)==1,('MISSING_OR_AMBIGUOUS_RECEIPT_INPUT_PATH',name)
    return next(iter(found))

def pin_legacy_adjudications(file):
    source=Path(file);baseline=loadj(source)
    assert baseline['active_adjudication_files']==34 and baseline['rows']==baseline['unique_ids']==1668 and not baseline['duplicate_ids'] and not baseline['outside_inventory']
    expected={Path(name).as_posix():digest for name,digest in baseline['sha256'].items()}
    registry=loadj(ROOT/'astra/current-artifacts.json')
    current={Path(x['adjudication']).as_posix() for x in registry.values() if isinstance(x,dict) and x.get('adjudication')}
    assert current==set(expected),'LEGACY_REVIEW_PIN_PATH_SET_DIFFERS'
    for name,digest in expected.items():assert s.sha(ROOT/name)==digest,('LEGACY_ADJUDICATION_DIFFERS_FROM_PRE_RESUME_REVIEW',name)
    target=RUN/'admin/legacy-adjudication-baseline-review.json'
    with target.open('xb') as f:f.write(source.read_bytes())
    s.js(RUN/'admin/legacy-adjudication-pin-receipt.json',{'source_review':source.as_posix(),'source_review_sha256':s.sha(source),'copied_baseline':target.as_posix(),'copied_baseline_sha256':s.sha(target),'validated_at_utc':s.stamp(),'files':len(expected),'rows':1668,'scope':'All raw legacy adjudications match the pre-resume review exactly. Subsequent source corrections must remain ordered overlays, not edits to pinned raw records.'},exclusive=True)
    print(json.dumps({'legacy_adjudication_files_pinned':len(expected),'rows':1668,'all_match_pre_resume_review':True}))

def prepare_legacy_audit_scope():
    folder=RUN/'legacy-audit-scope';folder.mkdir(exist_ok=True)
    status=CANON/'required-audit-status-current.csv';selected=[x for x in s.rd(status) if x['status']=='PENDING_SCOPE_VERIFICATION']
    assert selected and len(selected)==len({x['publication_id'] for x in selected})
    inventory=s.inv();s.wr(folder/'manifest.csv',selected,exclusive=True)
    s.wr(folder/'source-only.csv',[inventory[x['publication_id']]|{'audit_batch_id':x['batch_id']} for x in selected],exclusive=True)
    with (folder/'status-at-dispatch.csv').open('xb') as f:f.write(status.read_bytes())
    s.js(folder/'receipt.json',{'generated_at_utc':s.stamp(),'source_checked_n':0,'assigned_n':len(selected),'source_packet_sha256':s.sha(folder/'source-only.csv'),'manifest_sha256':s.sha(folder/'manifest.csv'),'status_at_dispatch_sha256':s.sha(folder/'status-at-dispatch.csv'),'inventory_sha256':s.EXPECTED_HASH,'scope':'Exact required legacy audit-scope verification cases; all unperformed at dispatch. Sol personally source-assesses them and writes explicit field-only overlays; raw legacy adjudications and original samples are preserved.'},exclusive=True)
    print(json.dumps({'legacy_audit_scope_cases':len(selected),'packet':(folder/'source-only.csv').as_posix()}))

def show_legacy_audit_scope(offset,limit):
    folder=RUN/'legacy-audit-scope';receipt=loadj(folder/'receipt.json');packet=folder/'source-only.csv'
    assert s.sha(packet)==receipt['source_packet_sha256'];rows=[];size=0
    for row in s.rd(packet)[offset:]:
        length=len(json.dumps(row,ensure_ascii=False))
        if rows and (len(rows)>=limit or size+length>22000):break
        rows.append(row);size+=length
    print(json.dumps({'scope':'Required legacy audit-scope verification, not initial screening','assigned_n':receipt['assigned_n'],'offset':offset,'n_shown':len(rows),'source_packet_sha256':receipt['source_packet_sha256'],'records':rows},ensure_ascii=False,indent=2))
def revision_rows(j,base):
    if 'supersedes_fields_only_from' in j:
        assert j['supersedes_fields_only_from']==base
        return j['entries']
    precedence=j.get('precedence','')
    assert j.get('batch')==base[:5] and base in precedence and 'revision after' in precedence.casefold(),'REVISION_PRECEDENCE_NOT_EXPLICIT'
    return j['revisions']

def validate_revision_inputs(revision,path,base,sources=None):
    if revision.get('base_sha256'):assert revision['base_sha256']==s.sha(base),('REVISION_BASE_HASH_DRIFT',path)
    for field in ['inputs','input_hashes','source_inputs']:
        for name,digest in revision.get(field,{}).items():
            actual=receipt_input_path(name,path.parent)
            assert s.sha(actual)==digest,('REVISION_INPUT_HASH_DRIFT',path,name)
            if sources is not None:sources[actual.as_posix()]=digest
    if revision.get('source_receipt'):
        actual=receipt_input_path(revision['source_receipt'],path.parent)
        if sources is not None:sources[actual.as_posix()]=s.sha(actual)

def apply_fields(result,row,path,digest):
    key=row['publication_id'];assert key in result
    assert not {'year','source_memberships_json','record_ids_json','reviewer','model','publication_id'}&(set(row)-{'publication_id'})
    for field,value in row.items():
        if field!='publication_id':result[key][field]=value
    if 'eligibility' in row:result[key]['adjudicated_eligibility']=row['eligibility']
    elif 'adjudicated_eligibility' in row:result[key]['eligibility']=row['adjudicated_eligibility']
    result[key].update(source_revision_artifact=path.as_posix(),source_revision_sha256=digest,source_revision_reviewer='Adjudicator_Sol_resume',source_revision_model='gpt-6.1-sol')
    if 'identity_issue' in row:
        result[key].update(identity_issue_source_artifact=path.as_posix(),identity_issue_source_sha256=digest,identity_issue_source_reviewer='Adjudicator_Sol_resume',identity_issue_source_model='gpt-6.1-sol')
def source_attachments(folder,batch):
    paths={x for x in folder.glob(batch+'-*source*.json') if 'source-revision-' not in x.name}
    parent=folder/(batch+'-parent-validation-input-receipt.json')
    if parent.exists():paths.add(parent)
    return sorted(paths)
def modality_token(raw):
    # Spelling/case only, never an inference from a device, keyword or source label.
    mapping={'xr':'XR','uncertain':'uncertain','nonimmersive_3d':'nonimmersive_3D','non_immersive_3d':'nonimmersive_3D'}
    assert raw.casefold() in mapping,('UNRECOGNIZED_MODALITY_VALUE',raw)
    return mapping[raw.casefold()]
def date_rows(entry):
    p=Path(entry['file']);assert s.sha(p)==entry['sha256'];raw=loadj(p)
    if isinstance(raw,dict) and raw.get('publication_id'):
        assert raw.get('model',raw.get('actual_model','gpt-6.1-terra'))=='gpt-6.1-terra'
        data=[raw]
    elif isinstance(raw,dict):
        container=next((field for field in ['records','checks','results','entries'] if isinstance(raw.get(field),list)),None)
        assert raw.get('worker',raw.get('worker_id')) in {None,entry['worker']} and raw.get('actual_model',raw.get('model'))=='gpt-6.1-terra' and container
        data=[row|{'date_recording_method':raw.get('method','')} for row in raw[container]]
    else:data=raw
    rows={r['publication_id']:r for r in data};assert len(rows)==len(data),'DUPLICATE_DATE_SIDECAR_ID'
    for row in data:
        assert row.get('worker',row.get('worker_id')) in {None,entry['worker']},('DATE_ROW_OWNER_MISMATCH',row['publication_id'])
        declared={row[field] for field in ['model','actual_model','authorship'] if row.get(field)}
        assert not declared or declared=={'gpt-6.1-terra'},('DATE_ROW_MODEL_MISMATCH',row['publication_id'])
    for extra in entry.get('corrections',[]):
        p=Path(extra['file']);assert s.sha(p)==extra['sha256']
        for r in loadj(p):assert r['publication_id'] in rows;rows[r['publication_id']]=r
    return list(rows.values())

def register_date(worker,file,corrections=()):
    p=Path(file);raw=loadj(p);assert (isinstance(raw,list) and raw) or (isinstance(raw,dict) and (raw.get('publication_id') or any(raw.get(field) for field in ['records','checks','results','entries'])))
    source_entry={'file':p.as_posix(),'sha256':s.sha(p),'corrections':[],'worker':worker,'pass_id':worker[0],'model':'gpt-6.1-terra'}
    for correction in corrections:
        q=Path(correction);source_entry['corrections'].append({'file':q.as_posix(),'sha256':s.sha(q)})
    rows=date_rows(source_entry)
    initials=s.worker_rows(worker);seen=set();fresh_legacy=None;stages={};legacy_links={}
    for r in rows:
        i=r['publication_id'];assert i not in seen
        if i in initials:stages[i]='OWN_INITIAL_DATE_SOURCE_CHECK'
        else:
            if fresh_legacy is None:fresh_legacy=rr.all_saved()
            saved=fresh_legacy.get((worker[0],i),{})
            assert saved.get('worker_id')==worker,('DATE_NOT_OWN_SAVED_INITIAL_OR_LEGACY_RECHECK',worker,i)
            stages[i]='FRESH_LEGACY_DATE_METADATA_CORRECTION'
            legacy_links[i]={'file':saved['recheck_artifact'],'sha256':saved['recheck_artifact_sha256'],'submitted_date_check_status':saved.get('date_check_status','')}
        seen.add(i)
        for k in ['date_check_status','date_basis','journal_first_publication_date','date_boundary_status']:assert r.get(k),('DATE_FIELD_MISSING',i,k)
        assert r['date_check_status'] in {'CHECKED_VERIFIED','CHECKED_UNRESOLVED','CHECKED_INDEXED_PRIMARY','CHECKED_SOURCE_LIMITED'}
        assert r.get('date_source') or r['date_check_status'] in {'CHECKED_UNRESOLVED','CHECKED_SOURCE_LIMITED'},('VERIFIED_DATE_REQUIRES_SOURCE',i)
    assert not (legacy_links and corrections),'LEGACY_DATE_AMENDMENTS_REQUIRE_NEW_IMMUTABLE_FILE_WITH_APPENDED_PRECEDENCE'
    j=loadj(DATEREG) if DATEREG.exists() else {'entries':[]}
    existing=next((e for e in reversed(j['entries']) if e['file']==p.as_posix()),None)
    if existing:
        assert existing['sha256']==s.sha(p),'IMMUTABLE_DATE_SIDECAR_DRIFT'
        if not corrections or existing.get('corrections',[])==source_entry['corrections']:return
        assert source_entry['corrections'][:len(existing.get('corrections',[]))]==existing.get('corrections',[]),'DATE_CORRECTIONS_MUST_APPEND_EXPLICIT_PRECEDENCE'
    j['entries'].append(source_entry|{'worker':worker,'pass_id':worker[0],'model':'gpt-6.1-terra','ids':sorted(seen),'date_assignment_stages':stages,'linked_fresh_legacy_artifacts':legacy_links,'precedence':len(j['entries'])+1,'registered_at_utc':s.stamp(),'validation':'Own saved initial or own fresh legacy-recheck IDs, unique rows, actual source/status/extent fields and explicit appended corrections; submitted raw records preserved; parent did not independently verify source correctness'})
    s.js(DATEREG,j);print(json.dumps({'registered_date_worker':worker,'n':len(rows)}))

def register_metadata(file):
    p=Path(file);r=loadj(p);assert r['reviewer']=='Adjudicator_Sol_resume' and r['model']=='gpt-6.1-sol'
    assert r['field']=='prior_exposure' and r['replacement'] and r['files']
    j=loadj(REG);entry={'file':p.as_posix(),'sha256':s.sha(p)}
    existing=j.setdefault('metadata_clarifications',[])
    if not any(x['file']==entry['file'] for x in existing):existing.append(entry)
    else:assert next(x for x in existing if x['file']==entry['file'])['sha256']==entry['sha256']
    s.js(REG,j);print(json.dumps({'registered_metadata':p.name,'field':r['field']}))

def register_method_review(file,revalidate=False):
    path=Path(file);receipt=loadj(path);folder=path.parent
    assert receipt['reviewer']=='Adjudicator_Sol_resume' and receipt['model']=='gpt-6.1-sol' and receipt['human_verification']=='PENDING'
    registry=loadj(REG);known=registry.setdefault('method_application_reviews',[])
    previous=next((x for x in known if x['file']==path.as_posix()),None)
    if previous:
        assert previous['sha256']==s.sha(path)
        if not revalidate:return
    for name,digest in receipt['input_hashes'].items():assert s.sha(folder/name)==digest,('METHOD_REVIEW_INPUT_DRIFT',name)
    inventory=s.inv();entries=receipt['entries'];ids=[x['publication_id'] for x in entries]
    assert len(ids)==len(set(ids))==receipt['scope_n']
    source_hashes={}
    for row in entries:
        key=row['publication_id'];assert key in inventory and row['batch_id'] in registry['entries']
        assert registry['entries'][row['batch_id']]['sha256']==row['base_sha256']
        batch=row['batch_id']
        if batch not in source_hashes:source_hashes[batch]={s.sha(ROOT/'shared/batches'/f'{batch}.csv'),s.sha(RUN/'paired'/batch/'source.csv')}
        assert row['source_sha256'] in source_hashes[batch],('METHOD_REVIEW_SOURCE_HASH',key)
        q=s.norm(row['supporting_evidence']);raw=inventory[key]
        if not any(q in s.norm(raw.get(k,'')) for k in ['title','abstract']):
            external=folder/row.get('external_receipt','')
            assert row.get('external_receipt') and external.is_file(),('METHOD_REVIEW_QUOTE_NOT_LITERAL',key)
            assert external.name in receipt['input_hashes'],('EXTERNAL_REVIEW_SOURCE_NOT_HASHED',key)
        assert row['source_assessment_extent'] and row['rationale']
    for revision in receipt['ordered_revision_files']:
        rp=folder/revision['path'];assert s.sha(rp)==revision['sha256'];jj=loadj(rp)
        base=jj['supersedes_fields_only_from'];batch=base[:5];e=registry['entries'][batch]
        assert Path(e['file']).name==base and jj['model']=='gpt-6.1-sol' and jj['reviewer']=='Adjudicator_Sol_resume' and jj['human_verification']=='PENDING'
        assert len(jj['entries'])==revision['n']
        for row in jj['entries']:
            assert row['publication_id'] in ids
            assert row.get('human_verification','PENDING')=='PENDING'
            if row.get('modality_stream'):modality_token(row['modality_stream'])
        if previous:
            registered=next((x for x in e['revisions'] if x['file']==rp.as_posix()),None)
            assert registered and registered['sha256']==revision['sha256'],'REGISTERED_METHOD_REVISION_MISSING_OR_CHANGED'
        if not any(x['file']==rp.as_posix() for x in e['revisions']):
            registry['history'].append(json.loads(json.dumps(e)))
            e['revisions'].append({'file':rp.as_posix(),'sha256':revision['sha256'],'precedence_basis':'Ordered method-application review after base and prior registered source revisions','audit_receipt':path.as_posix()})
    if previous:return
    known.append({'file':path.as_posix(),'sha256':s.sha(path),'precedence':len(known)+1,'registered_at_utc':s.stamp(),'source_checked_n':len(ids),'revised_n':receipt['revised_n'],'unchanged_n':receipt['unchanged_n']})
    s.js(REG,registry)
    print(json.dumps({'registered_method_review':path.name,'checked':len(ids),'revised':receipt['revised_n'],'unchanged':receipt['unchanged_n']}))

def register_method_index(file):
    path=Path(file);folder=path.parent;index=loadj(path)
    assert index['reviewer']=='Adjudicator_Sol_resume' and index['model']=='gpt-6.1-sol' and index['human_verification']=='PENDING'
    rows=s.rd(folder/index['status_csv']);assert s.sha(folder/index['status_csv'])==index['status_csv_sha256']
    ids=[x['publication_id'] for x in rows];assert len(ids)==len(set(ids))==index['scope_n']
    assert dict(Counter(x['audit_outcome'] for x in rows))==index['audit_outcomes']
    reviewed=[];ordered=[]
    for name,digest in index['input_hashes'].items():
        item=folder/name;assert s.sha(item)==digest,('METHOD_INDEX_INPUT_DRIFT',name)
        if name.endswith('-audit-receipt.json'):
            register_method_review(item.as_posix(),revalidate=True)
            receipt=loadj(item);reviewed.extend(x['publication_id'] for x in receipt['entries']);ordered.extend(receipt['ordered_revision_files'])
    assert len(reviewed)==len(set(reviewed)) and set(reviewed)==set(ids),'METHOD_INDEX_RECEIPT_COVERAGE'
    assert ordered==index['ordered_revision_files'],'METHOD_INDEX_REVISION_ORDER'
    for revision in ordered:assert s.sha(folder/revision['path'])==revision['sha256']
    candidates={r['publication_id'] for r in s.rd(folder/'method-046-application-followup-candidates-01.csv')}
    assert len(candidates)==index['followup_candidates_n']==index['followup_candidates_checked_n'] and candidates<=set(ids) and index['followup_candidates_pending_n']==0
    registry=loadj(REG);registry['method_application_review_index']={'file':path.as_posix(),'sha256':s.sha(path),'status_csv':(folder/index['status_csv']).as_posix(),'status_csv_sha256':index['status_csv_sha256'],'source_checked_unique':len(ids),'validation_at_utc':s.stamp(),'validation':'All receipt input/source/base/revision hashes and literal quote or hashed external-receipt linkage revalidated; exact unique scope, outcomes, candidate coverage and revision sequence. Factual correctness and human verification remain separate.'};s.js(REG,registry)
    obligation_path=RUN/'mandatory-audit-obligations.json';obligations=loadj(obligation_path)
    target=next(x for x in obligations['obligations'] if x['obligation_id']=='fresh-sol-046-immersion-application-review')
    target.update(status='COMPLETE_SOURCE_ASSESSED',source_checked_n=len(ids),source_limited_unchanged_n=index['audit_outcomes'].get('SOURCE_LIMITED_UNCHANGED',0),closure_index=path.as_posix(),closure_index_sha256=s.sha(path),closure_scope=index['scope'],human_verification='PENDING')
    s.js(obligation_path,obligations)
    print(json.dumps({'validated_method_index':path.name,'source_checked_unique':len(ids),'outcomes':index['audit_outcomes'],'scope':'Named application-review scope only'}))

def register_source_audit(file):
    """Register Sol-authored source audits/field overlays against preserved bases."""
    path=Path(file);receipt=loadj(path);folder=path.parent;registry=loadj(REG)
    assert receipt['reviewer']=='Adjudicator_Sol_resume' and receipt['model']=='gpt-6.1-sol' and receipt['human_verification']=='PENDING'
    assert receipt['screening_method_version']=='0.4.6' and receipt['inventory_sha256']==s.EXPECTED_HASH
    known=registry.setdefault('source_audit_reviews',[])
    prior=next((x for x in known if x['file']==path.as_posix()),None)
    if prior:assert prior['sha256']==s.sha(path);return
    for name,digest in receipt['inputs'].items():assert s.sha(Path(name))==digest,('SOURCE_AUDIT_INPUT_DRIFT',name)
    inventory=s.inv();rows=receipt['entries'];ids=[x['publication_id'] for x in rows]
    assert len(ids)==len(set(ids))==receipt['n']
    legacy=loadj(ROOT/'astra/current-artifacts.json');bases={}
    for row in rows:
        key=row['publication_id'];batch=row['batch_id'];assert key in inventory
        if batch in registry['entries']:base=registry['entries'][batch]
        else:
            old=legacy[batch];p=ROOT/old['adjudication'];base={'file':p.as_posix(),'sha256':s.sha(p)}
            pinned=loadj(RUN/'admin/legacy-adjudication-baseline-review.json')['sha256'];assert pinned[str(p.relative_to(ROOT))]==base['sha256']
        assert row['base_sha256']==base['sha256'] and row['base_csv']==Path(base['file']).name
        assert key in {x['publication_id'] for x in s.rd(Path(base['file']))},('SOURCE_AUDIT_WRONG_BASE',key)
        bases[batch]=base
        quote=s.norm(row['supporting_evidence']);raw=inventory[key];assert quote.strip()
        if not any(quote in s.norm(raw.get(field,'')) for field in ['title','abstract']):
            external=Path(row.get('external_receipt',''));assert external.is_file() and external.as_posix() in {Path(x).as_posix() for x in receipt['inputs']},('SOURCE_AUDIT_EXTERNAL_QUOTE_LINK_REQUIRED',key)
        assert row['source_assessment_extent'] and row['rationale'] and row['audit_outcome'] in {'CHECKED_UNCHANGED','REVISED','SOURCE_LIMITED_UNCHANGED'}
    revision_ids=[];rationale_wrapper_notes=[]
    for item in receipt['ordered_revision_files']:
        p=folder/item['path'];assert s.sha(p)==item['sha256'];revision=loadj(p)
        assert revision['reviewer']=='Adjudicator_Sol_resume' and revision['model']=='gpt-6.1-sol' and revision['human_verification']=='PENDING'
        batch=item['batch_id'];base=bases[batch];entries=revision_rows(revision,Path(base['file']).name)
        assert len(entries)==item['n']
        for row in entries:
            key=row['publication_id'];assert key in ids and not {'year','source_memberships_json','record_ids_json','reviewer','model'}&set(row)
            assert next(x for x in rows if x['publication_id']==key)['batch_id']==batch
            source_entry=next(x for x in rows if x['publication_id']==key)
            assert row.get('audit_status') and row.get('source_assessment_extent')==source_entry['source_assessment_extent']
            assert row.get('supporting_evidence')==source_entry['supporting_evidence']
            if row.get('rationale')!=source_entry['rationale']:
                authored=row.get('rationale','');recorded=source_entry['rationale']
                assert authored and recorded.endswith(authored),('SOURCE_AUDIT_RATIONALE_DIFFERS',key)
                prefix=recorded[:-len(authored)]
                wrapper=re.fullmatch(r'Own complete frozen source/both preserved originals/pinned and current fields/exact ([AB][1-4]) raw recheck personally read\. ',prefix)
                assert wrapper and wrapper[1] in {item.get('worker_id') for item in receipt.get('considered_rechecks',[]) if item['publication_id']==key},('SOURCE_AUDIT_RATIONALE_NOT_REDUNDANT_OWNER_WRAPPER',key)
                matches=[]
                for note in folder.glob('clarification-*-rationale-wrapper.json'):
                    data=loadj(note)
                    if data.get('publication_id')!=key or data.get('inputs',{}).get(path.as_posix())!=s.sha(path) or data.get('inputs',{}).get(p.as_posix())!=s.sha(p):continue
                    assert data['reviewer']=='Adjudicator_Sol_resume' and data['model']=='gpt-6.1-sol' and data['human_verification']=='PENDING' and data['clarification']
                    for name,digest in data['inputs'].items():assert s.sha(Path(name))==digest
                    matches.append({'publication_id':key,'file':note.as_posix(),'sha256':s.sha(note),'receipt_rationale_verbatim':recorded,'revision_rationale_verbatim':authored,'redundant_provenance_prefix_verbatim':prefix,'validation':'Explicit author-confirmed provenance-wrapper difference only; substantive authored rationale, exact quote and source extent unchanged. Both raw texts preserved; no rationale generated or source review credited by this adapter.'})
                assert len(matches)==1,('EXPLICIT_RATIONALE_WRAPPER_CLARIFICATION_REQUIRED',key)
                rationale_wrapper_notes.extend(matches)
            for field in ['eligibility','adjudicated_eligibility']:
                if row.get(field):assert row[field] in {'INCLUDE','EXCLUDE','UNCERTAIN'}
            if row.get('eligibility') in {'INCLUDE','EXCLUDE'} and not inventory[key]['abstract'].strip():
                exception=source_entry.get('source_access_exception',{})
                assert all(exception.get(field) for field in ['source_url','inspected_extent','own_source_excerpt','source_access_status']),('SOURCE_AUDIT_SUBSTANTIVE_ACCESS_EXCEPTION_REQUIRED',key)
            if row.get('modality_stream'):modality_token(row['modality_stream'])
            revision_ids.append(key)
        if batch in registry['entries']:target=registry['entries'][batch]
        else:
            target=registry.setdefault('legacy_revisions',{}).setdefault(batch,{'file':base['file'],'sha256':base['sha256'],'revisions':[]})
            assert target['file']==base['file'] and target['sha256']==base['sha256']
        assert not any(x['file']==p.as_posix() for x in target['revisions']),'SOURCE_AUDIT_REVISION_ALREADY_REGISTERED'
        target['revisions'].append({'file':p.as_posix(),'sha256':item['sha256'],'audit_receipt':path.as_posix(),'precedence_basis':'Explicit ordered source-audit overlay appended after preserved base and prior registered overlays'})
    assert len(revision_ids)==len(set(revision_ids)) and set(revision_ids)==set(ids),'SOURCE_AUDIT_OVERLAY_COVERAGE'
    fresh=rr.all_saved();considered=[]
    for row in receipt.get('considered_rechecks',[]):
        key=(row['pass_id'],row['publication_id']);assert key[1] in ids and row['consideration_extent']
        if key in fresh:
            assert row['recheck_artifact_sha256']==fresh[key]['recheck_artifact_sha256']
            assert Path(fresh[key]['recheck_artifact']).as_posix() in {Path(x).as_posix() for x in receipt['inputs']}
            considered.append(row|{'recheck_kind':'FRESH_LEGACY_SOURCE_RECHECK'})
        else:
            # Post-initial own-source notes are distinct from the frozen legacy
            # recheck task set; require the exact owner, note hash and named ID.
            worker=row['worker_id'];assert worker in s.WORKERS and worker[0]==key[0]
            own=s.worker_rows(worker);assert key[1] in own and own[key[1]]['worker_id']==worker
            linked=[]
            for name,digest in receipt['inputs'].items():
                note=Path(name)
                if note.resolve() not in {p.resolve() for p in worker_note_paths(worker)} or digest!=row['recheck_artifact_sha256']:continue
                assert note.name.startswith(('self-','prompted-','identity-issues-')) and ('recheck' in note.name or note.name.startswith(('identity-issues-','self-correction-','self-integrity-','prompted-integrity-locator-sweep')))
                payload=loadj(note)
                container=next((field for field in ['results','records','rechecks','entries','checks','notes','cases'] if isinstance(payload,dict) and isinstance(payload.get(field),list)),None)
                if container:
                    declared=payload.get('model',payload.get('actual_model',payload.get('authorship')))
                    assert payload.get('worker',payload.get('worker_id')) in {None,worker}
                    assert declared=='gpt-6.1-terra' or (declared is None and payload.get('worker',payload.get('worker_id'))==worker)
                    records=payload[container]
                else:records=payload if isinstance(payload,list) else [payload]
                assert key[1] in {record['publication_id'] for record in records}
                linked.append(note.as_posix())
            assert len(linked)==1,('POST_INITIAL_RECHECK_HASH_ID_OWNER_LINK_REQUIRED',key)
            considered.append(row|{'recheck_kind':'POST_INITIAL_OWN_SOURCE_NOTE','recheck_artifact':linked[0]})
    known.append({'file':path.as_posix(),'sha256':s.sha(path),'precedence':len(known)+1,'registered_at_utc':s.stamp(),'source_checked_n':len(ids),'considered_rechecks':considered,'rationale_wrapper_clarifications':rationale_wrapper_notes})
    s.js(REG,registry)
    print(json.dumps({'registered_source_audit':path.name,'source_checked_n':len(ids),'considered_rechecks_n':len(considered)}))

def register_source_audit_index(file):
    path=Path(file);index=loadj(path);folder=path.parent;registry=loadj(REG)
    assert index['reviewer']=='Adjudicator_Sol_resume' and index['model']=='gpt-6.1-sol' and index['human_verification']=='PENDING'
    previous=registry.get('legacy_source_audit_scope_index')
    if previous:assert previous['sha256']==s.sha(path);return
    rows=[];ordered=[]
    for name,digest in index['ordered_receipts'].items():
        receipt_path=folder/name;assert s.sha(receipt_path)==digest
        register_source_audit(receipt_path.as_posix());receipt=loadj(receipt_path);rows.extend(receipt['entries']);ordered.append(receipt_path.as_posix())
    ids=[row['publication_id'] for row in rows];scope=s.rd(RUN/'legacy-audit-scope/manifest.csv')
    assert len(ids)==len(set(ids))==index['n']==len(scope) and set(ids)=={row['publication_id'] for row in scope}
    assert dict(Counter(row['audit_outcome'] for row in rows))==index['audit_outcomes'] and index['unperformed_n']==0
    registry=loadj(REG);actual=[entry['file'] for entry in registry['source_audit_reviews'] if entry['file'] in ordered];assert actual==ordered
    current,_=adjudications(s.inv())
    for key in ids:
        assert current[key].get('source_revision_reviewer')=='Adjudicator_Sol_resume' and current[key].get('source_revision_model')=='gpt-6.1-sol'
        assert current[key].get('audit_status') and 'UNAUDIT' not in current[key]['audit_status'].upper() and 'UNPERFORMED' not in current[key]['audit_status'].upper()
    registry['legacy_source_audit_scope_index']={'file':path.as_posix(),'sha256':s.sha(path),'source_checked_unique':len(ids),'outcomes':index['audit_outcomes'],'validated_at_utc':s.stamp(),'scope_manifest_sha256':s.sha(RUN/'legacy-audit-scope/manifest.csv'),'scope':'Exact named legacy scope, all available sources assessed; scientific uncertainty and other required work remain separate'};s.js(REG,registry)
    print(json.dumps({'validated_legacy_source_audit_index':path.name,'source_checked_unique':len(ids),'outcomes':index['audit_outcomes'],'unperformed_in_named_scope':0}))
def register(batch,file,receipt,revisions,access_exceptions=None):
    p=Path(file);q=Path(receipt);r=loadj(q);assert s.sha(p)==r['output_sha256']
    exception_path=Path(access_exceptions) if access_exceptions else None
    if exception_path:
        exc=loadj(exception_path);assert exc.get('batch',exc.get('batch_id',batch))==batch and exception_path.name.startswith(batch) and exc['model']=='gpt-6.1-sol' and exc['reviewer']=='Adjudicator_Sol_resume'
        r=r|{'source_access_exceptions':exc['source_access_exceptions']}
    src={x['publication_id']:x for x in s.rd(ROOT/'shared/batches'/f'{batch}.csv')}
    rows=s.rd(p);ids=[x['publication_id'] for x in rows]
    assert len(ids)==len(set(ids))==len(src) and set(ids)==set(src)==set(r['ids'])
    for path,digest in r['inputs'].items():assert s.sha(Path(path))==digest,('ADJUDICATION_INPUT_DRIFT',path)
    a={x['publication_id']:x for x in s.rd(RUN/'paired'/batch/'pass-A.csv')};b={x['publication_id']:x for x in s.rd(RUN/'paired'/batch/'pass-B.csv')}
    selection=loadj(RUN/'paired'/batch/'audit-selection.json')
    assert set(r['fixed_agreed_exclusion_sample'])==set(selection['sample_ids'])
    assert r['original_agreement']['eligibility_agreed']==sum(a[i]['eligibility']==b[i]['eligibility'] for i in src)
    for x in rows:
        i=x['publication_id'];assert x['eligibility'] in {'INCLUDE','EXCLUDE','UNCERTAIN'}
        assert x['reviewer']=='Adjudicator_Sol_resume' and x['model']=='gpt-6.1-sol' and x['human_verification']=='PENDING'
        modality_token(x['modality_stream'])
        assert x.get('audit_status') and x.get('source_assessment_extent') and x.get('evidence_type') and x.get('evidence_type_basis')
        assert s.norm(x['supporting_evidence']) in s.norm(src[i]['title']+' '+src[i]['abstract'])
        for k in ['source_memberships_json','record_ids_json']:assert json.loads(x[k])==json.loads(src[i][k])
        if not src[i]['abstract'].strip() and x['eligibility']!='UNCERTAIN':
            exception=next((z for z in r.get('source_access_exceptions',[]) if z['publication_id']==i),None)
            assert exception and exception.get('source_url') and exception.get('inspected_extent') and exception.get('own_source_excerpt') and exception.get('source_access_status'),('SUBSTANTIVE_SOURCE_ACCESS_EXCEPTION_REQUIRED',i)
    entries=[]
    for v in revisions:
        vp=Path(v);jj=loadj(vp);items=revision_rows(jj,p.name)
        validate_revision_inputs(jj,vp,p)
        declared_models={jj[field] for field in ['model','actual_model'] if jj.get(field)}
        assert declared_models=={'gpt-6.1-sol'} and jj['reviewer']=='Adjudicator_Sol_resume'
        assert {x['publication_id'] for x in items}<=set(src)
        entries.append({'file':vp.as_posix(),'sha256':s.sha(vp)})
    j=loadj(REG) if REG.exists() else {'entries':{},'history':[]}
    old=j['entries'].get(batch)
    new={'batch_id':batch,'file':p.as_posix(),'sha256':s.sha(p),'receipt':q.as_posix(),'receipt_sha256':s.sha(q),'revisions':entries,'registered_at_utc':s.stamp(),'validation':'Exact batch IDs/memberships, literal frozen excerpts, all rows source-status/extent, source-input hashes, model/stage, original agreement and fixed sample. Does not establish medical accuracy or human approval.'}
    if exception_path:new['source_access_exceptions']={'file':exception_path.as_posix(),'sha256':s.sha(exception_path)}
    attachments=source_attachments(p.parent,batch)
    for attachment in attachments:
        if attachment.name.endswith('-parent-validation-input-receipt.json'):
            parent=loadj(attachment)
            assert parent['reviewer']=='Adjudicator_Sol_resume' and parent['model']=='gpt-6.1-sol' and parent['human_verification']=='PENDING'
            for name,digest in parent['inputs'].items():
                actual=receipt_input_path(name,RUN)
                assert actual.is_relative_to((RUN/'parent-validation').resolve()),('PARENT_INPUT_OUTSIDE_VALIDATION_FOLDER',name)
                assert s.sha(actual)==digest,('PARENT_VALIDATION_INPUT_DRIFT',name)
    new['additional_source_receipts']=[{'file':x.as_posix(),'sha256':s.sha(x)} for x in attachments]
    if old:j['history'].append(old)
    j['entries'][batch]=new;s.js(REG,j)
    print(json.dumps({'registered':batch,'n':len(rows),'counts':dict(Counter(x['eligibility'] for x in rows))}))

def adjudications(inventory):
    result={};sources={};registry=loadj(ROOT/'astra/current-artifacts.json')
    pin_path=RUN/'admin/legacy-adjudication-baseline-review.json'
    pins={Path(name).as_posix():digest for name,digest in loadj(pin_path)['sha256'].items()};seen_legacy=set()
    for batch,e in registry.items():
        if not isinstance(e,dict) or not e.get('adjudication'):continue
        p=ROOT/e['adjudication'];digest=s.sha(p);sources[p.as_posix()]=digest
        relative=p.relative_to(ROOT).as_posix();assert pins.get(relative)==digest,('PINNED_LEGACY_ADJUDICATION_DRIFT',relative);seen_legacy.add(relative)
        for raw in s.rd(p):
            key=raw['publication_id'];assert key not in result and key in inventory
            result[key]=raw|{'eligibility':raw.get('adjudicated_eligibility',raw.get('eligibility','')),'adjudication_artifact':p.as_posix(),'adjudication_artifact_sha256':digest,'adjudication_origin':'legacy_registered','batch_id':batch}
    assert seen_legacy==set(pins),'PINNED_LEGACY_ADJUDICATION_SCOPE_DRIFT'
    if REG.exists():
        current_registry=loadj(REG)
        for batch,e in current_registry.get('legacy_revisions',{}).items():
            base=Path(e['file']);assert s.sha(base)==e['sha256'] and pins[base.relative_to(ROOT).as_posix()]==e['sha256']
            for revision in e['revisions']:
                p=Path(revision['file']);assert s.sha(p)==revision['sha256'];sources[p.as_posix()]=revision['sha256']
                content=loadj(p);validate_revision_inputs(content,p,base,sources)
                for row in revision_rows(content,base.name):
                    assert result[row['publication_id']]['adjudication_origin']=='legacy_registered' and result[row['publication_id']]['batch_id']==batch
                    apply_fields(result,row,p,revision['sha256'])
        for batch,e in loadj(REG)['entries'].items():
            p=Path(e['file']);assert s.sha(p)==e['sha256'];sources[p.as_posix()]=e['sha256']
            assert s.sha(Path(e['receipt']))==e['receipt_sha256']
            sources[e['receipt']]=e['receipt_sha256']
            for name,digest in loadj(Path(e['receipt'])).get('inputs',{}).items():
                assert s.sha(Path(name))==digest,('REGISTERED_ADJUDICATION_INPUT_DRIFT',name)
                sources[Path(name).as_posix()]=digest
            for extra in e.get('additional_source_receipts',[]):
                xp=Path(extra['file']);assert s.sha(xp)==extra['sha256'];sources[xp.as_posix()]=extra['sha256']
            if e.get('source_access_exceptions'):
                extra=e['source_access_exceptions'];xp=Path(extra['file']);assert s.sha(xp)==extra['sha256'];sources[xp.as_posix()]=extra['sha256']
            for raw in s.rd(p):
                key=raw['publication_id'];assert key not in result,'REGISTERED_ADJUDICATION_OVERLAP'
                result[key]=raw|{'adjudicated_eligibility':raw['eligibility'],'adjudication_artifact':p.as_posix(),'adjudication_artifact_sha256':e['sha256'],'adjudication_origin':'resume_sol','additional_source_receipts_json':json.dumps(e.get('additional_source_receipts',[]))}
            exceptions=loadj(Path(e['receipt'])).get('source_access_exceptions',[])
            exception_artifact=e['receipt']
            if e.get('source_access_exceptions'):
                extra=e['source_access_exceptions']
                exceptions=loadj(Path(extra['file']))['source_access_exceptions'];exception_artifact=extra['file']
            for exception in exceptions:
                key=exception['publication_id'];assert key in result and result[key]['adjudication_artifact']==e['file']
                result[key]['substantive_source_access_exception_status']=exception['source_access_status'];result[key]['source_access_exception_artifact']=exception_artifact
            for revision in e['revisions']:
                vp=Path(revision['file']);assert s.sha(vp)==revision['sha256'];sources[vp.as_posix()]=revision['sha256']
                content=loadj(vp);validate_revision_inputs(content,vp,p,sources)
                for x in revision_rows(content,p.name):
                    apply_fields(result,x,vp,revision['sha256'])
        for e in current_registry.get('source_audit_reviews',[]):
            p=Path(e['file']);assert s.sha(p)==e['sha256'];sources[p.as_posix()]=e['sha256']
            for note in e.get('rationale_wrapper_clarifications',[]):
                extra=Path(note['file']);assert s.sha(extra)==note['sha256'];sources[extra.as_posix()]=note['sha256']
            audit=loadj(p)
            for name,digest in audit['inputs'].items():assert s.sha(Path(name))==digest;sources[Path(name).as_posix()]=digest
            for entry in audit['entries']:
                exception=entry.get('source_access_exception')
                if exception:
                    key=entry['publication_id'];result[key]['substantive_source_access_exception_status']=exception['source_access_status'];result[key]['source_access_exception_artifact']=p.as_posix()
        for e in loadj(REG).get('metadata_clarifications',[]):
            p=Path(e['file']);assert s.sha(p)==e['sha256'];sources[p.as_posix()]=e['sha256'];clarification=loadj(p)
            assert clarification['field']=='prior_exposure'
            for row in result.values():
                if Path(row['adjudication_artifact']).name in clarification['files']:
                    row['prior_exposure']=clarification['replacement'];row['provenance_clarification_artifact']=p.as_posix()
    for row in result.values():
        assert row['eligibility'] in {'INCLUDE','EXCLUDE','UNCERTAIN'},('INVALID_CURRENT_ROUTING',row['publication_id'])
        for field in ['source_memberships_json','record_ids_json']:
            assert json.loads(row[field])==json.loads(inventory[row['publication_id']][field]),('CURRENT_ADJUDICATION_MEMBERSHIP_DRIFT',row['publication_id'],field)
        raw=row.get('modality_stream','');standard=modality_token(raw)
        if raw!=standard:
            row['recorded_modality_spelling_before_normalization']=raw
            row['modality_stream']=standard
            row['modality_spelling_normalization']='Case/shared nonimmersive_3D token only; original decision and file preserved; no scientific reclassification.'
    return result,sources

def publish():
    inventory=s.inv();initial={p:{r['publication_id']:r for r in s.rd(CANON/f'pass-{p}-original-initials.csv')} for p in 'AB'}
    counts=loadj(CANON/'current-counts.json');adj,adjinputs=adjudications(inventory)
    fresh_rechecks=rr.all_saved()
    considered={}
    if REG.exists():
        for review in loadj(REG).get('source_audit_reviews',[]):
            for row in review.get('considered_rechecks',[]):considered[(row['pass_id'],row['publication_id'])]=row|{'source_review_receipt':review['file']}
    recheck_tasks=rr.task_rows() if rr.MANIFEST.exists() else []
    base_recheck_keys={(row['pass_id'],row['publication_id']) for row in s.rd(rr.MANIFEST)} if rr.MANIFEST.exists() else set()
    supplemental_date_keys={(row['pass_id'],row['publication_id']) for row in recheck_tasks if ((row['pass_id'],row['publication_id']) not in base_recheck_keys or row.get('obligation_addendum_files_json')) and 'independent_2020_date' in json.loads(row['obligations_json'])}
    recheck_status=[]
    for task in recheck_tasks:
        key=(task['pass_id'],task['publication_id']);saved=fresh_rechecks.get(key,{});review=considered.get(key,{})
        used=bool(saved and review.get('recheck_artifact_sha256')==saved.get('recheck_artifact_sha256'))
        recheck_status.append(task|{'source_check_status':'SOURCE_RECHECK_SAVED' if saved else 'UNPERFORMED','new_recheck_artifact':saved.get('recheck_artifact',''),'sol_consideration_status':'SOURCE_RECHECK_CONSIDERED' if used else 'PENDING_AFTER_SOURCE_RECHECK','source_review_receipt':review.get('source_review_receipt','') if used else '','human_verification':'PENDING'})
    if recheck_status:s.wr(CANON/'fresh-legacy-source-recheck-status.csv',recheck_status)
    if fresh_rechecks:s.wr(CANON/'fresh-legacy-source-rechecks.csv',list(fresh_rechecks.values()))
    assert all(x['eligibility']==x.get('adjudicated_eligibility',x['eligibility']) for x in adj.values()),'ADJUDICATION_ALIAS_CONFLICT'
    method_checks=[];method_checked_ids=set()
    if REG.exists():
        for e in loadj(REG).get('method_application_reviews',[]):
            rp=Path(e['file']);assert s.sha(rp)==e['sha256'];adjinputs[rp.as_posix()]=e['sha256']
            for row in loadj(rp)['entries']:
                method_checks.append(row|{'review_receipt':rp.as_posix(),'review_receipt_sha256':e['sha256'],'human_verification':'PENDING'});method_checked_ids.add(row['publication_id'])
    if method_checks:s.wr(CANON/'method-046-application-source-checks.csv',method_checks)
    source_checks=[]
    if REG.exists():
        for review in loadj(REG).get('source_audit_reviews',[]):
            for row in loadj(Path(review['file']))['entries']:source_checks.append(row|{'source_review_receipt':review['file'],'source_review_receipt_sha256':review['sha256'],'reviewer':'Adjudicator_Sol_resume','model':'gpt-6.1-sol','human_verification':'PENDING'})
    if source_checks:s.wr(CANON/'source-audit-source-checks-current.csv',source_checks)
    method_followups=[]
    for path in sorted((RUN/'adjudicator_sol').glob('method-046-application-followup-candidates-*.csv')):
        for row in s.rd(path):method_followups.append(row|{'source_file':path.as_posix(),'source_sha256':s.sha(path),'current_check_status':'SOURCE_ASSESSED' if row['publication_id'] in method_checked_ids else 'PENDING_SOURCE_APPLICATION_RECHECK'})
    if method_followups:s.wr(CANON/'method-046-application-followups-current.csv',method_followups)
    legacy={r['publication_id']:r for r in s.rd(ROOT/'astra/all-id-status-ledger.csv')}
    types={r['publication_id']:r for r in s.rd(ROOT/'astra/evidence-type-check-status-current.csv')}
    immersion={r['publication_id']:r for r in s.rd(ROOT/'astra/immersion-clarification-status-current.csv')}
    dates={(r['reviewer'],r['publication_id']):r for r in s.rd(ROOT/'astra/date-boundary-recheck-status-current.csv')}
    newdates={}
    for pas,byid in initial.items():
        for key,r in byid.items():
            checked=r.get('date_check_status','')
            if r.get('worker_id') and checked and r.get('date_basis') and (r.get('date_source') or checked in {'CHECKED_UNRESOLVED','CHECKED_SOURCE_LIMITED'}):newdates[(pas,key)]=r|{'source_file':r['initial_artifact']}
    if DATEREG.exists():
        for e in sorted(loadj(DATEREG)['entries'],key=lambda x:x['precedence']):
            for r in date_rows(e):
                key=r['publication_id'];stage=e.get('date_assignment_stages',{}).get(key,'OWN_INITIAL_DATE_SOURCE_CHECK')
                if stage=='FRESH_LEGACY_DATE_METADATA_CORRECTION':
                    fresh=fresh_rechecks[(e['pass_id'],key)];link=e['linked_fresh_legacy_artifacts'][key]
                    assert fresh['worker_id']==e['worker'] and s.sha(Path(link['file']))==link['sha256']==fresh['recheck_artifact_sha256']
                newdates[(e['pass_id'],key)]=r|{'source_file':e['file'],'date_source_sha256':e['sha256'],'date_correction_files':';'.join(x['file'] for x in e.get('corrections',[])),'date_registration_stage':stage,'date_metadata_author_worker':e['worker'],'reviewer':r.get('reviewer','Terra_'+e['worker']+'_resume_date_source'),'model':'gpt-6.1-terra'}
    required=s.rd(ROOT/'astra/required-recheck-status-v0.4.3.csv')
    additional_date_checks={}
    for path in sorted(RUN.glob('additional-date-boundary-audit/*/receipt.json')):
        scope=loadj(path);assert scope['inventory_sha256']==s.EXPECTED_HASH
        packet=Path(scope['source_packet']);assert s.sha(packet)==scope['source_packet_sha256']
        rows=s.rd(packet);keys=[row['publication_id'] for row in rows]
        assert len(keys)==len(set(keys)) and keys==scope['publication_ids'] and scope['additional_date_obligations']==2*len(keys)
        assert all(row==inventory[row['publication_id']] for row in rows)
        adjinputs[path.as_posix()]=s.sha(path);adjinputs[packet.as_posix()]=s.sha(packet)
        for trigger in scope['trigger_sources']:
            source_path=Path(trigger['file']);assert s.sha(source_path)==trigger['sha256'] and trigger['publication_id'] in keys
            adjinputs[source_path.as_posix()]=trigger['sha256']
        for key in keys:
            assert key not in additional_date_checks and inventory[key]['year']!='2020' and 2020 not in json.loads(inventory[key].get('year_candidates_json') or '[]')
            expected=scope['expected_date_source_files'][key];assert set(expected)=={'A','B'}
            for pas,name in expected.items():
                owner=initial[pas][key]['worker_id'];assert owner[0]==pas
                assert Path(name).resolve()==Path(initial[pas][key]['initial_artifact']).resolve() or Path(name).resolve().parent==(RUN/'workers'/owner).resolve()
            additional_date_checks[key]={'receipt':path.as_posix(),'expected':expected}
    allrows=[];queues=[];datequeue=[];retrospective=[];retrospective_completed=[]
    for key,source in inventory.items():
        old=legacy[key];r={'publication_id':key,'frozen_representative_year':source['year'],'source_memberships_json':source['source_memberships_json'],'record_ids_json':source['record_ids_json'],'inventory_sha256':s.EXPECTED_HASH,'human_verification':'PENDING'}
        for pas,who in [('A','sol'),('B','terra')]:
            x=initial[pas].get(key,{});r['pass_'+pas+'_initial_status']='SAVED' if x else 'PENDING'
            for k in ['reviewer','model','eligibility','evidence_stream','modality_stream','evidence_type','evidence_type_check_status','access_status','initial_artifact','prior_exposure']:r['pass_'+pas+'_'+k]=x.get(k,'')
            if not x:queues.append({'publication_id':key,'queue':'initial_assessment','pass_id':pas,'status':'UNPERFORMED','basis':'No saved validated initial judgment'})
            else:
                legacy_access_resolved=not x.get('worker_id') and old.get(who+'_eligibility_access_pending')=='False'
                if not source['abstract'].strip() and not legacy_access_resolved and not adj.get(key,{}).get('substantive_source_access_exception_status'):queues.append({'publication_id':key,'queue':'source_text_retrieval','pass_id':pas,'status':'SOURCE_ASSESSED_SUBSTANTIVE_TEXT_RETRIEVAL_PENDING' if key in adj else 'PENDING_AVAILABLE_SOURCE_CHECK','basis':x.get('uncertainty_note',x.get('rationale',''))})
                if source['year']=='2020' or 2020 in json.loads(source.get('year_candidates_json') or '[]') or key in additional_date_checks:
                    d=dates.get((who,key),{}) if not x.get('worker_id') else newdates.get((pas,key),{})
                    fresh=fresh_rechecks.get((pas,key),{})
                    if fresh and 'independent_2020_date' in json.loads(fresh['obligations_json']):d=fresh|{'source_file':fresh['recheck_artifact']}
                    amendment=newdates.get((pas,key),{})
                    if amendment.get('date_registration_stage')=='FRESH_LEGACY_DATE_METADATA_CORRECTION':d=amendment
                    if key in additional_date_checks:
                        expected=additional_date_checks[key]['expected'][pas]
                        d=amendment if amendment.get('source_file')==expected else {}
                    row={'publication_id':key,'pass_id':pas,'initial_reviewer':x.get('reviewer',''),'initial_model':x.get('model',''),'date_recheck_reviewer':d.get('reviewer',x.get('reviewer','')),'date_recheck_model':d.get('model',x.get('model','')),'date_check_status':d.get('date_check_status','PENDING_INDEPENDENT_SOURCE_CHECK'),'source_file':d.get('source_file',''),'source':d.get('source',d.get('date_source','')),'source_extent':d.get('date_basis',''),'earliest_report_publication':d.get('earliest_report_publication',d.get('journal_first_publication_date','UNVERIFIED')),'date_gate':d.get('date_gate',d.get('date_boundary_status','UNCERTAIN')),'human_verification':'PENDING'}
                    if isinstance(row['source'],list):
                        assert all(isinstance(url,str) and url for url in row['source'])
                        row['source']=json.dumps(row['source'],ensure_ascii=False)
                    if key in additional_date_checks:
                        row.update(additional_source_flag_scope=additional_date_checks[key]['receipt'],frozen_representative_year=source['year'],original_inline_date_check_status=x.get('date_check_status',''),original_inline_date_artifact=x['initial_artifact'],scope_note='Explicit source-flagged possible2020 report outside frozen2020metadata; exact scoped own-source artifact required. Valid saved actual attempts are reused; missing attempts require append-only own notes. No inference from CV/issue chronology alone.')
                    if (pas,key) in supplemental_date_keys:
                        historical=dates.get((who,key),{})
                        row.update(historical_date_check_status=historical.get('date_check_status',''),historical_date_source_file=historical.get('source_file',''),supplemental_date_requirement='Legacy unresolved status has no documented owning-source attempt/extent; fresh fixed-pool source check required, without claiming that no historical attempt occurred.')
                        if not fresh:row['date_check_status']='PENDING_FRESH_SOURCE_DATE_RECHECK'
                    if amendment.get('date_registration_stage')=='FRESH_LEGACY_DATE_METADATA_CORRECTION':
                        row.update(date_recording_stage=amendment['date_registration_stage'],submitted_fresh_date_check_status=fresh.get('date_check_status',''),submitted_fresh_recheck_artifact=fresh['recheck_artifact'],date_metadata_correction_sha256=amendment['date_source_sha256'],date_correction_limits_verbatim=amendment.get('limitations',''))
                    datequeue.append(row)
                if not x.get('worker_id'):
                    for field,ledger,k in [('evidence_type',types,who+'_type_check_status'),('immersion_clarification',immersion,who+'_clarification_status')]:
                        status=ledger.get(key,{}).get(k,'PENDING')
                        if status.startswith('PENDING'):
                            task={'publication_id':key,'pass_id':pas,'obligation':field,'status':status,'source_ledger':'astra/'+('evidence-type-check-status-current.csv' if field=='evidence_type' else 'immersion-clarification-status-current.csv')}
                            fresh=fresh_rechecks.get((pas,key),{})
                            if fresh and field in json.loads(fresh['obligations_json']):
                                retrospective_completed.append(task|{'legacy_status':status,'status':'FRESH_SOURCE_RECHECK_SAVED','fresh_reviewer':fresh['reviewer'],'fresh_model':fresh['model'],'fresh_recheck_artifact':fresh['recheck_artifact'],'fresh_recheck_artifact_sha256':fresh['recheck_artifact_sha256'],'sol_consideration_status':'SOURCE_RECHECK_CONSIDERED' if considered.get((pas,key),{}).get('recheck_artifact_sha256')==fresh['recheck_artifact_sha256'] else 'PENDING_SOL_CONSIDERATION','human_verification':'PENDING'})
                            else:retrospective.append(task)
        current=adj.get(key,{})
        r['both_initial_passes']=key in initial['A'] and key in initial['B'];r['adjudication_status']='PROVISIONAL_SAVED' if current else 'PENDING'
        for k in ['eligibility','reason_code','evidence_stream','modality_stream','evidence_type','audit_status','adjudication_artifact','reviewer','model','source_assessment_extent','pending_obligation','report_disposition','integrity_status','source_revision_artifact']:r['adjudicated_'+k]=current.get(k,'')
        for k in ['source_integrity_status','integrity_synthesis_hold','integrity_notice_doi','integrity_identity_status','all_doi_candidate_ids_json','doi_identity_verification_status','required_recheck_status']:r['legacy_'+k]=old.get(k,'')
        if current.get('eligibility')=='UNCERTAIN':queues.append({'publication_id':key,'queue':'adjudicated_uncertainty','pass_id':'','status':'SOURCE_ASSESSED_UNRESOLVED','basis':current.get('pending_obligation',current.get('rationale',''))})
        if not current and r['both_initial_passes']:queues.append({'publication_id':key,'queue':'adjudication','pass_id':'','status':'UNPERFORMED','basis':'Both initial assessments saved; source adjudication/routing not yet recorded'})
        allrows.append(r)
    s.wr(CANON/'all-id-status-current.csv',allrows)
    notes=[];identity_notes=[]
    identity_placeholders={'No grouping validation performed','Group identity and study-family overlap not source-verified','Report/version/family identity unverified','group linkage provisional; not independently verified','group linkage provisional'}
    for pas,byid in initial.items():
        for key,row in byid.items():
            identity=row.get('identity_issue','').strip();specific_identity=bool(identity and identity not in identity_placeholders)
            if row.get('uncertainty_note','').strip() or specific_identity:notes.append({'publication_id':key,'pass_id':pas,'initial_reviewer':row.get('reviewer',''),'initial_model':row.get('model',''),'uncertainty_note_verbatim':row.get('uncertainty_note',''),'identity_issue_verbatim':row.get('identity_issue',''),'initial_artifact':row['initial_artifact'],'current_adjudication_artifact':adj.get(key,{}).get('adjudication_artifact',''),'scope':'Explicit original note retained verbatim; its scientific resolution must be checked in later source/full-text records, not inferred automatically','human_verification':'PENDING'})
            if specific_identity:identity_notes.append({'publication_id':key,'pass_id':pas,'initial_reviewer':row.get('reviewer',''),'initial_model':row.get('model',''),'identity_issue_verbatim':row['identity_issue'],'initial_rationale_verbatim':row.get('rationale',''),'initial_artifact':row['initial_artifact'],'initial_artifact_sha256':row['initial_artifact_sha256'],'current_source_identity_text_verbatim':adj.get(key,{}).get('identity_issue',''),'current_adjudication_artifact':adj.get(key,{}).get('adjudication_artifact',''),'scope':'Original identity text except exact shared placeholders; this is a source-declared note inventory, not a verified conflict, new classification or merger instruction. Original text remains even after source consideration; later identity/family verification must inspect actual evidence. All original rows and generic placeholders remain in pass ledgers.','human_verification':'PENDING'})
    if notes:s.wr(CANON/'initial-explicit-source-notes.csv',notes)
    s.wr(CANON/'initial-explicit-identity-notes.csv',identity_notes)
    current_identity_notes=[]
    current_identity_placeholders=identity_placeholders|{'Report/study family not independently verified; original memberships preserved'}
    for key,row in adj.items():
        issue=row.get('identity_issue','').strip()
        if not issue or issue in current_identity_placeholders:continue
        current_identity_notes.append({'publication_id':key,'identity_issue_verbatim':row['identity_issue'],'identity_note_source_artifact':row.get('identity_issue_source_artifact',row['adjudication_artifact']),'identity_note_source_sha256':row.get('identity_issue_source_sha256',row['adjudication_artifact_sha256']),'identity_note_source_reviewer':row.get('identity_issue_source_reviewer',row.get('reviewer','')),'identity_note_source_model':row.get('identity_issue_source_model',row.get('model','')),'current_provisional_eligibility':row['eligibility'],'source_memberships_json':inventory[key]['source_memberships_json'],'record_ids_json':inventory[key]['record_ids_json'],'identity_verification_status':'PENDING_SOURCE_AND_HUMAN_IDENTITY_REVIEW','human_verification':'PENDING','scope':'Explicit current source-authored identity text except exact shared placeholders. Field-specific overlay provenance remains pinned when later unrelated fields change. No verified conflict, family classification, ID merger or eligibility transfer is inferred.'})
    s.wr(CANON/'source-adjudicated-identity-notes.csv',current_identity_notes)
    initial_integrity=[]
    for pas,byid in initial.items():
        for key,row in byid.items():
            if row.get('report_disposition')=='WITHHOLD_FROM_SYNTHESIS' or row.get('synthesis_disposition')=='WITHHOLD_FROM_SYNTHESIS' or row.get('integrity_status','').strip():
                initial_integrity.append({'publication_id':key,'pass_id':pas,'initial_reviewer':row.get('reviewer',''),'initial_model':row.get('model',''),'report_disposition_verbatim':row.get('report_disposition',''),'synthesis_disposition_verbatim':row.get('synthesis_disposition',''),'integrity_status_verbatim':row.get('integrity_status',''),'source_note_verbatim':row.get('uncertainty_note',row.get('integrity_note',row.get('rationale',''))),'supporting_evidence':row.get('supporting_evidence',''),'initial_artifact':row['initial_artifact'],'initial_artifact_sha256':row['initial_artifact_sha256'],'current_adjudication_artifact':adj.get(key,{}).get('adjudication_artifact',''),'current_adjudicated_report_disposition':adj.get(key,{}).get('report_disposition',''),'scope':'Explicit initial source flag, not a new coordinator hold or verified misconduct finding. Distinct from current source-adjudicated/legacy holds.','human_verification':'PENDING'})
    s.wr(CANON/'initial-explicit-integrity-flags.csv',initial_integrity)
    s.wr(CANON/'adjudicated-current.csv',[adj[i] for i in sorted(adj)])
    s.wr(CANON/'pending-queues-current.csv',queues);s.wr(CANON/'independent-2020-date-obligations.csv',datequeue);s.wr(CANON/'legacy-retrospective-pending.csv',retrospective)
    if retrospective_completed:s.wr(CANON/'legacy-retrospective-fresh-source-checks.csv',retrospective_completed)
    for task in required:
        complete=True
        for pas,who in [('A','sol'),('B','terra')]:
            fresh=fresh_rechecks.get((pas,task['publication_id']),{})
            available=bool(fresh and 'legacy_targeted_source_followup' in json.loads(fresh['obligations_json']))
            task['current_pass_'+pas+'_source_followup_status']='LEGACY_RECHECK_COMPLETE' if task[who+'_recheck_status']=='COMPLETE' else ('FRESH_TERRA_SOURCE_RECHECK_SAVED' if available else 'PENDING_SOURCE_RECHECK')
            task['fresh_pass_'+pas+'_source_recheck_artifact']=fresh.get('recheck_artifact','') if available else ''
            complete=complete and (task[who+'_recheck_status']=='COMPLETE' or available)
        task['current_required_source_followups_complete']=complete
    s.wr(CANON/'legacy-targeted-recheck-status.csv',required)
    self_rechecks=[];input_receipts={};deferred_notes=[];live_worker_rows={}
    if REG.exists():
        receipts=[loadj(Path(entry['receipt'])) for entry in loadj(REG)['entries'].values()]
        receipts.extend(loadj(Path(entry['file'])) for entry in loadj(REG).get('source_audit_reviews',[]))
        for receipt in receipts:
            covered=set(receipt.get('ids',[row['publication_id'] for row in receipt.get('entries',[])]))
            for path,digest in receipt.get('inputs',{}).items():
                token=(Path(path).resolve(),digest);input_receipts.setdefault(token,set()).update(covered)
    for worker in s.WORKERS:
        note_paths=worker_note_paths(worker)
        for path in sorted(note_paths):
            item=loadj(path)
            top_level_list=isinstance(item,list)
            wrapper_metadata={key:value for key,value in item.items() if not isinstance(value,(dict,list))} if isinstance(item,dict) else {}
            container=next((field for field in ['results','records','rechecks','entries','checks','notes','cases'] if isinstance(item,dict) and isinstance(item.get(field),list)),None)
            if container:
                declared=item.get('model',item.get('actual_model',item.get('authorship')))
                assert item.get('worker',item.get('worker_id')) in {None,worker}
                assert declared=='gpt-6.1-terra' or (declared is None and item.get('worker',item.get('worker_id'))==worker)
                items=item[container]
            else:items=item if isinstance(item,list) else [item]
            for item in items:
                declared_model=item.get('model') or item.get('actual_model') or item.get('authorship')
                if declared_model is not None:assert declared_model=='gpt-6.1-terra',('CONFLICTING_SOURCE_NOTE_MODEL',worker,path)
                key=item['publication_id']
                if key not in initial[worker[0]]:
                    if worker not in live_worker_rows:live_worker_rows[worker]=s.worker_rows(worker)
                    assert key in live_worker_rows[worker] and live_worker_rows[worker][key]['worker_id']==worker,('SOURCE_NOTE_NOT_OWN_INITIAL',worker,key)
                    deferred_notes.append({'worker':worker,'publication_id':key,'source_file':path.as_posix(),'scope':'Own immutable initial was written after the published input snapshot; note is retained raw and joins the next snapshot.'});continue
                assert initial[worker[0]][key].get('worker_id')==worker
                quotes=source_note_quotes(item)
                quote_fidelity=[]
                for quote in quotes:
                    if any(s.norm(quote) in s.norm(inventory[key][field]) for field in ['title','abstract']):continue
                    # Whole-title wording/punctuation must remain identical;
                    # only a space immediately before a colon may differ.
                    # Body quotations retain the original literal check.
                    title=inventory[key]['title']
                    if ':' in quote and s.norm(quote).replace(' :',':')==s.norm(title).replace(' :',':'):
                        quote_fidelity.append({'raw_note_quote':quote,'exact_frozen_title':title,'validation':'Whole-title wording, case and punctuation identical; whitespace before colon differs. Raw note and frozen source preserved; not represented as an exact byte quotation.'})
                        continue
                    # Post-initial author notes occasionally change sentence
                    # capitalization or U+2010/U+2011 hyphen typography. Keep
                    # the actual frozen substring beside the raw note; this is
                    # explicitly not promoted to a literal raw quotation.
                    pattern=''.join('[-\u2010-\u2015]' if char=='\ufffd' else ('[-\u2010\u2011]' if char in '-\u2010\u2011' else re.escape(char)) for char in s.norm(quote))
                    matches=[(field,re.search(pattern,s.norm(inventory[key][field]),re.I)) for field in ['title','abstract']]
                    match=next(((field,found) for field,found in matches if found),None)
                    if match:
                        field,found=match
                        replacement='\ufffd' in quote
                        fidelity={'raw_note_quote':quote,'exact_frozen_excerpt':found.group(0),'frozen_field':field,'validation':'Same wording and punctuation with capitalization and/or U+2010/U+2011 versus ASCII hyphen typography differences. Both strings preserved; raw note is not represented as an exact byte quotation.'}
                        if replacement:
                            fidelity.update(encoding_replacement_character_present=True,matched_frozen_punctuation_codepoints=[f'U+{ord(found.group(0)[i]):04X}' for i,char in enumerate(s.norm(quote)) if char=='\ufffd'],validation='Raw note contains U+FFFD only at matched frozen dash-punctuation positions (ASCII hyphen or U+2010 through U+2015). Every other character/word must match under the separately stated case/hyphen rules. Exact frozen substring is recorded; damaged raw note is not a literal quotation. No missing word or letter was reconstructed.')
                        quote_fidelity.append(fidelity)
                        continue
                    notice=bool(item.get('notice_source') and item.get('notice_extent'))
                    external_url=item.get('notice_source') if notice else (item.get('date_source') or item.get('source_url') or item.get('source',''))
                    external_extent=item.get('notice_extent') if notice else (item.get('inspected_extent') or item.get('source_extent'))
                    qualified=notice and 'integrity' in path.name or ('date' in path.name and item.get('date_check_status') in {'CHECKED_VERIFIED','CHECKED_UNRESOLVED','CHECKED_INDEXED_PRIMARY','CHECKED_SOURCE_LIMITED'})
                    assert qualified and isinstance(external_url,str) and re.match(r'https?://',external_url) and external_extent,('PROMPTED_RECHECK_QUOTE_NOT_LITERAL',key,quote)
                    quote_fidelity.append({'raw_note_quote':quote,'external_source_url':external_url,'author_reported_inspected_extent':external_extent,'external_source_kind':'integrity_notice' if notice else 'date_source','validation':'Author-reported external excerpt, linked to actual URL and stated inspected extent. Not a frozen-source quote; coordinator has not independently verified external wording, date or notice identity.'})
                used=key in input_receipts.get((path.resolve(),s.sha(path)),set())
                stage='SOURCE_IDENTITY_METADATA_NOTE_AFTER_INITIAL' if path.name.startswith('identity-issues-') else ('PROMPTED_RULE_SOURCE_RECHECK_NOT_AN_INITIAL' if path.name.startswith('prompted-') else 'SELF_DETECTED_SOURCE_RECHECK_NOT_AN_INITIAL')
                recorded_item_json=json.dumps(item,ensure_ascii=False,sort_keys=True)
                if path.name.startswith('identity-issues-') and isinstance(item.get('issue'),str):
                    item=dict(item)
                    if not item.get('identity_issue'):item['identity_issue']=item['issue']
                    if not item.get('rationale'):item['rationale']=item['issue']
                if 'revised_eligibility' in item and 'proposed_eligibility' not in item:item=item|{'proposed_eligibility':item['revised_eligibility']}
                if 'provisional_eligibility' in item and 'proposed_eligibility' not in item:item=item|{'proposed_eligibility':item['provisional_eligibility']}
                if isinstance(item.get('revised'),str) and 'proposed_eligibility' not in item and item['revised'] in {'INCLUDE','EXCLUDE','UNCERTAIN'}:item=item|{'proposed_eligibility':item['revised']}
                if 'reason' in item and not item.get('rationale'):item=item|{'rationale':item['reason']}
                self_rechecks.append({'publication_id':key,'pass_id':worker[0],'worker':worker,'note_model':'gpt-6.1-terra','note_model_recording_basis':'Known fixed fresh-agent configuration and owning initial receipt; explicit note model fields validated when present, raw missing fields preserved','stage':stage,'source_file':path.as_posix(),'source_sha256':s.sha(path),'both_initials_saved':key in initial['A'] and key in initial['B'],'adjudication_status':'RECHECK_HASH_LINKED_IN_ADJUDICATION_RECEIPT' if used else 'PENDING_SOURCE_RECHECK_ADJUDICATION','proposed_eligibility':item.get('proposed_eligibility',item.get('corrected_eligibility',item.get('eligibility',item.get('rechecked_disposition','')))),'proposed_reason':item.get('proposed_reason_code',item.get('corrected_reason_code',item.get('reason_code',item.get('proposed_reason','')))),'rechecked_label_verbatim':item.get('rechecked',item.get('proposed',item.get('rechecked_disposition',item.get('assessment','')))),'recheck_outcome_verbatim':item.get('outcome',item.get('recheck_outcome',item.get('date_check_status',''))),'rationale_verbatim':item.get('rationale',item.get('basis',item.get('assessment',item.get('date_basis','')))),'uncertainty_note_verbatim':next((item[field] for field in ['uncertainty_note','remaining_uncertainty','remaining_limits','scope_limits','source_limits','limitation','limit'] if item.get(field)),''),'identity_issue_verbatim':item.get('identity_issue',''),'integrity_status_verbatim':item.get('integrity_status',''),'source_extent_verbatim':next((item[field] for field in ['source_extent','source','assessed_extent','notice_extent','lookup_extent','frozen_source_extent'] if item.get(field)),''),'note_payload_json':recorded_item_json,'human_verification':'PENDING'})
                self_rechecks[-1]['source_quote_typography_notes_json']=json.dumps(quote_fidelity,ensure_ascii=False,sort_keys=True)
                self_rechecks[-1]['source_evidence_quotes_json']=json.dumps(quotes,ensure_ascii=False)
                self_rechecks[-1]['source_reported_disposition_verbatim']=next((item[field] for field in ['synthesis_disposition','report_disposition','integrity_disposition','synthesis_hold','routing','disposition'] if item.get(field)),'')
                self_rechecks[-1]['source_note_container_field']=container or ('top_level_list' if top_level_list else 'single_record')
                self_rechecks[-1]['source_note_wrapper_metadata_json']=json.dumps(wrapper_metadata,ensure_ascii=False,sort_keys=True)
                wrapper_extent_field=next((field for field in ['source_extent','inspected_extent','method'] if wrapper_metadata.get(field)),None)
                if not self_rechecks[-1]['source_extent_verbatim'] and wrapper_extent_field:
                    self_rechecks[-1]['source_extent_verbatim']=wrapper_metadata[wrapper_extent_field]
                    self_rechecks[-1]['source_extent_recording_basis']='Verbatim shared '+wrapper_extent_field+' declared by the owning note wrapper; individual payload and full raw file remain preserved.'
                else:self_rechecks[-1]['source_extent_recording_basis']='Individual source-note field, when present.'
                declared_kinds=item.get('audit_kinds_checked',[])
                assert isinstance(declared_kinds,list) and set(declared_kinds)<={'medical','date-window','integrity'},('INVALID_EXPLICIT_AUDIT_COVERAGE',worker,key)
                declaration_basis=[]
                markers=['Also covers identical source in medical-scope packet:','This also resolves the source-only medical-scope candidate:','This covers the own medical-scope candidate as well.']
                marker=next((phrase for phrase in markers if phrase in item.get('rationale','')),None)
                if path.name.startswith('prompted-') and marker:
                    declared_kinds=list(set(declared_kinds)|{'medical'})
                    declaration_basis.append({'field':'rationale','matched_author_coverage_phrase':marker,'verbatim_declaration':item['rationale'],'scope':'Exact author-written coverage declaration, not a new source assessment or classification.'})
                for kind,phrase in [('medical','from own medical-scope delta packet'),('date-window','from own date-window delta packet')]:
                    if path.name.startswith('prompted-') and phrase in item.get('source_extent',''):
                        declared_kinds=list(set(declared_kinds)|{kind})
                        declaration_basis.append({'field':'source_extent','matched_author_coverage_phrase':phrase,'verbatim_declaration':item['source_extent'],'scope':'Explicit author-named source packet purpose; not inferred from a mixed filename or scientific classification.'})
                self_rechecks[-1]['author_declared_audit_kinds_json']=json.dumps(sorted(declared_kinds))
                self_rechecks[-1]['author_declared_coverage_basis_json']=json.dumps(declaration_basis,ensure_ascii=False,sort_keys=True)
                if item.get('inspected_extent') and not item.get('source_extent'):self_rechecks[-1]['source_extent_verbatim']=item['inspected_extent']
                if not self_rechecks[-1]['uncertainty_note_verbatim']:self_rechecks[-1]['uncertainty_note_verbatim']=item.get('scope_limit',item.get('remaining_limit',item.get('date_limit','')))
                if not self_rechecks[-1]['uncertainty_note_verbatim']:self_rechecks[-1]['uncertainty_note_verbatim']=next((item[field] for field in ['limits','limitations','reason_uncertainty'] if item.get(field)),'')
    legacy_date_corrections=[]
    for (pas,key),amendment in newdates.items():
        if amendment.get('date_registration_stage')!='FRESH_LEGACY_DATE_METADATA_CORRECTION':continue
        path=Path(amendment['source_file']);digest=amendment['date_source_sha256'];assert s.sha(path)==digest
        used=key in input_receipts.get((path.resolve(),digest),set())
        fresh=fresh_rechecks[(pas,key)]
        raw=loadj(path)
        if isinstance(raw,dict) and raw.get('publication_id'):raw_records=[raw]
        elif isinstance(raw,list):raw_records=raw
        else:
            container=next(field for field in ['records','checks','results','entries'] if isinstance(raw.get(field),list))
            raw_records=raw[container]
        raw_record=next(record for record in raw_records if record['publication_id']==key)
        note={'publication_id':key,'pass_id':pas,'worker':amendment['date_metadata_author_worker'],'note_model':'gpt-6.1-terra','note_model_recording_basis':'Explicit owning date-amendment model and validated fresh legacy source-recheck owner','stage':'FRESH_LEGACY_DATE_METADATA_CORRECTION_NOT_INITIAL','source_file':path.as_posix(),'source_sha256':digest,'both_initials_saved':key in initial['A'] and key in initial['B'],'adjudication_status':'RECHECK_HASH_LINKED_IN_ADJUDICATION_RECEIPT' if used else 'PENDING_SOURCE_RECHECK_ADJUDICATION','proposed_eligibility':'','proposed_reason':'','rechecked_label_verbatim':'','recheck_outcome_verbatim':amendment.get('outcome','DATE_SOURCE_METADATA_CORRECTION'),'rationale_verbatim':amendment['date_basis'],'uncertainty_note_verbatim':amendment.get('limitations',''),'identity_issue_verbatim':'','integrity_status_verbatim':'','source_reported_disposition_verbatim':'','source_extent_verbatim':amendment.get('source_extent',amendment['date_basis']),'note_payload_json':json.dumps(amendment,ensure_ascii=False,sort_keys=True),'source_quote_typography_notes_json':'[]','source_evidence_quotes_json':'[]','source_note_container_field':'registered_date_metadata_amendment','source_note_wrapper_metadata_json':'{}','author_declared_audit_kinds_json':'[]','author_declared_coverage_basis_json':'[]','human_verification':'PENDING'}
        self_rechecks.append(note)
        note['note_payload_json']=json.dumps(raw_record,ensure_ascii=False,sort_keys=True)
        legacy_date_corrections.append(amendment|{'pass_id':pas,'submitted_fresh_date_check_status':fresh.get('date_check_status',''),'submitted_fresh_recheck_artifact':fresh['recheck_artifact'],'source_correction_consideration_status':note['adjudication_status'],'human_verification':'PENDING'})
    if legacy_date_corrections:s.wr(CANON/'fresh-legacy-date-corrections-current.csv',legacy_date_corrections)
    if self_rechecks:s.wr(CANON/'self-detected-recheck-queue.csv',self_rechecks)
    s.wr(CANON/'post-initial-identity-notes.csv',[row for row in self_rechecks if row['stage']=='SOURCE_IDENTITY_METADATA_NOTE_AFTER_INITIAL'])
    integrity_notes=[row for row in self_rechecks if row['integrity_status_verbatim'] or row['source_reported_disposition_verbatim']]
    if integrity_notes:s.wr(CANON/'integrity-source-flags-pending.csv',integrity_notes)
    exposures=[]
    for worker in s.WORKERS:
        exposure_files=sorted((RUN/'workers'/worker).glob('incidental-exposure-*.json'))
        if not exposure_files:continue
        initial_assigned_ids={key for batch in s.assignment(worker)['batches'] for key in batch['ids']}
        legacy_assigned_ids={task['publication_id'] for task in recheck_tasks if task['owner']==worker}
        assigned_ids=initial_assigned_ids|legacy_assigned_ids
        saved_ids=set(s.worker_rows(worker))
        for path in exposure_files:
            row=loadj(path)
            keys=row.get('assigned_publication_ids',row.get('publication_ids'))
            if keys is None:keys=[row.get('publication_id',row.get('assigned_publication_id'))]
            recorded_keys=json.dumps(keys,ensure_ascii=False)
            if isinstance(keys,list) and len(keys)==1 and isinstance(keys[0],str) and ',' in keys[0]:
                split_keys=[key.strip() for key in keys[0].split(',')]
                assert all(re.fullmatch(r'P\d{7}',key) for key in split_keys),('INVALID_COMMA_SEPARATED_DISCLOSURE_IDS',worker,path.name)
                keys=split_keys
            assert isinstance(keys,list) and keys and len(keys)==len(set(keys))
            assert all(key in assigned_ids for key in keys),('EXPOSURE_OUTSIDE_OWN_ASSIGNMENT',worker,path.name,keys)
            model_field=next((field for field in ['model','actual_model','authorship'] if row.get(field)),None)
            assert row['worker']==worker and model_field and row[model_field]=='gpt-6.1-terra'
            extent=row.get('extent_seen',row.get('exposure',''))
            impact_field=next((field for field in ['impact','routing_basis','informed_routing','routing_informed'] if field in row and row[field] is not None and row[field]!=''),None)
            impact=row[impact_field] if impact_field else None
            urls=row.get('source_urls')
            if urls is None:urls=[row.get('source_url')]
            assert isinstance(urls,list) and urls and all(isinstance(url,str) and url for url in urls) and extent and impact_field,('EXPOSURE_REQUIRED_FIELD_MISSING',worker,path.name)
            digest=s.sha(path);payload=json.dumps(row,ensure_ascii=False,sort_keys=True)
            for key in keys:
                exposures.append(row|{'publication_id':key,'pass_id':worker[0],'model':row[model_field],'recorded_model_field':model_field,'recorded_impact_field':impact_field,'recorded_assigned_ids_json':recorded_keys,'disclosure_assignment_stage':'OWN_INITIAL_SOURCE_ASSIGNMENT' if key in initial_assigned_ids else 'OWN_LEGACY_SOURCE_RECHECK_ASSIGNMENT','source_url':row.get('source_url','; '.join(urls)),'source_url_scope':'Event-level URLs preserved without inventing per-ID attribution','extent_seen':extent,'impact':impact,'disclosure_payload_json':payload,'source_file':path.as_posix(),'source_sha256':digest,'own_initial_saved_at_disclosure_scan':key in saved_ids,'own_legacy_source_recheck_in_published_harvest':fresh_rechecks.get((worker[0],key),{}).get('worker_id')==worker,'included_in_initial_snapshot':key in initial[worker[0]],'human_verification':'PENDING'})
    if exposures:s.wr(CANON/'worker-incidental-exposure-disclosures.csv',exposures)
    cross_agent_exposures=[]
    for worker in s.WORKERS:
        folder=RUN/'workers'/worker
        events=sorted(folder.glob('accidental-exposure-status-*.json'))
        if not events:continue
        assert len(events)==1,('MULTIPLE_CROSS_AGENT_EVENTS_REQUIRE_EXPLICIT_SUPPLEMENT_MAPPING',worker)
        event=events[0];raw=loadj(event)
        assert raw['worker']==worker and raw.get('model',raw.get('actual_model'))=='gpt-6.1-terra'
        for field in ['stage','event','exposure','timing','impact','limitations']:assert raw.get(field),('CROSS_AGENT_DISCLOSURE_FIELD_MISSING',worker,field)
        mentions=sorted(set(re.findall(r'P\d{7}',raw['exposure'])))
        assert mentions and set(mentions)<=set(inventory)
        own_ids=set(s.worker_rows(worker));own_mentions=sorted(set(mentions)&own_ids)
        assert own_mentions,('CROSS_AGENT_EVENT_NEEDS_EXPLICIT_AFFECTED_CASE_SCOPE',worker)
        supplements=sorted(folder.glob('accidental-exposure-chronology-supplement-*.json'))
        artifacts=[event,*supplements];artifact_hashes={path.as_posix():s.sha(path) for path in artifacts}
        for path in supplements:
            item=loadj(path);assert item['worker']==worker and item.get('model',item.get('actual_model'))=='gpt-6.1-terra'
        event_considered=all(key in input_receipts.get((path.resolve(),artifact_hashes[path.as_posix()]),set()) for key in own_mentions for path in artifacts)
        review_path=RUN/'admin'/f'{worker}-post-initial-exposure-review-20261113.json'
        cross_agent_exposures.append({'worker':worker,'pass_id':worker[0],'model':'gpt-6.1-terra','exposure_stage_verbatim':raw['stage'],'event_verbatim':raw['event'],'exposure_verbatim':raw['exposure'],'timing_account_verbatim':raw['timing'],'impact_verbatim':raw['impact'],'limitations_verbatim':raw['limitations'],'disclosed_id_mentions_json':json.dumps(mentions),'own_observed_initial_ids_json':json.dumps(own_mentions),'own_initials_in_published_snapshot':sum(row.get('worker_id')==worker for row in initial[worker[0]].values()),'disclosure_artifacts_sha256_json':json.dumps(artifact_hashes,sort_keys=True),'source_consideration_status':'EXACT_HASH_AND_AFFECTED_ID_LINKED_IN_SOL_RECEIPT' if event_considered else 'PENDING_SOL_SOURCE_CONSIDERATION_WITH_DISCLOSURE','coordinator_chronology_review':review_path.as_posix() if review_path.exists() else '','coordinator_chronology_review_sha256':s.sha(review_path) if review_path.exists() else '','disclosure_payload_json':json.dumps(raw,ensure_ascii=False,sort_keys=True),'scope':'Known disclosed post-initial cross-agent status view; original initials remain immutable. Chronology evidence and source-judgment validity are separate. No independent prompted agreement or clinical validation inferred.','human_verification':'PENDING'})
    if cross_agent_exposures:s.wr(CANON/'known-cross-agent-exposures.csv',cross_agent_exposures)
    # These preserve established queues or locate text for later source checks;
    # they never infer duplicate identity or manufacture integrity judgments.
    for source_name,destination in [('all-doi-identity-candidates-v2.csv','identity-doi-candidates-pending.csv'),('integrity-protections-B0032-v0.4.6.csv','integrity-holds-preserved.csv'),('focused-followups-20261112T174047Z.csv','legacy-focused-followups-pending.csv')]:
        p=ROOT/'astra'/source_name
        if p.exists():
            rows=s.rd(p)
            if source_name.startswith('focused-followups-'):
                followup=ROOT/'sol/B0031-B0032-targeted-followup-v0.4.6.csv'
                authority=loadj(ROOT/'sol/modality-precedence-manifest.json')['entries']
                registered=any(x.get('file')==followup.name and x.get('precedence')==640 for x in authority)
                checked={x['publication_id']:x for x in s.rd(followup)} if followup.exists() and registered else {}
                rows=[row|{'historical_queue_status':row['status'],'current_source_followup_status':'LEGACY_SOL_SOURCE_RECHECK_SAVED' if row['publication_id'] in checked else 'PENDING_SOURCE_FOLLOWUP','completed_followup_artifact':followup.as_posix() if row['publication_id'] in checked else '','completed_followup_sha256':s.sha(followup) if row['publication_id'] in checked else '','scope':'Historical queue preserved; current accounting recognizes explicitly registered source rechecks, without declaring human validation or unresolved evidence resolved'} for row in rows]
            s.wr(CANON/destination,rows)
    family_path=RUN/'admin/inherited-report-family-followups.json'
    if family_path.exists():
        family=loadj(family_path);note=Path(family['source_note']);assert note.exists()
        s.wr(CANON/'report-family-followups-pending.csv',[row|{'reported_trial_registration':family['reported_trial_registration'],'identity_status':family['identity_status'],'source_note':note.as_posix(),'source_note_sha256':s.sha(note),'provenance':family['provenance'],'human_verification':'PENDING','scope':'No ID merger, eligibility transfer or independent-study count'} for row in family['records']])
    notices=[]
    for key,source in inventory.items():
        if re.search(r'retract|expression of concern',source['title']+' '+source['abstract'],re.I):
            notices.append({'publication_id':key,'title':source['title'],'doi':source['doi'],'source_coordinate':key+':'+source['abstract_record_id']+':title/abstract','status':'TEXT_LOCATOR_ONLY_PENDING_NOTICE_IDENTITY_AND_SOURCE_ASSESSMENT','not_a_synthesis_hold_decision':'true','source_memberships_json':source['source_memberships_json']})
    s.wr(CANON/'integrity-text-locator-pending.csv',notices)
    s.wr(CANON/'human-verification-pending.csv',[{'publication_id':i,'human_verification':'PENDING','source_memberships_json':r['source_memberships_json']} for i,r in inventory.items()])
    holds=[];hold_consistency=[]
    for key,source in inventory.items():
        old=legacy[key];current=adj.get(key,{})
        if old.get('integrity_synthesis_hold') in {'True','true','WITHHOLD_FROM_SYNTHESIS'}:
            explicit_hold=current.get('report_disposition')=='WITHHOLD_FROM_SYNTHESIS' or current.get('synthesis_disposition')=='WITHHOLD_FROM_SYNTHESIS'
            documented=bool(current and current.get('eligibility')=='UNCERTAIN' and explicit_hold)
            hold_consistency.append({'publication_id':key,'preserved_legacy_hold':old['integrity_synthesis_hold'],'legacy_integrity_status':old.get('source_integrity_status',''),'current_eligibility':current.get('eligibility',''),'current_report_disposition':current.get('report_disposition',''),'current_synthesis_disposition':current.get('synthesis_disposition',''),'status':'SOURCE_ROUTING_AND_EXPLICIT_HOLD_DOCUMENTED' if documented else ('PENDING_CURRENT_SOURCE_ROUTING' if not current else 'PENDING_EXPLICIT_SOURCE_HOLD_FIELDS'),'source_artifact':current.get('source_revision_artifact',current.get('adjudication_artifact','')),'human_verification':'PENDING','scope':'Existing verified-notice holds cannot be silently lifted while required human verification remains pending. No new notice identity or misconduct inference.'})
        if old.get('integrity_synthesis_hold') in {'True','true','WITHHOLD_FROM_SYNTHESIS'} or current.get('report_disposition')=='WITHHOLD_FROM_SYNTHESIS' or current.get('synthesis_disposition')=='WITHHOLD_FROM_SYNTHESIS':
            holds.append({'publication_id':key,'legacy_hold':old.get('integrity_synthesis_hold',''),'legacy_integrity_status':old.get('source_integrity_status',''),'current_report_disposition':current.get('report_disposition',''),'current_synthesis_disposition':current.get('synthesis_disposition',''),'current_integrity_status':current.get('integrity_status',''),'adjudication_artifact':current.get('adjudication_artifact',''),'source_revision_artifact':current.get('source_revision_artifact',''),'human_verification':'PENDING','scope':'Explicit preserved or source-adjudicated synthesis holds only; no keyword-inferred misconduct or identity merger'})
    s.wr(CANON/'integrity-holds-current.csv',holds)
    s.wr(CANON/'preserved-integrity-hold-routing-check.csv',hold_consistency)
    s.wr(CANON/'full-text-selection-queue.csv',[{'publication_id':i,'stage':'ADVANCE_FOR_FULL_TEXT_ASSESSMENT_ONLY','modality_stream':x.get('modality_stream',''),'evidence_type':x.get('evidence_type',''),'source_artifact':x['adjudication_artifact'],'human_verification':'PENDING'} for i,x in adj.items() if x['eligibility']=='INCLUDE'])
    audits=[];auditbatches=[]
    for b in s.idx():
        bid=b['batch_id'];folder=RUN/'paired'/bid
        if not folder.exists():continue
        needed=s.rd(folder/'required-audit.csv');selection=loadj(folder/'audit-selection.json')
        for row in needed:
            key=row['publication_id'];x=adj.get(key,{})
            status=x.get('audit_status','UNPERFORMED')
            # Unsampled legacy rows are not promoted to audited by agreement alone.
            if x.get('adjudication_origin')=='legacy_registered' and ('UNAUDIT' in status.upper() or 'NOT_AUDIT' in status.upper() or ('AGREED_EXCLUSION' in status.upper() and 'NOT_' in status.upper())):status='PENDING_SCOPE_VERIFICATION'
            audits.append(row|{'batch_id':bid,'status':status,'source_coordinate':x.get('source_coordinate',''),'source_artifact':x.get('adjudication_artifact',''),'source_extent':x.get('source_assessment_extent',x.get('assessment_stage','')),'human_verification':'PENDING'})
        auditbatches.append({'batch_id':bid,'batch_n':b['n'],'required_unique_cases':len(needed),'sample_n':len(selection['sample_ids']),'sample_ids_json':json.dumps(selection['sample_ids']),'unperformed_required_cases':sum(1 for row in needed if row['publication_id'] not in adj)})
    s.wr(CANON/'required-audit-status-current.csv',audits);s.wr(CANON/'audit-batch-summary-current.csv',auditbatches)
    sampled={i for b in auditbatches for i in json.loads(b['sample_ids_json'])}
    findings=[]
    for key,current in adj.items():
        a=initial['A'].get(key,{});b=initial['B'].get(key,{})
        changed=[field for field in ['eligibility','evidence_stream','modality_stream','evidence_type'] if any(str(current.get(field,'')).casefold()!=str(x.get(field,'')).casefold() for x in [a,b])]
        if not changed and key not in sampled:continue
        findings.append({'publication_id':key,'batch_id':current.get('batch_id',''),'changed_fields_vs_either_original':';'.join(changed),'initial_A_eligibility':a.get('eligibility',''),'initial_B_eligibility':b.get('eligibility',''),'current_provisional_eligibility':current['eligibility'],'initial_A_modality':a.get('modality_stream',''),'initial_B_modality':b.get('modality_stream',''),'current_provisional_modality':current.get('modality_stream',''),'fixed_exclusion_sample':key in sampled,'audit_status':current.get('audit_status',''),'source_basis':current.get('rationale',''),'source_coordinate':current.get('source_coordinate',''),'source_artifact':current['adjudication_artifact'],'scope':'Current provisional routing differences or sampled-case receipt; not a ground-truth error or accuracy estimate','human_verification':'PENDING'})
    s.wr(CANON/'audit-findings-and-routing-differences.csv',findings)
    agreement=defaultdict(list)
    for key in set(initial['A'])&set(initial['B']):
        x,y=initial['A'][key],initial['B'][key];agreement[(x.get('model','UNKNOWN'),y.get('model','UNKNOWN'))].append((key,x['eligibility'],y['eligibility']))
    metrics=[]
    for pair,values in sorted(agreement.items()):
        n=len(values);a=Counter(x[1] for x in values);b=Counter(x[2] for x in values);p=sum(x[1]==x[2] for x in values)/n;chance=sum(a[k]*b[k] for k in {'INCLUDE','EXCLUDE','UNCERTAIN'})/n**2
        metrics.append({'pass_A_model':pair[0],'pass_B_model':pair[1],'n':n,'agreement_n':sum(x[1]==x[2] for x in values),'agreement_proportion':p,'cohens_kappa':(p-chance)/(1-chance) if chance<1 else None,'scope':'Original initial judgments only; consistency, not accuracy; new Terra/Terra model-family errors may correlate'})
    s.js(CANON/'original-agreement-by-actual-model.json',metrics)
    stratified=defaultdict(list)
    for key in set(initial['A'])&set(initial['B']):
        x,y=initial['A'][key],initial['B'][key]
        origins=tuple('NEW_FIXED_POOL_INITIAL' if row.get('worker_id') else 'LEGACY_ORIGINAL_INITIAL' for row in [x,y])
        stratified[(origins[0],origins[1],x.get('model','UNKNOWN'),y.get('model','UNKNOWN'))].append((x['eligibility'],y['eligibility']))
    origin_metrics=[]
    for (oa,ob,ma,mb),values in sorted(stratified.items()):
        n=len(values);aa=Counter(x for x,y in values);bb=Counter(y for x,y in values);agreed=sum(x==y for x,y in values);p=agreed/n;chance=sum(aa[k]*bb[k] for k in {'INCLUDE','EXCLUDE','UNCERTAIN'})/n**2
        origin_metrics.append({'pass_A_origin':oa,'pass_B_origin':ob,'pass_A_actual_model':ma,'pass_B_actual_model':mb,'n':n,'agreement_n':agreed,'agreement_proportion':p,'cohens_kappa':(p-chance)/(1-chance) if chance<1 else None,'scope':'Original initial eligibility only; separates legacy/legacy, missing-partner mixed origins, and two fresh fixed-pool initials. Unknown model values remain as recorded; no recheck or adjudication substituted. Consistency is not accuracy.'})
    s.js(CANON/'original-agreement-by-origin-and-model.json',origin_metrics)
    grouping=[]
    for dimension in ['year','medical_task','modality_stream','evidence_type','evidence_stream']:
        freq=Counter()
        for key,x in adj.items():
            value=inventory[key]['year'] if dimension=='year' else x.get(dimension,'')
            freq[value or 'MISSING_OR_UNASSESSED']+=1
        grouping.extend({'dimension':dimension,'provisional_value':k,'publication_ids':v,'denominator':'current provisional adjudications','warning':'Source-reported/grouped publications, not unique studies; year is frozen representative metadata, not verified publication year'} for k,v in sorted(freq.items()))
    s.wr(CANON/'preliminary-coverage-groups.csv',grouping)
    # Preserve actual screeners' task wording without inventing a harmonized taxonomy.
    taskrows=[];taskgroups=[]
    for pas in 'AB':
        freq=Counter()
        for key,source in inventory.items():
            x=initial[pas].get(key,{})
            value=x.get('medical_task','')
            status='RECORDED_VERBATIM_UNHARMONIZED' if value else ('MISSING_TASK_FIELD' if x else 'INITIAL_ASSESSMENT_UNPERFORMED')
            taskrows.append({'publication_id':key,'pass_id':pas,'medical_task_verbatim':value,'field_status':status,'initial_reviewer':x.get('reviewer',''),'initial_model':x.get('model',''),'source_artifact':x.get('initial_artifact',''),'current_adjudicated_eligibility':adj.get(key,{}).get('eligibility',''),'scope':'Original task wording only, no inferred or adjudicator-endorsed task grouping'})
            freq[(value or status,status)]+=1
        taskgroups.extend({'pass_id':pas,'medical_task_verbatim':value,'field_status':status,'publication_ids':n,'denominator':18976,'scope':'Provisional unharmonized original task labels with missingness; pass counts overlap'} for (value,status),n in sorted(freq.items()))
    s.wr(CANON/'preliminary-medical-task-source-labels.csv',taskrows)
    s.wr(CANON/'preliminary-medical-task-groups.csv',taskgroups)
    joint=Counter((x.get('evidence_stream','') or 'MISSING',x.get('modality_stream','') or 'MISSING',x['eligibility']) for x in adj.values())
    s.wr(CANON/'preliminary-stream-modality-routing-groups.csv',[{'evidence_stream':stream,'modality_stream':mode,'provisional_routing':route,'publication_ids':n,'scope':'Publication-level source routing only. Empirical data can concern technical design, needs or implementation; an XR target/category does not establish observed delivery or clinical use. No observed-application or independent-study denominator is inferred.'} for (stream,mode,route),n in sorted(joint.items())])
    counts.update(adjudicated_n=len(adj),adjudication_pending=18976-len(adj),adjudicated_eligibility_counts=dict(Counter(x['eligibility'] for x in adj.values())),required_audit_cases_in_paired_batches=len(audits),required_audits_unperformed=sum(x['status']=='UNPERFORMED' for x in audits),required_audits_scope_verification_pending=sum(x['status']=='PENDING_SCOPE_VERIFICATION' for x in audits),required_audit_source_status_counts=dict(Counter(x['status'] for x in audits)),independent_2020_date_obligations=len(datequeue),date_status_counts=dict(Counter(x['date_check_status'] for x in datequeue)),legacy_retrospective_unperformed=len(retrospective),legacy_targeted_rechecks_pending=sum(not x['current_required_source_followups_complete'] for x in required),self_detected_rechecks_pending=sum(x['adjudication_status'].startswith('PENDING') for x in self_rechecks),pending_queue_counts=dict(Counter(x['queue'] for x in queues)),generated_at_utc=s.stamp())
    obligation_path=RUN/'mandatory-audit-obligations.json'
    obligations=loadj(obligation_path)['obligations'] if obligation_path.exists() else []
    for task in obligations:
        if task['obligation_id']=='legacy-B0033-focused-pass-A-followup':
            keys=[('A',key) for key in task['publication_ids']]
            if all(key in fresh_rechecks and considered.get(key,{}).get('recheck_artifact_sha256')==fresh_rechecks[key]['recheck_artifact_sha256'] for key in keys):
                task.update(original_obligation_status=task['status'],status='COMPLETE_SOURCE_ASSESSED',completion_basis='Fresh fixed-pool Terra source rechecks and hash-linked fresh Sol source consideration; legacy Sol pending status remains historical',source_review_receipts=';'.join(sorted({considered[key]['source_review_receipt'] for key in keys})))
    if obligations:s.wr(CANON/'mandatory-audit-obligations-current.csv',obligations)
    counts['mandatory_operational_audits_pending']=sum(x['status']!='COMPLETE_SOURCE_ASSESSED' for x in obligations)
    counts['additional_source_flag_date_obligations']=2*len(additional_date_checks)
    counts['method_application_source_checked_unique']=len(method_checked_ids)
    counts['method_application_followups_pending']=sum(x['current_check_status'].startswith('PENDING') for x in method_followups)
    counts['fresh_legacy_source_recheck_tasks']=len(recheck_tasks)
    counts['fresh_legacy_source_recheck_obligations']=sum(len(json.loads(row['obligations_json'])) for row in recheck_tasks)
    counts['fresh_legacy_independent_date_tasks']=sum('independent_2020_date' in json.loads(row['obligations_json']) for row in recheck_tasks)
    counts['fresh_legacy_source_rechecks_saved']=len(fresh_rechecks)
    counts['fresh_legacy_source_rechecks_unperformed']=len(recheck_tasks)-len(fresh_rechecks)
    counts['fresh_legacy_rechecks_sol_consideration_pending']=sum(row['source_check_status']=='SOURCE_RECHECK_SAVED' and row['sol_consideration_status']!='SOURCE_RECHECK_CONSIDERED' for row in recheck_status)
    counts['post_initial_source_notes_deferred_to_next_snapshot']=len(deferred_notes)
    counts['initial_explicit_integrity_flags_pass_ids']=len(initial_integrity)
    counts['initial_explicit_integrity_flags_publication_ids']=len({row['publication_id'] for row in initial_integrity})
    counts['preserved_integrity_hold_routing_pending']=sum(row['status']!='SOURCE_ROUTING_AND_EXPLICIT_HOLD_DOCUMENTED' for row in hold_consistency)
    counts['known_cross_agent_exposure_events']=len(cross_agent_exposures)
    counts['cross_agent_exposures_pending_sol_source_consideration']=sum(row['source_consideration_status'].startswith('PENDING') for row in cross_agent_exposures)
    counts['goal_complete']=counts['initial_assessments_remaining']==0 and counts['adjudication_pending']==0 and counts['required_audits_unperformed']==0 and counts['required_audits_scope_verification_pending']==0 and not retrospective and not counts['legacy_targeted_rechecks_pending'] and not counts['self_detected_rechecks_pending'] and not counts['mandatory_operational_audits_pending'] and not counts['fresh_legacy_source_rechecks_unperformed'] and not counts['fresh_legacy_rechecks_sol_consideration_pending'] and not counts['preserved_integrity_hold_routing_pending'] and all(not x['date_check_status'].startswith('PENDING') for x in datequeue)
    counts['goal_complete']=counts['goal_complete'] and not counts['cross_agent_exposures_pending_sol_source_consideration']
    s.js(CANON/'coverage-and-flow-current.json',counts)
    sources={str(s.INVENTORY):s.EXPECTED_HASH}|adjinputs
    sources.update(loadj(RUN/'legacy-adapter-reconciliation.json')['input_hashes'])
    for byid in initial.values():
        for row in byid.values():
            p=Path(row['initial_artifact'])
            if p.as_posix() not in sources:
                assert s.sha(p)==row['initial_artifact_sha256'],'PUBLISHED_INITIAL_ARTIFACT_DRIFT'
                sources[p.as_posix()]=row['initial_artifact_sha256']
            if row.get('worker_id'):
                receipt=p.with_suffix('.receipt.json')
                if receipt.as_posix() not in sources:sources[receipt.as_posix()]=s.sha(receipt)
    if DATEREG.exists():
        sources[DATEREG.as_posix()]=s.sha(DATEREG)
        for e in loadj(DATEREG)['entries']:
            sources[e['file']]=e['sha256']
            for extra in e.get('corrections',[]):sources[extra['file']]=extra['sha256']
    for p in [ROOT/'shared/method-v0.4.6.md',*(ROOT/'shared').glob('*addendum-v0.4.6-*.md'),ROOT.parent/'Medical-XR-Capability-Assessment-Pilot/reconciled-codebook-v0.2.md',Path('10 - Locked question and capability analysis.md'),ROOT/'shared/inventory-column-fingerprint-v2-no-seed.json',ROOT/'astra/current-artifacts.json',ROOT/'astra/date-correction-precedence.json',ROOT/'sol/modality-precedence-manifest.json',RUN/'INITIAL-SCREENER-RULES.md',RUN/'TEAM-AND-METHOD-LOG.md',RUN/'task-manifest.csv',RUN/'legacy-adapter-reconciliation.json',RUN/'admin/original-provenance-amendment.json',Path('work/screening_qa/resume_screening.py'),Path(__file__)]:sources[p.as_posix()]=s.sha(p)
    for pattern in ['parent-validation/*.json','adjudicator_sol/*parent-validation-input-receipt.json','adjudicator_sol/method-046-application-*.json','adjudicator_sol/method-046-application-*.tsv','adjudicator_sol/method-046-application-*.csv','adjudicator_sol/legacy-required-audit-scope-index-*.json','adjudicator_sol/*-source-provenance-receipt.json','mandatory-audit-obligations.json','adjudication-registry.json','legacy-recheck-*.json','legacy-recheck-task-manifest.csv','LEGACY-RECHECK-RULES.md','SOURCE-AUDIT-OVERLAY-SCHEMA.md','legacy-audit-scope/*','admin/legacy-recheck-scope-snapshot/*','admin/legacy-adjudication-*.json','admin/initial-exposure-metadata-clarification.json','admin/inherited-report-family-followups.json','workers/*/legacy-rechecks/assignment.json','workers/*/legacy-rechecks/source-only.csv']:
        for p in RUN.glob(pattern):sources[p.as_posix()]=s.sha(p)
    for pattern in ['medical-scope-audit/*/*','workers/*/medical-scope-audit/*/*','date-window-audit/*/*','date-window-audit/current-scope.json','workers/*/date-window-audit/*/*','workers/*/self-*date*flag*.json','workers/*/self-audit-date-rule-*.json','initial-date-gap-audit/*/*','additional-date-boundary-audit/*/*','additional-date-boundary-audit/*/*/*','workers/*/date-gap-source-only-*.csv','legacy-recheck-supplement-*.csv','legacy-recheck-supplement-*.json','workers/*/legacy-rechecks/supplements/*/*','adjudicator_sol/*.py','adjudicator_sol/*fix-receipt*.json','workers/*/incidental-exposure-*.json','admin/initial-date-inline-status-clarification.json','COORDINATOR-HANDOFF.md','DATA-DICTIONARY.md']:
        for p in RUN.glob(pattern):
            if p.is_file():sources[p.as_posix()]=s.sha(p)
    for p in (RUN/'admin').glob('initial-worker-count-*.json'):sources[p.as_posix()]=s.sha(p)
    for pattern in ['admin/date-sidecar-exact-recovery-*.json','admin/manifest-validation-*.json','admin/initial-screening-completion-*.json','admin/complete-initial-structure-and-samples-*.json','admin/coordinator-publication-events/*.json','admin/context-label-guard-validation-*.json','admin/coordinator-handoff-before-*.md','admin/*-post-initial-exposure-review-*.json','admin/*-exposure-initial-snapshot-manifest-*.json','admin/show_legacy_rechecks-before-*.py','workers/*/accidental-exposure-*.json','workers/*/prompted-integrity-locator-sweep*.json','workers/*/integrity-marker-sweep-*.json','workers/*/own-audit-coverage-map-*.json','workers/*/audit-ready-handoff-*.json']:
        for p in RUN.glob(pattern):
            if p.is_file():sources[p.as_posix()]=s.sha(p)
    for pattern in ['integrity-disposition-audit/*/*','workers/*/integrity-disposition-audit/*/*','label-stream-diagnostics/*/*','observation-gate-audit/*/*','technology-exclusion-audit/*/*','date-route-audit/*/*','adjudicator_sol/observation-gate-*-complete-index.json','INITIAL-LABEL-STREAM-APPLICATION-NOTE-20261113.md']:
        for p in RUN.glob(pattern):
            if p.is_file():sources[p.as_posix()]=s.sha(p)
    for p in [Path('work/screening_qa/refresh_resume_run.py'),Path('work/screening_qa/watch_resume_publications.py'),Path('work/screening_qa/validate_parent_sources.py'),Path('work/screening_qa/resume_rechecks.py'),Path('work/screening_qa/validate_resume_manifest.py'),Path('work/screening_qa/validate_complete_initial_structure.py'),Path('work/screening_qa/locate_medical_scope_rechecks.py'),Path('work/screening_qa/locate_date_window_rechecks.py'),Path('work/screening_qa/prepare_initial_date_gaps.py'),Path('work/screening_qa/close_medical_scope_audit.py'),Path('work/screening_qa/audit_context_stream_labels.py'),Path('work/screening_qa/observation_gate_application_audit.py')]:sources[p.as_posix()]=s.sha(p)
    if family_path.exists():sources[family['source_note']]=s.sha(Path(family['source_note']))
    for row in self_rechecks:sources[row['source_file']]=row['source_sha256']
    for row in fresh_rechecks.values():
        receipt_path=Path(row['recheck_receipt']);receipt=loadj(receipt_path);draft=Path(receipt['draft_file'])
        artifact=Path(row['recheck_artifact']);assert s.sha(artifact)==row['recheck_artifact_sha256']
        sources[artifact.as_posix()]=row['recheck_artifact_sha256'];sources[receipt_path.as_posix()]=s.sha(receipt_path)
        assert s.sha(draft)==receipt['draft_sha256'];sources[draft.as_posix()]=receipt['draft_sha256']
    for p in CANON.glob('*.csv'):sources[p.as_posix()]=s.sha(p)
    s.js(CANON/'validation-current.json',{'generated_at_utc':s.stamp(),'passed':True,'goal_complete':counts['goal_complete'],'checks':['18976 frozen IDs and inventory hash','Legacy initial-artifact hash preservation, including original B0001 provenance exception','Unique pass/ID assignment and fixed worker ownership','Submitted labels, exact source excerpts and memberships','Registered adjudication IDs, source-input/output hashes and field-only revision order','Original deterministic exclusion sample and agreement for new adjudications','All-ID coverage and pending queues derived from actual saved files'],'limits':'Mechanical validation does not establish source classification correctness, human approval, full-text selection or independent-study identity. Pending initial/audit/date/retrospective work prevents goal completion.'})
    headline='provisional AI screening and prescribed audits complete' if counts['goal_complete'] else 'work in progress'
    goal_status='The provisional AI screening goal is complete; independent human verification remains pending.' if counts['goal_complete'] else 'Goal remains active.'
    completeness_note='Every frozen publication ID has two valid original initial assessments and a provisional routing disposition; required AI source audits and retrospective obligations are accounted for. Source-limited evidence remains unresolved where documented.' if counts['goal_complete'] else 'The work is incomplete while any initial assessments or prescribed audits remain unperformed.'
    report=f'''# Medical XR screening review packet — {headline}

Generated {counts['generated_at_utc']}. {goal_status} Method0.4.6/codebook0.2 are unchanged. INCLUDE means advance for full-text assessment.

New primary-report work begins2020-06-01; historical and contemporary context remain separately retained. See the [ledger data dictionary](DATA-DICTIONARY.md) for provenance fields, legacy compatibility aliases and stage boundaries.

Locked question: Since 2020, has progress from commercial XR and AI capabilities to useful, sustainable medical applications accelerated—and what technical, staffing, financial and organizational conditions enable or constrain further acceleration?

Inventory, paired coverage, adjudications and human-stage counts use publication IDs. Initial assessments and independent date/fresh legacy obligations use pass/ID assessments; the two passes overlap. Audit totals are the required publication-ID case union within paired batches. These units must not be summed as independent studies.

| Quantity | Exact count |
|---|---:|
| Frozen inventory | 18,976 |
| Pass A saved / remaining | {counts['pass_A_saved']:,} / {counts['pass_A_pending']:,} |
| Pass B saved / remaining | {counts['pass_B_saved']:,} / {counts['pass_B_pending']:,} |
| Both initial passes | {counts['both_initial_passes']:,} |
| Initial assessments remaining | {counts['initial_assessments_remaining']:,} |
| Provisional adjudication saved / remaining | {len(adj):,} / {18976-len(adj):,} |
| Required audit cases in currently paired batches | {len(audits):,} |
| Required audits unperformed / scope check pending | {counts['required_audits_unperformed']:,} / {counts['required_audits_scope_verification_pending']:,} |
| Independent 2020 / source-flag date obligations recorded | {len(datequeue):,} |
| Legacy retrospective checks unperformed | {len(retrospective):,} |
| Fresh legacy source-recheck tasks saved / unperformed | {len(fresh_rechecks):,} / {len(recheck_tasks)-len(fresh_rechecks):,} |
| Known post-initial sibling-status exposures / awaiting Sol source consideration | {len(cross_agent_exposures):,} / {counts['cross_agent_exposures_pending_sol_source_consideration']:,} |
| Human verified / pending | 0 / 18,976 |

Current provisional routing: {counts['adjudicated_eligibility_counts'].get('INCLUDE',0):,} INCLUDE, {counts['adjudicated_eligibility_counts'].get('EXCLUDE',0):,} EXCLUDE, and {counts['adjudicated_eligibility_counts'].get('UNCERTAIN',0):,} UNCERTAIN publication IDs. Review, protocol, commercial and adjacent streams remain separately retained; these routing counts are not final study inclusion or clinical findings. Empirical data can concern design, technical validation, needs or implementation. A reported XR target/category alone does not establish observed delivery or clinical use; component-specific source extent must govern later extraction.

Current outputs are in [canonical](canonical/): provenance-preserving [Pass A](canonical/pass-A-original-initials.csv), [Pass B](canonical/pass-B-original-initials.csv), [adjudications](canonical/adjudicated-current.csv), [all-ID status](canonical/all-id-status-current.csv), [exact flow](canonical/coverage-and-flow-current.json), [audit obligations](canonical/required-audit-status-current.csv), [fixed samples](canonical/audit-batch-summary-current.csv), [pending queues](canonical/pending-queues-current.csv), [date obligations](canonical/independent-2020-date-obligations.csv), [retrospective checks](canonical/legacy-retrospective-pending.csv), [model-specific original agreement](canonical/original-agreement-by-actual-model.json), [preliminary groupings](canonical/preliminary-coverage-groups.csv), [validation](canonical/validation-current.json), and [hashed provenance](canonical/provenance-manifest-current.json).

Medical-task wording is additionally available as [unharmonized original task groups with missingness](canonical/preliminary-medical-task-groups.csv) and [row-level original task labels and sources](canonical/preliminary-medical-task-source-labels.csv). Original label/stream application diagnostics remain in label-stream-diagnostics, with their final accounting linked from the mandatory audit ledger; they preserve original semantics and do not supply a ground-truth error or accuracy estimate.

The eight fresh Terra workers remain split between fixed Pass A and Pass B pools. Initial assignments used source-only packets with instructions hiding the other pass. Known later sibling-status exposure is separately recorded in [the exposure ledger](canonical/known-cross-agent-exposures.csv) when present, with worker accounts, chronology limits and Sol consideration distinct from unchanged original initials. The fresh Sol adjudicator reads paired sources after initials are saved. Legacy identities/exposure are retained. Original agreement excludes rechecks and source routing; shared-model agreement can contain correlated errors.

Historical artifacts and corrected decisions are preserved in their original folders; new field-only source revisions are ordered in adjudication-registry.json. Legacy status was guarded-refreshed after B0033 supplemental/date registration; its old-format counts cover legacy work only. This packet supplies combined current counts. Source limitations, unresolved evidence, integrity/identity holds, retrieval and independent date work remain separate. Queue memberships overlap and must not be added as disjoint totals.

Additional review files preserve [post-initial rechecks and dissent](canonical/self-detected-recheck-queue.csv), [fresh legacy recheck status](canonical/fresh-legacy-source-recheck-status.csv), [mandatory operational audits](canonical/mandatory-audit-obligations-current.csv), [source-audit receipts/findings](canonical/source-audit-source-checks-current.csv), [original identity notes](canonical/initial-explicit-identity-notes.csv) and [separately authored later identity notes](canonical/post-initial-identity-notes.csv), and [current source-authored identity flags](canonical/source-adjudicated-identity-notes.csv) for later verification, [explicit initial integrity flags](canonical/initial-explicit-integrity-flags.csv), and [current source-adjudicated/legacy holds](canonical/integrity-holds-current.csv). Incidental source-exposure disclosures, when present, are saved separately in canonical/worker-incidental-exposure-disclosures.csv. Source flags do not establish misconduct or report identity.

Cole and the reviewing chat should use this packet with the external execution brief. {completeness_note} Later work includes full-text selection, study/report-family verification, source-specific appraisal, deeper capability/outcome/commercial extraction, and independent human verification. These screening totals do not establish medical effectiveness, commercial causality or acceleration. Preliminary year grouping uses frozen representative metadata; medical-task labels are verbatim and unharmonized, and missingness and uncertain modality/type remain explicit.
'''
    (RUN/'REVIEW-PACKET-CURRENT.md').write_text(report,encoding='utf-8')
    (ROOT/'README-current-checkpoint.md').write_text('# Medical XR combined screening checkpoint\n\nThe active fixed-pool resume run and exact combined counts are in [the current review packet](resume-20261112/REVIEW-PACKET-CURRENT.md). Legacy astra/current-counts.json covers the pre-resume reviewers only; do not use it as the combined total. All work remains provisional and human verification is pending.\n',encoding='utf-8')
    for p in CANON.glob('*.json'):
        if p.name!='provenance-manifest-current.json':sources[p.as_posix()]=s.sha(p)
    for p in [RUN/'REVIEW-PACKET-CURRENT.md',ROOT/'README-current-checkpoint.md']:sources[p.as_posix()]=s.sha(p)
    s.js(CANON/'provenance-manifest-current.json',{'generated_at_utc':s.stamp(),'inventory_n':18976,'inventory_sha256':s.EXPECTED_HASH,'input_and_output_sha256':sources,'snapshot_definition':'Counted initial and fresh legacy-recheck artifacts are exactly those referenced by the published ledgers and validated harvests, with immutable receipts/input snapshots. Workers may submit additional chunks during refresh; those enter later validated harvests. Current derived files are hashed after publication. Raw later work remains preserved without premature assessment credit.','initial_worker_models':{w:'gpt-6.1-terra' for w in s.WORKERS},'new_adjudicator_model':'gpt-6.1-sol','legacy_identity_policy':'Original recorded authors/models/exposure retained; new Terra initials never labelled as Sol authored','no_human_verification':True})
    print(json.dumps({k:counts[k] for k in ['pass_A_saved','pass_B_saved','both_initial_passes','initial_assessments_remaining','adjudicated_n','required_audits_unperformed','required_audits_scope_verification_pending','legacy_retrospective_unperformed','goal_complete']}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['register','publish','register-date','register-metadata','register-method-review','register-method-index','pin-legacy','register-source-audit','register-source-audit-index','prepare-legacy-audit','show-legacy-audit']);p.add_argument('--batch');p.add_argument('--file');p.add_argument('--receipt');p.add_argument('--revision',action='append',default=[]);p.add_argument('--access-exceptions');p.add_argument('--worker',choices=s.WORKERS);p.add_argument('--offset',type=int,default=0);p.add_argument('--limit',type=int,default=5);args=p.parse_args()
    if args.command=='register':register(args.batch,args.file,args.receipt,args.revision,args.access_exceptions)
    elif args.command=='register-date':register_date(args.worker,args.file,args.revision)
    elif args.command=='register-metadata':register_metadata(args.file)
    elif args.command=='register-method-review':register_method_review(args.file)
    elif args.command=='register-method-index':register_method_index(args.file)
    elif args.command=='pin-legacy':pin_legacy_adjudications(args.file)
    elif args.command=='register-source-audit':register_source_audit(args.file)
    elif args.command=='register-source-audit-index':register_source_audit_index(args.file)
    elif args.command=='prepare-legacy-audit':prepare_legacy_audit_scope()
    elif args.command=='show-legacy-audit':show_legacy_audit_scope(args.offset,args.limit)
    else:publish()
