"""Prepare source text for the agreed-inclusion and sampled-exclusion audit.

Selection uses the two original independent batch files and the prespecified
seed. It is a source bundle, not an automated clinical judgment or adjudication.
"""
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path


def load(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    if len({r["publication_id"] for r in rows}) != len(rows):
        raise ValueError(f"Duplicate IDs in {path}")
    return {r["publication_id"]: r for r in rows}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output_root", type=Path)
    parser.add_argument("batch")
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"B\d{4}", args.batch):
        raise ValueError("Batch must use B0000 format")
    root = args.output_root
    sol_path = root / "sol" / f"{args.batch}.csv"
    terra_path = root / "terra" / f"{args.batch}.csv"
    source_path = root / "shared" / "batches" / f"{args.batch}.csv"
    sol, terra, source = map(load, (sol_path, terra_path, source_path))
    if set(sol) != set(terra) or set(sol) != set(source):
        raise ValueError("Original reviewer and frozen batch ID sets differ")
    include = [i for i in source if sol[i]["eligibility"] == terra[i]["eligibility"] == "INCLUDE"]
    exclude = [i for i in source if sol[i]["eligibility"] == terra[i]["eligibility"] == "EXCLUDE"]
    sample_n = min(len(exclude), max(10, math.ceil(0.1 * len(exclude))))
    sample = sorted(exclude, key=lambda i: hashlib.sha256(("MedicalXR-20261111-v03:" + i).encode()).hexdigest())[:sample_n]
    edge = [i for i in source if sol[i]["eligibility"] != terra[i]["eligibility"] or
            "UNCERTAIN" in (sol[i]["eligibility"], terra[i]["eligibility"])]
    def compact(i, category):
        original = source[i]
        return {"publication_id": i, "audit_category": category, "title": original["title"],
                "abstract": original["abstract"], "abstract_record_id": original["abstract_record_id"],
                "year": original["year"], "date_tags_json": original["date_tags_json"], "doi": original["doi"],
                "sol_original": {k: sol[i].get(k, "") for k in ("eligibility", "reason_code", "rationale", "modality_stream", "evidence_type")},
                "terra_original": {k: terra[i].get(k, "") for k in ("eligibility", "reason_code", "rationale", "modality_stream", "evidence_type")}}
    payload = {"batch": args.batch, "sample_seed": "MedicalXR-20261111-v03", "source_sha256": digest(source_path),
               "sol_original_sha256": digest(sol_path), "terra_original_sha256": digest(terra_path),
               "agreed_inclusions": [compact(i, "agreed_inclusion") for i in include],
               "sampled_agreed_exclusions": [compact(i, "sampled_agreed_exclusion") for i in sample],
               "edge_ids": edge,
               "limitation": "Automatically selected source bundle only; every source judgment still requires an actual reviewer."}
    if args.bundle.exists():
        raise FileExistsError(f"Refusing to overwrite audit bundle: {args.bundle}")
    args.bundle.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"batch": args.batch, "agreed_inclusions": len(include), "agreed_exclusions": len(exclude),
                      "sampled_exclusions": len(sample), "edge_ids": edge, "bundle": str(args.bundle)}, indent=2))


if __name__ == "__main__":
    main()
