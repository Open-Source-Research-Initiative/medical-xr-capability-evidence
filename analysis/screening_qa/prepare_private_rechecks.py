"""Build source-complete, reviewer-private recheck views; never classify records."""
import argparse
import csv
import json
from pathlib import Path


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("inventory", type=Path)
    p.add_argument("ledger", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--reviewer", choices=["sol", "terra"], required=True)
    p.add_argument("--max-chars", type=int, default=18000)
    p.add_argument("--max-records", type=int, default=10)
    args = p.parse_args()
    src = {r["publication_id"]: r for r in read_csv(args.inventory)}
    ledger = read_csv(args.ledger)
    if any(r.get("reviewer", "").strip().casefold() != args.reviewer for r in ledger):
        raise SystemExit("Wrong-reviewer rows in ledger; refusing to create view.")
    if len({r["publication_id"] for r in ledger}) != len(ledger):
        raise SystemExit("Duplicate IDs in ledger; resolve revisions before preparing view.")
    args.out.mkdir(parents=True, exist_ok=True)
    views, current, chars = [], [], 0
    for decision in ledger:
        ident = decision["publication_id"]
        if ident not in src:
            raise SystemExit(f"Unknown ID {ident}")
        row = src[ident]
        record = {
            "publication_id": ident,
            "title": row.get("title", ""),
            "abstract": row.get("abstract", ""),
            "abstract_record_id": row.get("abstract_record_id", ""),
            "doi": row.get("doi", ""),
            "year": row.get("year", ""),
            "document_types_json": row.get("document_types_json", ""),
            "prior_own_eligibility": decision.get("eligibility", ""),
            "prior_own_modality": decision.get("modality_stream", ""),
            "prior_own_evidence_stream": decision.get("evidence_stream", ""),
            "prior_own_rationale": decision.get("rationale", ""),
            "prior_own_source_evidence": decision.get("supporting_evidence", ""),
        }
        line = json.dumps(record, ensure_ascii=False)
        if current and (len(current) >= args.max_records or chars + len(line) > args.max_chars):
            views.append(current)
            current, chars = [], 0
        current.append(line)
        chars += len(line)
    if current:
        views.append(current)
    for i, view in enumerate(views, start=1):
        (args.out / f"{args.reviewer}-recheck-{i:04}.jsonl").write_text("\n".join(view) + "\n", encoding="utf-8")
    manifest = {"reviewer": args.reviewer, "source_ledger": str(args.ledger), "record_count": len(ledger), "views": len(views), "max_chars": args.max_chars, "max_records": args.max_records, "warning": "Private source views contain only this reviewer's original decisions. They are organizational artifacts, not new assessments; no original source or ledger was changed."}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest))


if __name__ == "__main__":
    main()
