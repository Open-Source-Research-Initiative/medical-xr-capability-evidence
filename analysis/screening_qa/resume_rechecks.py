"""Source-only legacy followups for the existing fixed pools; never an initial pass.

Mechanical dispatch/quote/provenance checks only. Workers must author all source
judgments. Current adjudication and original agreement are not changed here.
"""
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
import resume_screening as s

MANIFEST=s.RUN/'legacy-recheck-task-manifest.csv'
DATE_FIELDS=['date_check_status','date_source','date_basis','journal_first_publication_date','date_boundary_status']

def init():
    assert not MANIFEST.exists(),'LEGACY_RECHECK_SCOPE_ALREADY_FROZEN'
    inventory=s.inv();legacy,_=s.legacy();obligations=defaultdict(set);inputs={}
    path=s.RUN/'canonical/legacy-retrospective-pending.csv';inputs[path.as_posix()]=s.sha(path)
    for row in s.rd(path):obligations[(row['pass_id'],row['publication_id'])].add(row['obligation'])
    path=s.RUN/'canonical/legacy-targeted-recheck-status.csv';inputs[path.as_posix()]=s.sha(path)
    for row in s.rd(path):
        for pas,who in [('A','sol'),('B','terra')]:
            if row[who+'_recheck_status']!='COMPLETE':obligations[(pas,row['publication_id'])].add('legacy_targeted_source_followup')
    path=s.RUN/'canonical/independent-2020-date-obligations.csv';inputs[path.as_posix()]=s.sha(path)
    for row in s.rd(path):
        if row['publication_id'] in legacy[row['pass_id']] and row['date_check_status'].startswith('PENDING'):
            obligations[(row['pass_id'],row['publication_id'])].add('independent_2020_date')
    for key in ['P0001624','P0001655','P0001641','P0001643']:obligations[('A',key)].add('legacy_B0033_focused_followup')
    batch_by_id={key:b['batch_id'] for b in s.idx() for key in b['ids']}
    loads=Counter({w:0 for w in s.WORKERS});tasks=[];byworker=defaultdict(list)
    for (pas,key),kinds in sorted(obligations.items()):
        assert key in inventory and key in legacy[pas]
        worker=min((w for w in s.WORKERS if w.startswith(pas)),key=lambda w:(loads[w],w));loads[worker]+=1
        row={'pass_id':pas,'publication_id':key,'owner':worker,'batch_id':batch_by_id.get(key,'CALIBRATION'),'obligations_json':json.dumps(sorted(kinds)),'state':'assigned','assessment_stage':'prompted_source_recheck_not_initial','model':'gpt-6.1-terra','screening_method_version':'0.4.6','prompt_version':'resume-legacy-rechecks-20261112-v1','inventory_sha256':s.EXPECTED_HASH}
        tasks.append(row);byworker[worker].append(row)
    for worker,items in byworker.items():
        folder=s.RUN/'workers'/worker/'legacy-rechecks';packet=folder/'source-only.csv'
        s.wr(packet,[inventory[x['publication_id']] for x in items],exclusive=True);digest=s.sha(packet)
        for row in items:row.update(source_packet=packet.as_posix(),source_packet_sha256=digest)
        # No original decisions, other-pass fields, adjudications or case proposals.
        s.js(folder/'assignment.json',{'worker':worker,'pass_id':worker[0],'assigned_n':len(items),'source_packet':packet.as_posix(),'source_packet_sha256':digest,'tasks':items,'instruction':'Start only after own initial assignment is complete. Read every complete available source and relevant metadata. Reassess current fields from source under rule-only0.4.6; record genuine uncertainty. Independent date tasks require an own publisher/index check or documented source-limited attempt. These are new attributed source rechecks, not historical-reviewer completion or new initial judgments. Other-pass and adjudication decisions remain hidden.'},exclusive=True)
    s.wr(MANIFEST,tasks,exclusive=True)
    s.js(s.RUN/'legacy-recheck-dispatch-receipt.json',{'generated_at_utc':s.stamp(),'task_n':len(tasks),'obligation_n':sum(len(json.loads(x['obligations_json'])) for x in tasks),'by_worker':dict(loads),'manifest_sha256':s.sha(MANIFEST),'source_scope_inputs':inputs,'scope':'Frozen legacy pending source obligations only, plus explicit B0033 four. Later new-worker date gaps require separate accounting. All eight existing workers keep fixed pool membership; no new agents.'},exclusive=True)
    print(json.dumps({'legacy_recheck_tasks':len(tasks),'by_worker':dict(loads)}))

