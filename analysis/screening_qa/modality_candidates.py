"""Locate records for manual modality review, without classifying any record."""
import argparse
import csv
import json
import re
from pathlib import Path


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("inventory", type=Path)
    p.add_argument("ledger", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    source = {r["publication_id"]: r for r in read_csv(args.inventory)}
    rows = read_csv(args.ledger)
    explicit = re.compile(r"\b(immers(?:ive|ion)|head[ -]?mounted|headset|hmd|augmented\s+reality|mixed\s+reality|hololens|oculus|meta\s+quest|htc\s+vive|playstation\s+vr)\b", re.I)
    found = []
    for r in rows:
        ident = r.get("publication_id", "")
        src = source.get(ident)
        if not src or r.get("modality_stream", "").strip().upper() != "XR":
            continue
        text = src.get("title", "") + " " + src.get("abstract", "")
        if not explicit.search(text):
            found.append({"publication_id": ident, "title": src.get("title", ""), "source_coordinate": r.get("source_coordinate", "")})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"ledger": str(args.ledger), "records_in_ledger": len(rows), "candidate_count": len(found), "candidates": found, "warning": "Candidate locator only: absence of these terms does not prove modality is unknown, and their presence does not prove how any method was used. Read each record; this is not screening or adjudication."}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"records_in_ledger": len(rows), "candidate_count": len(found), "output": str(args.output)}))


if __name__ == "__main__":
    main()
