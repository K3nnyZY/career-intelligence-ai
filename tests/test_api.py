import unittest
import re
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from career_ai.api import app, MAX_REQUEST_BYTES
from document_fixtures import docx_bytes


class APITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, base_url="http://127.0.0.1")

    def test_local_interface_and_headers(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('<div id="root"></div>', response.text)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertIn("frame-ancestors 'none'", response.headers["content-security-policy"])
        script = re.search(r'src="(/static/assets/[^" ]+\.js)"', response.text)
        self.assertIsNotNone(script)
        asset = self.client.get(script.group(1))
        self.assertEqual(asset.status_code, 200)
        self.assertIn("javascript", asset.headers["content-type"])

    def test_missing_frontend_build_does_not_disable_api(self):
        with patch("career_ai.api.STATIC", Path("/private/tmp/career-ai-missing-build")):
            self.assertEqual(self.client.get("/").status_code, 503)
            self.assertEqual(self.client.get("/health").status_code, 200)

    def test_full_reviewed_document_flow(self):
        response = self.client.post("/documents/extract", content=docx_bytes(), headers={"x-document-format": "docx", "content-type": "application/octet-stream"})
        self.assertEqual(response.status_code, 200, response.text)
        profile = response.json()
        self.assertEqual(profile["skills"], ["python", "sql"])
        reviewed = self.client.post("/profile/review", json={"text": profile["text"] + "\nAWS"}).json()
        result = self.client.post("/compare", json={"cv_text": reviewed["text"], "vacancy_text": "Required: SQL\nPreferred: Docker", "selected_skills": ["sql"]})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["groups"]["required"]["matched"], ["sql"])
        self.assertEqual(result.json()["groups"]["desirable"]["missing_evidence"], ["docker"])

    def test_untrusted_host_and_cross_origin_are_rejected(self):
        self.assertEqual(self.client.get("/health", headers={"host": "external.example"}).status_code, 400)
        self.assertEqual(self.client.post("/compare", json={}, headers={"origin": "https://external.example"}).status_code, 403)
        self.assertEqual(self.client.get("/health", headers={"origin": "http://127.0.0.1"}).status_code, 200)
        self.assertEqual(self.client.get("/health", headers={"origin": "null"}).status_code, 403)

    def test_errors_do_not_echo_sensitive_inputs(self):
        secret = "fictitious-sensitive-contact"
        response = self.client.post("/compare", json={"cv_text": secret, "vacancy_text": 123})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(secret, response.text)
        response = self.client.post("/compare", content='{ "cv_text": "' + secret, headers={"content-type": "application/json"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn(secret, response.text)

    def test_body_cap_and_bad_file_errors(self):
        response = self.client.post("/compare", content=b"x", headers={"content-length": str(MAX_REQUEST_BYTES + 1)})
        self.assertEqual(response.status_code, 413)
        response = self.client.post("/profile/review", content=(b"x" * (MAX_REQUEST_BYTES + 1)))
        self.assertEqual(response.status_code, 413)
        response = self.client.post("/documents/extract", content=b"x", headers={"x-document-format": "txt"})
        self.assertEqual(response.status_code, 415)

    def test_logs_contain_metrics_but_no_cv_or_query(self):
        with self.assertLogs("career_ai.requests", level="INFO") as captured:
            self.client.post("/compare?contact=fictitious-contact", json={"cv_text": "private-cv-marker SQL", "vacancy_text": "SQL"})
        log = " ".join(captured.output)
        self.assertNotIn("private-cv-marker", log)
        self.assertNotIn("fictitious-contact", log)
        self.assertIn('"latency_ms"', log)

    def test_legacy_analysis_remains_available(self):
        response = self.client.post("/analyze", json={"jobs": [{"title": "Demo", "company": "Demo", "description": "Python SQL"}], "profile_skills": ["SQL"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["jobs"][0]["match"]["skill_coverage"], .5)
