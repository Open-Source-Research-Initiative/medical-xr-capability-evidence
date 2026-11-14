# Shared screening method v0.3 — 2026-11-11



Since 2020, has progress from commercial XR and AI capabilities to useful, sustainable medical applications accelerated—and what technical, staffing, financial and organizational conditions enable or constrain further acceleration?



Governing codebook: outputs/Medical-XR-Capability-Assessment-Pilot/reconciled-codebook-v0.2.md. Prompt source: 11 - Calibration and full inventory screening prompts.md. Retrospective capability evidence map; not a registered meta-analysis or a human-approved dataset lock. Unit is provisional publication group, not independent study. Title/abstract INCLUDE advances for full-text assessment only. All decisions are provisional AI assessments; human_verification=PENDING.



Read each record's title, complete available abstract, date tags and metadata. Never treat keyword filtering as record-level assessment. Do not consult legacy decisions or the other screener's decisions before completing a batch. Disclose known prior exposure per record and in your reviewer notes.



Broad medical task and evaluated XR or interactive OR patient-specific 3D are eligible. Keep XR and nonimmersive_3D separate; uncertain display remains uncertain. Technical, phantom, healthy-volunteer, usability, qualitative workflow, implementation and economic evidence may qualify. No AI, cost, comparator, commercial-hardware, English-language or full-text-access requirement. Pure AI, ordinary 2D, generic rendering without evaluated medical spatial task are adjacent context. Reviews, protocols without observed results and commercial documents are separate streams; a protocol-labelled paper with observed usability results can be empirical.



Use eligibility INCLUDE/EXCLUDE/UNCERTAIN, reason ELIGIBLE/DATE/MEDICAL_TASK/TECHNOLOGY/EVIDENCE_TYPE/INSUFFICIENT_DESCRIPTION. For consistency eligibility refers to the new empirical full-text queue: reviews/protocol-only/context are EXCLUDE with EVIDENCE_TYPE while retained in their separate stream, never discarded. Insufficient description is UNCERTAIN unless explicit independent exclusion evidence exists. If the technology is clearly eligible but immersion is uncertain, INCLUDE with modality_stream=uncertain is allowed. A solely hypothetical proposed system with no implementation/observations enters protocol or adjacent_context. Distinguish assessed attitudes towards real deployment from speculative general opinion; retain uncertainty if not resolvable.



New primary report work starts 2020-06-01. Year 2020 without reliable month/day is uncertain at boundary. Publication metadata dates are provisional: January 1 may be an indexing placeholder; year 2026/2027 issue metadata may conflict with earlier online publication. Do not infer future/unpublished solely from issue year. Date conflict needing identity check remains flagged. Earlier study execution does not itself exclude a new report; follow-up/version overlap is retained for later linkage.



Report disposition UNIQUE/LINKED_VERSION/POSSIBLE_DUPLICATE is administrative. Preserve all source memberships and record IDs. Do not merge or remove uncertain duplicate/version links.



Output schema: publication_id, reviewer, model, model_version, codebook_version, prompt_version, batch_id, eligibility, reason_code, rationale, supporting_evidence, source_coordinate, evidence_stream, modality_stream, medical_task, date_status, report_disposition, identity_issue, access_status, prior_exposure, human_verification, screened_at.



Use model actual configured name, model_version=runtime_version_not_exposed if unknown; never invent a build. codebook_version=0.3; prompt_version=11-2026-11-11. evidence_stream=empirical/historical_review/protocol/commercial_context/adjacent_context/uncertain. source_coordinate points to snapshot publication_id + abstract_record_id and title/abstract/date_tags; supporting_evidence is short exact source wording or a clearly marked close paraphrase. access_status=title_abstract/title_only/metadata_only. Save append-only per-batch CSVs under each reviewer folder. Save progress with exact completed ID list and pending count, not estimates.



Calibration is purposive diversity, not representative prevalence. Eighteen records cover 2020–2026, review/protocol, rehabilitation, education, clinical guidance, patient communication, qualitative evidence, animal-health boundary, phantom, nonimmersive, commercial and incomplete abstracts. Candidate identification used title searches only; no eligibility labels were assigned by those searches.



Audit plan prespecified before receiving screener outcomes: seed string MedicalXR-20261111-v03. For each completed common batch, adjudicate every disagreement and any uncertainty; briefly check all agreed inclusions. Independently inspect max(10, ceiling(10% of agreed exclusions)), capped at all agreed exclusions, selecting lowest SHA256(seed + ':' + publication_id) values. This deterministic pseudorandom order is fixed across batches. Audit context and modality discrepancies too. Errors prompt correction and recheck of affected rules/records across completed batches. AI agreement is consistency, not accuracy or human validation.



After calibration clarifications, both reviewers recheck affected records before full screening. Full batch allocation is stable inventory order excluding calibration IDs, 50 records each; both reviewers must assess every ID. Automation may assemble source bundles, validate schemas, hash inputs and reconcile ID sets; it must not label unassessed records.



