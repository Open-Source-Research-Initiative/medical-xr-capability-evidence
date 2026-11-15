# Public data and evidence

The project data is available publicly, without an invitation or private-repository access. The preserved snapshot is dated **13 November 2026**; this public data release was prepared on **15 November 2026**. Screening remains paused after B0182/source audit 0216, and documented human verification remains zero.

## Browse the data

The [open data directory](open/README.md) contains 43 CSV tables: all 18,976 frozen publication IDs, both complete initial decision passes, 9,226 adjudicated records, source memberships, review provenance, pending queues and audit metadata. The [catalog](open/catalog.csv) lists paths, row counts, sizes, hashes and original-source mappings. The [derivation manifest](open/derivation-manifest.json) specifies every retained and omitted column from 45 original inputs.

Read IDs as strings and preserve leading zeros, unknown values and qualified dates. Use the [methods and dictionary](../methods/README.md) to interpret fields. `sources.csv` at the repository root indexes migration guidance; it is not the research inventory. The human-verification and feasibility templates remain blank.

## Complete evidence archive

[Download the complete evidence snapshot](https://github.com/Open-Source-Research-Initiative/medical-xr-from-capabilities-to-sustainable-use/releases/tag/evidence-2026-11-13) for all **36,839 original files**, including raw RIS exports, bulk abstracts, frozen inventories, original free-text decisions and rationales, source receipts, prompts, scripts, earlier drafts and corrections. It includes the historical tables and columns omitted from the convenient CSV projections. The archive preserves the original internal paths and bytes.

| Asset | Size and verification |
| --- | --- |
| `workspace.zip` | 212,673,172 compressed bytes; 853,955,550 uncompressed bytes |
| `file-manifest.csv` | 36,839 paths, byte sizes, original modification times and SHA-256 hashes; also [versioned in Git](../provenance/legacy-file-manifest.csv) |
| `SHA256SUMS.txt` | SHA-256 values for the archive and manifest |
| `RESTORE.md` | Standalone layout, verification and restoration instructions |

Archive SHA-256: `31bb771230857c4eb4dd0a7d3d0fff8861d7fa996f3de9a02b36f746569396bb`.

From a public clone, run:

```sh
python scripts/verify_open_data.py
python scripts/verify_open_data.py --archive /path/to/workspace.zip
```

The second command verifies every original file inside the ZIP without extracting it. Extract only into a separate empty directory; preserve internal paths. The archive contains original workstation paths in historical scripts and documentation. Modification times are preservation metadata, not reconstructed commit dates.

From the restored workspace, the inherited read-only structural check is:

```sh
python -X utf8 work/screening_qa/validate_resume_manifest.py
```

Same-machine restoration previously passed all 36,839 archive hashes and the 22,601-path inherited validator. Cross-machine reproduction of the original analysis remains unperformed. Copied historical scripts depend on the original layout. Some publication scripts and the watcher mutate research outputs; do not run those while screening is paused.

## Reuse and provenance

Cole / @ajhcs requested public sharing and confirmed on 15 November 2026 that the records, exports and bulk materials are OK to share. [The publication record](../provenance/open-data-publication.json) records that confirmation and the archive checks. This is owner clearance, not an independent license audit. Original project code is MIT; original project prose and decision metadata are CC BY 4.0. Third-party material retains its own source terms and notices; see [LICENSE.md](../LICENSE.md).

The [archive check](../provenance/archive-publication-check-20261115.json) confirms all original hashes and records bounded credential checks. These checks do not establish scientific accuracy. INCLUDE is a provisional route to later full-text assessment; publication groups are not verified independent studies, and repeated historical rows are not new observations.

The earlier private metadata companion is a historical collaboration copy; access to it is no longer required for the released data. Older records describing these datasets as local-only or restricted reflect the state before the 15 November clearance. Later administration/context packages and the original controlled Git bundle are outside the frozen research snapshot. Their [history map](../provenance/history-map.json) remains preserved; this release does not publish unrelated private context or rewrite original history.

## Contribute

Read [Join the project](../docs/join-the-project.md) and [CONTRIBUTING.md](../CONTRIBUTING.md). Anyone can inspect, download and fork the public record. Scientific assignments and write permissions are coordinated by Cole. Before source-review work, read [human verification](../docs/human-verification.md) and disclose any prior exposure to the public AI decisions.
