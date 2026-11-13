"""High-recall text locator for a known rule-application audit, never screening.

Every candidate still needs personal source assessment. No eligibility/rationale
is generated or changed; original decisions remain immutable.
"""
import argparse,json,re
from collections import Counter
from pathlib import Path
import resume_screening as s

p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);p.add_argument('--kind',choices=['medical','integrity'],default='medical');args=p.parse_args()
assert re.fullmatch(r'[A-Za-z0-9_-]+',args.snapshot)
inventory=s.inv();inputs={};candidates=[]
species=re.compile(r'\b(?:veterinar\w*|non[- ]human|canine|feline|equine|bovine|porcine|ovine|mouse|mice|murine|rats?|rabbits?|zebrafish|drosophila|animals?|dogs?|cats?|pigs?|horses?|cattle|fish(?:es)?|aquaculture|livestock|primates?|monkeys?)\b',re.I)
wording=re.compile(r'veterinar|non.?human|animal.only|human medical|human.only',re.I)
uncertain_gate_wording=re.compile(r'veterinar|non.?human|animal.only|human.only|only.{0,20}human|(?:no|not|without|outside|absen\w*).{0,35}human (?:medical|clinical|patient|subject)',re.I)
integrity_marker=re.compile(r'\b(?:retract(?:ed|ion)|withdrawn|expression[ _-]+of[ _-]+concern)\b',re.I)
folder_name='medical-scope-audit' if args.kind=='medical' else 'integrity-disposition-audit'
instruction='Individually reread every complete available source under the existing broad medical-purpose criteria. Human participants are not mandatory; species alone neither includes nor excludes a report. Determine the actual medical/public-health/education task, evaluated technology, evidence type and source limits without a prescribed label. Preserve originals. Save own worker/model-qualified prompted-scope-recheck JSON with each ID, literal source excerpt, actual extent, outcome/rationale and limitations. Prior valid own source checks may cover the same IDs without format-only repetition. No other-pass judgments or initial labels are supplied.'
scope_text='New fixed-pool original exclusions under any reason code with nonhuman source terms or scope wording, plus uncertain records with possible human-only gate wording.'
if args.kind=='integrity':
    instruction='After own initials, personally reread each complete available source under existing Rule 9 in INITIAL-SCREENER-RULES.md and the integrity addendum. Determine whether a marker concerns this report, a separate notice or cited literature; title markers are not verified notice content. If this report itself documents retraction/concern, retain provisional UNCERTAIN/integrity and WITHHOLD_FROM_SYNTHESIS pending notice/identity and human verification, even if substantive scope would qualify. Ordinary corrections are not automatically retractions. Preserve all originals and actual notice-access limits without misconduct inference. Save an own worker/model-qualified prompted-integrity-recheck JSON with ID, literal source excerpt, actual extent, outcome/rationale, integrity/hold fields and limitations. Existing actual integrity rechecks may cover the same ID without format-only repetition. No other-pass decisions or initial labels supplied.'
    scope_text='Fresh fixed-pool original INCLUDE/EXCLUDE records, plus UNCERTAIN records without an explicit structured WITHHOLD_FROM_SYNTHESIS disposition, with an integrity marker in the assigned title/abstract or an explicit retraction/concern status. This locates possible disposition/documentation errors, including physical maneuvers, participant withdrawal and cited literature; it does not classify integrity or eligibility. Prior genuine own-source notes may cover unchanged original records.'