## v0.4 clarification amendment



This amendment supersedes conflicting metadata wording above. `capability_codebook_version=0.2`, `screening_method_version=0.4`; retain legacy `codebook_version=0.3` only in original v0.3 files. New files may retain codebook_version=0.2 plus the two explicit fields. `review_context` replaces `historical_review` as general evidence-stream label; `review_role=historical_baseline/contemporary_context/uncertain` separates role from publication date. Opinion/editorial can use adjacent_context. `modality_components` records XR and nonimmersive_3D when a report compares both, without double-counting its publication ID. Report-level modality_stream may stay XR with component note, but components must remain separate in later denominators.



Original calibration is independent TA assessment. Source-enriched rechecks/adjudication are a separate stage, not retroactive independent TA judgments. Add `assessment_stage=title_abstract/source_enriched_recheck` and source URLs, assessed sections, access limitation. Selective HTML inspection is not full complete-article assessment or a downloaded/hashed PDF. Preserve both original ledgers and any rechecks.



Enrollment counts and a developed prototype alone do not establish reported evaluation results. If source inspection confirms planned tests with results pending, retain protocol stream. A report called protocol may still advance if it reports relevant actual technical, usability, implementation or other evaluated results. Case examples of actual medical use advance at TA without a comparator requirement, subject to full-text evidence-depth and study-family checks.



General tourism/recreation with speculative rehabilitation benefits is adjacent context when inspected aims and measured outcomes clearly evaluate tourism rather than a substantive medical/health task. Do not apply this to rehabilitation, explicit therapeutic activities, disability-focused assistive evaluation or assessed clinical wellbeing merely because they also involve recreation.



Interviews after conceptual videos/orientation are real empirical attitudes but do not demonstrate patient use, usability or task capability of implemented XR. Retain UNCERTAIN in new empirical queue when relevance as organizational/medical-application evidence remains unresolved; retain the source separately as contextual empirical attitudes, and code actual exposure explicitly. Do not exclude solely for veterinarians/nonhuman test objects; zoonotic/public-health scope remains potentially relevant.



A 2020 journal report with an earlier preprint remains an eligible report for assessment, with earlier date and substantive novelty/overlap unresolved; never count reports as new independent studies automatically. Source conflicts in outcome labels/values must be recorded verbatim separately; do not silently substitute a preferred number or use unresolved values for synthesis. P0000404 has an observed abstract/table discrepancy in angle bounds and interval terminology, requiring human/source reconciliation.



## v0.4 metadata correction (same-day append, before B0001 audit)



`report_disposition=UNASSESSED` is permitted and required when independent report/version uniqueness has not been checked. An existing provisional publication group does not establish UNIQUE; preserve grouping_status separately. Use LINKED_VERSION/POSSIBLE_DUPLICATE only with evidence. `review_role=UNASSESSED` is allowed and preferred until the source's actual analytic role has been considered; publication year alone does not establish contemporary_context. `modality_components=UNASSESSED` is allowed where not determined, with explicit source-indicated comparisons recorded per record. Do not automatically copy one report-level stream into a complete list of components. Recheck these fields across every already-screened record affected by an automated default, preserving originals and documenting changes. These metadata defaults do not change empirical eligibility without source-based reason.



## Revision identity v0.4.1



Immutable revision 2026-11-11: explicit UNASSESSED report disposition/review role/modality components; direct quotation versus paraphrase labeling. No eligibility rule changes from v0.4. v0.4 original plus amendment remains provenance; use screening_method_version=0.4.1 going forward and corrections file metadata_revision=0.4.1. Codebook remains 0.2. Original independent decisions and later metadata corrections are distinct artifacts; never silently overwrite prior judgments. Calibration/B0001 metadata correction does not change eligibility unless separately adjudicated with a source reason.



## Revision identity v0.4.2 — medical task boundary correction



Supersedes Astra's initial B0002 exercise inference. Generic fitness/exercise, ordinary recreation, or physiological/mood endpoints alone do not establish a substantive medical task. Require a source-supported clinical, rehabilitation, targeted prevention/health-service, medical education or other medical application link; when unclear, UNCERTAIN/MEDICAL_TASK, with full-text/context follow-up. Healthy volunteers remain eligible for relevant medical-task evaluation. Do not exclude explicit rehabilitation or therapeutic/prevention work for using games or exercise. P61/P64/P66 are unresolved generic-exercise boundary cases, not established health-promotion inclusions. Source-specific intended task and endpoint context govern; no keyword-based exclusion rule is added.



Already adjudicated calibration/B0001/B0002 were checked for related exercise/wellness contexts. P0000334 explicitly studies physical therapy/balance/fall-risk intervention in nonagenarians; P0000049 treats Parkinson mobility/fear of falling; P0000045 assesses post-stroke dexterity; P0000081 evaluates cognitive training in older adults framed around cognitive health/dementia risk, so advance with task efficacy distinct from general enjoyment. P0000068 evaluates a community health-equity planning method, not generic leisure. P0000020 remains UNCERTAIN for basic episodic-memory task to neurorehabilitation linkage; P0000375 remains tourism context. P0000061/P0000064/P0000066 alone require superseding the initial B0002 adjudicated INCLUDE with UNCERTAIN. Both reviewers must independently recheck affected records; original decisions/rechecks remain preserved.



