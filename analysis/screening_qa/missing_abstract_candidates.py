"""List frozen inventory records whose abstract field is blank.

This is a source-access locator only. A full text or other source may exist,
and a populated abstract does not prove that full text is available. Never
derive an eligibility decision from this list.
"""
import argparse
import csv
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    columns = ["publication_id", "title", "year", "doi", "document_types_json",
               "source_memberships_json", "record_ids_json"]
    with args.inventory.open(encoding="utf-8-sig", newline="") as source:
        candidates = [{column: row.get(column, "") for column in columns}
                      for row in csv.DictReader(source) if not (row.get("abstract") or "").strip()]
    with args.output.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=columns)
        writer.writeheader()
        writer.writerows(candidates)
    print(f"{len(candidates)} blank-abstract source-access candidates; no eligibility decisions")


if __name__ == "__main__":
    main()
