"""Source-only dispatch and provenance adapter. Never generates scientific labels."""
import argparse, csv, hashlib, io, json, math, re, sys, uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('outputs/Medical-XR-Calibration-and-Full-Screening')
RUN = ROOT / 'resume-20261112'
INVENTORY = ROOT / 'shared/snapshot/provisional_publications.csv'
EXPECTED_HASH = '2b4eb990d6d03a6682e8133f19f0b39e144af887fba7a745a8c8040306c28d13'
WORKERS = [p + str(i) for p in 'AB' for i in range(1, 5)]
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')

def stamp(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rd(p):
    with p.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def wr(p, rows, exclusive=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    if exclusive: assert not p.exists(), ('IMMUTABLE_OUTPUT_EXISTS',p)
    temporary=p.with_name(p.name+'.writing-'+uuid.uuid4().hex)
    with temporary.open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)
    if exclusive:temporary.rename(p)
    else:temporary.replace(p)
def js(p, data, exclusive=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:assert not p.exists(),('IMMUTABLE_OUTPUT_EXISTS',p)
    temporary=p.with_name(p.name+'.writing-'+uuid.uuid4().hex)
    with temporary.open('x', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False); f.write('\n')
    if exclusive:temporary.rename(p)
    else:temporary.replace(p)
def inv():
    assert sha(INVENTORY) == EXPECTED_HASH, 'FROZEN_INVENTORY_DRIFT'
    rows = rd(INVENTORY); assert len(rows) == len({r['publication_id'] for r in rows}) == 18976
    return {r['publication_id']: r for r in rows}
def idx(): return json.loads((ROOT/'shared/batch-index.json').read_text(encoding='utf-8'))

def legacy():
    """Match the existing read-only coverage reporter, retaining actual legacy identities."""
    ledgers = {}; sources = {}
    for pas, folder in [('A','sol'), ('B','terra')]:
        rows = {}; paths = [ROOT/folder/'calibration-v0.3.csv']
        groups = defaultdict(list)
        for p in (ROOT/folder).glob('B*.csv'):
            m = re.fullmatch(r'(B\d{4})(-partial)?\.csv',p.name,re.I)
            if m: groups[m[1].upper()].append(p)
        for b, pp in sorted(groups.items()):
            paths.append(sorted(pp,key=lambda p:(p.stem.endswith('-partial'),p.name))[0])
        if pas == 'B':
            for sub, lo, hi in [('terra_shard_2',191,380),('terra_coordinator',351,379)]:
                for p in sorted((ROOT/sub).glob('B*-partial-*.csv')):
                    m=re.fullmatch(r'(B\d{4})-partial-\d+\.csv',p.name,re.I)
                    if m and lo<=int(m[1][1:])<=hi and not (ROOT/folder/(m[1]+'.csv')).exists(): paths.append(p)
        for p in paths:
            sources[p.as_posix()] = sha(p)
            selected=p
            if pas=='A' and p.name=='B0001.csv':
                p=ROOT/'sol/B0001-before-metadata-correction.csv'
                assert sha(p)=='2a9041af74b74c1f7a077c623d97f7c7db101655dbaecb77f22f5b333c0cf629','LEGACY_ORIGINAL_DRIFT'
                sources[p.as_posix()]=sha(p)
            for r in rd(p):
                key=r['publication_id']; assert key not in rows, ('DUPLICATE_LEGACY',pas,key)
                rows[key] = r | {'pass_id':pas,'initial_artifact':p.as_posix(),'initial_artifact_sha256':sources[p.as_posix()]}
                if p!=selected:rows[key]['legacy_later_metadata_artifact']=selected.as_posix()
        ledgers[pas] = rows
    return ledgers, sources

def init():
    inventory=inv(); old, hashes=legacy(); A=set(old['A']); B=set(old['B']); universe=set(inventory)
    counts={'A':len(A),'B':len(B),'both':len(A&B),'at_least_one':len(A|B),'neither':len(universe-(A|B))}
    assert counts=={'A':2918,'B':2862,'both':1854,'at_least_one':3926,'neither':15050}, counts
    RUN.mkdir(parents=True,exist_ok=True)
    assert not (RUN/'task-manifest.csv').exists(), 'ALREADY_INITIALIZED'
    js(RUN/'legacy-adapter-reconciliation.json', {'generated_at_utc':stamp(),'expected_legacy_checkpoint':counts,'matched':True,'inventory_sha256':EXPECTED_HASH,'input_hashes':hashes}, True)
    tasks=[]; summary={}
    for pas in 'AB':
        own=set(old[pas]); other=set(old['B' if pas=='A' else 'A']); missing=universe-own
        load=Counter({pas+str(i):0 for i in range(1,5)})
        assignments=defaultdict(list)
        for phase, pool in [('missing_partner', missing&other),('both_missing',missing-other)]:
            for b in idx():
                ids=[i for i in b['ids'] if i in pool]
                if not ids: continue
                worker=min(load,key=lambda x:(load[x],x)); load[worker]+=len(ids)
                folder=RUN/'workers'/worker; packet=folder/'sources'/f"{b['batch_id']}.csv"
                # A batch cannot span phases in this checkpoint; fail rather than overwrite.
                assert not packet.exists(), ('PHASE_SPLIT',pas,b['batch_id'])
                wr(packet,[inventory[i]|{'batch_id':b['batch_id']} for i in ids],True)
                packet_hash=sha(packet)
                assignments[worker].append({'batch_id':b['batch_id'],'priority':phase,'ids':ids,'source_packet':packet.as_posix(),'source_packet_sha256':packet_hash})
                for key in ids:
                    tasks.append({'pass_id':pas,'publication_id':key,'owner':worker,'model':'gpt-6.1-terra','batch_id':b['batch_id'],'priority':phase,'state':'assigned','source_packet':packet.as_posix(),'source_packet_sha256':packet_hash,'inventory_sha256':EXPECTED_HASH,'prompt_version':'resume-20261112-v1','screening_method_version':'0.4.6'})
        for worker, batches in assignments.items():
            js(RUN/'workers'/worker/'assignment.json',{'worker':worker,'pass_id':pas,'model':'gpt-6.1-terra','assigned_n':load[worker],'batches':batches},True)
        summary.update(load)
    assert len(tasks)==32172 and len({(r['pass_id'],r['publication_id']) for r in tasks})==len(tasks)
    wr(RUN/'task-manifest.csv',tasks,True)
    js(RUN/'dispatch-summary.json',{'generated_at_utc':stamp(),'remaining_initial_assessments':len(tasks),'by_worker':summary,'priority_counts':dict(Counter(r['priority'] for r in tasks))},True)
    print(json.dumps(summary))

def assignment(worker): return json.loads((RUN/'workers'/worker/'assignment.json').read_text(encoding='utf-8'))
def worker_rows(worker):
    result={}
    for p in sorted((RUN/'workers'/worker/'assessments').glob('*.csv')):
        digest=sha(p);rows=rd(p);receipt_path=p.with_suffix('.receipt.json')
        assert receipt_path.is_file(),('INITIAL_CHUNK_RECEIPT_NOT_YET_COMMITTED',p)
        receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
        assert receipt['worker']==worker and receipt['model']=='gpt-6.1-terra'
        assert receipt['file_sha256']==digest,('IMMUTABLE_INITIAL_CHUNK_DRIFT',p)
        assert receipt['n']==len(rows) and receipt['ids']==[row['publication_id'] for row in rows],('INITIAL_RECEIPT_COVERAGE',p)
        for r in rows:
            assert r['worker_id']==worker and r['pass_id']==worker[0] and r['model']=='gpt-6.1-terra' and r['reviewer']=='Terra_'+worker+'_resume'
            assert r['source_packet_sha256']==receipt['source_packet_sha256'] and r['inventory_sha256']==EXPECTED_HASH
            assert r['assessment_stage']=='title_abstract' and r['human_verification']=='PENDING'
            key=r['publication_id']; assert key not in result, ('DUPLICATE_NEW',worker,key)
            result[key]=r|{'initial_artifact':p.as_posix(),'initial_artifact_sha256':digest}
    return result

REQUIRED=['publication_id','eligibility','reason_code','rationale','supporting_evidence','evidence_stream','modality_stream','medical_task','date_status','evidence_type','evidence_type_basis','evidence_type_check_status']
def norm(s): return ' '.join(s.split())
def check_judgment(r,s):
    for k in REQUIRED: assert str(r.get(k,'')).strip(), ('MISSING_FIELD',r.get('publication_id'),k)
    assert r['eligibility'] in {'INCLUDE','EXCLUDE','UNCERTAIN'}
    assert r['reason_code'] in {'ELIGIBLE','DATE','MEDICAL_TASK','TECHNOLOGY','EVIDENCE_TYPE','INSUFFICIENT_DESCRIPTION'}
    assert r['evidence_stream'] in {'empirical','review_context','protocol','commercial_context','adjacent_context','uncertain'}
    assert r['modality_stream'] in {'XR','nonimmersive_3D','uncertain'}
    assert r['evidence_type_check_status'] in {'CHECKED','CHECKED_UNCLEAR'}
    # The supporting excerpt must be literal; the rationale contains interpretation.
    quote=r['supporting_evidence'].strip()
    assert any(norm(quote) in norm(s.get(k,'')) for k in ['title','abstract','date_tags_json']), ('QUOTE_NOT_LITERAL',r['publication_id'],quote)
    if not s.get('abstract','').strip(): assert r['eligibility']=='UNCERTAIN', ('MISSING_TEXT_MUST_REMAIN_PENDING',r['publication_id'])

def submit(worker,batch,path):
    inventory=inv(); a=assignment(worker); task=next(b for b in a['batches'] if b['batch_id']==batch)
    packet=Path(task['source_packet']); assert sha(packet)==task['source_packet_sha256']
    raw=json.loads(Path(path).read_text(encoding='utf-8-sig')); assert isinstance(raw,list) and raw
    done=worker_rows(worker); keys=[r['publication_id'] for r in raw]
    assert len(keys)==len(set(keys)) and set(keys)<=set(task['ids']) and not set(keys)&set(done)
    rows=[]
    for judgment in raw:
        key=judgment['publication_id']; source=inventory[key]; check_judgment(judgment,source)
        meta={'reviewer':'Terra_'+worker+'_resume','model':'gpt-6.1-terra','model_version':'runtime_version_not_exposed','pass_id':a['pass_id'],'worker_id':worker,'codebook_version':'0.2','capability_codebook_version':'0.2','screening_method_version':'0.4.6','prompt_version':'resume-20261112-v1','batch_id':batch,'assessment_stage':'title_abstract','human_verification':'PENDING','screened_at':stamp(),'prior_exposure':'Fixed-pool source-only worker; own sources, saved work and rule reminders may be known; no other-pass judgments or adjudications consulted. Case-specific exposure is disclosed when known.','exposure_metadata_version':'resume-description-v2','report_disposition':'UNASSESSED','review_role':'UNASSESSED','modality_components':'UNASSESSED','identity_issue':'Report/version/family identity unverified','access_status':'title_abstract' if source.get('abstract','').strip() else 'title_only','source_coordinate':key+':'+source.get('abstract_record_id','')+':title/complete_available_abstract/date_tags_json','source_packet_sha256':task['source_packet_sha256'],'inventory_sha256':EXPECTED_HASH,'source_urls':'https://doi.org/'+source['doi'] if source.get('doi') else source.get('url',''),'assessed_sections':'Complete available frozen title, abstract, date tags and source metadata','access_limitation':'Full text not assessed','source_memberships_json':source['source_memberships_json'],'record_ids_json':source['record_ids_json'],'date_tags_json':source.get('date_tags_json','')}
        # Scientific labels come exclusively from the worker's per-record judgment.
        for k in ['modality_components','review_role','uncertainty_note','source_urls','access_limitation','prior_exposure','identity_issue','report_disposition']:
            if k in judgment: meta[k]=judgment[k]
        rows.append(judgment|meta)
    folder=RUN/'workers'/worker/'assessments'; folder.mkdir(exist_ok=True)
    number=1
    while (folder/f'{batch}-chunk{number:04}.csv').exists(): number+=1
    target=folder/f'{batch}-chunk{number:04}.csv'; wr(target,rows,True)
    js(target.with_suffix('.receipt.json'),{'worker':worker,'model':'gpt-6.1-terra','generated_at_utc':stamp(),'ids':keys,'n':len(rows),'file_sha256':sha(target),'source_packet_sha256':task['source_packet_sha256'],'checks':'Assignment, unique IDs, allowed labels, literal supporting excerpt, missing-text routing; classification accuracy is not mechanically established'},True)
    print(json.dumps({'saved':target.as_posix(),'n':len(rows),'worker_total':len(done)+len(rows),'assigned_total':a['assigned_n']}))

def show(worker,batch=None,offset=0,limit=10):
    a=assignment(worker); done=worker_rows(worker)
    candidates=[b for b in a['batches'] if set(b['ids'])-set(done)]
    if batch: candidates=[b for b in candidates if b['batch_id']==batch]
    if not candidates: print(json.dumps({'worker':worker,'complete':len(done),'pending':a['assigned_n']-len(done)})); return
    b=candidates[0]; p=Path(b['source_packet']); assert sha(p)==b['source_packet_sha256']
    candidates=[r for r in rd(p) if r['publication_id'] not in done][offset:offset+limit]
    fields=['publication_id','title','abstract','abstract_record_id','year','year_candidates_json','date_tags_json','doi','dois_json','authors_json','first_author','keywords_json','journal','document_types_json','source_memberships_json','record_ids_json','titles_json','title_conflict','year_conflict','doi_conflict','grouping_status']
    rows=[]; chars=0
    for raw in candidates:
        r={k:raw.get(k,'') for k in fields};size=len(json.dumps(r,ensure_ascii=False))
        if rows and chars+size>22000:break
        rows.append(r);chars+=size
    print(json.dumps({'worker':worker,'batch':b['batch_id'],'priority':b['priority'],'worker_saved':len(done),'worker_pending':a['assigned_n']-len(done),'records_shown':len(rows),'display_note':'Complete selected source fields and abstracts; number of whole records is reduced for long sources, never text-truncated. Remaining source fields preserved in own source packet.','records':rows},ensure_ascii=False,indent=2))
    js(RUN/'workers'/worker/'progress.json',{'worker':worker,'generated_at_utc':stamp(),'saved_n':len(done),'pending_n':a['assigned_n']-len(done),'current_batch':b['batch_id'],'state':'in-progress','in_progress_ids':[r['publication_id'] for r in rows],'source_packet_sha256':b['source_packet_sha256']})

def show_audit(batch,offset=0,limit=10):
    folder=RUN/'paired'/batch
    source={r['publication_id']:r for r in rd(folder/'source.csv')}
    a={r['publication_id']:r for r in rd(folder/'pass-A.csv')};b={r['publication_id']:r for r in rd(folder/'pass-B.csv')}
    sample=json.loads((folder/'audit-selection.json').read_text(encoding='utf-8'))['sample_ids']
    keys=[i for i in source if a[i]['eligibility']==b[i]['eligibility']=='INCLUDE' or i in sample]
    rows=[]
    for i in keys[offset:offset+limit]:
        raw=source[i]
        rows.append({k:raw.get(k,'') for k in ['publication_id','title','abstract','abstract_record_id','year','year_candidates_json','date_tags_json','doi','journal','document_types_json']}|{'routine_selection':'fixed_exclusion_sample' if i in sample else 'agreed_inclusion','initial_A_eligibility':a[i]['eligibility'],'initial_B_eligibility':b[i]['eligibility'],'initial_A_modality':a[i].get('modality_stream',''),'initial_B_modality':b[i].get('modality_stream','')})
    print(json.dumps({'batch':batch,'routine_n':len(keys),'offset':offset,'n_shown':len(rows),'source_sha256':sha(folder/'source.csv'),'sample_ids':sample,'records':rows},ensure_ascii=False,indent=2))

def refresh():
    inventory=inv(); ledgers,hashes=legacy()
    baseline=json.loads((RUN/'legacy-adapter-reconciliation.json').read_text(encoding='utf-8'))
    assert all(hashes.get(p)==h for p,h in baseline['input_hashes'].items()),'LEGACY_ORIGINAL_DRIFT'
    assert set(hashes)-set(baseline['input_hashes']) <= {(ROOT/'sol/B0001-before-metadata-correction.csv').as_posix()},'UNREGISTERED_LEGACY_SOURCE'
    tasks=rd(RUN/'task-manifest.csv'); taskmap={(r['pass_id'],r['publication_id']):r for r in tasks}
    assert len(tasks)==len(taskmap)==32172,'INITIAL_TASK_MANIFEST_DUPLICATE_OR_COUNT_DRIFT'
    for pas in 'AB':assert {key for p,key in taskmap if p==pas}==set(inventory)-set(ledgers[pas]),('INITIAL_TASK_MANIFEST_SCOPE_DRIFT',pas)
    for worker in WORKERS:
        a=assignment(worker)
        assigned=[r for r in tasks if r['owner']==worker]
        expected={key for b in a['batches'] for key in b['ids']}
        assert a['worker']==worker and a['pass_id']==worker[0] and a['model']=='gpt-6.1-terra'
        assert len(assigned)==len(expected)==a['assigned_n'] and {r['publication_id'] for r in assigned}==expected
        batches={b['batch_id']:b for b in a['batches']}
        for task in assigned:
            b=batches[task['batch_id']]
            assert task['pass_id']==worker[0] and task['model']=='gpt-6.1-terra' and task['inventory_sha256']==EXPECTED_HASH
            assert task['source_packet']==b['source_packet'] and task['source_packet_sha256']==b['source_packet_sha256']
        progress=RUN/'workers'/worker/'progress.json'
        if progress.exists():
            for key in json.loads(progress.read_text(encoding='utf-8')).get('in_progress_ids',[]):
                taskmap[(a['pass_id'],key)]['state']='in-progress'
        for key,r in worker_rows(worker).items():
            t=taskmap[(a['pass_id'],key)]; assert t['owner']==worker
            assert r['batch_id']==t['batch_id'] and r['source_packet_sha256']==t['source_packet_sha256']
            assert key not in ledgers[a['pass_id']], ('EXISTING_INITIAL_OVERWRITE',worker,key)
            assert r['model']=='gpt-6.1-terra' and r['reviewer']=='Terra_'+worker+'_resume'
            for k in ['source_memberships_json','record_ids_json']: assert json.loads(r[k])==json.loads(inventory[key][k])
            check_judgment(r,inventory[key]); ledgers[a['pass_id']][key]=r; t['state']='validated'
    canonical=RUN/'canonical'; canonical.mkdir(exist_ok=True)
    for pas in 'AB':
        exported=[]
        for key in sorted(ledgers[pas]):
            row=ledgers[pas][key].copy()
            for field in ['source_memberships_json','record_ids_json']:
                if row.get(field):assert json.loads(row[field])==json.loads(inventory[key][field]),('LEGACY_MEMBERSHIP_CONFLICT',pas,key,field)
                else:
                    row[field]=inventory[key][field]
                    row['administrative_membership_join']='Frozen inventory by stable publication_id; original artifact remains unchanged and separately hashed.'
            exported.append(row)
        wr(canonical/f'pass-{pas}-original-initials.csv',exported)
    wr(canonical/'task-status-current.csv',tasks)
    A=set(ledgers['A']); B=set(ledgers['B']); universe=set(inventory); common=A&B
    counts={'generated_at_utc':stamp(),'inventory_n':len(universe),'pass_A_saved':len(A),'pass_A_pending':len(universe-A),'pass_B_saved':len(B),'pass_B_pending':len(universe-B),'both_initial_passes':len(common),'at_least_one_initial_pass':len(A|B),'neither_initial_pass':len(universe-(A|B)),'initial_assessments_remaining':len(universe-A)+len(universe-B),'new_validated_assessments':sum(t['state']=='validated' for t in tasks),'by_worker':{w:sum(t['owner']==w and t['state']=='validated' for t in tasks) for w in WORKERS},'human_verified':0,'human_pending':18976,'validation_errors':[],'scope':'Initial AI assessments saved, not resolved eligibility, full-text assessment, independent-study totals or human verification'}
    counts['priority_status']={phase:dict(Counter(t['state'] for t in tasks if t['priority']==phase)) for phase in ['missing_partner','both_missing']}
    ready=[]; paired=RUN/'paired'; paired.mkdir(exist_ok=True)
    registry=json.loads((ROOT/'astra/current-artifacts.json').read_text(encoding='utf-8'))
    for b in idx():
        if not set(b['ids'])<=common: continue
        bid=b['batch_id']; folder=paired/bid; folder.mkdir(exist_ok=True)
        for pas in 'AB': wr(folder/f'pass-{pas}.csv',[ledgers[pas][i] for i in b['ids']])
        wr(folder/'source.csv',[inventory[i] for i in b['ids']])
        excluded=[i for i in b['ids'] if all(ledgers[p][i]['eligibility']=='EXCLUDE' for p in 'AB')]
        sample=sorted(excluded,key=lambda i:hashlib.sha256(('MedicalXR-20261111-v03:'+i).encode()).hexdigest())[:min(len(excluded),max(10,math.ceil(.1*len(excluded))))]
        obligations=[]
        for key in b['ids']:
            x,y=ledgers['A'][key],ledgers['B'][key]; reasons=[]
            for field in ['eligibility','evidence_stream','modality_stream','evidence_type']:
                if x.get(field,'').casefold()!=y.get(field,'').casefold(): reasons.append(field+'_difference')
            if any(r['eligibility']=='UNCERTAIN' or r.get('modality_stream','').casefold()=='uncertain' or r.get('evidence_stream')=='uncertain' for r in [x,y]): reasons.append('any_uncertainty')
            if x['eligibility']==y['eligibility']=='INCLUDE': reasons.append('agreed_inclusion')
            if key in sample: reasons.append('fixed_agreed_exclusion_sample')
            if any(r.get('reviewer','').startswith('Coordinator') for r in [x,y]): reasons.append('legacy_coordinator_independent_audit')
            if reasons: obligations.append({'publication_id':key,'audit_reasons':';'.join(reasons)})
        wr(folder/'required-audit.csv',obligations)
        js(folder/'audit-selection.json',{'batch_id':bid,'batch_n':len(b['ids']),'agreed_exclusion_ids':excluded,'sample_ids':sample,'seed':'MedicalXR-20261111-v03','sampling_rule':'lowest SHA256(seed+":"+id), min(n,max(10,ceil(.1*n)))','required_unique_ids':len(obligations),'source_sha256':sha(folder/'source.csv'),'pass_A_sha256':sha(folder/'pass-A.csv'),'pass_B_sha256':sha(folder/'pass-B.csv')})
        ready.append({'batch_id':bid,'n':len(b['ids']),'legacy_adjudication':registry.get(bid,{}).get('adjudication',''),'packet':folder.as_posix(),'required_audit_n':len(obligations)})
    wr(canonical/'paired-batch-queue.csv',ready); js(canonical/'current-counts.json',counts)
    print(json.dumps(counts))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('command',choices=['init','show','show-audit','submit','refresh']);p.add_argument('--worker',choices=WORKERS);p.add_argument('--batch');p.add_argument('--input');p.add_argument('--offset',type=int,default=0);p.add_argument('--limit',type=int,default=10);a=p.parse_args()
    if a.command=='init':init()
    elif a.command=='refresh':refresh()
    elif a.command=='submit':submit(a.worker,a.batch,a.input)
    elif a.command=='show-audit':show_audit(a.batch,a.offset,a.limit)
    else:show(a.worker,a.batch,a.offset,a.limit)
