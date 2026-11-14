# Checking a proposed public contribution

Use a complete Git clone and Python 3.12 or later. From the public repository root:

```
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -v
python scripts/verify_public_tree.py
python -O scripts/verify_public_tree.py
python scripts/show_example.py
```

Before committing, stage the intended files and run `python scripts/verify_public_tree.py --staged`. Selected-tree bytes must match working files. No restricted inputs or original screening workspace are required. The 51 historical code copies are preserved by exact hashes; the independent example has its own command.

The checker inspects selected files and reachable branches/tags, including historical blob, commit and annotated-tag content. It checks names, bounded credential/private-path patterns, decoded JSON strings, public text encoding, source-copy hashes, import ancestry and the pause record. It rejects shallow or grafted histories. Explicit guards remain active under Python optimization.

An optional `--receipt PATH` creates a new receipt after successful checks; existing destinations are refused. The older `provenance/publication-check.json` describes the earlier export revision and is retained as historical evidence. Do not overwrite it or treat it as a result for a later revision.

These are bounded automated checks, not arbitrary-encoding detection, rights clearance, a complete secret scanner or scientific validation. A clean result does not authorize publication. Deletion leaves historical contents reachable. Do not push controlled draft refs or bundles. Follow the human's reviewed authorization and [OSRI-0.1.0](https://github.com/Open-Source-Research-Initiative/osri/blob/8c39a0a36c0e962060659b1d51f666c367f9464a/governance/contribution-standards.md).
