"""Check the public tree and every reachable Git object without restricted inputs.

Patterns are bounded checks, not proof that all sensitive information is absent.
Security and provenance guards deliberately use explicit exceptions, never assert.
"""
import argparse
import ast
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SAFE_IMPORT = "aae894e2284b89d9a1b48b50582a43798c6280c3"
BLOCKED_COMMITS = {"2515272b6feb75854082fc14344fe06d5fcfc822", "d7d11a583c5594acbc67d5af96758b4ac8b01d5a"}
BLOCKED_BLOB = "cc8e20c3a1b5115e05935ead3af281a28d396812"
WITHHELD_PATH = "analysis/screening_qa/coordinator_screen_B0380.py"
MAX_OBJECT_BYTES = 100 * 1024 * 1024
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".csv", ".tsv", ".yml", ".yaml", ".toml", ".svg"}
FORBIDDEN_DIRS = {"outputs", "restricted", "supporting-context", "source-review", "meta analysis exports"}
CONTENT_RULES = (
    ("CREDENTIAL_PATTERN", re.compile(rb"(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}")),
    ("CREDENTIAL_PATTERN", re.compile(rb"sk-proj-[A-Za-z0-9_-]{20,}")),
    ("CREDENTIAL_PATTERN", re.compile(rb"AKIA[0-9A-Z]{16}")),
    ("PRIVATE_KEY", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("PRIVATE_USER_PATH", re.compile(rb"[A-Za-z]:[/\\]+Users[/\\]+", re.I)),
)


class ValidationError(Exception):
    """A failed check. Messages never include offending object contents."""


def require(condition, rule, detail=None):
    if not condition:
        raise ValidationError(rule + (": " + str(detail) if detail else ""))


class Repository:
    def __init__(self, root):
        self.root = Path(root).resolve()

    def git(self, *args, data=None):
        result = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(self.root), *args],
            input=data, capture_output=True,
        )
        require(result.returncode == 0, "GIT_COMMAND_FAILED", args[0])
        return result.stdout

    def entries(self, tree):
        for entry in filter(None, self.git("ls-tree", "-r", "-z", tree).split(b"\0")):
            metadata, raw_name = entry.split(b"\t", 1)
            mode, kind, oid = metadata.decode("ascii").split()
            try:
                name = raw_name.decode("utf-8")
            except UnicodeDecodeError:
                raise ValidationError("NON_UTF8_FILENAME") from None
            require(mode in {"100644", "100755"} and kind == "blob", "UNREVIEWED_GIT_MODE")
            check_name(name)
            yield name, oid

    def object_info(self, oid):
        line = self.git("cat-file", "--batch-check", data=(oid + "\n").encode()).decode("ascii").strip()
        fields = line.split()
        if len(fields) == 2 and fields[1] == "missing":
            return None
        require(len(fields) == 3 and fields[0] == oid, "INVALID_OBJECT_RESPONSE")
        return fields[1], int(fields[2])

    def body(self, oid, kind):
        info = self.object_info(oid)
        require(info is not None and info[0] == kind, "MISSING_OR_WRONG_OBJECT", oid)
        require(info[1] <= MAX_OBJECT_BYTES, "OBJECT_TOO_LARGE_TO_INSPECT", oid)
        body = self.git("cat-file", kind, oid)
        require(len(body) == info[1], "OBJECT_READ_INCOMPLETE", oid)
        return body


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def check_name(name):
    check_content(name.encode("utf-8"), "public-path")
    require(bool(name) and not any(ord(c) < 32 for c in name), "INVALID_PUBLIC_PATH")
    require("\\" not in name and not re.match(r"^[A-Za-z]:", name), "NONPORTABLE_PUBLIC_PATH")
    path = PurePosixPath(name)
    require(not path.is_absolute() and all(p not in {".", ".."} for p in name.split("/")), "INVALID_PUBLIC_PATH")
    require(name.casefold() != WITHHELD_PATH.casefold(), "WITHHELD_SOURCE_PATH")
    require(not any(p.casefold() in FORBIDDEN_DIRS for p in path.parts), "CONTROLLED_DIRECTORY")
    require(path.suffix.casefold() not in {".pdf", ".ris", ".zip", ".bundle", ".jsonl"}, "CONTROLLED_FILE_TYPE")
    require("private-access" not in path.name.casefold(), "CONTROLLED_ACCESS_MAP")