for pas in 'AB':
    path=s.RUN/'canonical'/f'pass-{pas}-original-initials.csv';inputs[path.as_posix()]=s.sha(path)
    for row in s.rd(path):
        if row.get('worker_id') not in s.WORKERS:continue
        key=row['publication_id'];source=inventory[key]
        if args.kind=='integrity':
            has_structured_hold=any('WITHHOLD_FROM_SYNTHESIS' in row.get(field,'') for field in ['report_disposition','synthesis_disposition','integrity_status'])
            if row['eligibility']=='UNCERTAIN' and has_structured_hold:continue
            hits=sorted({match.group().casefold() for match in integrity_marker.finditer(source['title']+' '+source['abstract'])})
            has_wording=bool(integrity_marker.search(row.get('integrity_status','')))
            if not hits and not has_wording:continue
        else:
            if row['eligibility'] not in {'EXCLUDE','UNCERTAIN'}:continue
            hits=sorted({match.group().casefold() for match in species.finditer(source['title']+' '+source['abstract']+' '+source.get('keywords_json',''))})
            saved_text=row.get('rationale','')+' '+row.get('medical_task','')
            has_wording=bool((wording if row['eligibility']=='EXCLUDE' else uncertain_gate_wording).search(saved_text))
            if not has_wording and not (row['eligibility']=='EXCLUDE' and hits):continue
        candidates.append({'pass_id':pas,'publication_id':key,'worker':row['worker_id'],'source_term_hits_json':json.dumps(hits),'saved_scope_wording_locator':has_wording,'original_eligibility':row['eligibility'],'original_reason_code':row.get('reason_code',''),'original_rationale_verbatim':row['rationale'],'initial_artifact':row['initial_artifact'],'initial_artifact_sha256':row['initial_artifact_sha256'],'status':'LOCATOR_ONLY_REQUIRES_PERSONAL_SOURCE_RECHECK','not_a_classification':'true'})
folder=s.RUN/folder_name/args.snapshot;folder.mkdir(parents=True,exist_ok=False)
s.wr(folder/'candidates.csv',candidates,exclusive=True)
s.wr(folder/'source-only.csv',[inventory[key] for key in sorted({row['publication_id'] for row in candidates})],exclusive=True)
packets={}
for worker in s.WORKERS:
    ids=[row['publication_id'] for row in candidates if row['worker']==worker]
    if not ids:continue
    own=s.RUN/'workers'/worker/folder_name/args.snapshot;packet=own/'source-only.csv'
    s.wr(packet,[inventory[key] for key in ids],exclusive=True)
    s.js(own/'assignment.json',{'worker':worker,'pass_id':worker[0],'model':'gpt-6.1-terra','stage':'PROMPTED_RULE_SOURCE_RECHECK_NOT_INITIAL','audit_kind':args.kind,'candidate_ids':ids,'source_packet':packet.as_posix(),'source_packet_sha256':s.sha(packet),'instruction':instruction},exclusive=True)
    packets[worker]={'n':len(ids),'file':packet.as_posix(),'sha256':s.sha(packet)}
s.js(folder/'receipt.json',{'generated_at_utc':s.stamp(),'audit_kind':args.kind,'locator_version':'2-broadened-reason-codes-and-uncertain-gate-wording' if args.kind=='medical' else '3-title-abstract-including-uncertain-without-structured-hold','inventory_sha256':s.EXPECTED_HASH,'input_snapshot_sha256':inputs,'candidate_pass_id_n':len(candidates),'candidate_publication_id_n':len({row['publication_id'] for row in candidates}),'by_worker':dict(Counter(row['worker'] for row in candidates)),'candidates_sha256':s.sha(folder/'candidates.csv'),'source_packet_sha256':s.sha(folder/'source-only.csv'),'source_only_worker_packets':packets,'scope':scope_text+' This only locates audit candidates; no classifications or synthetic rationales. Personally source-check every case. Re-run against complete final initial ledgers for later work.','limits':'Not an exhaustive semantic detector; source terms can occur in unrelated contexts. Absence of a hit is not proof of correct classification. Unchanged/source-limited outcomes remain valid actual source judgments. Original decisions, samples and agreement remain unchanged.','classification_count_generated_by_script':0},exclusive=True)
print(json.dumps({'snapshot':args.snapshot,'candidate_pass_ids':len(candidates),'candidate_publication_ids':len({row['publication_id'] for row in candidates}),'by_worker':dict(Counter(row['worker'] for row in candidates)),'classification_count_generated_by_script':0}))
