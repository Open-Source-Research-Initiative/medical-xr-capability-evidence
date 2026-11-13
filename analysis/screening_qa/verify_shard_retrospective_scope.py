"""Verify the added Terra reviewer's 400 + 5 retrospective scope by ID.

This only verifies checkpoint coverage against frozen batches and the first
saved B0199 partial. It does not validate the judgments or confirm that revised
fields have been incorporated into adjudicated/current ledgers.
"""
import argparse
import collections
import csv
import hashlib
import json
import re
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_ids(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [row["publication_id"] for row in csv.DictReader(handle)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    shard = args.root / "terra_shard_2"
    sources = [args.root / "shared" / "batches" / f"B{n:04d}.csv" for n in range(191, 199)]
    sources.append(shard / "B0199-partial-001.csv")
    source_ids = [ident for path in sources for ident in csv_ids(path)]
    checkpoints = sorted(shard.glob("modality-recheck-checkpoint-*.md"))
    checked = []
    for path in checkpoints:
        checked.extend(re.findall(r"^(?:\|\s*|-\s*)(P\d{7})(?=\s*(?:\||/|:))",
                                  path.read_text(encoding="utf-8-sig"), re.MULTILINE))
    counts = collections.Counter(checked)
    result = {"expected_count": len(source_ids), "unique_expected": len(set(source_ids)),
              "checkpoint_rows": len(checked), "unique_checked": len(counts),
              "missing_ids": sorted(set(source_ids) - set(counts)),
              "extra_ids": sorted(set(counts) - set(source_ids)),
              "duplicate_ids": sorted(k for k, v in counts.items() if v > 1),
              "source_hashes": {str(p): digest(p) for p in sources},
              "checkpoint_hashes": {str(p): digest(p) for p in checkpoints},
              "limitation": "Coverage only; source judgments, precedence integration and human validation remain separate."}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {k: result[k] for k in ("expected_count", "unique_expected", "checkpoint_rows", "unique_checked", "missing_ids", "extra_ids", "duplicate_ids")}
    print(json.dumps(summary, ensure_ascii=False))
    if len(set(source_ids)) != len(source_ids) or result["missing_ids"] or result["extra_ids"] or result["duplicate_ids"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