def check_content(body, oid):
    """Apply the same content boundary to current and historical objects."""
    for rule, pattern in CONTENT_RULES:
        require(not pattern.search(body), rule, oid)
    # Valid JSON string values can encode separators/characters not present as raw bytes.
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError:
        return
    if not text.lstrip().startswith(("{", "[", '"')):
        return
    try:
        # Preserve every key and value, including overwritten duplicate keys.
        value = json.loads(text, object_pairs_hook=lambda pairs: [part for pair in pairs for part in pair])
    except json.JSONDecodeError:
        return  # Raw-byte checks still apply; this is not a general JSON validator.
    except (RecursionError, MemoryError):
        raise ValidationError("JSON_CONTENT_UNINSPECTABLE: " + oid) from None
    pending = [value]
    while pending:
        value = pending.pop()
        if isinstance(value, str):
            for rule, pattern in CONTENT_RULES:
                require(not pattern.search(value.encode("utf-8")), rule, oid)
        elif isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)


def check_text(body, name):
    if PurePosixPath(name).suffix.casefold() not in TEXT_SUFFIXES and name not in {".gitignore", ".gitattributes"}:
        return
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError("NON_UTF8_PUBLIC_TEXT") from None
    require("\0" not in text, "NUL_IN_PUBLIC_TEXT")
    if name.endswith(".py"):
        try:
            ast.parse(text, filename=name)
        except (SyntaxError, ValueError):
            raise ValidationError("INVALID_PYTHON_SYNTAX") from None


