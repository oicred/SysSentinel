import unittest
import json
import os
from agents import (
    check_disk_space,
    check_db_connections,
    get_process_list,
    create_agent
)

class TestSysSentinel(unittest.TestCase):
    
    def test_check_disk_space_tool(self):
        # Test default response for web server
        web_res = json.loads(check_disk_space("prod-web-02"))
        self.assertEqual(web_res["status"], "CRITICAL")
        self.assertEqual(web_res["disk_usage"], "97%")
        
        # Test db response
        db_res = json.loads(check_disk_space("prod-db-01"))
        self.assertEqual(db_res["status"], "OK")
        
    def test_check_db_connections_tool(self):
        # Test db connection status
        db_conn = json.loads(check_db_connections("prod-db-01"))
        self.assertEqual(db_conn["status"], "CRITICAL")
        self.assertEqual(db_conn["connection_state"], "Exhausted")
        
    def test_get_process_list_tool(self):
        # Test process list on web
        processes = json.loads(get_process_list("prod-web-02"))
        self.assertTrue(len(processes["processes"]) > 0)
        self.assertEqual(processes["processes"][0]["name"], "nginx-worker")

    def test_triage_agent_run(self):
        triage_agent = create_agent("triage_agent", "Test Instruction")
        res_raw = triage_agent.run("Database connection pool exhausted in prod-db-01")
        res = json.loads(res_raw)
        
        self.assertEqual(res["category"], "Database")
        self.assertEqual(res["severity"], "CRITICAL")
        self.assertEqual(res["target_server"], "prod-db-01")

    def test_rag_agent_run(self):
        rag_agent = create_agent("rag_agent", "Test Instruction")
        res_raw = rag_agent.run("database timeout")
        res = json.loads(res_raw)
        
        self.assertTrue(len(res["historical_matches"]) > 0)
        self.assertEqual(res["historical_matches"][0]["ticket_id"], "INC-1024")

    def test_diagnostic_agent_run(self):
        diagnostic_agent = create_agent("diagnostic_agent", "Test Instruction")
        res_raw = diagnostic_agent.run("db-01 server database issues")
        res = json.loads(res_raw)
        
        self.assertEqual(res["server"], "prod-db-01")
        self.assertTrue("pg_terminate_backend" in res["recommended_patch_script"])

if __name__ == "__main__":
    unittest.main()
