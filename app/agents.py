import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

# --- Configuration & Mode Detection ---
USE_MOCK = True
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

try:
    if GEMINI_API_KEY:
        import google.generativeai as genai
        # Configure the Google GenAI SDK
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Try importing ADK
        try:
            from google.adk.agents import Agent
            print("[SysSentinel] Successfully loaded Google ADK and configured Gemini API.")
            USE_MOCK = False
        except ImportError:
            # Fallback to direct GenAI if ADK is missing but API key is available
            print("[SysSentinel] Google ADK library not found, but GEMINI_API_KEY is present. Using direct Gemini GenAI fallback.")
            USE_MOCK = False
    else:
        print("[SysSentinel] GEMINI_API_KEY environment variable not set. Running in MOCK/SIMULATION mode.")
except Exception as e:
    print(f"[SysSentinel] Setup error ({e}). Running in MOCK/SIMULATION mode.")


# --- Simulated Tools / Data Sources ---

def check_disk_space(server_id: str) -> str:
    """Queries the server for disk space usage.
    
    Args:
        server_id: The hostname or ID of the server (e.g. 'prod-web-02', 'prod-db-01')
    """
    server_id = server_id.lower()
    if "web" in server_id or "web-02" in server_id:
        return json.dumps({
            "server": server_id,
            "status": "CRITICAL",
            "disk_usage": "97%",
            "available_space": "1.2GB",
            "partition": "/var/log"
        })
    elif "db" in server_id or "db-01" in server_id:
        return json.dumps({
            "server": server_id,
            "status": "OK",
            "disk_usage": "48%",
            "available_space": "120GB",
            "partition": "/data"
        })
    else:
        return json.dumps({
            "server": server_id,
            "status": "OK",
            "disk_usage": "35%",
            "available_space": "15GB",
            "partition": "/"
        })


def check_db_connections(server_id: str) -> str:
    """Checks active connection pools and database statistics.
    
    Args:
        server_id: The database server ID or hostname.
    """
    server_id = server_id.lower()
    if "db" in server_id or "db-01" in server_id:
        return json.dumps({
            "server": server_id,
            "status": "CRITICAL",
            "active_connections": 198,
            "max_connections": 200,
            "connection_state": "Exhausted",
            "slow_queries": 12
        })
    else:
        return json.dumps({
            "server": server_id,
            "status": "WARNING",
            "active_connections": 5,
            "max_connections": 50,
            "connection_state": "Idle"
        })


def get_process_list(server_id: str) -> str:
    """Gets the top CPU and Memory intensive processes on the target server.
    
    Args:
        server_id: Target server hostname.
    """
    server_id = server_id.lower()
    if "web" in server_id:
        return json.dumps({
            "server": server_id,
            "processes": [
                {"pid": 1205, "name": "nginx-worker", "cpu": "85.2%", "memory": "2.1%"},
                {"pid": 1206, "name": "nginx-worker", "cpu": "12.4%", "memory": "1.8%"},
                {"pid": 943, "name": "systemd-journal", "cpu": "0.1%", "memory": "0.5%"}
            ]
        })
    elif "db" in server_id:
        return json.dumps({
            "server": server_id,
            "processes": [
                {"pid": 4501, "name": "postgres-backend", "cpu": "45.0%", "memory": "15.2%"},
                {"pid": 4502, "name": "postgres-backend", "cpu": "38.5%", "memory": "12.1%"},
                {"pid": 801, "name": "sshd", "cpu": "0.1%", "memory": "0.2%"}
            ]
        })
    else:
        return json.dumps({
            "server": server_id,
            "processes": [
                {"pid": 111, "name": "systemd", "cpu": "0.0%", "memory": "0.1%"}
            ]
        })


# --- Mock Agent Definition (Fallback) ---

