# Medical XR rubric and capability codebook v0.2
Reconciled calibration method, 11 November 2026. Ready for further pilot use; not human-validated, a final inclusion frame or a locked dataset. Sol's original v0.1 and independent extraction records are preserved separately.

## Approved primary question
> Since 2020, has progress from commercial XR and AI capabilities to useful, sustainable medical applications accelerated—and what technical, staffing, financial and organizational conditions enable or constrain further acceleration?

Retrospective capability analysis is the governing design. Historical reviews supply context; new article-level work begins June 1, 2020. No mandatory pre-2020 corpus, two-domain quota, fixed 80-study ceiling, economic model or new experiment applies.

## Screening rule
Include original observed or experimentally generated evidence where VR, AR, MR, or interactive OR patient-specific 3D visualization is central to an evaluated medical task. Retain desktop, tethered, custom and commercial configurations. Scope includes anatomy/procedural education, communication/encounter training, planning/guidance, rehearsal/mentoring/robotics, rehabilitation and other substantive medical applications. Phantoms, healthy volunteers, technical validation, usability, implementation, qualitative workflow and economic studies can qualify for their stated claims; they do not become patient-effectiveness evidence.

No English-only restriction. Translation and unavailable full text are access statuses, not exclusions. Do not require AI, commercial hardware, positive findings, costs, comparator, sample size or open access. Ordinary 2D software, incidental illustrations, generic rendering with no evaluated medical spatial task and pure AI without implemented target-workflow connection enter adjacent context. Static patient-specific 3D is not automatically excluded. Borderlines remain UNCERTAIN. Code XR and nonimmersive 3D separately in all denominators. Telementoring/visualization does not establish remote robotic control.

Use `eligibility=INCLUDE/EXCLUDE/UNCERTAIN`; reason `DATE/MEDICAL_TASK/TECHNOLOGY/EVIDENCE_TYPE/INSUFFICIENT_DESCRIPTION/ELIGIBLE`. INSUFFICIENT_DESCRIPTION implies uncertainty unless sufficient exclusion evidence exists. Reviews, protocols without results and commercial/context documents go to their own streams; retain them for discovery and explanation. `report_disposition=UNIQUE/LINKED_VERSION/POSSIBLE_DUPLICATE` is administrative, not scientific exclusion.

Apply actual report publication date, retaining online, issue and preprint dates separately. Earlier family findings do not automatically exclude substantive new follow-up. Repeated old outcomes are not independent new findings. Earliest substantive public family date is earliest FOUND with coverage stated. Historical linked comparators may be inspected without a new pre-2020 corpus. Partial June–December 2020 and partial 2026 remain distinct from complete years.

## Selection and review workflow
Preserve raw exports and original pilot decisions. Append v0.2 decisions. Construct eligible coverage by year, task, configuration and evidence type before final sampling. Include negative, stalled and discontinued cases. Capability lineages can be purposive; their frequencies do not estimate prevalence. If sampling is necessary, record frame, probability/purposive rule, omissions and access handling before selection. One worked case is neither a workload estimate nor validation of all eligibility boundaries.

Two independent AI-assisted passes followed by source adjudication were used in this pilot. Both reviewers disclosed prior work exposure; agreement is not independent human validation. Coding changes require each extractor to recheck their own record, with responses logged. Human source and inclusion validation remains outstanding.

## Core linked tables and fields
Every table uses stable IDs. Keep a report distinct from its study, continuing project and technical lineage. Family linkage has evidence and certainty; do not assume all project reports share participants or count versions twice.

| Table / row unit | Required fields |
|---|---|
| report: one assessed report/version | report_id, original_record_id, title, authors, DOI_or_URL, source_version, access_status, modality_stream, medical_task, evidence_stream, eligibility, eligibility_reason, report_disposition, study_id_provisional, family_link_evidence, family_link_certainty, novelty_status |
| date: one event/date | report_id, date_type, date_value, precision, source_coordinate, verification_status; date_type = release/study_execution/measurement/preprint/journal_online/issue/practical_availability/support_end/earliest_found |
| configuration: one implemented configuration | configuration_id, report_id, actor, task, test_object, intended_population, setting, input, output, device_generation, sensors_tracking, compute_network, software_SDK_versions, data_model, interaction, integration_dependencies, custom_development |
| AI function: one claimed/implemented function | configuration_id, author_AI_label, assessed_AI_status, algorithm_function, input_output, stage, training_validation, source_coordinate; status = IMPLEMENTED/EXPLICIT_ABSENCE/NOT_ESTABLISHED/PROPOSED_ONLY; stage = preparation/runtime/offline/proposed |
| design: one study/comparison | study_id, report_id, design, comparator_id, comparator_timing, centers, operators_experience, test_objects, allocation_order, pairing, repeats, reference_standard, stopping_criterion, followup, missing_failures, conflicts_funding |
| outcome: one metric × arm × condition × timepoint | outcome_id, comparison_id, configuration_id, construct, metric, unit, favorable_direction, value, dispersion, dispersion_type, CI, reported_test_p, timepoint, condition, comparator_id, participant_n, object_n, attempt_n, measurement_replicates, n_status, analyzed_unit, pairing, difficulty_experience, source_coordinate |
| resource: one resource/cost observation | resource_id, report_id, actor_skill, resource_type, amount_unit, person_time, actual_paid_or_reported_price, currency, price_year, geography, perspective, utilization, subsidy, licensing_support, claimant, supplier_verified |
| organization: one observed/proposed condition | report_id, responsible_actor, ownership, handoff, integration_governance, capacity, routine_use, maintenance_training, continuity, availability_uptake_access, condition_status |
| relationship: one explicit arrow | edge_id, from_node, to_node, task_mechanism, inputs_outputs, responsible_actors, operating_conditions, dependencies, measured_result_id, comparator, evidence_status, claimant, rival_explanations, causal_limit, source_coordinate |