def scope_folder(worker,scope=None):
    folder=s.RUN/'workers'/worker/'legacy-rechecks'
    if scope:
        assert scope.replace('-','').replace('_','').isalnum()
        folder=folder/'supplements'/scope
    return folder

def effective_tasks(rows):
    rows=[row.copy() for row in rows];bykey={(row['pass_id'],row['publication_id']):row for row in rows}
    for path in sorted(s.RUN.glob('legacy-recheck-obligation-addendum-*.json')):
        addendum=json.loads(path.read_text(encoding='utf-8'))
        assert addendum['inventory_sha256']==s.EXPECTED_HASH and addendum['base_manifest_sha256']==s.sha(MANIFEST)
        base={(row['pass_id'],row['publication_id']):row for row in s.rd(MANIFEST)}
        for name,digest in addendum['source_inputs'].items():assert s.sha(Path(name))==digest,('OBLIGATION_ADDENDUM_SOURCE_DRIFT',name)
        assert len(addendum['entries'])==len({(row['pass_id'],row['publication_id']) for row in addendum['entries']})
        for item in addendum['entries']:
            key=(item['pass_id'],item['publication_id']);assert key in base and item['owner']==base[key]['owner']
            added=item['added_obligations'];assert added==['independent_2020_date'] and not set(added)&set(json.loads(base[key]['obligations_json']))
            if key not in bykey:continue
            row=bykey[key];assert row['owner']==item['owner']
            row['obligations_json']=json.dumps(sorted(set(json.loads(row['obligations_json']))|set(added)))
            files=json.loads(row.get('obligation_addendum_files_json','[]'));files.append({'file':path.as_posix(),'sha256':s.sha(path)});row['obligation_addendum_files_json']=json.dumps(files)
    return rows

def assignment(worker,scope=None,effective=True):
    info=json.loads((scope_folder(worker,scope)/'assignment.json').read_text(encoding='utf-8'))
    if effective:info['tasks']=effective_tasks(info['tasks'])
    return info

def check_date(row):
    assert all(str(row.get(k,'')).strip() for k in DATE_FIELDS if k!='date_source'),('DATE_RECHECK_FIELDS_REQUIRED',row.get('publication_id'))
    assert row['date_check_status'] in {'CHECKED_VERIFIED','CHECKED_UNRESOLVED','CHECKED_INDEXED_PRIMARY','CHECKED_SOURCE_LIMITED'}
    assert row.get('date_source') or row['date_check_status'] in {'CHECKED_UNRESOLVED','CHECKED_SOURCE_LIMITED'},('VERIFIED_DATE_SOURCE_REQUIRED',row.get('publication_id'))

def supplements():
    return sorted(s.RUN.glob('legacy-recheck-supplement-*-receipt.json'))

