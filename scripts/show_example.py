"""Display an existing authored source trace; never generate screening labels."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_record(record):
    if record.get("format") != "medical-xr-source-route-example/1":
        raise ValueError("Unknown example format")
    for key in ("publication_id", "doi", "interpretation", "original_assessments", "history", "limits"):
        if not record.get(key):
            raise ValueError("Missing traceability field: " + key)
    source = record["source"]
    for key in ("url", "section", "accessed_on", "authors", "year", "license", "license_url", "excerpt"):
        if not source.get(key):
            raise ValueError("Missing source attribution: " + key)
    if not source["url"].startswith("https://") or len(source["excerpt"].split()) > 25:
        raise ValueError("Invalid source link or excessive excerpt")
    if record["recorded_route"].get("human_verification") != "PENDING":
        raise ValueError("This example is not a human verification result")
    if not record["history"].get("source_revision_sha256"):
        raise ValueError("Missing source-revision hash")
    return record


def main():
    record = validate_record(json.loads((ROOT / "examples/P0000314.json").read_text(encoding="utf-8")))
    print(record["publication_id"] + ": " + record["title"])
    print("Source: " + record["source"]["url"] + " — " + record["source"]["section"])
    print("Existing AI route: " + json.dumps(record["recorded_route"], sort_keys=True))
    for limit in record["limits"]:
        print("Limit: " + limit)


if __name__ == "__main__":
    main()