Shared fields: reviewer, codebook_version, review_date, source_URL, exact_source_version, physical_PDF_page_or_section, brief_supporting_passage, limitations, unresolved_issue. Preserve literal source values separately from reviewer inference. Use linked expandable tables rather than forcing all outcomes into a single wide record.

`evidence_stream=empirical/historical_review/commercial_context/protocol`; `modality_stream=XR/nonimmersive_3D/uncertain`. `access_status=full_assessed/partial/unavailable/version_unverified`. `n_status=observed/calculated/unclear`. Nominal scheduled attempts are not verified complete-case observations. Operators, attempts and measurement replicates are separate denominators; repeated measures remain paired/correlated. Stopping criterion is not a clinical acceptability standard.

## Nulls and evidence labels
`NR`: assessed source silent. `NOT_MEASURED`: source explicitly says not assessed. `UNCLEAR`: ambiguous/conflicting. `NA`: genuinely inapplicable. Access/version limitations remain separate; inaccessible full text is not NR in the unseen article. Nulls never equal zero, failure or absence of benefit.

Evidence status: `OBSERVED_STUDY`, `SUPPLIER_REPORT`, `PAPER_REPORTED_PRODUCT`, `DOCUMENTED_LINEAGE`, `CALCULATED_ASSUMPTIONS`, `INTERPRETATION`, `UNKNOWN`. Record claimant separately. A product specification/price quoted by authors uses PAPER_REPORTED_PRODUCT and supplier_verified=false until owning source is inspected. Actual acquisition payment, list price and full delivery cost differ. A suggested requirement is not an observed barrier. Corporate loss/spending cannot be allocated to a medical effect without a supported pathway.

## Analysis and appraisal rules
A capability is what an actor/system can do for a task with stated performance, resources and conditions. Trace components → individual task → workflow → institution → wider access, auditing each arrow; benefits need not propagate. Capture inheritance, migration and lost support when documented; commercial success and medical usefulness are separate.

Improvement is favorable change in a specified comparable metric. Acceleration requires changing improvement rates or shorter transfer intervals across sufficiently comparable dated observations/cohorts, with scale, time unit and uncertainty. Two endpoints show change only. Publication growth and within-session learning are different constructs. Missing follow-up means unknown sustainability, especially for recent cohorts.

Preserve clinical, educational, technical, usability and implementation outcomes separately. Check task difficulty, population, comparator/dose, operator experience, reference standard, timing and uncertainty before pooling or comparing. Nonsignificance is not equivalence; SEM is not SD or individual reliability. Isolated registration time is not procedure time, throughput or cash saved. Supplier specifications are not medical validation. Do not invent a composite progress score or force a rate estimate when comparability fails.

Use design-appropriate appraisal for each claim; distinguish reporting gaps, bias and extraction inconvenience. PRISMA-ScR is proposed for a future systematic breadth map, not a compliance claim for this pilot. No full formal reporting checklist or risk-of-bias score was performed here. Source-specific appraisal and human confirmation precede final inference. Stop affected synthesis when unresolved versions, overlap, dates or endpoint definitions could reverse the conclusion.

## Apply to existing inventory
Read `decision-log-and-readiness.md` for field mapping. Preserve legacy record_id (for example P0003073) as original_record_id; use publication_id only in sources that actually contain that field; never treat export_year as execution date, legacy date_allocation as verified timing or fulltext_accessed as journal-version access without checking. Append report/source-version, study-family, outcomes and relationship tables. Terra's automated dictionary describes the legacy 23-row/26-column ledger; its flagged semantics require human confirmation. Original v0.1 and both independent records/rechecks remain supporting provenance.

