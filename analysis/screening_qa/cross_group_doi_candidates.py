"""Find repeated DOI strings across frozen provisional publication groups.

These are verification candidates, not automatically duplicate reports. Conference
proceedings and source errors can give distinct reports the same DOI. Every group
retains its ID and requires individual screening.
"""
import argparse
import collections
import csv
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    by_doi = collections.defaultdict(list)
    invalid_json = []
    with args.inventory.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            try:
                observed = json.loads(row.get("dois_json") or "[]")
                if not isinstance(observed, list):
                    raise ValueError("dois_json is not a list")
            except (ValueError, json.JSONDecodeError):
                invalid_json.append(row["publication_id"])
                observed = []
            primary = (row.get("doi") or "").strip().casefold()
            values = {str(x).strip().casefold() for x in observed if str(x).strip()}
            if primary:
                values.add(primary)
            for doi in values:
                by_doi[doi].append((row, primary == doi))
    if invalid_json:
        raise ValueError(f"Invalid DOI JSON for {len(invalid_json)} IDs: {invalid_json[:10]}")
    candidates = {doi: members for doi, members in by_doi.items() if len(members) > 1}
    columns = ["candidate_doi", "candidate_group_size", "publication_id", "title",
               "doi_is_primary", "doi_conflict", "source_memberships_json", "record_ids_json"]
    with args.output.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=columns)
        writer.writeheader()
        for doi, members in sorted(candidates.items()):
            for row, is_primary in sorted(members, key=lambda item: item[0]["publication_id"]):
                writer.writerow({"candidate_doi": doi, "candidate_group_size": len(members),
                                 "publication_id": row["publication_id"], "title": row["title"],
                                 "doi_is_primary": int(is_primary), "doi_conflict": row["doi_conflict"],
                                 "source_memberships_json": row["source_memberships_json"],
                                 "record_ids_json": row["record_ids_json"]})
    print(json.dumps({"repeated_doi_strings": len(candidates),
                      "candidate_rows": sum(map(len, candidates.values())),
                      "unique_publication_ids": len({r["publication_id"] for members in candidates.values() for r, _ in members}),
                      "invalid_doi_json": len(invalid_json),
                      "normalization": "strip and casefold only; includes primary DOI and all dois_json candidates",
                      "interpretation": "identity verification candidates; not screened or merged"}, indent=2))


if __name__ == "__main__":
    main()
