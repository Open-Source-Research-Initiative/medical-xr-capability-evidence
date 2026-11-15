# Open screening data

These 43 CSV tables expose the frozen project decision and provenance metadata without an account or access request. Download the repository or choose a table in the [catalog](catalog.csv). Read IDs as strings, retaining leading zeros and empty or unknown values.

| Start with | Contents |
| --- | --- |
| [provisional_publications.csv](ledger-projections/provisional_publications.csv) | All 18,976 frozen publication-group identifiers and bibliographic relationships |
| [record_membership.csv](ledger-projections/record_membership.csv) | Source-record membership and database identifiers |
| [pass-A-original-initials.csv](ledger-projections/pass-A-original-initials.csv) | All 18,976 original Pass A assessments and available reviewer/model provenance |
| [pass-B-original-initials.csv](ledger-projections/pass-B-original-initials.csv) | All 18,976 original Pass B assessments and available reviewer/model provenance |
| [adjudicated-current.csv](ledger-projections/adjudicated-current.csv) | 9,226 current adjudicated records, original labels and available correction references |
| [all-id-status-current.csv](ledger-projections/all-id-status-current.csv) | Per-ID progress and pending state |
| [required-audit-status-current.csv](ledger-projections/required-audit-status-current.csv) | Required audit progress |
| [human-verification-pending.csv](ledger-projections/human-verification-pending.csv) | Pending human verification; no completed human checks are claimed |

The remaining tables retain audit, queue, identity, integrity, modality, task and exposure metadata. The [derivation manifest](derivation-manifest.json) maps all 45 original input tables, their hashes, row counts and included/omitted columns to the 43 projections. Two inputs have no fields in this projection. The manifest retains its original historical `controlled-derivatives/1` format name; these copies are now public and byte-identical to that earlier export.

For complete source text, original rationales, historical versions and the two unprojected tables, use the [full evidence archive](../README.md#complete-evidence-archive). These convenient tables are projections, not replacements for the original record. Column meanings are in the [inherited dictionary](../../methods/inherited/data-dictionary.md); schema-only preservation records are in [schema-index.json](../schema-index.json).

Run `python scripts/verify_open_data.py` from the repository root to verify hashes, headers, original-source bindings, row counts and coverage. Run `python scripts/verify_open_data.py --archive PATH_TO_WORKSPACE_ZIP` to additionally verify every archived file without extracting it. Python 3.12 or later is sufficient; no extra packages are required.

Original project decision metadata is released under [CC BY 4.0](../../LICENSE.md). Cite Cole / Medical XR project, OSRI-0001, the snapshot date (13 November 2026), repository revision and any changes. Third-party sources retain their own notices and terms. Publication groups and repeated history rows are not independent studies. Screening remains paused and human verification remains zero.