def validate_supplement(path):
    receipt=json.loads(path.read_text(encoding='utf-8'));scope=receipt['scope_id']
    assert receipt['inventory_sha256']==s.EXPECTED_HASH and receipt['model']=='gpt-6.1-terra'
    manifest=Path(receipt['manifest']);assert s.sha(manifest)==receipt['manifest_sha256']
    tasks=s.rd(manifest);bykey={(row['pass_id'],row['publication_id']):row for row in tasks};assert len(tasks)==len(bykey)==receipt['task_n']
    for name,digest in receipt['source_inputs'].items():assert s.sha(Path(name))==digest,('SUPPLEMENT_SOURCE_INPUT_DRIFT',name)
    seen=set()
    for worker,n in receipt['by_worker'].items():
        info=assignment(worker,scope,effective=False);assert info['worker']==worker and info['pass_id']==worker[0] and info['assigned_n']==n
        packet=Path(info['source_packet']);assert s.sha(packet)==info['source_packet_sha256']
        rows=s.rd(packet);assert len(rows)==len({row['publication_id'] for row in rows})==n
        assert not {'eligibility','reason_code','rationale','modality_stream','evidence_stream','adjudicated_eligibility'}&set(rows[0])
        assert {row['publication_id'] for row in rows}=={row['publication_id'] for row in info['tasks']}
        for task in info['tasks']:
            key=(task['pass_id'],task['publication_id']);assert key not in seen and task['owner']==worker and task['pass_id']==worker[0]
            assert all(str(task.get(k,''))==str(v) for k,v in bykey[key].items())
            seen.add(key)
    assert seen==set(bykey)
    return tasks

def task_rows():
    rows=s.rd(MANIFEST)
    for path in supplements():rows.extend(validate_supplement(path))
    assert len(rows)==len({(r['pass_id'],r['publication_id']) for r in rows}),'DUPLICATE_BASE_OR_SUPPLEMENT_RECHECK_TASK'
    return effective_tasks(rows)

def validate_dispatch():
    receipt=json.loads((s.RUN/'legacy-recheck-dispatch-receipt.json').read_text(encoding='utf-8'))
    assert s.sha(MANIFEST)==receipt['manifest_sha256'],'RECHECK_TASK_MANIFEST_DRIFT'
    tasks=s.rd(MANIFEST);bykey={(x['pass_id'],x['publication_id']):x for x in tasks}
    assert len(tasks)==len(bykey)==receipt['task_n']
    seen=set();obligation_counts=Counter()
    forbidden={'eligibility','reason_code','rationale','modality_stream','evidence_stream','adjudicated_eligibility','initial_A_eligibility','initial_B_eligibility'}
    for worker in s.WORKERS:
        info=assignment(worker,effective=False);assert info['worker']==worker and info['pass_id']==worker[0] and info['assigned_n']==receipt['by_worker'][worker]
        packet=Path(info['source_packet']);assert s.sha(packet)==info['source_packet_sha256']
        source=s.rd(packet);assert len(source)==len({x['publication_id'] for x in source})==info['assigned_n']
        assert not forbidden&set(source[0]),'DECISION_FIELDS_IN_RECHECK_SOURCE_PACKET'
        assert {x['publication_id'] for x in source}=={x['publication_id'] for x in info['tasks']}
        for task in info['tasks']:
            key=(task['pass_id'],task['publication_id']);assert key not in seen and task['owner']==worker and task['pass_id']==worker[0]
            assert all(str(task.get(k,''))==str(value) for k,value in bykey[key].items()),('RECHECK_ASSIGNMENT_MANIFEST_MISMATCH',key)
            seen.add(key);obligation_counts.update(json.loads(task['obligations_json']))
    assert seen==set(bykey) and sum(obligation_counts.values())==receipt['obligation_n']
    snapshot=json.loads((s.RUN/'legacy-recheck-scope-snapshot-receipt.json').read_text(encoding='utf-8'))
    assert snapshot['dispatch_receipt_sha256']==s.sha(s.RUN/'legacy-recheck-dispatch-receipt.json')
    for row in snapshot['source_snapshots']:assert s.sha(Path(row['immutable_snapshot']))==row['sha256']
    return {'tasks':len(tasks),'obligations':dict(obligation_counts),'unique_stage_pass_id':True,'source_only_no_decision_fields':True,'fixed_pool_ownership':True,'source_and_manifest_hashes_match':True,'immutable_scope_snapshots_match':True}

