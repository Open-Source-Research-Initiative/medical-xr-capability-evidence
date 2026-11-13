"""Locate and account for an earlier rule-application audit; never classify reports."""
import argparse, json, re
from collections import Counter
from pathlib import Path
import resume_screening as s
import publish_resume_review as p

cli=argparse.ArgumentParser();cli.add_argument('command',choices=['prepare','status','close']);cli.add_argument('--snapshot',required=True);cli.add_argument('--kind',choices=['observation','technology-exclusion','date-route'],default='observation');args=cli.parse_args()
assert re.fullmatch(r'[A-Za-z0-9_-]+',args.snapshot)
technology=args.kind=='technology-exclusion'
date_route=args.kind=='date-route'
folder=s.RUN/({'observation':'observation-gate-audit','technology-exclusion':'technology-exclusion-audit','date-route':'date-route-audit'}[args.kind])/args.snapshot
obligation_id={'observation':'earlier-adjudication-observational-evidence-gate-application-review','technology-exclusion':'earlier-technology-exclusion-application-review','date-route':'earlier-non2020-date-route-application-review'}[args.kind]

if args.command=='prepare':
    patterns=[r'\b(?:no|without|lack\w*|not|absence of)\b.{0,55}\b(?:implemented|delivered|firsthand)\b.{0,45}\b(?:application\w*|exposure|intervention\w*|treatment|evaluation|cohort|deployment|observations?)\b',r'\bno\s+(?:(?:actual|observed)\s+)?(?:intervention|treatment)\s+(?:delivered|outcomes?|results?|findings?)\b',r'\b(?:no|without|not|lack\w*)\b.{0,40}\bsystematic\b.{0,30}\b(?:outcome\w*|evaluat\w*|observations?)\b',r'\bfirsthand implemented\b']
    regex=re.compile('|'.join(patterns),re.I);can=s.RUN/'canonical';rows=s.rd(can/'adjudicated-current.csv');inventory=s.inv();candidates=[]
    for row in rows:
        batch=row.get('batch_id','')
        if date_route:
            if row['eligibility'] not in {'EXCLUDE','UNCERTAIN'} or row.get('reason_code','').upper()!='DATE' or not row.get('year','').isdigit() or int(row['year'])<2021:continue
            hits=[]
        elif technology:
            if row['eligibility']!='EXCLUDE' or row.get('reason_code','').upper()!='TECHNOLOGY':continue
            hits=[]
        else:
            earlier=batch.casefold()=='calibration' or (re.fullmatch(r'B\d{4}',batch) and (int(batch[1:])<=129 or int(batch[1:])>=378))
            if not earlier or row['eligibility'] not in {'EXCLUDE','UNCERTAIN'} or row.get('evidence_stream')=='empirical':continue
            hits=[m.group() for m in regex.finditer(row.get('rationale',''))]
        if technology or date_route or hits:candidates.append({'publication_id':row['publication_id'],'batch_id':batch,'matched_wording_json':json.dumps(hits),'locator_basis':'Every recorded current EXCLUDE/TECHNOLOGY in the frozen source snapshot' if technology else 'Potential negative observational-evidence wording','current_eligibility_at_dispatch':row['eligibility'],'current_reason_at_dispatch':row.get('reason_code',''),'current_stream_at_dispatch':row.get('evidence_stream',''),'current_type_at_dispatch':row.get('evidence_type',''),'current_rationale_at_dispatch':row['rationale'],'current_base_artifact':row['adjudication_artifact'],'current_revision_artifact':row.get('source_revision_artifact',''),'status_at_dispatch':'POTENTIAL_TECHNOLOGY_EXCLUSION_REQUIRES_SOURCE_REVIEW' if technology else 'POTENTIAL_APPLICATION_WORDING_REQUIRES_SOURCE_REVIEW','not_a_confirmed_error':'true'})
    if date_route:
        for row in candidates:
            row.update(locator_basis='Every recorded current EXCLUDE/UNCERTAIN with reason DATE and frozen representative year2021or later',status_at_dispatch='POTENTIAL_DATE_ROUTE_REQUIRES_SOURCE_REVIEW')
    ids={r['publication_id'] for r in candidates};assert candidates and len(ids)==len(candidates)
    folder.mkdir(parents=True,exist_ok=False)
    s.wr(folder/'manifest.csv',candidates,exclusive=True);s.wr(folder/'source-only.csv',[inventory[key] for key in sorted(ids)],exclusive=True)
    s.wr(folder/'current-fields-at-dispatch.csv',[r for r in rows if r['publication_id'] in ids],exclusive=True)
    if technology or date_route:
        fields=['publication_id','batch_id','eligibility','reason_code','evidence_stream','modality_stream','evidence_type','rationale','adjudication_artifact','adjudication_artifact_sha256','source_revision_artifact','source_revision_sha256']
        s.wr(folder/'scope-selection-snapshot.csv',[{field:row.get(field,'') for field in fields} for row in rows],exclusive=True)
        with (folder/'registry-at-dispatch.json').open('xb') as handle:handle.write(p.REG.read_bytes())
    for pas in 'AB':
        source=s.rd(can/f'pass-{pas}-original-initials.csv');selected=[r for r in source if r['publication_id'] in ids];assert {r['publication_id'] for r in selected}==ids
        s.wr(folder/f'pass-{pas}-originals.csv',selected,exclusive=True)
    inputs={name.as_posix():s.sha(name) for name in [can/'adjudicated-current.csv',can/'pass-A-original-initials.csv',can/'pass-B-original-initials.csv',p.REG,s.INVENTORY]}
    outputs={name.as_posix():s.sha(name) for name in folder.glob('*.csv')}
    receipt={'generated_at_utc':s.stamp(),'owner':'Adjudicator_Sol_resume','model':'gpt-6.1-sol','inventory_sha256':s.EXPECTED_HASH,'snapshot':args.snapshot,'n':len(ids),'candidate_ids':sorted(ids),'input_hashes_at_dispatch':inputs,'scope_files_sha256':outputs,'locator_patterns':patterns,'cutoff':'Already adjudicated B0001-B0129, calibration and preserved earlier high B0378-B0380; prospective paired work uses the clarified existing rule. This is not another initial/calibration pass.','scope':'Current non-empirical EXCLUDE/UNCERTAIN routing with negative implementation/delivery/firsthand or systematic-evaluation wording. Protocols, secondary reports and genuine source/configuration gaps can be unchanged false positives. Wording locates candidates, never determines eligibility.','instruction':'Personally assess complete available source, both preserved initials and prior current/source fields under existing method0.4.6 lines17/21/121. Actual medical task-specific needs/co-design/qualitative/economic/technical observations can qualify without delivered clinical treatment or systematic outcome evaluation. Distinguish real observations/design findings from speculative general opinion, protocols without observations, generic XR and unresolved medical/spatial linkage. No prescribed outcome. Preserve originals and available-source limitations. Use normal source-audit receipt(s), hash this manifest and source-only packet, and include each actually considered ID with excerpt/rationale/extent and unchanged/revised/source-limited outcome. Existing valid recent source readings may support the same case when explicitly confirmed in a scoped receipt; no synthetic/default source judgments.','human_verification':'PENDING','classification_count_generated_by_script':0}
    receipt['kind']=args.kind
    if technology:
        receipt.update(locator_patterns=[],cutoff='All source-adjudicated current EXCLUDE/TECHNOLOGY IDs in the exact frozen dispatch snapshot, including preserved calibration/high batches; future source work applies the same existing rule prospectively.',scope='Every current technology exclusion is a candidate, not an inferred error. Known P7474 and P7685 corrections motivated this source audit but their current uncertain routes are outside this EXCLUDE-only candidate set. Clear ordinary2D/nonspatial or other independent exclusions may remain unchanged.',instruction='Personally read complete available source, both preserved initials and prior current fields under unchanged method0.4.6 lines17/21/119/146 and codebook0.2. Eligible alternatives include XR OR interactive OR patient-specific3D; static patient-specific3D is not automatically excluded. Actual task-specific immersion does not require named hardware; XR need not contain virtual3Dobjects. Distinguish affirmative ordinary2D/nonspatial/pureAI evidence or another independent exclusion from unreported spatial configuration. Future AR/VR alone does not determine whether a current digital game/system is eligible nonimmersive3D. If whether any eligible spatial technology was evaluated is unresolved, keep a justified uncertainty rather than infer absence from missing detail. Definite secondary/protocol/context or other independently established exclusions can remain separately routed. No clinical-outcome/comparator/human-patient/delivered-treatment gate. No prescribed label; every candidate can be valid unchanged. Use normal individually authored source-audit receipts, hash this manifest AND source-only packet, provide exact ID/excerpt/rationale/actual extent/outcome and ordered field overlays. Explicitly confirmed valid recent readings can support unchanged cases without inventing a new reread; preserve all raw history and source limitations.',known_application_corrections=['P0007474','P0007685'])
        receipt['scope_files_sha256'][(folder/'registry-at-dispatch.json').as_posix()]=s.sha(folder/'registry-at-dispatch.json')
    if date_route:
        receipt.update(locator_patterns=[],cutoff='All source-adjudicated current EXCLUDE/UNCERTAIN DATE routes with frozen representative year2021or later in the exact dispatch snapshot; future work follows the same Rule7.',scope='Every selected date route is a candidate, not an inferred error. Actual verified first journal publication before June2020, genuine unresolved lower-boundary conflicts and actual identity/publication-status conflicts can remain unchanged. Known P8930/P8949 application corrections motivate this bounded check; they may already be outside the active DATE set.',instruction='Personally read complete available source, both preserved initials, current and prior source fields and all relevant actual date evidence under unchanged Rule7/date addendum. An unverified exact first-publication day can remain metadata without eligibility change when no actual boundary/publication-status conflict is established. Do not infer an unpublished report from future issue year or infer first publication from DOI year. No invented2025,2026or inventory-day eligibility ceiling. Use verified first journal/version-of-record date where the June2020 boundary actually matters; preserve genuine uncertainty, source limits and valid historical/context exclusions. Independently supported technology, medical-task or evidence-type uncertainty/exclusions remain valid; no prescribed outcome. Do not claim date verification from frozen index metadata. Hash BOTH this manifest and source-only packet in normal source-audit receipts, with each actual ID/excerpt/rationale/extent/outcome and ordered overlays. Explicit valid recent readings may support unchanged cases when specifically confirmed, without synthetic rereads.',known_application_corrections=['P0008930','P0008949'])
        receipt['scope_files_sha256'][(folder/'registry-at-dispatch.json').as_posix()]=s.sha(folder/'registry-at-dispatch.json')
    s.js(folder/'receipt.json',receipt,exclusive=True)
    path=s.RUN/'mandatory-audit-obligations.json';doc=p.loadj(path);assert not any(r['obligation_id']==obligation_id for r in doc['obligations'])
    doc['obligations'].append({'obligation_id':obligation_id,'status':'PENDING_SOURCE_APPLICATION_REVIEW','owner':'Adjudicator_Sol_resume','model':'gpt-6.1-sol','scope_receipt':(folder/'receipt.json').as_posix(),'scope_receipt_sha256':s.sha(folder/'receipt.json'),'candidate_n':len(ids),'publication_ids':sorted(ids),'basis':('Two actual future-issue/exact-day eligibility gates P8930/P8949 were withdrawn under unchanged Rule7. Audit the remaining non2020 DATE routes without presuming errors.' if date_route else 'Two actual missing-description exclusions P7474/P7685 were source-corrected to uncertainty. Audit every earlier current technology exclusion against the same existing eligibility/uncertainty rule; no new criterion or presumed error count.' if technology else 'Additional earlier source judgments outside the exact eight readiness cases used a systematic-outcome/delivered-use gate. Bounded earlier wording audit under existing criteria, not a new rule or confirmed-error count.'),'required_result':'Personally account for every named available source, with exact scoped-input hashes and per-ID registered source-audit entries; preserve valid unchanged/protocol/context and source-limited outcomes.','human_verification':'PENDING'});s.js(path,doc)
    print(json.dumps({'snapshot':args.snapshot,'candidate_n':len(ids),'by_reason':dict(Counter(r['current_reason_at_dispatch'] for r in candidates)),'classification_count_generated_by_script':0}))
