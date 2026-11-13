"""Recompute the prespecified agreed-exclusion sample for completed batches.

Uses only original blind batch files and the sample IDs in current audit metrics.
This checks reproducibility of selection, not correctness of classification or
adequacy of the source audit. The calibration set is not included.
"""
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [r["publication_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate IDs in {path}")
    return {r["publication_id"]: r for r in rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root
    artifacts = json.loads((root / "astra/current-artifacts.json").read_text(encoding="utf-8"))
    results = []
    for batch, entry in sorted(artifacts.items()):
        if not re.fullmatch(r"B\d{4}", batch) or not isinstance(entry, dict) or not entry.get("metrics"):
            continue
        left = read_rows(root / "sol" / f"{batch}.csv")
        right = read_rows(root / "terra" / f"{batch}.csv")
        if set(left) != set(right):
            raise ValueError(f"Independent batch ID sets differ for {batch}")
        candidates = [i for i in left if left[i].get("eligibility") == right[i].get("eligibility") == "EXCLUDE"]
        n_sample = min(len(candidates), max(10, math.ceil(0.10 * len(candidates))))
        expected = sorted(candidates, key=lambda i: hashlib.sha256(("MedicalXR-20261111-v03:" + i).encode()).hexdigest())[:n_sample]
        metrics_path = root / entry["metrics"]
        metric = json.loads(metrics_path.read_text(encoding="utf-8"))
        observed = metric.get("sampled_exclusion_ids", metric.get("exclusion_sample_ids"))
        if observed is None:
            results.append({"batch": batch, "status": "SAMPLE_FIELD_UNRECOGNIZED", "metrics": str(metrics_path)})
            continue
        results.append({"batch": batch, "agreed_exclusions": len(candidates), "expected_sample_size": n_sample,
                        "reported_sample_size": len(observed), "exact_set_match": set(expected) == set(observed),
                        "missing_ids": sorted(set(expected) - set(observed)),
                        "unexpected_ids": sorted(set(observed) - set(expected)), "metrics": str(metrics_path)})
    payload = {"seed": "MedicalXR-20261111-v03", "checked_batches": len(results), "batches": results,
               "limitation": "Checks the selection algorithm only; not clinical accuracy or human validation."}
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps({"checked_batches": len(results),
                      "mismatches_or_unreadable": [r for r in results if not r.get("exact_set_match", False)]}, indent=2))


if __name__ == "__main__":
    main()