def saved(worker,scope=None):
    info=assignment(worker,scope);packet=Path(info['source_packet']);assert s.sha(packet)==info['source_packet_sha256']
    source={x['publication_id']:x for x in s.rd(packet)};tasks={x['publication_id']:x for x in info['tasks']};result={}
    for path in sorted((packet.parent/'assessments').glob('*.csv')):
        receipt=path.with_suffix('.receipt.json');r=json.loads(receipt.read_text(encoding='utf-8'))
        assert r['worker']==worker and r['model']=='gpt-6.1-terra' and r['assessment_stage']=='prompted_source_recheck_not_initial'
        assert r['inventory_sha256']==s.EXPECTED_HASH
        assert r['output_sha256']==s.sha(path) and r['source_packet_sha256']==info['source_packet_sha256']
        draft=Path(r['draft_file']);assert s.sha(draft)==r['draft_sha256'],('RECHECK_DRAFT_INPUT_DRIFT',draft.as_posix())
        rows=s.rd(path);assert len(rows)==r['n'] and {x['publication_id'] for x in rows}==set(r['ids'])
        for row in rows:
            key=row['publication_id'];assert key in tasks and key not in result
            s.check_judgment(row,source[key])
            assert row['worker_id']==worker and row['pass_id']==worker[0] and row['model']=='gpt-6.1-terra' and row['assessment_stage']=='prompted_source_recheck_not_initial' and row['human_verification']=='PENDING'
            assert row['inventory_sha256']==s.EXPECTED_HASH and row['screening_method_version']=='0.4.6'
            assert row['source_packet_sha256']==info['source_packet_sha256'] and json.loads(row['obligations_json'])==json.loads(tasks[key]['obligations_json'])
            for field in ['source_memberships_json','record_ids_json']:assert json.loads(row[field])==json.loads(source[key][field])
            if 'independent_2020_date' in json.loads(tasks[key]['obligations_json']):
                check_date(row)
            result[key]=row|{'recheck_artifact':path.as_posix(),'recheck_artifact_sha256':r['output_sha256'],'recheck_receipt':receipt.as_posix()}
    return result

def show(worker,limit,scope=None):
    info=assignment(worker,scope);done=saved(worker,scope);source={x['publication_id']:x for x in s.rd(Path(info['source_packet']))};rows=[];budget=0
    for task in info['tasks']:
        if task['publication_id'] in done:continue
        row=source[task['publication_id']]|{'recheck_obligations':json.loads(task['obligations_json'])};length=len(json.dumps(row,ensure_ascii=False))
        if rows and (len(rows)>=limit or budget+length>22000):break
        rows.append(row);budget+=length
    print(json.dumps({'worker':worker,'stage':'prompted_source_recheck_not_initial','saved':len(done),'pending':info['assigned_n']-len(done),'records':rows},ensure_ascii=False,indent=2))

