import unittest
from career_ai.core import pipeline, skills, match

class PipelineTests(unittest.TestCase):
    def test_boundaries_and_aliases(self):
        self.assertEqual(skills("NoSQL pythonista RAG LLMs"), ["llm", "rag"])
    def test_dedup_quality_and_quarantine(self):
        row = {"title": " AI Engineer ", "company": "Demo", "description": "Python SQL"}
        result = pipeline([row, dict(row, title="AI Engineer"), {"title": "bad"}])
        self.assertEqual(result["quality"], {"input_rows": 3, "accepted_unique": 1, "rejected_rows": 1, "duplicates": 1})
        self.assertEqual(result["skill_demand"], {"python": 1, "sql": 1})
    def test_coverage_and_empty(self):
        self.assertEqual(match({"skills": ["python", "sql"]}, ["Python"])["skill_coverage"], .5)
        self.assertIsNone(match({"skills": []}, ["Python"])["skill_coverage"])
    def test_repeatable(self):
        rows = [{"title": "Data", "company": "Demo", "description": "Databricks PySpark"}]
        self.assertEqual(pipeline(rows), pipeline(rows))
    def test_changed_description_is_new_version(self):
        row = {"title": "Data", "company": "Demo", "description": "Python"}
        self.assertEqual(len(pipeline([row, dict(row, description="Python SQL")])["jobs"]), 2)

if __name__ == "__main__":
    unittest.main()
