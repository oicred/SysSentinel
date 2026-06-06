"""
SysSentinel — Test Suite (Phase 2)
====================================
Tests tools, agents (mock mode), and the FastAPI API endpoints.
All tests run offline (MOCK mode) — no API key required.
"""

import json
import os
import sys
import unittest

# Ensure app/ is on path when running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from agents import (
    check_disk_space,
    check_db_connections,
    get_process_list,
    search_incident_knowledge_base,
    create_agent,
    get_run_mode,
    is_elastic_active,
)


# ─── Tool Tests ────────────────────────────────────────────────────────────────

class TestDiagnosticTools(unittest.TestCase):

    def test_disk_space_web_critical(self):
        data = json.loads(check_disk_space("prod-web-02"))
        self.assertEqual(data["status"], "CRITICAL")
        self.assertEqual(data["disk_usage"], "97%")
        self.assertIn("partition", data)

    def test_disk_space_db_ok(self):
        data = json.loads(check_disk_space("prod-db-01"))
        self.assertEqual(data["status"], "OK")
        self.assertGreater(int(data["available_space"].replace("GB", "")), 100)

    def test_db_connections_exhausted(self):
        data = json.loads(check_db_connections("prod-db-01"))
        self.assertEqual(data["status"], "CRITICAL")
        self.assertEqual(data["connection_state"], "Exhausted")
        self.assertGreaterEqual(data["active_connections"], 195)

    def test_db_connections_idle_server(self):
        data = json.loads(check_db_connections("prod-web-02"))
        self.assertEqual(data["status"], "WARNING")

    def test_process_list_web(self):
        data = json.loads(get_process_list("prod-web-02"))
        self.assertTrue(len(data["processes"]) > 0)
        self.assertEqual(data["processes"][0]["name"], "nginx-worker")

    def test_process_list_db(self):
        data = json.loads(get_process_list("prod-db-01"))
        self.assertTrue(any("postgres" in p["name"] for p in data["processes"]))


# ─── Knowledge Base / RAG Tool Tests ──────────────────────────────────────────

class TestKnowledgeBase(unittest.TestCase):

    def test_database_query_returns_inc1024(self):
        result = json.loads(search_incident_knowledge_base("database connection timeout"))
        ids = [m["ticket_id"] for m in result["historical_matches"]]
        self.assertIn("INC-1024", ids)

    def test_disk_query_returns_inc2048(self):
        result = json.loads(search_incident_knowledge_base("disk space log web"))
        ids = [m["ticket_id"] for m in result["historical_matches"]]
        self.assertIn("INC-2048", ids)

    def test_result_has_resolution_field(self):
        result = json.loads(search_incident_knowledge_base("cpu high load"))
        for match in result["historical_matches"]:
            self.assertIn("resolution", match)
            self.assertIn("ticket_id", match)

    def test_max_results_respected(self):
        result = json.loads(search_incident_knowledge_base("server issue", max_results=1))
        self.assertLessEqual(len(result["historical_matches"]), 1)

    def test_elastic_inactive_in_test_env(self):
        # In test env without ES credentials, should use mock
        self.assertFalse(is_elastic_active())
        result = json.loads(search_incident_knowledge_base("any query"))
        self.assertEqual(result["source"], "mock_knowledge_base")


# ─── Agent Tests ───────────────────────────────────────────────────────────────

class TestTriageAgent(unittest.TestCase):

    def setUp(self):
        self.agent = create_agent("triage_agent", "Test instruction")

    def test_database_alert_classified_critical(self):
        raw = self.agent.run("Database connection pool timeout in prod-db-01")
        data = json.loads(raw)
        self.assertEqual(data["category"], "Database")
        self.assertEqual(data["severity"], "CRITICAL")
        self.assertEqual(data["target_server"], "prod-db-01")

    def test_disk_alert_classified_high(self):
        raw = self.agent.run("Disk space is critical on server prod-web-02")
        data = json.loads(raw)
        self.assertEqual(data["category"], "Infrastructure")
        self.assertEqual(data["severity"], "HIGH")
        self.assertEqual(data["target_server"], "prod-web-02")

    def test_triage_has_summary_field(self):
        raw = self.agent.run("CPU spike on prod-web-02")
        data = json.loads(raw)
        self.assertIn("triage_summary", data)
        self.assertTrue(len(data["triage_summary"]) > 0)


class TestRAGAgent(unittest.TestCase):

    def setUp(self):
        self.agent = create_agent(
            "rag_agent", "Test instruction",
            tools=[search_incident_knowledge_base]
        )

    def test_db_query_returns_matches(self):
        raw = self.agent.run("database timeout prod-db-01")
        data = json.loads(raw)
        self.assertIn("historical_matches", data)
        self.assertGreater(len(data["historical_matches"]), 0)

    def test_disk_query_returns_matches(self):
        raw = self.agent.run("disk space web server log")
        data = json.loads(raw)
        self.assertIn("historical_matches", data)


class TestDiagnosticAgent(unittest.TestCase):

    def setUp(self):
        self.agent = create_agent(
            "diagnostic_agent", "Test instruction",
            tools=[check_disk_space, check_db_connections, get_process_list]
        )

    def test_db_alert_generates_pg_patch(self):
        raw = self.agent.run("db-01 database connection pool exhausted")
        data = json.loads(raw)
        self.assertIn("recommended_patch_script", data)
        self.assertIn("pg_terminate_backend", data["recommended_patch_script"])

    def test_disk_alert_generates_logrotate_patch(self):
        raw = self.agent.run("disk space critical on prod-web-02")
        data = json.loads(raw)
        self.assertIn("recommended_patch_script", data)
        self.assertIn("truncate", data["recommended_patch_script"].lower())

    def test_action_plan_has_numbered_steps(self):
        raw = self.agent.run("db-01 database timeout")
        data = json.loads(raw)
        self.assertIn("action_plan", data)
        self.assertIn("1.", data["action_plan"])


# ─── Run Mode Test ─────────────────────────────────────────────────────────────

class TestRunMode(unittest.TestCase):

    def test_mode_is_mock_without_api_key(self):
        # In CI / no-key environments this must be MOCK
        if not os.environ.get("GEMINI_API_KEY"):
            self.assertEqual(get_run_mode(), "MOCK")


if __name__ == "__main__":
    unittest.main(verbosity=2)
