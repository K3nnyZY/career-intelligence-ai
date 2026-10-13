import copy
import json
import unittest
from pathlib import Path

from career_ai.evaluation import evaluate, metrics, validate_dataset

ROOT = Path(__file__).resolve().parents[1]


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.dataset = json.loads((ROOT / "data/evaluation_smoke.json").read_text())

    def test_synthetic_smoke_and_matching(self):
        report = evaluate(self.dataset, ROOT / "data")
        self.assertEqual(report["extraction"]["precision"], 1)
        self.assertEqual(report["extraction"]["recall"], 1)
        self.assertEqual(report["extraction"]["requirement_accuracy"], 1)
        self.assertEqual(report["matching"]["exact_match_rate"], 1)
        self.assertEqual(report["source_counts"]["real"], 0)
        self.assertNotIn(self.dataset["cases"][0]["text"], json.dumps(report))

    def test_false_positives_and_unknown_skills_are_measured(self):
        self.dataset["cases"][0]["expected_skills"] = ["unknown_tool", "sql"]
        report = evaluate(self.dataset, ROOT / "data")
        row = report["cases"][0]
        self.assertEqual(row["omitted"], ["unknown_tool"])
        self.assertIn("python", row["incorrect"])
        self.assertLess(report["extraction"]["recall"], 1)

    def test_failed_files_count_as_omissions(self):
        case = self.dataset["cases"][0]
        del case["text"]
        case["file"] = "does-not-exist.docx"
        report = evaluate(self.dataset, ROOT / "data")
        self.assertEqual(report["extraction"]["error_count"], 1)
        self.assertEqual(report["extraction"]["false_negatives"], 5)
        self.assertEqual(report["matching"]["error_count"], 1)

    def test_bad_annotations_and_permissions_fail_contract(self):
        duplicate = copy.deepcopy(self.dataset)
        duplicate["cases"].append(duplicate["cases"][0])
        with self.assertRaises(ValueError):
            validate_dataset(duplicate)
        self.dataset["cases"][0]["source"] = {"type": "real"}
        with self.assertRaises(ValueError):
            validate_dataset(self.dataset)

    def test_all_empty_metrics_are_null(self):
        self.assertIsNone(metrics(0, 0, 0)["precision"])
        self.assertIsNone(metrics(0, 0, 0)["recall"])