P0000066 journal report date is 2020-10-28 and earlier preprint posted 2019-11-13 per publisher history; novelty/overlap unresolved, not an automatic report exclusion. Exact source: https://games.jmir.org/2020/4/e16693 .





## Revision identity v0.4.3 — audit enforcement and modality uncertainty

The existing requirement to audit context and modality discrepancies was incompletely implemented by Astra in B0001–B0005. The corrected selection takes the union of all eligibility, evidence_stream and modality_stream disagreements, any uncertainty, all agreed inclusions and the prespecified random agreed-exclusion sample. Context exclusions with metadata disagreements require explicit field review even when outside that random sample. Preserve original values and field-level source resolution. This repair changes metadata, not eligibility, in the first five batches.

A VR label alone may not establish immersive XR or interactive/patient-specific 3D; nonimmersive alone never establishes 3D. For mixed reviews, use uncertain single-stream modality when the mixture cannot be represented accurately, with components only where individually established. Review inclusion in context does not require assigning it to an XR denominator. Reviewers must recheck affected metadata without rewriting original independent records.

Evidence stream concerns the source's role in the eligible medical evidence map, not merely whether it contains any measured data. Empirical surveys may retain uncertain applicability/stream where evaluated medical-application linkage is unresolved; notes must identify actual observations separately. Previously audited source-specific uncertainty remains visible.





## Revision identity v0.4.4 — explicit evidence type

`evidence_stream` is evidence-map routing; it does not replace the user's per-record evidence-type field. Add `evidence_type`, `evidence_type_basis`, `evidence_type_check_status`. Use a source-grounded type/design, allowing multiple components: randomized trial; nonrandomized comparative evaluation; observational cohort/cross-sectional; qualitative interviews/focus groups; survey; technical/phantom evaluation; implementation/development evaluation; case report/series; systematic/scoping/narrative review; bibliometric analysis; protocol; editorial/opinion; commercial document. Use UNCLEAR if source does not state enough. Do not infer randomization, comparator, prospective design, or evaluated implementation solely from title keywords. A source's claimed design is not methodological validation.

Every already-assessed ID in both independent passes must receive a separately tracked type check. Explicit and accurate source-grounded rationale can supply a type, otherwise individually revisit the source or mark UNCLEAR with the actual gap. An administrative default UNCLEAR with PENDING does not count as a completed check; UNCLEAR with a documented source inspection can be CHECKED_UNCLEAR. Preserve original independent files and save append-only reviewer evidence-type corrections. Future initial screens include the fields. These are metadata completion requirements, not changes to eligibility rules or proof of human validation.

The linked all-ID evidence-type-check-status-current.csv distinguishes unscreened, type-check pending, checked clear and checked unclear. Provisional title/abstract assessment counts remain separate from metadata-check completion.


Evidence type is the reported design, separate from the medical application/task and routing stream. A protocol label may coexist with an observed preliminary evaluation; trial registration alone does not establish results. Preserve both components when supported.



## Revision identity v0.4.5 - UTF-8 encoding correction only
Preserves the scientific and screening rules of v0.4.4. Recovered isolated Windows-1252 punctuation bytes in the v0.4.3/v0.4.4 amendments while preserving valid UTF-8 text. Earlier originals remain unchanged. Use explicit UTF-8 for future text artifacts. No eligibility, evidence-type or modality rule changed.


## v0.4.6: task-specific immersion evidence and device uncertainty

An explicit methodological description of an actual intervention as immersive VR supports provisional XR modality even when the headset/model/display implementation is not named. An explicitly specified immersive planned intervention can similarly be coded XR in the protocol stream, with planned rather than observed use. Unknown hardware remains a separate configuration limitation. General introductory statements that VR is immersive, marketing possibilities, subjective presence/immersion ratings, and an unspecified VR label do not establish delivered immersion. A device brand used only for tracking or audiovisual streaming does not establish spatial-display use.

This corrects Astra's overstrict interpretation during the second retrospective modality reconciliation; it does not impose a new hardware requirement or change eligibility. P0000215, P0000217, P0000220 and P0000226 have task-specific immersion descriptions. Both reviewers must independently examine earlier corrections potentially affected by this distinction, preserving originals, source-specific bases, dissent, and per-ID pending status. Candidate searches only locate records and never determine their label. Forward screening continues while retrospective repairs remain pending.

An explicitly mixed empirical report may use report-level XR with separately established nonimmersive 3D or 2D components; unknown component denominators remain pending. Do not infer that all observations came from XR or count a provisional publication twice. Review syntheses with uncharacterized mixtures remain uncertain.