class MockAgent:
    def __init__(self, name: str, instruction: str, tools=None):
        self.name = name
        self.instruction = instruction
        self.tools = tools or []

    def run(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        
        if self.name == "triage_agent":
            # Categorize the alert
            severity = "HIGH"
            category = "Infrastructure"
            target_server = "unknown-server"
            
            # Find target server in prompt
            server_match = re.search(r'(prod-web-\d+|prod-db-\d+|api-\w+)', prompt_lower)
            if server_match:
                target_server = server_match.group(1)
                
            if "database" in prompt_lower or "db" in prompt_lower or "timeout" in prompt_lower:
                category = "Database"
                severity = "CRITICAL"
                if target_server == "unknown-server":
                    target_server = "prod-db-01"
            elif "cpu" in prompt_lower or "memory" in prompt_lower or "disk" in prompt_lower or "space" in prompt_lower:
                category = "Infrastructure"
                severity = "HIGH"
                if target_server == "unknown-server":
                    target_server = "prod-web-02"
                    
            return json.dumps({
                "alert": prompt,
                "category": category,
                "severity": severity,
                "target_server": target_server,
                "triage_summary": f"Identified a {severity} severity {category} issue affecting {target_server}."
            }, indent=2)

        elif self.name == "rag_agent":
            # Search database
            tickets = [
                {
                    "ticket_id": "INC-1024",
                    "title": "Database connection timeout in prod-db-01",
                    "root_cause": "Active connections reached connection pool limit (200).",
                    "resolution": "Run pg_terminate_backend on idle connections. Reconfigure pool size."
                },
                {
                    "ticket_id": "INC-2048",
                    "title": "Disk space low /var/log/nginx on prod-web-02",
                    "root_cause": "Nginx access logs accumulated without rotation.",
                    "resolution": "Truncate /var/log/nginx/access.log, force logrotate run, update logrotate cron configuration."
                }
            ]
            
            matched = []
            if "db" in prompt_lower or "database" in prompt_lower or "timeout" in prompt_lower:
                matched.append(tickets[0])
            if "disk" in prompt_lower or "web" in prompt_lower or "log" in prompt_lower:
                matched.append(tickets[1])
                
            if not matched:
                matched.append({
                    "ticket_id": "INC-GENERIC",
                    "title": "Generic resource alert",
                    "root_cause": "Underlying process consuming excessive system resources.",
                    "resolution": "Gather thread dumps, analyze CPU processes, and restart service."
                })
                
            return json.dumps({
                "query": prompt,
                "historical_matches": matched
            }, indent=2)

        elif self.name == "diagnostic_agent":
            # Extract server from prompt
            target_server = "prod-web-02"
            if "db" in prompt_lower or "db-01" in prompt_lower:
                target_server = "prod-db-01"
                
            # Simulate calling the correct tool
            diag_output = ""
            patch_script = ""
            action_plan = ""
            
            if target_server == "prod-db-01":
                db_stats = check_db_connections(target_server)
                processes = get_process_list(target_server)
                diag_output = f"DB Status: {db_stats}\nTop Processes: {processes}"
                patch_script = "sudo -u postgres psql -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '5 minutes';\""
                action_plan = "Terminate idle connections holding onto connection pool slots. Increase database max_connections parameter to 300."
            else:
                disk_stats = check_disk_space(target_server)
                processes = get_process_list(target_server)
                diag_output = f"Disk Space: {disk_stats}\nTop Processes: {processes}"
                patch_script = "sudo truncate -s 0 /var/log/nginx/access.log && sudo logrotate -f /etc/logrotate.d/nginx"
                action_plan = "Truncate the bloated Nginx access logs to reclaim disk space immediately. Force log rotation."

            return json.dumps({
                "server": target_server,
                "diagnostic_run": diag_output,
                "recommended_patch_script": patch_script,
                "action_plan": action_plan
            }, indent=2)

        return "Mock response"


# --- Real Gemini SDK Fallback Class ---

class GeminiAgent:
    def __init__(self, name: str, instruction: str, tools=None):
        self.name = name
        self.instruction = instruction
        self.tools = tools or []
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=instruction,
            tools=self.tools if self.tools else None
        )

    def run(self, prompt: str) -> str:
        try:
            response = self.model.generate_content(prompt)
            # If the model used tools, call them. 
            # In a full ADK implementation, the framework handles this loop automatically.
            # Here, we do a basic function calling execution handler if model wants tool call.
            if response.candidates and response.candidates[0].function_calls:
                call = response.candidates[0].function_calls[0]
                tool_func = None
                for t in self.tools:
                    if t.__name__ == call.name:
                        tool_func = t
                        break
                if tool_func:
                    # Executing function tool
                    args = dict(call.args)
                    tool_result = tool_func(**args)
                    # Send result back to model
                    chat = self.model.start_chat()
                    follow_up = chat.send_message(f"Tool {call.name} returned: {tool_result}. Please summarize the final resolution.")
                    return follow_up.text
            return response.text
        except Exception as e:
            print(f"[GeminiAgent {self.name}] Error running LLM call ({e}). Falling back to simulation.")
            fallback_mock = MockAgent(self.name, self.instruction, self.tools)
            return fallback_mock.run(prompt)


# --- Factory Function for Agents ---

def create_agent(name: str, instruction: str, tools=None):
    if USE_MOCK:
        return MockAgent(name, instruction, tools)
    else:
        # If ADK was successfully loaded, use the ADK Agent
        try:
            from google.adk.agents import Agent
            # Note: Depending on the ADK SDK version, we initialize Agent using name, model, instruction, tools.
            return Agent(
                name=name,
                model="gemini-2.5-flash",
                instruction=instruction,
                tools=tools
            )
        except Exception:
            # Fallback to direct Gemini GenAI wrapper if ADK has syntax discrepancy
            return GeminiAgent(name, instruction, tools)