else:
    scope=p.loadj(folder/'receipt.json');assert scope['inventory_sha256']==s.EXPECTED_HASH
    assert scope.get('kind','observation')==args.kind
    for name,digest in scope['scope_files_sha256'].items():assert s.sha(Path(name))==digest
    ids=set(scope['candidate_ids']);registry=p.loadj(p.REG);links={};inputs={}
    required_inputs={name:scope['scope_files_sha256'][name] for name in [(folder/'manifest.csv').as_posix(),(folder/'source-only.csv').as_posix()]}
    for registered in registry.get('source_audit_reviews',[]):
        path=Path(registered['file']);assert s.sha(path)==registered['sha256'];raw=p.loadj(path)
        actual={str(Path(name).resolve()):digest for name,digest in raw['inputs'].items()}
        if not all(actual.get(str(Path(name).resolve()))==digest for name,digest in required_inputs.items()):continue
        assert raw['reviewer']=='Adjudicator_Sol_resume' and raw['model']=='gpt-6.1-sol' and raw['human_verification']=='PENDING'
        for entry in raw['entries']:
            key=entry['publication_id']
            if key not in ids:continue
            assert all(entry.get(field) for field in ['supporting_evidence','rationale','source_assessment_extent'])
            assert entry['audit_outcome'] in {'REVISED','CHECKED_UNCHANGED','SOURCE_LIMITED_UNCHANGED'}
            links[key]={'publication_id':key,'source_review_receipt':path.as_posix(),'source_review_receipt_sha256':registered['sha256'],'audit_outcome':entry['audit_outcome'],'source_quote':entry['supporting_evidence'],'source_rationale':entry['rationale'],'source_assessment_extent':entry['source_assessment_extent'],'human_verification':'PENDING'}
            inputs[path.as_posix()]=registered['sha256']
    if args.command=='status':
        print(json.dumps({'snapshot':args.snapshot,'candidate_n':len(ids),'source_assessed_n':len(links),'unperformed_n':len(ids-set(links)),'unperformed_ids':sorted(ids-set(links)),'audit_outcomes':dict(Counter(r['audit_outcome'] for r in links.values())),'classification_count_generated_by_script':0}));raise SystemExit(0)
    assert set(links)==ids,('SOURCE_APPLICATION_CHECKS_UNPERFORMED',sorted(ids-set(links)))
    s.wr(folder/'source-accounting.csv',[links[key] for key in sorted(ids)],exclusive=True)
    inputs.update(scope['scope_files_sha256']);inputs[(folder/'receipt.json').as_posix()]=s.sha(folder/'receipt.json');inputs[(folder/'source-accounting.csv').as_posix()]=s.sha(folder/'source-accounting.csv')
    closure={'generated_at_utc':s.stamp(),'owner':'Coordinator_source_scope_accounting_resume','model':'coordinator_model_not_exposed','inventory_sha256':s.EXPECTED_HASH,'candidate_n':len(ids),'source_assessed_n':len(links),'unperformed_n':0,'audit_outcomes':dict(Counter(r['audit_outcome'] for r in links.values())),'inputs':inputs,'human_verification':'PENDING','scope':('Exact frozen current non2020 DATE-route candidate set source-accounted through registered fresh Sol receipts under existing Rule7. This is not a new date criterion, inferred-error count, accuracy estimate or human validation.' if date_route else 'Exact frozen recorded technology-exclusion candidate set source-accounted through registered fresh Sol receipts. Every recorded E/TECHNOLOGY case in the dispatch snapshot was selected, without a wording/error selector. This is not a new criterion, exhaustive correctness claim, accuracy estimate or human validation.' if technology else 'Exact bounded earlier application-wording candidate set source-accounted through registered fresh Sol receipts. Not an exhaustive semantic detector, new rule, error-rate or human validation.')}
    s.js(folder/'closure-index.json',closure,exclusive=True)
    path=s.RUN/'mandatory-audit-obligations.json';doc=p.loadj(path);task=next(r for r in doc['obligations'] if r['obligation_id']==obligation_id);assert task['status']!='COMPLETE_SOURCE_ASSESSED'
    task.update(status='COMPLETE_SOURCE_ASSESSED',closure_index=(folder/'closure-index.json').as_posix(),closure_index_sha256=s.sha(folder/'closure-index.json'),source_assessed_n=len(links),unperformed_n=0);s.js(path,doc)
    print(json.dumps({'closed':obligation_id,'source_assessed_n':len(links),'unperformed_n':0}))
