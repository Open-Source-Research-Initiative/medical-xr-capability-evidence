"""Check the offline example's honest provenance and presentation contract."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("show_example", ROOT / "scripts/show_example.py")
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)


class ExampleTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / "examples/P0000314.json").read_text(encoding="utf-8"))

    def test_missing_attribution_rejected(self):
        record = copy.deepcopy(self.record)
        del record["source"]["license"]
        with self.assertRaises(ValueError):
            example.validate_record(record)

    def test_human_status_cannot_be_promoted(self):
        self.record["recorded_route"]["human_verification"] = "VERIFIED"
        with self.assertRaises(ValueError):
            example.validate_record(self.record)

    def test_runs_outside_original_workspace(self):
        p = subprocess.run([sys.executable, str(ROOT / "scripts/show_example.py")], cwd=ROOT.parent, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("not human verification", p.stdout)
        self.assertIn("P0000314", p.stdout)