def audit_boundary(repository, tree="HEAD", compare_worktree=True):
    """Inspect all refs/HEAD plus the selected tree; return only safe metadata."""
    repo = repository if isinstance(repository, Repository) else Repository(repository)
    require(not os.environ.get("GIT_GRAFT_FILE"), "EXTERNAL_GRAFT_FILE_UNVERIFIED")
    graft_name = Path(os.fsdecode(repo.git("rev-parse", "--git-path", "info/grafts").strip()))
    graft_path = graft_name if graft_name.is_absolute() else repo.root / graft_name
    require(not graft_path.exists(), "GRAFTED_HISTORY_UNVERIFIED")
    require(repo.git("rev-parse", "--is-shallow-repository").strip() == b"false", "SHALLOW_HISTORY_UNVERIFIED")
    check_content(repo.git("for-each-ref", "--format=%(refname)"), "public-ref-names")
    commits = set(repo.git("rev-list", "--all", "HEAD").decode("ascii").splitlines())
    require(not (commits & BLOCKED_COMMITS), "CONTROLLED_DRAFT_COMMIT")
    object_ids = set(repo.git("rev-list", "--objects", "--no-object-names", "--all", "HEAD").decode("ascii").splitlines())
    object_ids.update(repo.git("for-each-ref", "--format=%(objectname)").decode("ascii").splitlines())
    require(BLOCKED_BLOB not in object_ids and repo.object_info(BLOCKED_BLOB) is None, "WITHHELD_SOURCE_BLOB")
    bodies = {}
    inspected = set()
    def inspect(oid):
        if oid in inspected:
            return
        info = repo.object_info(oid)
        require(info is not None, "MISSING_REACHABLE_OBJECT", oid)
        kind, _ = info
        if kind in {"blob", "commit", "tag"}:
            body = repo.body(oid, kind)
            check_content(body, oid)
            if kind == "blob":
                bodies[oid] = body
            elif kind == "tag":
                first = body.splitlines()[0].split()
                require(len(first) == 2 and first[0] == b"object", "INVALID_TAG_OBJECT")
                target = first[1].decode("ascii")
                require(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", target) is not None, "INVALID_TAG_TARGET")
                inspect(target)
        elif kind == "tree":
            for name, blob in repo.entries(oid):
                inspect(blob)
                check_text(bodies[blob], name)
        else:
            raise ValidationError("UNSUPPORTED_GIT_OBJECT")
        inspected.add(oid)
    for oid in sorted(object_ids):
        inspect(oid)
    for commit in sorted(commits):
        for name, blob in repo.entries(commit):
            inspect(blob)
            check_text(bodies[blob], name)
    files = {}
    for name, blob in repo.entries(tree):
        inspect(blob)
        check_text(bodies[blob], name)
        if compare_worktree:
            path = repo.root / name
            require(not path.is_symlink() and path.resolve().is_relative_to(repo.root), "UNSAFE_WORKTREE_PATH")
            require(path.is_file() and path.read_bytes() == bodies[blob], "WORKTREE_DIFFERS", name)
        files[name] = hashlib.sha256(bodies[blob]).hexdigest()
    return files, {"reachable_commits": len(commits), "unique_blobs_content_checked": len(bodies), "reachable_objects_content_checked": len(inspected)}


def validate_records(repo, files):
    def load(name):
        require(name in files, "REQUIRED_RECORD_NOT_TRACKED", name)
        return json.loads((repo.root / name).read_text(encoding="utf-8"))
    copies = load("provenance/public-code-copies.json")["files"]
    require(len(copies) == 51, "PUBLIC_CODE_COPY_COUNT")
    for row in copies:
        require(row["candidate_path"] in files and isinstance(row["sha256"], str)
                and files[row["candidate_path"]] == row["sha256"], "CODE_COPY_HASH_MISMATCH", row["candidate_path"])
    imported = load("provenance/pre-adoption-import.json")
    require("provenance/legacy-file-manifest.csv" in files, "REQUIRED_RECORD_NOT_TRACKED")
    require(sha(repo.root / "provenance/legacy-file-manifest.csv") == imported["file_manifest_sha256"], "INHERITED_MANIFEST_HASH")
    with (repo.root / "provenance/legacy-file-manifest.csv").open(encoding="utf-8", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    require(len(manifest) == len({row["path"] for row in manifest}) == 36839, "INHERITED_MANIFEST_COUNT")
    require(sum(int(row["bytes"]) for row in manifest) == imported["original_workspace_bytes"], "INHERITED_MANIFEST_BYTES")
    counts = load("data/pause-counts.json")
    pause = load("data/pause-state.json")
    require(counts["pass_A_saved"] == counts["pass_B_saved"] == 18976, "INITIAL_COVERAGE")
    require(counts["adjudicated_n"] == pause["adjudicated_n"] == 9226, "ADJUDICATION_COUNT")
    require(counts["adjudication_pending"] == pause["adjudication_remaining"] == 9750, "PENDING_COUNT")
    require(pause["state"] == "PAUSED_BY_HUMAN" and not pause["screening_goal_complete"], "SCREENING_PAUSE_CHANGED")
    require(pause["next_batch"] == "B0183" and pause["human_verified"] == 0, "SCREENING_CHECKPOINT_CHANGED")
    authorization = load("provenance/publication-authorization.json")
    require(authorization["repository_publication_authorized"] and not authorization["scientific_screening_resume_authorized"], "AUTHORIZATION_SCOPE")
    require(SAFE_IMPORT in set(repo.git("rev-list", "--all", "HEAD").decode().splitlines()), "SAFE_IMPORT_NOT_PRESERVED")
    return len(copies), len(manifest)


def main(argv=None):
    cli = argparse.ArgumentParser()
    cli.add_argument("--repo", type=Path, default=ROOT)
    cli.add_argument("--staged", action="store_true", help="Validate the index and all reachable history.")
    cli.add_argument("--write-receipt", action="store_true", help="Exclusively create the original receipt path.")
    cli.add_argument("--receipt", type=Path, help="Exclusively create a new receipt after all checks pass.")
    args = cli.parse_args(argv)
    require(not (args.write_receipt and args.receipt), "AMBIGUOUS_RECEIPT_DESTINATION")
    repo = Repository(args.repo)
    tree = repo.git("write-tree").decode().strip() if args.staged else "HEAD"
    files, history = audit_boundary(repo, tree)
    copies, manifest = validate_records(repo, files)
    result = {"format": "medical-xr-public-check/2", "checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "performed_by": "Publication checker; automated software check, not human scientific verification",
              "result": "PASS", "inspected_tree": tree, "public_files": len(files),
              "public_unchanged_code_copies": copies, "inherited_manifest_files": manifest, **history,
              "original_safe_import_preserved": True, "excerpt_bearing_blob_absent": True,
              "controlled_draft_commits_absent": True, "screening_state": "PAUSED",
              "human_verification": "PENDING", "file_sha256": {k: v for k, v in files.items() if k != "provenance/publication-check.json"},
              "limits": "Bounded raw-byte/JSON-string patterns over reachable objects and public text rules. Not arbitrary-encoding detection, rights clearance, scientific validation or human review."}
    output = args.receipt or (repo.root / "provenance/publication-check.json" if args.write_receipt else None)
    if output:
        try:
            with output.open("x", encoding="utf-8", newline="\n") as handle:
                json.dump(result, handle, indent=2)
                handle.write("\n")
        except OSError:
            raise ValidationError("RECEIPT_NOT_CREATED") from None
    print(json.dumps({key: value for key, value in result.items() if key != "file_sha256"}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValidationError, OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        code = str(error) if isinstance(error, ValidationError) else type(error).__name__
        print(json.dumps({"result": "FAIL", "rule": code}), file=sys.stderr)
        sys.exit(1)
