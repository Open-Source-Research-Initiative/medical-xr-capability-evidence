"""Validate Sol's ordered, append-only modality correction manifest.

Checks file presence, ID shape, explicit filters and unique precedence. It does
not inspect source evidence or decide whether a modality judgment is correct.
"""
import argparse
import csv
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("reviewer_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.reviewer_dir.resolve()
    manifest = json.loads((root / "modality-precedence-manifest.json").read_text(encoding="utf-8"))
    errors = []
    orders = []
    for entry in manifest["entries"]:
        order = entry.get("precedence")
        orders.append(order)
        path = (root / entry["file"]).resolve()
        if path.parent != root or not path.is_file():
            errors.append({"precedence": order, "issue": "missing_or_outside_reviewer_directory", "file": str(path)})
            continue
        with path.open(encoding="utf-8-sig", newline="") as source:
            ids = [r.get("publication_id", "") for r in csv.DictReader(source)]
        malformed = [i for i in ids if not re.fullmatch(r"P\d{7}", i)]
        if malformed:
            errors.append({"precedence": order, "issue": "malformed_ids", "ids": malformed})
        chosen = entry.get("ids")
        if chosen != "ALL_ROWS":
            if not isinstance(chosen, list):
                errors.append({"precedence": order, "issue": "missing_or_invalid_id_filter"})
            elif set(chosen) - set(ids):
                errors.append({"precedence": order, "issue": "filtered_ids_not_in_file", "ids": sorted(set(chosen) - set(ids))})
    if len(orders) != len(set(orders)):
        errors.append({"issue": "duplicate_precedence"})
    result = {"entries": len(orders), "unique_precedence": len(set(orders)), "errors": errors,
              "limitation": "Structural validation only; source evidence and modality decisions require independent assessment."}
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
