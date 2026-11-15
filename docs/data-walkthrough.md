# Understand one publication group

The [43 public CSV tables](../data/open/README.md) are a frozen view of work saved on 13 November 2026. They contain existing AI assessments and review metadata. Use them to inspect the research record; they are not validated clinical findings or a final list of included studies.

**For prospective human source reviewers:** start with [the source-first procedure](human-verification.md) before viewing decisions below. Record any prior exposure.

## Terms used in the tables

| Term | Meaning here |
| --- | --- |
| Publication group | A provisional group of exported bibliographic records assigned one `publication_id`. It is not a verified independent study. |
| Pass A / Pass B | The two saved initial AI assessments. Their actual reviewer/model identities and known exposure qualifications are preserved; these are not human reviews. |
| Adjudication | A later, still-provisional reconciliation using available source evidence. It can retain uncertainty and does not establish a gold standard. |
| Projection | A copy of selected columns from an original table. The full original, including omitted text, is in the evidence archive. |
| `INCLUDE` | Advance for later empirical full-text assessment; not final inclusion. |
| `EXCLUDE` | The saved exclusion route at that assessment stage; not proof that every exclusion is correct. |
| `UNCERTAIN` | An unresolved route at that stage; consult the reason, access and pending-work fields. |

The [catalog](../data/open/catalog.csv) gives table row counts, sizes, hashes and original-source mappings. Those row counts describe different, overlapping views. Do not add them to estimate studies, participants or completed reviews.

## Follow a single ID

Use the exact `publication_id`, including its leading zeros, to connect these tables:

1. `provisional_publications.csv`: inventory identifiers, candidate DOI/year values, grouping status and memberships.
2. `pass-A-original-initials.csv` and `pass-B-original-initials.csv`: each original assessment, reviewer/model, eligibility, streams and artifact references.
3. `adjudicated-current.csv`: a current adjudicated row when one exists, plus saved correction and provenance fields.
4. `record_membership.csv`: the underlying source-record identifiers. Several records may belong to one publication group.

From a [local checkout](quickstart.md#explore-locally), run:

```sh
python scripts/lookup_publication.py P0000314
python scripts/lookup_publication.py P0000314 --json
```

The lookup reads the public inventory, original-pass projections and optional adjudication projection. It preserves their values in JSON, including empty strings and artifact/hash references; it does not restore columns omitted from the projections. Missing adjudication is `null` in JSON and “not yet recorded” in the summary. It does not mean EXCLUDE: 9,750 groups have no completed adjudication in this snapshot. An unknown ID produces an error; short IDs are not silently padded or merged.

The matching [worked trace](../examples/README.md) explains one existing source/configuration correction. That example does not establish scientific accuracy across the corpus.

## Read the provenance as well as the decision

| Field or field family | How to use it |
| --- | --- |
| `publication_id`, `record_ids_json`, `source_memberships_json` | Connect the provisional group to source records; preserve values as strings. Fields ending `_json` contain JSON within a CSV cell. |
| `eligibility`, `adjudicated_eligibility`, `reason_code` | Keep the assessment stage attached to each route. Initial and later values can differ. |
| `reviewer`, `model`, `model_version` | Retain recorded identities and unknown/empty fields. Do not fill an unknown model from a neighboring row. |
| `initial_artifact`, `adjudication_artifact`, `source_revision_artifact` and their hashes | Locate the original decision and later overlay in the evidence archive. These are archive-relative references, not links to missing files in the public Git tree. |
| Access, date, integrity, audit and pending fields | Qualify what was read, resolved or left open. An eligibility label alone does not describe these limits. |
| `human_verification` | The saved human-review state. No completed human verification is documented at this checkpoint. |

For exact column meanings, use the [inherited dictionary](../methods/inherited/data-dictionary.md). The [derivation manifest](../data/open/derivation-manifest.json) names omitted columns and the original file/hash for every projection. Empty fields remain empty; absence is not an affirmative negative.

## Get the complete record

GitHub refuses to preview some large CSVs. Use **Download raw file**, a repository download or the lookup above. For original rationales, source text, all historical tables and prompts, get the evidence release's **`workspace.zip`** and follow [verification and restoration](../data/README.md#complete-evidence-archive). The automatic **Source code (zip)** / **Source code (tar.gz)** assets contain the Git repository snapshot and are not the full evidence archive.
