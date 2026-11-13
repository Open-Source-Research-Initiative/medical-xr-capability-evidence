# Research method and changes

The operative methods are now [publicly available](methods/README.md), including unchanged method0.4.6, addenda, rule-only packet, codebook0.2 and the dictionary. This index preserves earlier recovery pointers and chronology; it is not retrospective registration or a replacement protocol. Preserve the exact question in README.md.

Read [search provenance and gaps](methods/search-provenance.md), [the dated measurement draft](methods/measurement-framework.md), [one existing source trace](examples/README.md) and [the human verification procedure](docs/human-verification.md). The draft proposes reviewable definitions; no deeper extraction or new scientific labels were performed during remediation.

## Scope and units

Investigate capabilities and their transfer into sustainable medical applications. Historical reviews provide the baseline. New article work begins 1 June 2020. There is no 2025 or inventory-day upper cutoff.

Retain broad medical applications, including education, communication, planning, guidance, rehabilitation, rehearsal, mentoring and robotics. Relevant technical, phantom, healthy-volunteer, qualitative, implementation and economic observations can qualify. AI, costs, comparators and English-language text are not mandatory gates.

The 18,976 IDs represent provisional publication groups. Reports, versions and independent studies remain incompletely reconciled. Repeated identifiers do not authorize merging.

## Recover the operative records

Preserve these exact archive paths:

- 10 - Locked question and capability analysis.md.
- outputs/Medical-XR-Calibration-and-Full-Screening/shared/current-method-guide.md.
- outputs/Medical-XR-Calibration-and-Full-Screening/shared/method-v0.4.6.md and operative addenda.
- outputs/Medical-XR-Capability-Assessment-Pilot/reconciled-codebook-v0.2.md.
- outputs/Medical-XR-Calibration-and-Full-Screening/resume-20261112/INITIAL-SCREENER-RULES.md.
- That run's DATA-DICTIONARY.md, TEAM-AND-METHOD-LOG.md, COORDINATOR-HANDOFF.md and ordered registries.

The external execution brief is preserved separately; see provenance/external-context-manifest.json. Earlier pilot/exploratory work must not be relabeled as prespecified.

## Initial review and adjudication

Both independent initial assessments exist for every ID. Preserve legacy authors and unknown model fields. New owners A1–A4/B1–B4 used gpt-6.1-terra in independent pools. The fresh adjudicator used gpt-6.1-sol. Other-pass decisions were hidden from initial workers. Known exposure disclosures and their qualified chronology remain preserved.

INCLUDE advances for empirical full text. Context evidence is retained separately. Missing description means uncertainty unless an independent exclusion is established.

XR OR interactive OR patient-specific 3D may qualify when central to the medical task. Missing configuration is not affirmative nonspatial evidence. Actual task-specific immersion can support XR without a named headset. Generic presence, tracking, streaming or a VR label alone is insufficient.

First journal publication, issue, preprint and execution dates are distinct. Known 2020 boundary records need own-pass actual date attempts. An unknown exact day may remain metadata when no actual boundary/publication-status conflict exists.

Assigned-report integrity flags follow the existing uncertain/withhold rule. Ordinary corrections, cited retractions and physical retraction are distinct. Preserve verified legacy holds and source history.

Within each original common batch, sort agreed-exclusion IDs by SHA256 of MedicalXR-20261111-v03: plus publication ID. Select min(n, max(10, ceil(0.1*n))), where n is the number of agreed exclusions. Preserve the actual saved sample IDs. Original agreement uses original assessments.

## Unfinished work

There are 9,750 remaining adjudications, 9,464 unperformed required source-audit cases, 88 future legacy considerations and 418 post-initial note considerations.

Five gates remain: final medical scope (318 pass IDs across 200 publications); date-window (136 pass IDs across 134 publications); integrity (115 pass IDs across 90 publications); final context-label/source accounting; and six earlier DATE routes. The six unread cases are P1705/P2173/P4111/P4337/P8362/P8632.

All 1,648 independent date obligations have actual attempts; many dates remain unresolved or indexed-only. Final disposition checks for 33 original integrity-flag publications and three legacy holds remain required. Keep the context-label gate open until those checks are complete. Do not repeat closed application audits or completed high batches.

## Execution and checks

Restore the whole archive to a separate empty directory, keeping internal paths. From that restored root:

    python -X utf8 work/screening_qa/validate_resume_manifest.py

This read-only command passed before migration: 22,601 hashed paths, zero errors, both initial passes complete. It checks structure and coverage, not scientific accuracy.

Publication commands mutate canonical outputs. Do not run them or restart the watcher while paused. Copied scripts assume the original relative layout.

environment/current-toolchain.json records current observed versions. It does not reconstruct every historical environment. Restoration into a different directory on this Windows machine passed: all 36,839 files matched their hashes, and the inherited validator passed all 22,601 manifest paths. See provenance/restore-validation.json. Fresh-environment and cross-machine execution remain unperformed.

Full-text selection, report families, deeper extraction and human verification remain later work. Screening totals establish no acceleration finding. Record future changes, reasons and whether results had already been inspected in the decision log.
