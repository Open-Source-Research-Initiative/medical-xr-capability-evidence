"""Locate date-rule application audit candidates; never classify a publication."""
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path
import resume_screening as s

p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);a=p.parse_args()
assert re.fullmatch(r'[A-Za-z0-9_-]+',a.snapshot)
inventory=s.inv();initial={};inputs={}
for pas in 'AB':
    path=s.RUN/'canonical'/f'pass-{pas}-original-initials.csv';inputs[path.as_posix()]=s.sha(path)
    initial[pas]={r['publication_id']:r for r in s.rd(path)}
flagged=defaultdict(set);deferred=[]
for worker in s.WORKERS:
    folder=s.RUN/'workers'/worker
    flags=set(folder.glob('self-*date*flag*.json'))|set(folder.glob('self-audit-date-rule-*.json'))
    for path in sorted(flags):
        raw=path.read_text(encoding='utf-8-sig');json.loads(raw);inputs[path.as_posix()]=s.sha(path)
        for key in sorted(set(re.findall(r'P\d{7}',raw))):
            row=initial[worker[0]].get(key)
            if row and row.get('worker_id')==worker:flagged[(worker[0],key)].add(path.as_posix())
            elif not row:deferred.append({'worker':worker,'publication_id':key,'flag_file':path.as_posix(),'status':'NOT_IN_CURRENT_CANONICAL_INITIAL_SNAPSHOT_RECONCILE_NEXT_SWEEP'})
upper=re.compile(r'(?:\b2020\b.{0,6}\b2025\b|\b2025\b.{0,35}\b(?:upper|end|cutoff)\b|\b(?:upper|end|cutoff)\b.{0,35}\b2025\b|\b(?:outside|beyond|after)\b.{0,50}\bfrozen\b)',re.I)
candidates=[];legacy=[]
for pas,rows in initial.items():
    for key,row in rows.items():
        source=inventory[key];years=[source.get('year',''),*json.loads(source.get('year_candidates_json') or '[]')]
        high=any(str(value).isdigit() and int(value)>=2026 for value in years)
        text=' '.join(row.get(field,'') for field in ['rationale','date_status','uncertainty_note'])
        reasons=[]
        if row.get('reason_code')=='DATE' and high:reasons.append('DATE_REASON_WITH_2026_OR_LATER_ISSUE_METADATA')
        if high and re.search(r'OUT_OF_(?:WINDOW|RANGE)|OUTSIDE',row.get('date_status',''),re.I):reasons.append('HIGH_YEAR_OUTSIDE_DATE_STATUS')
        if upper.search(text) and (high or re.search(r'202[567]',text)):reasons.append('UPPER_PERIOD_WORDING_LOCATOR')
        if (pas,key) in flagged:reasons.append('OWN_WORKER_SCOPE_FLAG')
        if not reasons:continue
        item={'pass_id':pas,'publication_id':key,'worker':row.get('worker_id',''),'locator_reasons_json':json.dumps(reasons),'own_flag_files_json':json.dumps(sorted(flagged.get((pas,key),set()))),'original_eligibility':row['eligibility'],'original_reason':row.get('reason_code',''),'original_rationale_verbatim':row.get('rationale',''),'original_date_status_verbatim':row.get('date_status',''),'initial_artifact':row['initial_artifact'],'initial_artifact_sha256':row['initial_artifact_sha256'],'status':'LOCATOR_ONLY_PERSONAL_SOURCE_RECHECK_REQUIRED','not_a_classification':True}
        (candidates if row.get('worker_id') else legacy).append(item)
folder=s.RUN/'date-window-audit'/a.snapshot;folder.mkdir(parents=True,exist_ok=False)
s.wr(folder/'candidates.csv',candidates,exclusive=True)
s.wr(folder/'source-only.csv',[inventory[key] for key in sorted({r['publication_id'] for r in candidates})],exclusive=True)
s.wr(folder/'legacy-unassigned-candidates.csv',legacy,exclusive=True)
s.wr(folder/'deferred-flags.csv',deferred,exclusive=True)
packets={}
for worker in s.WORKERS:
    ids=[r['publication_id'] for r in candidates if r['worker']==worker]
    if not ids:continue
    own=s.RUN/'workers'/worker/'date-window-audit'/a.snapshot;packet=own/'source-only.csv'
    s.wr(packet,[inventory[key] for key in ids],exclusive=True)
    info={'worker':worker,'pass_id':worker[0],'model':'gpt-6.1-terra','stage':'PROMPTED_RULE_SOURCE_RECHECK_NOT_INITIAL','candidate_ids':ids,'source_packet':packet.as_posix(),'source_packet_sha256':s.sha(packet),'instruction':'Individually reread every full available source under existing rule7. Inventory/run12Nov2026, no2025 upper cutoff; frozen fixesIDs. Normal2025DOI/2026issue alone is not a date conflict. Reassess actual medical/task/technology/type evidence without a prescribed label. Preserve originals and source limitations. Save own model/worker-qualified prompted-date-recheck JSON with each ID, exact source quote, actual extent, outcome/rationale and date/status limits. Previously performed post-clarification own-source rechecks can supply the exact-ID coverage; do not repeat them merely to change format. No other-pass judgments or prior labels are supplied in this packet.'}
    s.js(own/'assignment.json',info,exclusive=True);packets[worker]={'n':len(ids),'file':packet.as_posix(),'sha256':s.sha(packet)}
s.js(folder/'receipt.json',{'generated_at_utc':s.stamp(),'inventory_sha256':s.EXPECTED_HASH,'input_snapshot_sha256':inputs,'candidate_pass_id_n':len(candidates),'candidate_publication_id_n':len({r['publication_id'] for r in candidates}),'by_worker':dict(Counter(r['worker'] for r in candidates)),'legacy_unassigned_n':len(legacy),'deferred_flag_n':len(deferred),'candidates_sha256':s.sha(folder/'candidates.csv'),'source_packet_sha256':s.sha(folder/'source-only.csv'),'source_only_worker_packets':packets,'scope':'Text/metadata/own-flag locator for erroneous upper-year window application; no classifications generated. Original judgments/metrics remain unchanged. Repeat after all initials and personally assess every candidate; preserve legitimate source-limited/unchanged outcomes.','limits':'High-recall locator, not exhaustive semantic detection or proof each candidate is an error. Legacy unassigned/deferred cases must be explicitly accounted for before closure.','classification_count_generated_by_script':0},exclusive=True)
print(json.dumps({'snapshot':a.snapshot,'candidate_pass_ids':len(candidates),'candidate_publication_ids':len({r['publication_id'] for r in candidates}),'by_worker':dict(Counter(r['worker'] for r in candidates)),'legacy_unassigned':len(legacy),'deferred_flags':len(deferred),'classification_count_generated':0}))
