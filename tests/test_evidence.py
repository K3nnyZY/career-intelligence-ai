import unittest

from career_ai.evidence import compare, extract_profile, mentions


class EvidenceTests(unittest.TestCase):
    def test_evidence_offsets_survive_unicode_and_original_casing(self):
        text = "Straße: Implementé procesos con PYTHON, PostgreSQL y SQL."
        for item in mentions(text):
            self.assertEqual(text[item["start"]:item["end"]], item["matched_text"])
            self.assertEqual(text[item["quote_start"]:item["quote_end"]], item["quote"])
        self.assertEqual(extract_profile(text)["skills"], ["postgresql", "python", "sql"])

    def test_required_desirable_and_unspecified(self):
        result = compare("Python SQL", "Required:\nPython\nPreferred:\nDocker\nResponsibilities:\nSQL")
        self.assertEqual(result["groups"]["required"]["matched"], ["python"])
        self.assertEqual(result["groups"]["desirable"]["missing_evidence"], ["docker"])
        self.assertEqual(result["groups"]["unspecified"]["matched"], ["sql"])

    def test_inline_heading_inherits_but_sentence_does_not(self):
        items = mentions("Required: Python\nSQL", vacancy=True)
        self.assertTrue(all(item["requirement"] == "required" for item in items))
        items = mentions("We have several essential values.\nPython", vacancy=True)
        self.assertEqual(items[0]["requirement"], "unspecified")

    def test_negation_and_contrast(self):
        result = compare("No tengo experiencia en Python. Implementé SQL.",
                         "No se requiere Python, pero SQL obligatorio. Docker is not required.")
        self.assertEqual([row["skill"] for row in result["skills"]], ["sql"])
        self.assertEqual({row["skill"] for row in result["excluded_mentions"]}, {"docker", "python"})

    def test_repeated_required_overrides_preferred(self):
        result = compare("Python", "Python preferred. Python required.")
        self.assertEqual(result["skills"][0]["requirement"], "required")
        self.assertEqual(len(result["skills"][0]["vacancy_evidence"]), 2)

    def test_reviewer_can_reject_mentions_and_cannot_invent_evidence(self):
        result = compare("Python SQL", "Python required. SQL required.", ["sql"])
        python = next(row for row in result["skills"] if row["skill"] == "python")
        self.assertEqual(python["status"], "missing_evidence")
        self.assertEqual(python["cv_evidence"], [])
        with self.assertRaises(ValueError):
            compare("Python", "SQL", ["sql"])
        self.assertEqual(compare("Python", "Python", [])["groups"]["unspecified"]["coverage"], 0)

    def test_experience_highlights_are_exact_and_relevant(self):
        cv = "Implementé pipelines SQL. Migré workloads a AWS. Python."
        result = compare(cv, "SQL required")
        self.assertEqual(len(result["highlights"]), 1)
        highlight = result["highlights"][0]
        self.assertEqual(cv[highlight["start"]:highlight["end"]], highlight["quote"])
        self.assertEqual(highlight["relevant_skills"], ["sql"])

    def test_unknown_skills_do_not_create_score(self):
        result = compare("Python", "Buena comunicación")
        self.assertTrue(all(group["coverage"] is None for group in result["groups"].values()))
        self.assertEqual(result["skills"], [])

    def test_large_evidence_is_bounded_without_changing_offsets(self):
        text = "x " * 10000 + "Python" + " z" * 10000
        item = mentions(text)[0]
        self.assertLessEqual(len(item["quote"]), 406)
        self.assertEqual(text[item["quote_start"]:item["quote_end"]], item["quote"])
        with self.assertRaises(ValueError):
            mentions("SQL " * 1001)

    def test_repeatable_and_blank_rejected(self):
        self.assertEqual(compare("Python", "SQL required"), compare("Python", "SQL required"))
        with self.assertRaises(ValueError):
            extract_profile("   ")
