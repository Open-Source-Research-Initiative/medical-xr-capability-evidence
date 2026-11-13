"""Synthetic Git-boundary regression tests; never use the research corpus."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

CHECKER = Path(__file__).resolve().parents[1] / "scripts/verify_public_tree.py"
spec = importlib.util.spec_from_file_location("publication_checker", CHECKER)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        base = Path(os.environ.get("MEDICAL_XR_TEST_ROOT", tempfile.gettempdir())).resolve()
        base.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="medical_xr_qa_", dir=base)).resolve()
        self.base = base
        self.addCleanup(self.clean)
        self.git("init", "--initial-branch=main")
        self.git("config", "user.name", "OSRI synthetic test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "core.autocrlf", "false")
        self.git("config", "commit.gpgsign", "false")
        self.write(".gitattributes", "* -text\n")
        self.write("safe.txt", "Safe synthetic fixture.\n")
        self.commit("Clean synthetic baseline")

    def clean(self):
        path = self.root.resolve()
        if path.parent != self.base or not path.name.startswith("medical_xr_qa_"):
            raise RuntimeError("Refusing unsafe test cleanup")
        def writable(function, name, exc):
            os.chmod(name, 0o700)
            function(name)
        shutil.rmtree(path, onerror=writable)

    def git(self, *args, data=None):
        p = subprocess.run(["git", "-C", str(self.root), *args], input=data, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr.decode(errors="replace"))
        return p.stdout

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8", newline="\n")

    def commit(self, message):
        self.git("add", "--all")
        self.git("commit", "-m", message)

    def marker(self):
        return "C:" + chr(92) + "Users" + chr(92) + "SyntheticReviewer" + chr(92) + "placeholder"

    def audit(self, *args, **kwargs):
        return checker.audit_boundary(self.root, *args, **kwargs)

    def expect_rejected(self, code):
        with self.assertRaisesRegex(checker.ValidationError, code):
            self.audit()

    def optimized_process(self, optimization, expected):
        program = (
            "import importlib.util,sys;"
            "s=importlib.util.spec_from_file_location('v',sys.argv[1]);"
            "v=importlib.util.module_from_spec(s);s.loader.exec_module(v);"
            "v.audit_boundary(sys.argv[2])"
        )
        result = subprocess.run(
            [sys.executable, optimization, "-c", program, str(CHECKER), str(self.root)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode == 0, expected)
        return result

    def test_clean_control(self):
        files, counts = self.audit()
        self.assertIn("safe.txt", files)
        self.assertEqual(counts["reachable_commits"], 1)

    def test_no_assert_guards(self):
        self.assertFalse(any(isinstance(n, ast.Assert) for n in ast.walk(ast.parse(CHECKER.read_text(encoding="utf-8")))))

    def test_historical_deleted_marker(self):
        self.write("probe.txt", self.marker()); self.commit("Synthetic marker")
        (self.root / "probe.txt").unlink(); self.commit("Remove current marker")
        self.expect_rejected("PRIVATE_USER_PATH")
        self.optimized_process("-O", False)
        self.optimized_process("-OO", False)

    def test_historical_replaced_marker(self):
        self.write("safe.txt", self.marker()); self.commit("Synthetic marker")
        self.write("safe.txt", "Safe replacement"); self.commit("Replace current content")
        self.expect_rejected("PRIVATE_USER_PATH")

    def test_other_branch_history(self):
        self.git("switch", "-c", "other")
        self.write("probe.txt", self.marker()); self.commit("Other branch marker")
        self.git("switch", "main")
        self.expect_rejected("PRIVATE_USER_PATH")

    def test_tag_only_history(self):
        self.write("probe.txt", self.marker()); self.commit("Tagged marker")
        self.git("tag", "marked")
        self.git("checkout", "main~1")
        self.git("branch", "-f", "main", "HEAD")
        self.expect_rejected("PRIVATE_USER_PATH")

    def test_current_guard_under_optimization(self):
        self.write("probe.txt", self.marker()); self.commit("Current marker")
        self.optimized_process("-O", False)
        self.optimized_process("-OO", False)

    def test_clean_optimization_controls(self):
        self.optimized_process("-O", True)
        self.optimized_process("-OO", True)

    def test_staged_deletion_cannot_hide_history(self):
        self.write("probe.txt", self.marker()); self.commit("Committed marker")
        (self.root / "probe.txt").unlink(); self.git("add", "-u")
        tree = self.git("write-tree").decode().strip()
        with self.assertRaisesRegex(checker.ValidationError, "PRIVATE_USER_PATH"):
            self.audit(tree)

    def test_clean_staged_addition(self):
        self.write("new.txt", "Safe staged record"); self.git("add", "new.txt")
        files, _ = self.audit(self.git("write-tree").decode().strip())
        self.assertIn("new.txt", files)

    def test_credential_history(self):
        token = "gh" + "p_" + "x" * 24
        self.write("probe.txt", token); self.commit("Synthetic credential")
        (self.root / "probe.txt").unlink(); self.commit("Remove current credential")
        self.expect_rejected("CREDENTIAL_PATTERN")

    def test_json_escaped_private_path(self):
        payload = json.dumps({"location": self.marker()}).replace("C:", "C" + chr(92) + "u003a")
        self.write("metadata.json", payload); self.commit("Escaped synthetic marker")
        self.expect_rejected("PRIVATE_USER_PATH")

    def test_json_duplicate_key_cannot_hide_escaped_value(self):
        escaped = "".join(chr(92) + "u%04x" % ord(char) for char in self.marker())
        self.write("metadata.json", '{"location":"' + escaped + '","location":"safe"}')
        self.commit("Duplicate JSON key fixture")
        self.expect_rejected("PRIVATE_USER_PATH")

    def test_credential_filename(self):
        self.write("gh" + "p_" + "x" * 24 + ".txt", "Safe bytes")
        self.commit("Synthetic filename fixture")
        self.expect_rejected("CREDENTIAL_PATTERN")

    def test_credential_ref_name(self):
        self.git("branch", "gh" + "p_" + "x" * 24)
        self.expect_rejected("CREDENTIAL_PATTERN")

    def test_grafts_cannot_truncate_history(self):
        self.write("probe.txt", self.marker()); self.commit("Historical marker")
        (self.root / "probe.txt").unlink(); self.commit("Delete current marker")
        (self.root / ".git/info/grafts").write_bytes(self.git("rev-parse", "HEAD"))
        self.expect_rejected("GRAFTED_HISTORY_UNVERIFIED")
        self.optimized_process("-O", False)

    def test_external_graft_file_fails_closed(self):
        with patch.dict(os.environ, {"GIT_GRAFT_FILE": str(self.root / "synthetic-grafts")}):
            self.expect_rejected("EXTERNAL_GRAFT_FILE_UNVERIFIED")

    def test_case_and_separator_variants(self):
        self.write("probe.txt", self.marker().replace("Users", "users").replace(chr(92), "/"))
        self.commit("Case variant"); self.expect_rejected("PRIVATE_USER_PATH")

    def test_same_blob_new_forbidden_path(self):
        self.write("restricted/safe.txt", "Safe synthetic fixture.\n"); self.commit("Reuse clean bytes")
        self.expect_rejected("CONTROLLED_DIRECTORY")

    def test_worktree_mismatch(self):
        self.write("safe.txt", "Unstaged change")
        self.expect_rejected("WORKTREE_DIFFERS")

    def test_commit_message_content(self):
        self.write("safe.txt", "Changed")
        self.commit(self.marker())
        self.expect_rejected("PRIVATE_USER_PATH")

    def test_annotated_tag_content(self):
        self.git("tag", "-a", "tagged", "-m", self.marker())
        self.expect_rejected("PRIVATE_USER_PATH")

    def test_utf16_public_text_rejected(self):
        (self.root / "probe.txt").write_bytes(self.marker().encode("utf-16"))
        self.commit("UTF16 fixture")
        self.expect_rejected("NON_UTF8_PUBLIC_TEXT")

    def test_invalid_python_not_hidden_by_content_cache(self):
        self.write("data.txt", "not valid python !!!")
        self.commit("Text fixture")
        self.write("invalid.py", "not valid python !!!"); self.commit("Same bytes as Python")
        self.expect_rejected("INVALID_PYTHON_SYNTAX")

    def test_forbidden_file_under_optimization(self):
        self.write("restricted/probe.txt", "Safe bytes"); self.commit("Controlled directory")
        self.optimized_process("-O", False)

    def test_bad_repository_fails(self):
        with self.assertRaises(checker.ValidationError):
            checker.audit_boundary(self.root / "not-a-repository")


class GuardUnitTests(unittest.TestCase):
    def test_explicit_guard_survives_optimization(self):
        with self.assertRaises(checker.ValidationError):
            checker.require(False, "EXPECTED")

    def test_nonportable_path(self):
        for path in ["../outside.txt", "/outside.txt", "folder" + chr(92) + "outside.txt"]:
            with self.subTest(path_hash=hash(path)):
                with self.assertRaises(checker.ValidationError):
                    checker.check_name(path)

    def test_missing_selected_provenance_record(self):
        with self.assertRaisesRegex(checker.ValidationError, "REQUIRED_RECORD_NOT_TRACKED"):
            checker.validate_records(checker.Repository(CHECKER.parent.parent), {})


if __name__ == "__main__":
    unittest.main()
