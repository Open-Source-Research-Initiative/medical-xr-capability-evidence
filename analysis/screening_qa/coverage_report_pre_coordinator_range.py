"""Reconcile live reviewer checkpoints against the frozen inventory.

Partial and complete files for the same batch are treated as revisions of the
same assessments, never as additional independent records. This script does
not change reviewer decisions or classify unscreened records.
"""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("inventory", type=Path)
    p.add_argument("root", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    ids = {r["publication_id"] for r in read_csv(args.inventory)}
    result = {"inventory_ids": len(ids), "reviewers": {}}
    completed = {}
    for reviewer in ("sol", "terra"):
        folder = args.root / reviewer
        calibration = folder / "calibration-v0.3.csv"
        decisions = {}
        errors = []
        if calibration.exists():
            for row in read_csv(calibration):
                key = row.get("publication_id", "")
                if key in decisions:
                    errors.append({"type": "duplicate_calibration", "id": key})
                decisions[key] = row
        batches = {}
        for f in folder.glob("B*.csv"):
            m = re.fullmatch(r"(B\d{4})(-partial)?\.csv", f.name, flags=re.I)
            if m:
                batches.setdefault(m.group(1).upper(), []).append(f)
        batch_summary = []
        for batch, paths in sorted(batches.items()):
            # A final file takes priority over an earlier partial file for the same batch.
            selected = sorted(paths, key=lambda q: (q.stem.endswith("-partial"), q.name))[0]
            source = args.root / "shared" / "batches" / (batch + ".csv")
            expected = {r["publication_id"] for r in read_csv(source)} if source.exists() else set()
            rows = read_csv(selected)
            got = [r.get("publication_id", "") for r in rows]
            duplicates = sorted(x for x, n in Counter(got).items() if n > 1)
            if duplicates:
                errors.append({"type": "duplicate_batch_ids", "batch": batch, "ids": duplicates})
            for key, row in zip(got, rows):
                if key in decisions:
                    errors.append({"type": "duplicate_across_batches", "id": key, "batch": batch})
                decisions[key] = row
            batch_summary.append({"batch": batch, "file": str(selected.relative_to(args.root)), "assessed": len(set(got)), "expected": len(expected), "missing": len(expected - set(got)), "extra_ids": sorted(set(got) - expected)})
        # The second Terra worker saves immutable, disjoint 10-row partials in
        # its own folder. Count them as saved initial assessments until a final
        # byte-identical batch has been integrated into the main Terra folder.
        # These are not final batches or extra independent reviewers of the same ID.
        if reviewer == "terra":
            shard = args.root / "terra_shard_2"
            partials = {}
            if shard.exists():
                for f in shard.glob("B*-partial-*.csv"):
                    m = re.fullmatch(r"(B\d{4})-partial-\d+\.csv", f.name, flags=re.I)
                    if m and 191 <= int(m.group(1)[1:]) <= 380:
                        partials.setdefault(m.group(1).upper(), []).append(f)
            for batch, paths in sorted(partials.items()):
                if (folder / (batch + ".csv")).exists():
                    continue
                source = args.root / "shared" / "batches" / (batch + ".csv")
                expected = {r["publication_id"] for r in read_csv(source)} if source.exists() else set()
                got = []
                for f in sorted(paths):
                    for row in read_csv(f):
                        key = row.get("publication_id", "")
                        if key not in expected or not row.get("supporting_evidence", "").strip() or row.get("eligibility") not in {"INCLUDE", "EXCLUDE", "UNCERTAIN"}:
                            errors.append({"type": "invalid_shard_partial_row", "batch": batch, "id": key})
                            continue
                        if key in decisions:
                            errors.append({"type": "duplicate_shard_partial", "batch": batch, "id": key})
                            continue
                        decisions[key] = row
                        got.append(key)
                batch_summary.append({"batch": batch, "file": "terra_shard_2/partial chunks",
                                      "assessed": len(got), "expected": len(expected),
                                      "missing": len(expected - set(got)), "extra_ids": [],
                                      "partial_files": [str(f.relative_to(args.root)) for f in sorted(paths)]})
            # The coordinator is a separately identified Terra-side reviewer.
            # Count its saved B0379 partials without treating them as a completed
            # batch, and never count them again after the final integrated copy.
            coordinator = args.root / "terra_coordinator"
            batch = "B0379"
            paths = sorted(coordinator.glob("B0379-partial-*.csv")) if coordinator.exists() else []
            if paths and not (folder / (batch + ".csv")).exists():
                source = args.root / "shared" / "batches" / (batch + ".csv")
                expected = {r["publication_id"] for r in read_csv(source)}
                got = []
                for f in paths:
                    for row in read_csv(f):
                        key = row.get("publication_id", "")
                        if (key not in expected or not row.get("supporting_evidence", "").strip()
                                or row.get("eligibility") not in {"INCLUDE", "EXCLUDE", "UNCERTAIN"}
                                or row.get("reviewer") != "Coordinator_Terra_shard_3"):
                            errors.append({"type": "invalid_coordinator_partial_row", "batch": batch, "id": key})
                            continue
                        if key in decisions:
                            errors.append({"type": "duplicate_coordinator_partial", "batch": batch, "id": key})
                            continue
                        decisions[key] = row
                        got.append(key)
                batch_summary.append({"batch": batch, "file": "terra_coordinator/partial chunks",
                                      "assessed": len(got), "expected": len(expected),
                                      "missing": len(expected - set(got)), "extra_ids": [],
                                      "partial_files": [str(f.relative_to(args.root)) for f in paths]})
        valid = set(decisions) & ids
        invalid = sorted(set(decisions) - ids)
        result["reviewers"][reviewer] = {"assessed_unique": len(valid), "pending": len(ids - valid), "invalid_ids": invalid, "errors": errors, "eligibility_counts": dict(Counter(decisions[i].get("eligibility", "") for i in valid)), "batches": batch_summary}
        completed[reviewer] = valid
    result["common_assessed_ids"] = len(completed["sol"] & completed["terra"])
    result["at_least_one_assessed_ids"] = len(completed["sol"] | completed["terra"])
    result["both_pending_ids"] = len(ids - (completed["sol"] | completed["terra"]))
    result["human_verification"] = "PENDING for all AI assessments unless separately documented"
    result["limitation"] = "Structural coverage only. Counts do not validate classification, source fidelity, study independence, or human review."
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
