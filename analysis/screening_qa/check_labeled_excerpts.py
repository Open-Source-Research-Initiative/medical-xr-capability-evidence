"""Flag source text labeled as exact that does not match its frozen source.

This check strips only recognized labels and normalizes Unicode, quotes, dashes
and whitespace. A match does not establish relevance or correctness of the
screening decision; a mismatch may be a benign transcription variant, a
paraphrase, or an excerpt from a source other than the frozen text. No record
is changed or automatically reclassified.
"""
import argparse
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path


def normalize(value):
    value = unicodedata.normalize("NFKC", value or "").casefold()
    value = re.sub(r"[\u2010-\u2015\u2212]", "-", value)
    value = re.sub(r"[\u2018\u2019]", "'", value)
    value = re.sub(r"[\u201c\u201d]", '"', value)
    return re.sub(r"\s+", " ", value).strip(" \t\r\n\"'“”‘’")


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source = {r["publication_id"]: r for r in read(args.source)}
    rows = read(args.ledger)
    if len(source) != len(rows) or set(source) != {r["publication_id"] for r in rows}:
        raise ValueError("Frozen source and ledger IDs must match exactly")
    result = {"source": str(args.source), "ledger": str(args.ledger),
              "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
              "ledger_sha256": hashlib.sha256(args.ledger.read_bytes()).hexdigest(),
              "checked": 0, "matched": 0, "not_exact_label": 0, "flagged": []}
    for row in rows:
        support = row.get("supporting_evidence", "")
        match = re.match(r"^exact\s+(abstract|title)\s+excerpt\s*:\s*(.+)$", support, re.I | re.S)
        if not match:
            result["not_exact_label"] += 1
            continue
        field, excerpt = match.groups()
        result["checked"] += 1
        frozen = source[row["publication_id"]].get(field.lower(), "")
        if normalize(excerpt) and normalize(excerpt) in normalize(frozen):
            result["matched"] += 1
        else:
            result["flagged"].append({"publication_id": row["publication_id"], "source_field": field.lower(),
                                      "claimed_excerpt": excerpt, "source_coordinate": row.get("source_coordinate", ""),
                                      "status": "NEEDS_SOURCE_REVIEW"})
    result["limitation"] = "Literal source matching is not a relevance, eligibility, or human-accuracy audit."
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("ledger", "checked", "matched", "not_exact_label")}, ensure_ascii=False))
    print("flagged=" + str(len(result["flagged"])))


if __name__ == "__main__":
    main()
