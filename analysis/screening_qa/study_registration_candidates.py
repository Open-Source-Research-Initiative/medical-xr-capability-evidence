"""Locate registration strings repeated across frozen inventory groups.

This only searches title and abstract; registry identifiers may be missing,
mistyped, or refer to earlier/background research. Matches are candidates for
source verification, not automatic report merges or screening decisions.
"""
import argparse
import collections
import csv
import json
import re
from pathlib import Path

PATTERN = re.compile(
    r"\b(?:NCT\d{8}|ISRCTN\d{8}|IRCT\d{8,}N\d+|ACTRN\d{14}|"
    r"DRKS\d{8}|ChiCTR[A-Z]*\d{6,})\b", re.IGNORECASE
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    groups = collections.defaultdict(list)
    with args.inventory.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            text = (row.get("title") or "") + "\n" + (row.get("abstract") or "")
            for registration in {m.group().upper() for m in PATTERN.finditer(text)}:
                groups[registration].append(row)
    repeated = {key: rows for key, rows in groups.items() if len(rows) > 1}
    fields = ["candidate_registration", "candidate_group_size", "publication_id", "title", "doi",
              "source_memberships_json", "record_ids_json"]
    with args.output.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        for registration, rows in sorted(repeated.items()):
            for row in sorted(rows, key=lambda r: r["publication_id"]):
                writer.writerow({"candidate_registration": registration, "candidate_group_size": len(rows),
                                 **{key: row.get(key, "") for key in fields[2:]}})
    print(json.dumps({"repeated_registration_strings": len(repeated),
                      "candidate_rows": sum(map(len, repeated.values())),
                      "unique_publication_ids": len({r["publication_id"] for rows in repeated.values() for r in rows}),
                      "note": "Only literal title/abstract matches; candidate links require source verification."}, indent=2))


if __name__ == "__main__":
    main()
