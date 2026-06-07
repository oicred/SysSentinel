"""
SysSentinel API Tests
======================
Tests the FastAPI endpoints using TestClient (no server required).
Runs offline — MOCK mode only.
"""

import json
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from api import app

client = TestClient(app)


class TestHealthEndpoint(unittest.TestCase):

    def test_health_returns_200(self):
        resp = client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_health_has_service_name(self):
        data = resp = client.get("/").json()
        self.assertEqual(data["service"], "SysSentinel")

    def test_health_has_run_mode(self):
        data = client.get("/").json()
        self.assertIn("run_mode", data)
        self.assertIn(data["run_mode"], ["MOCK", "LIVE_GENAI", "LIVE_ADK"])

    def test_health_has_endpoints(self):
        data = client.get("/").json()
        self.assertIn("endpoints", data)

    def test_health_discloses_safety_boundary(self):
        data = client.get("/").json()
        self.assertEqual(data["diagnostics_source"], "simulated_diagnostic_tools")
        self.assertTrue(data["remediation_requires_approval"])


class TestResolveEndpoint(unittest.TestCase):

    def _post(self, alert: str, context: str = None) -> dict:
        payload = {"alert": alert}
        if context:
            payload["context"] = context
        resp = client.post("/resolve", json=payload)
        self.assertEqual(resp.status_code, 200, msg=resp.text)
        return resp.json()

    def test_db_alert_resolves(self):
        data = self._post("Database connection pool timeout in prod-db-01")
        self.assertEqual(data["triage"]["severity"], "CRITICAL")
        self.assertEqual(data["triage"]["category"], "Database")
        self.assertIn("pg_terminate_backend",
                      data["diagnostics"]["recommended_patch_script"])

    def test_disk_alert_resolves(self):
        data = self._post("Disk space critical on prod-web-02", context="production")
        self.assertEqual(data["triage"]["category"], "Infrastructure")
        self.assertIn("truncate",
                      data["diagnostics"]["recommended_patch_script"].lower())

    def test_response_has_resolution_time(self):
        data = self._post("CPU usage high on prod-web-02")
        self.assertIn("resolution_time_ms", data)
        self.assertGreaterEqual(data["resolution_time_ms"], 0)

    def test_response_discloses_sources_and_approval_requirement(self):
        data = self._post("database timeout prod-db-01")
        self.assertEqual(data["diagnostics_source"], "simulated_diagnostic_tools")
        self.assertTrue(data["remediation_requires_approval"])
        self.assertIn("knowledge_source", data)

    def test_response_has_knowledge_base(self):
        data = self._post("database timeout prod-db-01")
        self.assertIn("knowledge_base", data)
        self.assertIn("historical_matches", data["knowledge_base"])
        self.assertGreater(len(data["knowledge_base"]["historical_matches"]), 0)

    def test_empty_alert_returns_422(self):
        resp = client.post("/resolve", json={"alert": ""})
        self.assertEqual(resp.status_code, 422)

    def test_missing_alert_returns_422(self):
        resp = client.post("/resolve", json={})
        self.assertEqual(resp.status_code, 422)


class TestExamplesEndpoint(unittest.TestCase):

    def test_examples_returns_200(self):
        resp = client.get("/resolve/examples")
        self.assertEqual(resp.status_code, 200)

    def test_examples_has_list(self):
        data = client.get("/resolve/examples").json()
        self.assertIn("examples", data)
        self.assertGreaterEqual(len(data["examples"]), 2)

    def test_each_example_has_payload(self):
        data = client.get("/resolve/examples").json()
        for ex in data["examples"]:
            self.assertIn("payload", ex)
            self.assertIn("alert", ex["payload"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
