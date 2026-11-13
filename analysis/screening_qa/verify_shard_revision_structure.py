"""Verify provenance/structure of prompted shard recheck rows, not correctness."""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path


REQUIRED = ("publication_id", "batch_id", "original_eligibility", "original_reason",
            "original_modality", "revised_eligibility", "revised_reason", "revised_modality",
            "reviewer", "source_coordinate", "source_support", "checkpoint", "confirmation",
            "human_verification", "review_context")


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    shard = args.root / "terra_shard_2"
    files = sorted(shard.glob("retrospective-decisions-*.csv"))
    errors, ids, files_seen = [], [], {}
    for path in files:
        rows = read(path)
        files_seen[str(path)] = {"rows": len(rows), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for row in rows:
            ident = row.get("publication_id", "")
            ids.append(ident)
            missing = [k for k in REQUIRED if not row.get(k, "").strip()]
            if missing:
                errors.append({"id": ident, "error": "missing_required", "fields": missing})
                continue
            original_path = shard / (row["batch_id"] + ".csv")
            original = {x["publication_id"]: x for x in read(original_path)}
            if ident not in original:
                errors.append({"id": ident, "error": "not_in_original_batch"})
                continue
            source = original[ident]
            for old, field in (("original_eligibility", "eligibility"), ("original_reason", "reason_code"),
                               ("original_modality", "modality_stream")):
                if row[old].casefold() != source[field].casefold():
                    errors.append({"id": ident, "error": "original_field_mismatch", "field": old})
            if row["revised_eligibility"] not in {"INCLUDE", "EXCLUDE", "UNCERTAIN"}:
                errors.append({"id": ident, "error": "invalid_revised_eligibility"})
            if row["human_verification"].upper() != "PENDING" or row["reviewer"] != "Terra_shard_2":
                errors.append({"id": ident, "error": "invalid_review_provenance"})
            if ident not in row["source_coordinate"]:
                errors.append({"id": ident, "error": "missing_id_in_source_coordinate"})
    duplicates = sorted(k for k, v in collections.Counter(ids).items() if v > 1)
    result = {"reviewed_rows": len(ids), "unique_ids": len(set(ids)), "duplicate_ids": duplicates,
              "structural_errors": errors, "input_files": files_seen,
              "limitation": "Checks mappings and provenance only; source validity, ledger precedence, and human review are not established."}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("reviewed_rows", "unique_ids", "duplicate_ids", "structural_errors")}))
    if duplicates or errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
