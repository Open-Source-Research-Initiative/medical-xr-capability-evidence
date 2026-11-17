# Checking a proposed public contribution

Use a complete Git clone and Python 3.12 or later; [local setup](quickstart.md#explore-locally) shows the commands. A Code → Download ZIP copy has no Git history and cannot run the public-history checker. For a browser-only documentation change, report the wording/links checked and let required PR CI run these checks. From the public repository root:

```
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -v
python scripts/verify_public_tree.py
python -O scripts/verify_public_tree.py
python scripts/verify_open_data.py
python -O scripts/verify_open_data.py
python scripts/show_example.py
python scripts/lookup_publication.py P0000314
```

Before committing, stage the intended files and run `python scripts/verify_public_tree.py --staged`. Selected-tree bytes must match working files. No original screening workspace is required. The 51 historical code copies are preserved by exact hashes; the independent example has its own command.

The open-data verifier checks all 43 tables against their source-linked derivation manifest, catalog, frozen ID sets, saved label counts and empty human-result template. It binds each of the 45 original inputs to the immutable legacy manifest. CI runs it on Linux and Windows, normally and with optimization. After downloading the full release archive, run `python scripts/verify_open_data.py --archive PATH_TO_WORKSPACE_ZIP` to additionally check its whole-file SHA-256 and all 36,839 member hashes without extracting it.

The public checkers deliberately preserve the **November 13** pause record and 9,226 adjudications. Their `PAUSED` output is a historical-snapshot check, not a current-run status or validation of later adjudications. The [17 November checkpoint and work map](../data/runs/2026-11-17/README.md) separately report 11,076 integrated adjudications and the exact 7,900 pending IDs. New work-map/packet tests check assignment coverage and frozen-input reconstruction; those checks do not perform scientific screening. The [resumed-run status](active-screening.md) describes the local manifest check and why the complete newer decisions cannot yet be reproduced from the original release.

To test a real contributor packet, use `python scripts/prepare_screening_packet.py --batch B0215 --archive PATH_TO_WORKSPACE_ZIP --output NEW_PACKET_DIRECTORY`, or use `--source-root EXTRACTED_ARCHIVE`. The output must be a new directory. This separately verifies the selected five frozen inputs, exact ID membership and saved audit sample. It creates no scientific assessment or reading credit. Keep generated source packets outside the public Git tree.

The checker also requires all 13 inherited methods in `provenance/open-methods.json`. Each unique public/original path pair must link to the preserved original file manifest, and both its SHA-256 and byte count must match. Every tracked file under `methods/inherited/` must be listed. Editing a method and updating its declared hash/size still fails against the original manifest. The original manifest is itself checked against the recorded import hash. Clean receipts include `public_unchanged_method_copies`. Synthetic regressions exercise both HEAD and staged validation, including under Python optimization.

The checker inspects selected files and reachable branches/tags, including historical blob, commit and annotated-tag content. It checks names, bounded credential/private-path patterns, decoded JSON strings, public text encoding, source-copy hashes, import ancestry and the pause record. It rejects shallow or grafted histories. Explicit guards remain active under Python optimization.

An optional `--receipt PATH` creates a new receipt after successful checks; existing destinations are refused. The older `provenance/publication-check.json` describes the earlier export revision and is retained as historical evidence. Do not overwrite it or treat it as a result for a later revision.

These are bounded automated checks, not arbitrary-encoding detection, rights clearance, a complete secret scanner or scientific validation. A clean result alone does not authorize publication. Under Cole's [17 November standing instruction](screening-workflow.md), appropriate model/source review and required CI gate provisional integration/public work within the issue-driven screening scope. This is a recorded project-specific review-timing difference from [OSRI-0.1.0](https://github.com/Open-Source-Research-Initiative/osri/blob/8c39a0a36c0e962060659b1d51f666c367f9464a/governance/contribution-standards.md); final human scientific review/sign-off follows completion of all model work and the immutable packet. Do not claim PI acceptance from a green check or model review. Deletion leaves historical contents reachable. Keep controlled draft refs and bundles out of public Git, and preserve source-sharing limits.
