"""Locate title-prefix integrity and correction cues in the frozen inventory.

This is a locator, not a judgment that a report is retracted or corrected.
Unflagged reports are not established to be free of integrity notices. An actual
notice and its relationship to the report require source verification.
"""
import argparse
import csv
import re
from pathlib import Path

PATTERN = re.compile(r"^\s*(retract(?:ion|ed)|withdrawn|expression of concern|"
                     r"erratum|corrigendum|correction)(?:\b|:)", re.I)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.inventory.open(encoding="utf-8-sig", newline="") as source:
        records = []
        for row in csv.DictReader(source):
            hit = PATTERN.search(row.get("title", ""))
            if hit:
                records.append({"publication_id": row["publication_id"], "title_cue": hit.group(1),
                                "title": row["title"], "doi": row.get("doi", ""),
                                "source_memberships_json": row.get("source_memberships_json", ""),
                                "record_ids_json": row.get("record_ids_json", ""),
                                "verification_status": "PENDING_SOURCE_VERIFICATION"})
    with args.output.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=["publication_id", "title_cue", "title", "doi",
                                                   "source_memberships_json", "record_ids_json",
                                                   "verification_status"])
        writer.writeheader()
        writer.writerows(records)
    print(f"{len(records)} title-prefix candidates; source verification pending; no eligibility determinations")


if __name__ == "__main__":
    main()