def submit(worker,file,scope=None):
    info=assignment(worker,scope);done=saved(worker,scope);tasks={x['publication_id']:x for x in info['tasks']};source={x['publication_id']:x for x in s.rd(Path(info['source_packet']))};draft=Path(file);rows=json.loads(draft.read_text(encoding='utf-8-sig'));assert isinstance(rows,list) and rows
    seen=set();now=s.stamp()
    for row in rows:
        key=row['publication_id'];assert key in tasks and key not in done and key not in seen;seen.add(key);s.check_judgment(row,source[key])
        if 'independent_2020_date' in json.loads(tasks[key]['obligations_json']):
            check_date(row)
        row.update(worker_id=worker,pass_id=worker[0],reviewer='Terra_'+worker+'_resume_source_recheck',model='gpt-6.1-terra',model_version='runtime_version_not_exposed',assessment_stage='prompted_source_recheck_not_initial',human_verification='PENDING',screening_method_version='0.4.6',capability_codebook_version='0.2',prompt_version='resume-legacy-rechecks-20261112-v1',source_packet_sha256=info['source_packet_sha256'],inventory_sha256=s.EXPECTED_HASH,obligations_json=tasks[key]['obligations_json'],screened_at=now,prior_exposure='Own fixed-pool work and source-only recheck packet; other-pass decisions and adjudications hidden',source_memberships_json=source[key]['source_memberships_json'],record_ids_json=source[key]['record_ids_json'],source_coordinate=key+':'+source[key].get('abstract_record_id','')+':title/complete_available_abstract/date_tags_json')
    folder=scope_folder(worker,scope)/'assessments';folder.mkdir(parents=True,exist_ok=True);dest=folder/f'chunk{len(list(folder.glob("*.csv")))+1:04d}.csv'
    input_snapshot=dest.with_suffix('.input.json')
    with input_snapshot.open('xb') as output:output.write(draft.read_bytes())
    s.wr(dest,rows,exclusive=True)
    s.js(dest.with_suffix('.receipt.json'),{'worker':worker,'model':'gpt-6.1-terra','assessment_stage':'prompted_source_recheck_not_initial','inventory_sha256':s.EXPECTED_HASH,'output_sha256':s.sha(dest),'source_packet_sha256':info['source_packet_sha256'],'draft_file':input_snapshot.as_posix(),'draft_sha256':s.sha(input_snapshot),'submitted_draft_file':draft.as_posix(),'draft_preservation':'Exact immutable byte snapshot at submission; the original working draft path need not remain unchanged.','n':len(rows),'ids':sorted(seen),'generated_at_utc':now,'scope':'Schema, own assignment, literal quotes and provenance validated mechanically; human verification remains pending.'},exclusive=True)
    print(json.dumps({'saved_rechecks':len(rows),'worker':worker,'total':len(done)+len(rows),'pending':info['assigned_n']-len(done)-len(rows)}))

def all_saved():
    if not MANIFEST.exists():return {}
    validate_dispatch()
    result={(worker[0],key):row for worker in s.WORKERS for key,row in saved(worker).items()}
    for path in supplements():
        validate_supplement(path);receipt=json.loads(path.read_text(encoding='utf-8'))
        for worker in receipt['by_worker']:
            for key,row in saved(worker,receipt['scope_id']).items():
                pair=(worker[0],key);assert pair not in result;result[pair]=row
    return result

def freeze_scope_snapshot():
    receipt=s.RUN/'legacy-recheck-dispatch-receipt.json';scope=json.loads(receipt.read_text(encoding='utf-8'));rows=[]
    folder=s.RUN/'admin/legacy-recheck-scope-snapshot';folder.mkdir(parents=True,exist_ok=True)
    for name,digest in scope['source_scope_inputs'].items():
        source=Path(name);assert s.sha(source)==digest,('SCOPE_SOURCE_CHANGED_BEFORE_SNAPSHOT',name)
        target=folder/source.name
        if not target.exists():
            with target.open('xb') as f:f.write(source.read_bytes())
        assert s.sha(target)==digest
        rows.append({'source_at_dispatch':name,'immutable_snapshot':target.as_posix(),'sha256':digest})
    s.js(s.RUN/'legacy-recheck-scope-snapshot-receipt.json',{'generated_at_utc':s.stamp(),'dispatch_receipt_sha256':s.sha(receipt),'task_manifest_sha256':s.sha(MANIFEST),'source_snapshots':rows,'scope':'Exact byte snapshots of dispatch-time derived ledgers; current canonical paths will later refresh. Original dispatch receipt preserved.'},exclusive=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['init','show','submit','snapshot','validate']);p.add_argument('--worker',choices=s.WORKERS);p.add_argument('--limit',type=int,default=5);p.add_argument('--input');p.add_argument('--scope');args=p.parse_args()
    if args.command=='init':init()
    elif args.command=='snapshot':freeze_scope_snapshot()
    elif args.command=='validate':
        tasks=task_rows();print(json.dumps(validate_dispatch()|{'combined_base_and_supplement_tasks':len(tasks),'effective_obligations':sum(len(json.loads(row['obligations_json'])) for row in tasks),'independent_date_tasks':sum('independent_2020_date' in json.loads(row['obligations_json']) for row in tasks)}))
    elif args.command=='show':show(args.worker,args.limit,args.scope)
    else:submit(args.worker,args.input,args.scope)
