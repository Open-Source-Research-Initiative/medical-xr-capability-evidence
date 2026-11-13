"""Validate and atomically copy a completed Terra-2 shard batch into Terra's pass.

The two files remain byte-identical. This does not classify records or judge
source fidelity; it only validates structure and preserves a receipt. No file in
the shared pass is overwritten, and the other reviewer's decisions are not read.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = ["publication_id", "reviewer", "model", "screening_method_version", "prompt_version",
            "batch_id", "eligibility", "reason_code", "rationale", "supporting_evidence",
            "source_coordinate", "evidence_stream", "evidence_type", "evidence_type_basis",
            "evidence_type_check_status", "modality_stream", "medical_task", "date_status",
            "access_status", "prior_exposure", "human_verification", "screened_at",
            "source_memberships_json", "record_ids_json"]


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        result = list(reader)
        return reader.fieldnames or [], result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output_root", type=Path)
    parser.add_argument("batch")
    parser.add_argument("receipt_dir", type=Path)
    args = parser.parse_args()
    match = re.fullmatch(r"B(\d{4})", args.batch)
    if not match or not 191 <= int(match.group(1)) <= 380:
        raise ValueError("The second Terra shard is restricted to B0191–B0380")
    root = args.output_root.resolve()
    original = root / "terra_shard_2" / f"{args.batch}.csv"
    destination = root / "terra" / f"{args.batch}.csv"
    source_batch = root / "shared" / "batches" / f"{args.batch}.csv"
    args.receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = args.receipt_dir / f"terra_shard_2-{args.batch}-integration.json"
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing Terra batch: {destination}")
    if receipt_path.exists():
        raise FileExistsError(f"Refusing to overwrite receipt: {receipt_path}")
    _, inventory = rows(source_batch)
    fieldnames, assessed = rows(original)
    missing_fields = sorted(set(REQUIRED) - set(fieldnames))
    if missing_fields:
        raise ValueError(f"Required columns missing from shard: {missing_fields}")
    expected = [r["publication_id"] for r in inventory]
    observed = [r["publication_id"] for r in assessed]
    if len(expected) != len(set(expected)) or len(observed) != len(set(observed)) or set(expected) != set(observed):
        raise ValueError("Shard IDs must exactly match unique source batch IDs")
    source_by_id = {r["publication_id"]: r for r in inventory}
    for r in assessed:
        ident = r["publication_id"]
        missing = [key for key in REQUIRED if not (r.get(key) or "").strip()]
        if missing:
            raise ValueError(f"{ident}: blank required fields: {missing}")
        if r["batch_id"] != args.batch or r["eligibility"] not in {"INCLUDE", "EXCLUDE", "UNCERTAIN"}:
            raise ValueError(f"{ident}: invalid batch or eligibility")
        if r["human_verification"].strip().upper() != "PENDING" or ident not in r["source_coordinate"]:
            raise ValueError(f"{ident}: invalid human status or source coordinate")
        for field in ("source_memberships_json", "record_ids_json"):
            try:
                source_values = json.loads(source_by_id[ident][field])
                observed_values = json.loads(r[field])
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{ident}: invalid {field} JSON") from exc
            if not isinstance(source_values, list) or not isinstance(observed_values, list) or sorted(source_values) != sorted(observed_values):
                raise ValueError(f"{ident}: {field} differs from frozen source")
    content = original.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    descriptor, staging_name = tempfile.mkstemp(prefix=f".{args.batch}-", suffix=".staging", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as staging:
            staging.write(content)
            staging.flush()
            os.fsync(staging.fileno())
        os.rename(staging_name, destination)  # On Windows, raises if the destination exists.
    finally:
        if os.path.exists(staging_name):
            os.unlink(staging_name)
    if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Copied bytes did not match the original shard")
    receipt = {"created_utc": datetime.now(timezone.utc).isoformat(), "batch": args.batch,
               "source_shard": str(original), "integrated_copy": str(destination), "sha256": digest,
               "ids": sorted(observed), "count": len(observed),
               "limitations": "Structural validation and byte preservation only; no eligibility or source judgment."}
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"batch": args.batch, "count": len(observed), "sha256": digest,
                      "copy": str(destination), "receipt": str(receipt_path)}, indent=2))


if __name__ == "__main__":
    main()
