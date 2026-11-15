# Human validation design for review

**13 November 2026 — proposed, not executed or approved.** This companion to the [feasibility milestone](feasibility-milestone.md) separates source checking, screening error, missing evidence and scientific interpretation. No reviewers have been recruited, no final sample has been drawn, and human-verified records remain zero.

## People and reference assessments

Use two humans who save independent assessments before comparison. Between them, require evidence-synthesis/screening-method expertise and relevant medical-task plus XR/interactive-3D expertise. Add a technical specialist for configuration/AI disputes and an information specialist for retrieval questions as needed. Record actual qualifications, conflicts, authorship, prior AI exposure and who performed each task. Do not label founder self-review as independent review. If only one suitably qualified person is available, report that limitation and keep independent validation pending.

An adjudicator may resolve human disagreements after the two initial entries are frozen. Preserve those entries, the adjudicated reference and unresolved cases. An AI adjudicator does not replace the human reference. Do not optimize the rubric or select raters to maximize agreement with saved AI decisions. The proposed dual-human procedure draws on [Cochrane's study-selection guidance](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-04#section-4-6); it is a project design proposal, not a claim that this broad evidence map is a Cochrane intervention review.

Use two distinct reference questions. First, was the **screening action** justified under the recorded method version and evidence available at that stage? INCLUDE means advance, not final full-text eligibility. Second, what does a sufficiently inspected owning source now establish? Information obtained later may change the current disposition without proving that the original action was erroneous. Record method-version differences, newly available evidence and actual misreading separately. Do not retroactively apply a new rule and call every difference an old-model error.

## Diagnostic pilot and worked chain

The existing proposed 20-record diagnostic pilot can reveal rubric, retrieval and packet failures. Its ten adjudicated-frame and ten targeted records do not establish general screening reliability. Preserve any already fixed audit samples; this pilot does not replace them. Record selection reasons and source availability rather than silently substituting accessible records.

For the feasibility family, have two humans check every central date, configuration link, outcome value, resource claim and follow-up statement. That case-series check addresses the worked analysis only. It is not a representative test of all 18,976 initial assessment pairs.

Pilot findings may motivate a new rubric or method version. Record the change before validation, retain the old results, and draw a fresh validation sample. Calibration cases cannot be presented as an untouched validation set.

## Probability validation: frame and draw

1. Freeze the inventory and both original initial-pass tables by hash, the decision checkpoint to evaluate, and the rule/codebook versions. All 18,976 provisional IDs are the initial assessment frame, including records outside the 9,226 adjudicated subset. Validate that each pass covers exactly that frame. Linked reports remain visible; do not assume one ID equals one independent study.
2. Define separate action frames for each pass's original EXCLUDE, INCLUDE and UNCERTAIN decisions. The principal safety endpoint is unjustified exclusion; unnecessary advancement is a separate workload endpoint. Do not sample only agreed exclusions or only adjudicated records. A current adjudicated-decision audit needs its own frozen frame and stage-matched reference; its result cannot stand in for the initial-pass audit.
3. Within each pass/action frame, stratify by recorded screening-method version and model-identity category, retaining unknown identities as their own category. Preserve source-access/missingness flags and reviewer/worker/batch metadata. If sparse cells must be combined, state the rule before drawing; report which version/model subgroups then lack a separate estimate. Model identity is descriptive and does not establish independent errors.
4. Fix sample sizes and inclusion probabilities before human outcomes. Draw without replacement using a recorded random seed and algorithm; save the frame hash, seed, ordered selected IDs and probabilities. Publish safe metadata only. Oversampling missing-source or rare-version cells is allowed if its probabilities and weighting are retained. Targeted diagnostic cases stay separate from probability estimates.
5. The same ID may be selected from more than one pass/action frame. Review its source once where appropriate, but make stage/version-specific reference assessments and preserve its membership in each sample. Estimate each pass separately using its own draw probabilities. Do not treat two passes or linked reports as independent observations in a pooled estimate.
6. Keep previously exposed/calibration cases separate from the untouched validation frame. State the resulting target population. A full-corpus estimate needs a defensible accounting for those excluded cases, not an assertion that the remainder automatically represents them.

The reported 15,050 same-Terra pairs and 1,008 unknown pass-B model identities motivate this stratification. They are provenance counts, not an empirical estimate of shared-error dependence or model accuracy. The version/model cross-tabulation and per-frame sample allocations must be frozen from the owning metadata before the draw.

## Size and precision decision

The responsible human and a methods/statistical reviewer must choose the tolerable missed-eligibility risk and required interval precision. This plan does not silently choose that scientific tolerance. Use the following reproducible planning calculation to make the resource decision concrete.

For a simple random sample in a sufficiently large action frame, the probability of seeing at least one error when the error fraction is `p` is `1-(1-p)^n`. Requiring at least 95% probability gives `n = ceil(log(0.05)/log(1-p))`:

| Error fraction to detect | Assessable independent sampled IDs needed | If zero errors, one-sided 95% binomial upper bound |
| --- | ---: | ---: |
| 5% | 59 | about 4.95% |
| 1% | 299 | about 1.00% |

These are **per action frame**, not per combined project and not automatic reliability criteria. With zero errors in 20 simple-random assessable cases the analogous bound is about 13.9%; the actual purposive diagnostic pilot does not justify even that population bound. The calculation detects error; it does not guarantee a desired interval width when errors occur, prove sensitivity, or validate subgroup performance. It assumes a suitable probability draw and assessable reference outcomes. Source failures are not assessable successes.

Use the exact hypergeometric calculation for a finite simple-random frame when its sampling fraction matters. For unequal stratified sampling, allocate by the chosen estimand/precision, retain `N_h` and `n_h`, use inverse-probability weights and an appropriate design-based interval; do not reuse the simple binomial bound on a weighted total. A 1% claim for an individual method/version subgroup requires enough evidence in that subgroup. If the available review budget cannot meet the chosen precision, narrow the claim or report the uncertainty; do not lower the standard after seeing outcomes. Freeze the actual allocations, not just this planning table, before collection.

## Endpoints and missingness

Report per pass and per stage:

- Unjustified exclusion among sampled EXCLUDE actions, with a stage-matched human reference and uncertainty interval.
- Unnecessary advancement among sampled INCLUDE actions, without mislabeling advancement as final false inclusion.
- Resolution and appropriate abstention among sampled UNCERTAIN actions.
- Missing sources, incomplete inspected extent, date/version ambiguity, rubric/version differences and human disagreements as separate outcomes.
- Attempts, authorized access, sufficient source inspection, assessable references, unresolved cases and discrepancies, each with its own denominator.

An error fraction among excluded records is not the false-negative rate among all truly eligible records. Estimating recall/false-negative rate requires human eligibility information across the action classes, weighted back to their frame sizes. Likewise, do not call a purposive disagreement count a corpus accuracy estimate. Report both same-model and other/unknown-model strata descriptively; formal error correlation requires a suitable human-reference sample.

Do not drop inaccessible sources or replace them with easy cases. Report assessable-only results with their denominator, plus bounds treating unresolved reference outcomes as errors versus non-errors where meaningful. Any reserve draw must be prespecified; it adds observations without erasing original nonresponse. Record retrieval effort and whether missingness differs by action, method version or year. Accuracy inside the inventory says nothing about missed evidence outside it.

## Assigned-record packets

The private companion's 43 metadata projections are an index for review, not a source-and-decision packet. Prepare two separated packet components for each assigned record:

| Component | Contents | Disclosure timing |
| --- | --- | --- |
| Source-only | Original ID and report/version identity; exact applicable rule text/hash; authorized source locator/access route; source version/hash where lawful; relevant sections and required inspected extent; date/identity evidence; blank independent assessment | Before any AI decision/rationale comparison |
| Decision comparison | Immutable initial actions and actual author/model/version fields; original rationales and source locators for that assigned record; later correction/adjudication chronology and hashes | After independent human entries are saved |

Maintain a packet manifest with record IDs, component/file hashes, compiler/date, recipient, access authority/terms, source availability, omissions and prior exposure. Store restricted material only in an approved location with item-specific sharing rights. When copying is not allowed, supply the authorized owning-source route and local locator; do not infer rights from private GitHub access. If the necessary rationale/source cannot be provided, label that part of review unreproducible/pending.

Save human entries, inspection dates/extents, source versions, independent judgment, uncertainty, prior exposure and correction/disagreement disposition. Reveal and compare only after entries are frozen. Audit packet completeness before the review starts. Neither a blank template nor a validated metadata projection counts as a completed review.

## Decision and reporting

Before any resume or reliability claim, name the human reviewers, accepted rubric/versions, frozen frames, allocations, error/precision targets, missingness rules and disagreement procedure. After collection, report actual estimates and their limits before making a decision. Corrections remain attributed additions; existing initial records and fixed audit IDs are preserved. No automatic screening restart or scientific acceptance follows from a CI pass.
