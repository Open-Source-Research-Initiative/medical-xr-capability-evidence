# Screening work and final PI review

Cole's 17 November 2026 instruction authorizes issue-driven model work open to contributors. Required human scientific review occurs after all model work is finished and an immutable packet is ready for PI review and sign-off. This prospectively supersedes earlier per-batch/per-PR human-review timing for provisional work in this screening scope. It does not change the question, method0.4.6/addenda01–04, codebook0.2, frozen originals or original samples.

Start with [tracker #9](https://github.com/Open-Source-Research-Initiative/medical-xr-from-capabilities-to-sustainable-use/issues/9) and the [exact work map](../data/runs/2026-11-17/README.md). There are 35 source packages containing 158 original batches and exactly 7,900 pending publication IDs. Each batch has 50 records. Some have saved model artifacts; do not duplicate their work or count a saved file as an accepted result.

## Review sequence

| Stage | Work and completion rule |
| --- | --- |
| Frozen originals | Preserve both original passes, source fields, actual/unknown authors and models, memberships, samples and correction order. Do not restart initials. |
| Sol source adjudication | Read complete available sources/metadata and both originals; perform every assigned audit and exact note consideration. Document source access and unresolved facts. |
| Conditional Astra | Refer only completed Sol uncertainty. Perform further source research under the same criteria; retain Sol, Astra and disagreement separately. |
| Date and operational checks | Complete genuine independent date attempts, attributed later consideration and all medical/date/integrity/context/source-year gates. Unavailable evidence may remain unresolved. |
| Coordinator/model checks | Validate identities, hashes, membership, frozen samples, source accounting and ordered changes. Integrate checked provisional work and record actual model review. |
| Final model packet | Reconcile all IDs/counts/hashes, attempts, findings, code/environment, disagreements, holds, source gaps and limitations in an immutable packet. |
| PI review/sign-off | After the preceding model work is complete, Cole/PI reviews the exact packet and records acceptance, rework or rejection against its revision/digest. |

Ordinary model-stage issues may close as **model-complete / PI-pending** after their real work and checks are complete. They do not require an earlier PI review. Provisional documentation, tooling, work records and model outputs may be integrated/published within this standing instruction after required CI and appropriate model/source checks. Such integration must not be described as Cole's case-by-case review or scientific acceptance. The [PI issue](https://github.com/Open-Source-Research-Initiative/medical-xr-from-capabilities-to-sustainable-use/issues/22) remains open until an actual human decision; no agent may supply that decision.

This is a recorded project-specific review-timing difference under [OSRI-0.1.0](https://github.com/Open-Source-Research-Initiative/osri/blob/8c39a0a36c0e962060659b1d51f666c367f9464a/governance/contribution-standards.md), particularly its human acceptance/publication rule. Cole remains responsible and authorizes this provisional work; human acceptance of the scientific screening packet is reserved for the final PI gate. The organization-wide standard is unchanged. See the [dated authorization](../provenance/issue-workflow-2026-11-17.json).

## Claim a contribution

1. Open a [source-package issue](../data/runs/2026-11-17/README.md) and comment with one unclaimed batch or a smaller exact-ID/tooling/provenance task. Coordinate the claim to avoid overlapping canonical writes. Read access needs no invitation, organization membership or agent subscription.
2. Download the [frozen evidence release](../data/README.md#complete-evidence-archive), or use a verified restored copy. Run:

   `python scripts/prepare_screening_packet.py --batch B0215 --archive workspace.zip --output my-B0215`

   Alternatively use `--source-root EXTRACTED_ARCHIVE`. The command verifies the five selected frozen inputs and copies them unchanged into a new directory. It does not read scientifically, verify the whole archive or assign labels. Use `python scripts/verify_open_data.py --archive workspace.zip` for the separate whole-archive check.
3. Preserve the packet. Submit append-only assessments/receipts in a branch and PR linked to the issue. Record every assigned ID, actual reviewer/model/version, exposure, source/version/sections read, evidence and access limits, route/type/modality/task reasoning, original-note/date links and remaining uncertainty. Source leads may be submitted in comments without claiming an assessment. Keep editable records and source terms.
4. The coordinator checks/integrates the submission and records the issue's model-stage outcome. Additional actual contributor identities may be registered through bounded issue assignments; nobody inherits a former identity or replaces original initial owners. Changes to scientific scope/eligibility still need Cole's instruction.

For source adjudication, both initial passes already exist: reading them is deliberate exposed adjudication, not a new blinded pass. If a person voluntarily performs an independent source-first check, use the [human procedure](human-verification.md), save their own assessment before comparison and disclose exposure. That optional work does not block the model phase; issue #1 is deferred to final PI review.

## Final packet requirements

The [packet issue](https://github.com/Open-Source-Research-Initiative/medical-xr-from-capabilities-to-sustainable-use/issues/21) depends on every source package, model referral, date/integration task and prescribed audit. Model completion means all assigned checks were actually performed; it does not mean every result became certain. Retain irreducible gaps, conflicts and integrity holds. Include the frozen question/method and dated deviations, exact source/results/manifests, actor/exposure and stage-coverage matrices, attempts and failures, accessible reproducibility records, search/report-family limitations, and an explicit PI decision brief.

PI sign-off authorizes only its recorded scope. It does not automatically mark all 18,976 records human-verified, validate clinical efficacy, establish independent model accuracy or external peer review, or answer acceleration. Per-record human verification changes only with actual attributable human source work. No new extraction, feasibility analysis or research conclusion is authorized by this screening workflow.

The [17 November assignment record](../provenance/issue-assignments-2026-11-17.json) identifies the first six new bounded Sol contexts and their exposure stage. Claims are not completed source work or canonical registration. Earlier contexts are unavailable; their saved authorship is preserved.
