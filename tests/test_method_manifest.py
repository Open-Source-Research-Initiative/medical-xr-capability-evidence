"""Synthetic method provenance fixtures; no papers or research decisions are used."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

CHECKER = Path(__file__).resolve().parents[1] / "scripts/verify_public_tree.py"
spec = importlib.util.spec_from_file_location("method_checker", CHECKER)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class MethodManifestTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(os.environ.get("MEDICAL_XR_TEST_ROOT", tempfile.gettempdir())).resolve()
        self.base.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="medical_xr_methods_", dir=self.base)).resolve()
        self.addCleanup(self.clean)
        self.rows, self.legacy = [], []
        for i in range(13):
            public, original = f"methods/inherited/method-{i}.md", f"legacy/method-{i}.md"
            body = f"Synthetic inherited method {i}.\n".encode()
            self.write(public, body)
            digest = hashlib.sha256(body).hexdigest()
            self.rows.append(dict(public_path=public, original_path=original, bytes=len(body),
                                  sha256=digest, changes="none"))
            self.legacy.append(dict(path=original, bytes=str(len(body)), sha256=digest))
        self.record = dict(format="medical-xr-open-methods/1", files=self.rows)
        self.save()

    def clean(self):
        path = self.root.resolve()
        if path.parent != self.base or not path.name.startswith("medical_xr_methods_"):
            raise RuntimeError("Refusing unsafe test cleanup")
        def writable(function, name, exc):
            os.chmod(name, 0o700)
            function(name)
        shutil.rmtree(path, onerror=writable)

    def write(self, name, body):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body if isinstance(body, bytes) else body.encode())

    def save(self):
        self.write("provenance/open-methods.json", json.dumps(self.record))

    def files(self):
        return {p.relative_to(self.root).as_posix(): checker.sha(p)
                for p in self.root.rglob("*") if p.is_file() and ".git" not in p.relative_to(self.root).parts}

    def validate(self):
        return checker.validate_open_methods(checker.Repository(self.root), self.files(), self.legacy)

    def rejected(self, rule):
        with self.assertRaisesRegex(checker.ValidationError, rule):
            self.validate()

    def test_clean_thirteen_methods(self):
        self.assertEqual(self.validate(), 13)

    def test_missing_manifest(self):
        (self.root / "provenance/open-methods.json").unlink()
        self.rejected("REQUIRED_RECORD_NOT_TRACKED")

    def test_manifest_format(self):
        self.record["format"] = "unknown"
        self.save()
        self.rejected("OPEN_METHODS_FORMAT")

    def test_empty_short_and_wrong_type_files(self):
        for rows in ([], self.rows[:-1], {}, None):
            with self.subTest(row_type=type(rows).__name__):
                self.record["files"] = rows
                self.save()
                self.rejected("OPEN_METHODS_COUNT")

    def test_duplicate_public_path(self):
        self.rows[1]["public_path"] = self.rows[0]["public_path"]
        self.save()
        self.rejected("OPEN_METHODS_DUPLICATE")

    def test_duplicate_original_path(self):
        self.rows[1]["original_path"] = self.rows[0]["original_path"]
        self.save()
        self.rejected("OPEN_METHODS_DUPLICATE")

    def test_changed_method_with_original_hash(self):
        self.write(self.rows[0]["public_path"], "Changed method.\n")
        self.rejected("OPEN_METHODS_HASH_MISMATCH")

    def test_method_and_manifest_changed_together(self):
        body = b"Changed method.\n"
        self.write(self.rows[0]["public_path"], body)
        self.rows[0].update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        self.save()
        self.rejected("OPEN_METHODS_LEGACY_MISMATCH")

    def test_declared_size_must_match_original(self):
        self.rows[0]["bytes"] += 1
        self.save()
        self.rejected("OPEN_METHODS_LEGACY_MISMATCH")

    def test_actual_size_checked_even_with_consistent_metadata(self):
        self.rows[0]["bytes"] += 1
        self.legacy[0]["bytes"] = str(self.rows[0]["bytes"])
        self.save()
        self.rejected("OPEN_METHODS_SIZE_MISMATCH")

    def test_missing_original(self):
        self.legacy.pop(0)
        self.rejected("OPEN_METHODS_ORIGINAL_MISSING")

    def test_duplicate_original_manifest_row(self):
        self.legacy.append(self.legacy[0])
        self.rejected("OPEN_METHODS_LEGACY_DUPLICATE")

    def test_missing_method_file(self):
        (self.root / self.rows[0]["public_path"]).unlink()
        self.rejected("OPEN_METHODS_FILE_NOT_TRACKED")

    def test_unlisted_method(self):
        self.write("methods/inherited/unlisted.md", "Unlisted method.\n")
        self.rejected("OPEN_METHODS_COVERAGE")

    def test_invalid_paths(self):
        for path in ("../outside.md", "methods/inherited/../outside.md", "/outside.md",
                     "methods/inherited//method-0.md", "methods/other.md",
                     "methods" + chr(92) + "inherited/method-0.md"):
            with self.subTest(path=path):
                self.rows[0]["public_path"] = path
                self.save()
                with self.assertRaises(checker.ValidationError):
                    self.validate()

    def test_invalid_metadata(self):
        original = dict(self.rows[0])
        for change in ({"bytes": True}, {"bytes": -1}, {"bytes": "1"}, {"sha256": "x" * 64},
                       {"changes": "edited"}, {"original_path": None}, {"public_path": None}):
            with self.subTest(fields=tuple(change)):
                self.rows[0] = dict(original, **change)
                self.save()
                with self.assertRaises(checker.ValidationError):
                    self.validate()

    def test_nonobject_row(self):
        self.rows[0] = None
        self.save()
        self.rejected("OPEN_METHODS_ROW")

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        return result.stdout

    def complete_fixture(self):
        """Supply every real CLI record, replacing only the known import commit ID."""
        self.git("init", "--initial-branch=main")
        for key, value in (("user.name", "Synthetic method QA"), ("user.email", "test@example.invalid"),
                           ("core.autocrlf", "false"), ("commit.gpgsign", "false")):
            self.git("config", key, value)
        self.write(".gitattributes", "* -text\n")
        copies = []
        for i in range(51):
            path = f"analysis/code-{i}.py"
            self.write(path, "pass\n")
            copies.append(dict(candidate_path=path, sha256=checker.sha(self.root / path)))
        self.write("provenance/public-code-copies.json", json.dumps(dict(files=copies)))
        rows = list(self.legacy) + [dict(path=f"legacy/placeholder-{i}", bytes="0", sha256="0" * 64)
                                    for i in range(36839 - len(self.legacy))]
        manifest = "path,bytes,sha256\n" + "".join(f"{r['path']},{r['bytes']},{r['sha256']}\n" for r in rows)
        self.write("provenance/legacy-file-manifest.csv", manifest)
        self.write("provenance/pre-adoption-import.json", json.dumps(dict(
            file_manifest_sha256=checker.sha(self.root / "provenance/legacy-file-manifest.csv"),
            original_workspace_bytes=sum(int(r["bytes"]) for r in rows))))
        self.write("data/pause-counts.json", json.dumps(dict(pass_A_saved=18976, pass_B_saved=18976,
                   adjudicated_n=9226, adjudication_pending=9750)))
        self.write("data/pause-state.json", json.dumps(dict(state="PAUSED_BY_HUMAN", adjudicated_n=9226,
                   adjudication_remaining=9750, screening_goal_complete=False, next_batch="B0183", human_verified=0)))
        self.write("provenance/publication-authorization.json", json.dumps(dict(
            repository_publication_authorized=True, scientific_screening_resume_authorized=False)))
        self.commit()
        self.safe_import = self.git("rev-parse", "HEAD").decode().strip()

    def commit(self):
        self.git("add", "--all")
        self.git("commit", "-m", "Synthetic method fixture")

    def cli(self, staged=False):
        program = ("import importlib.util,sys;"
                   "s=importlib.util.spec_from_file_location('v',sys.argv[1]);"
                   "v=importlib.util.module_from_spec(s);s.loader.exec_module(v);"
                   "v.SAFE_IMPORT=sys.argv[2];sys.exit(v.main(sys.argv[3:]))")
        optimized = ["-" + "O" * sys.flags.optimize] if sys.flags.optimize else []
        return subprocess.run([sys.executable, *optimized, "-X", "utf8", "-c", program,
                               str(CHECKER), self.safe_import, "--repo", str(self.root),
                               *(["--staged"] if staged else [])], capture_output=True, text=True)

    def test_complete_cli_clean_head_and_index(self):
        self.complete_fixture()
        for staged in (False, True):
            with self.subTest(staged=staged):
                result = self.cli(staged)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["public_unchanged_method_copies"], 13)

    def test_complete_cli_rejects_committed_tamper(self):
        self.complete_fixture()
        self.write(self.rows[0]["public_path"], "Changed method.\n")
        self.commit()
        result = self.cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OPEN_METHODS_HASH_MISMATCH", result.stderr)

    def test_complete_cli_rejects_staged_tamper(self):
        self.complete_fixture()
        self.write(self.rows[0]["public_path"], "Changed method.\n")
        self.git("add", "--all")
        result = self.cli(staged=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OPEN_METHODS_HASH_MISMATCH", result.stderr)

    def test_complete_cli_rejects_rewritten_hash_and_size(self):
        self.complete_fixture()
        body = b"Changed method.\n"
        self.write(self.rows[0]["public_path"], body)
        self.rows[0].update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        self.save()
        self.commit()
        for staged in (False, True):
            with self.subTest(staged=staged):
                result = self.cli(staged)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("OPEN_METHODS_LEGACY_MISMATCH", result.stderr)


if __name__ == "__main__":
    unittest.main()
