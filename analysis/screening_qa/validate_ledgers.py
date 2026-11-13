"""Independent structural/source-support check for medical XR screening ledgers.

This flags unsupported-looking excerpts for review; it does not decide whether a
paraphrase is accurate or whether an eligibility judgment is correct.
"""
import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path


def normalized(value):
    text = unicodedata.normalize("NFKC", value or "").casefold()
    text = re.sub(r"[\u2010-\u2015\u2212]", "-", text)
    text = re.sub(r"[\u2018\u2019]", "'", text)
    text = re.sub(r"[\u201c\u201d]", '"', text)
    return re.sub(r"\s+", " ", text).strip(" \t\r\n\"'“”‘’")


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    inventory = {r["publication_id"]: r for r in read_csv(args.inventory)}
    rows = read_csv(args.ledger)
    counts = Counter(r.get("publication_id", "") for r in rows)
    errors, excerpt_flags, ellipsis_review = [], [], []
    for number, row in enumerate(rows, start=2):
        ident = row.get("publication_id", "").strip()
        if not ident or ident not in inventory:
            errors.append({"row": number, "id": ident, "issue": "unknown_or_empty_id"})
            continue
        if row.get("eligibility") not in {"INCLUDE", "EXCLUDE", "UNCERTAIN"}:
            errors.append({"row": number, "id": ident, "issue": "invalid_eligibility"})
        if not row.get("supporting_evidence", "").strip():
            errors.append({"row": number, "id": ident, "issue": "empty_support"})
            continue
        source = inventory[ident]
        haystack = " ".join(normalized(source.get(k, "")) for k in ("title", "abstract", "date_tags_json", "year", "document_types_json"))
        evidence = normalized(row["supporting_evidence"])
        parts = re.split(r"\s*(?:\.{3,}|…)\s*", evidence)
        cursor = 0
        ordered = True
        for part in parts:
            found = haystack.find(part, cursor) if part else cursor
            if found < 0:
                ordered = False
                break
            cursor = found + len(part)
        if len(parts) > 1:
            ellipsis_review.append({"row": number, "id": ident, "support": row["supporting_evidence"], "pieces_in_source_order": ordered})
        if evidence not in haystack and not (len(parts) > 1 and ordered):
            excerpt_flags.append({"row": number, "id": ident, "support": row["supporting_evidence"], "coordinate": row.get("source_coordinate", "")})
        if ident not in row.get("source_coordinate", ""):
            errors.append({"row": number, "id": ident, "issue": "coordinate_lacks_id"})
    duplicates = sorted(k for k, v in counts.items() if v > 1)
    result = {
        "inventory_count": len(inventory),
        "ledger": str(args.ledger),
        "rows": len(rows),
        "unique_ids": len(counts),
        "pending_if_only_this_ledger": len(set(inventory) - set(counts)),
        "eligibility_counts": dict(Counter(r.get("eligibility", "") for r in rows)),
        "duplicate_ids": duplicates,
        "structural_errors": errors,
        "evidence_not_literal_count": len(excerpt_flags),
        "evidence_not_literal_review_queue": excerpt_flags,
        "ellipsis_review_queue": ellipsis_review,
        "limitation": "Nonliteral support may be a valid paraphrase or may have a full-text source; assess against its stated source before judging fidelity. Ellipsis may omit important qualifiers even when fragments match in order. Literal matching does not validate the decision.",
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
