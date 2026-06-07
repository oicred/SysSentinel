"""
SysSentinel Agent Definitions
==============================
Multi-agent IT Incident Resolution system built on Google ADK + Gemini.

Run modes (auto-detected from environment):
  1. LIVE ADK    — GEMINI_API_KEY + google-adk installed → full Gemini reasoning
  2. LIVE GENAI  — GEMINI_API_KEY only (no ADK) → direct google-generativeai
  3. MOCK        — No API key → deterministic simulation for offline demos

Optional integration: Elasticsearch REST API
  Set ELASTICSEARCH_URL + ELASTICSEARCH_API_KEY in .env to activate live REST search.
"""

import os
import json
import re
import asyncio
from dotenv import load_dotenv

load_dotenv()

# ─── Configuration ─────────────────────────────────────────────────────────────

GEMINI_API_KEY      = os.environ.get("GEMINI_API_KEY", "")
ELASTICSEARCH_URL   = os.environ.get("ELASTICSEARCH_URL", "")
ELASTICSEARCH_API_KEY = os.environ.get("ELASTICSEARCH_API_KEY", "")
GEMINI_MODEL        = "gemini-2.5-flash"

# Google ADK reads GOOGLE_API_KEY, while the project exposes GEMINI_API_KEY.
if GEMINI_API_KEY and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

# Determine run mode
RUN_MODE = "MOCK"
_adk_available = False
_genai_available = False

try:
    if GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _genai_available = True

        try:
            from google.adk.agents import Agent
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            from google.genai.types import Content, Part
            _adk_available = True
            RUN_MODE = "LIVE_ADK"
            print(f"[SysSentinel] [OK] Google ADK + Gemini API active (model: {GEMINI_MODEL})")
        except ImportError:
            RUN_MODE = "LIVE_GENAI"
            print(f"[SysSentinel] [OK] Gemini API active (direct genai, no ADK). Model: {GEMINI_MODEL}")
    else:
        print("[SysSentinel] [MOCK] GEMINI_API_KEY not set - running in MOCK/SIMULATION mode")
except Exception as e:
    print(f"[SysSentinel] [WARN] Setup error ({e}) - falling back to MOCK mode")

# Elastic live-search status
MCP_ELASTIC_ACTIVE = bool(ELASTICSEARCH_URL and ELASTICSEARCH_API_KEY)
if MCP_ELASTIC_ACTIVE:
    print(f"[SysSentinel] [Elastic] Live search configured -> {ELASTICSEARCH_URL}")
else:
    print("[SysSentinel] [KB] Live Elastic search not configured - using mock knowledge base")


# --- Simulated Diagnostic Tools (MCP-compatible function signatures) -----------

def check_disk_space(server_id: str) -> str:
    """Query disk space usage on the target server.

    Args:
        server_id: The hostname or ID of the server (e.g. 'prod-web-02', 'prod-db-01')

    Returns:
        JSON string with disk usage statistics.
    """
    s = server_id.lower()
    if "web" in s:
        return json.dumps({
            "server": server_id, "status": "CRITICAL",
            "disk_usage": "97%", "available_space": "1.2GB",
            "partition": "/var/log", "inode_usage": "88%"
        })
    elif "db" in s:
        return json.dumps({
            "server": server_id, "status": "OK",
            "disk_usage": "48%", "available_space": "120GB",
            "partition": "/data", "inode_usage": "12%"
        })
    return json.dumps({
        "server": server_id, "status": "OK",
        "disk_usage": "35%", "available_space": "15GB", "partition": "/"
    })


def check_db_connections(server_id: str) -> str:
    """Check active database connection pool statistics.

    Args:
        server_id: The database server hostname or ID.

    Returns:
        JSON string with connection pool metrics.
    """
    s = server_id.lower()
    if "db" in s:
        return json.dumps({
            "server": server_id, "status": "CRITICAL",
            "active_connections": 198, "max_connections": 200,
            "connection_state": "Exhausted", "slow_queries": 12,
            "avg_query_time_ms": 4230, "deadlocks_last_hour": 3
        })
    return json.dumps({
        "server": server_id, "status": "WARNING",
        "active_connections": 5, "max_connections": 50,
        "connection_state": "Idle", "slow_queries": 0
    })


def get_process_list(server_id: str) -> str:
    """Get top CPU and memory intensive processes on the server.

    Args:
        server_id: Target server hostname.

    Returns:
        JSON string listing top processes.
    """
    s = server_id.lower()
    if "web" in s:
        return json.dumps({
            "server": server_id,
            "processes": [
                {"pid": 1205, "name": "nginx-worker", "cpu": "85.2%", "memory": "2.1%", "state": "R"},
                {"pid": 1206, "name": "nginx-worker", "cpu": "12.4%", "memory": "1.8%", "state": "R"},
                {"pid": 943,  "name": "systemd-journal", "cpu": "0.1%", "memory": "0.5%", "state": "S"},
            ]
        })
    elif "db" in s:
        return json.dumps({
            "server": server_id,
            "processes": [
                {"pid": 4501, "name": "postgres-backend", "cpu": "45.0%", "memory": "15.2%", "state": "R"},
                {"pid": 4502, "name": "postgres-backend", "cpu": "38.5%", "memory": "12.1%", "state": "R"},
                {"pid": 801,  "name": "sshd",             "cpu": "0.1%",  "memory": "0.2%",  "state": "S"},
            ]
        })
    return json.dumps({"server": server_id, "processes": [
        {"pid": 1, "name": "systemd", "cpu": "0.0%", "memory": "0.1%", "state": "S"}
    ]})


# --- Elastic Knowledge Base Tool ---------------------------------------------

def search_incident_knowledge_base(query: str, max_results: int = 3) -> str:
    """Search the Elastic knowledge base for historical incidents matching the query.

    When ELASTICSEARCH_URL and ELASTICSEARCH_API_KEY are set in the environment,
    this tool connects to a live Elasticsearch cluster through its REST API and
    queries incident ticket data.

    When not configured, returns curated simulated ticket data for demo purposes.

    Args:
        query: Natural language description of the current incident.
        max_results: Maximum number of historical matches to return.

    Returns:
        JSON string with list of matching historical incidents and resolutions.
    """
    if MCP_ELASTIC_ACTIVE:
        # Live Elasticsearch REST path
        # The REST path is usable in both ADK and fallback GenAI modes.
        try:
            import httpx
            headers = {
                "Authorization": f"ApiKey {ELASTICSEARCH_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "description", "resolution", "tags"],
                        "type": "best_fields"
                    }
                },
                "size": max_results
            }
            resp = httpx.post(
                f"{ELASTICSEARCH_URL}/incidents/_search",
                json=payload, headers=headers, timeout=10.0
            )
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
            matches = [
                {
                    "ticket_id": h["_source"].get("ticket_id", h["_id"]),
                    "title":       h["_source"].get("title", ""),
                    "root_cause":  h["_source"].get("root_cause", ""),
                    "resolution":  h["_source"].get("resolution", ""),
                    "score":       round(h["_score"], 3)
                }
                for h in hits
            ]
            return json.dumps({
                "source": "elastic_rest_live",
                "query": query,
                "historical_matches": matches
            }, indent=2)
        except Exception as e:
            print(f"[Elastic] [WARN] Live search failed ({e}), falling back to mock data")

    # ── Mock / offline path ────────────────────────────────────────────────────
    mock_tickets = [
        {
            "ticket_id": "INC-1024",
            "title":      "Database connection pool timeout in prod-db-01",
            "root_cause": "Active connections reached connection pool limit (200/200).",
            "resolution": "Run pg_terminate_backend on idle connections older than 5 min. "
                          "Increase max_connections to 300 in postgresql.conf and reload.",
            "score": 0.98
        },
        {
            "ticket_id": "INC-2048",
            "title":      "Disk space low /var/log/nginx on prod-web-02",
            "root_cause": "Nginx access logs accumulated without rotation (logrotate misconfigured).",
            "resolution": "Truncate /var/log/nginx/access.log, force logrotate run, "
                          "set daily rotation with 7-day retention in /etc/logrotate.d/nginx.",
            "score": 0.97
        },
        {
            "ticket_id": "INC-3072",
            "title":      "High CPU usage on api-gateway-01 during peak hours",
            "root_cause": "Unoptimized SQL queries in payment service causing full table scans.",
            "resolution": "Add composite index on (user_id, created_at). "
                          "Enable slow query log and review EXPLAIN plans.",
            "score": 0.89
        }
    ]
    ql = query.lower()
    if any(kw in ql for kw in ["db", "database", "timeout", "connection"]):
        matched = [mock_tickets[0]]
    elif any(kw in ql for kw in ["disk", "log", "space", "web"]):
        matched = [mock_tickets[1]]
    else:
        matched = [mock_tickets[2]]

    return json.dumps({
        "source": "mock_knowledge_base",
        "elastic_mcp_configured": MCP_ELASTIC_ACTIVE,
        "query": query,
        "historical_matches": matched[:max_results]
    }, indent=2)


# ─── Mock Agent (zero-dependency offline mode) ─────────────────────────────────

class MockAgent:
    """Deterministic rule-based agent for offline/demo use. No API calls."""

    def __init__(self, name: str, instruction: str, tools=None):
        self.name = name
        self.instruction = instruction
        self.tools = tools or []

    def run(self, prompt: str) -> str:
        ql = prompt.lower()

        if self.name == "triage_agent":
            server = "unknown-server"
            m = re.search(r'(prod-web-\d+|prod-db-\d+|api-[\w-]+)', ql)
            if m:
                server = m.group(1)
            if any(k in ql for k in ["database","db","timeout","connection","postgres","mysql"]):
                cat, sev = "Database", "CRITICAL"
                if server == "unknown-server": server = "prod-db-01"
            elif any(k in ql for k in ["cpu","memory","load","oom"]):
                cat, sev = "Compute", "HIGH"
                if server == "unknown-server": server = "prod-web-02"
            elif any(k in ql for k in ["disk","space","storage","inode","log"]):
                cat, sev = "Infrastructure", "HIGH"
                if server == "unknown-server": server = "prod-web-02"
            elif any(k in ql for k in ["network","latency","packet","dns","ssl"]):
                cat, sev = "Network", "MEDIUM"
                if server == "unknown-server": server = "api-gateway-01"
            else:
                cat, sev = "Infrastructure", "MEDIUM"
                if server == "unknown-server": server = "prod-web-02"

            return json.dumps({
                "alert": prompt,
                "category": cat,
                "severity": sev,
                "target_server": server,
                "triage_summary": f"{sev} severity {cat} incident detected on {server}."
            }, indent=2)

        elif self.name == "rag_agent":
            return search_incident_knowledge_base(prompt)

        elif self.name == "diagnostic_agent":
            server = "prod-db-01" if any(k in ql for k in ["db","database","postgres","connection"]) \
                     else "prod-web-02"
            if "db" in server:
                db  = json.loads(check_db_connections(server))
                ps  = json.loads(get_process_list(server))
                diag = f"DB connections: {db['active_connections']}/{db['max_connections']} " \
                       f"({db['connection_state']}), slow queries: {db['slow_queries']}, " \
                       f"deadlocks/hr: {db.get('deadlocks_last_hour',0)}"
                patch = ('sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) '
                         "FROM pg_stat_activity WHERE state = 'idle' "
                         "AND state_change < now() - interval '5 minutes';\"")
                plan  = ("1. Terminate idle Postgres connections (patch below).\n"
                         "2. Increase max_connections to 300 in postgresql.conf.\n"
                         "3. Set idle_in_transaction_session_timeout = '5min'.\n"
                         "4. Monitor pg_stat_activity for recurrence.")
            else:
                dk  = json.loads(check_disk_space(server))
                ps  = json.loads(get_process_list(server))
                diag = f"Disk: {dk['disk_usage']} used on {dk['partition']} " \
                       f"(only {dk['available_space']} free), inodes: {dk.get('inode_usage','N/A')}"
                patch = ("sudo truncate -s 0 /var/log/nginx/access.log\n"
                         "sudo logrotate -f /etc/logrotate.d/nginx\n"
                         "sudo find /var/log -name '*.gz' -mtime +7 -delete")
                plan  = ("1. Truncate bloated Nginx access log (patch below).\n"
                         "2. Force log rotation to create fresh log file.\n"
                         "3. Remove compressed logs older than 7 days.\n"
                         "4. Verify logrotate cron runs daily: crontab -l | grep logrotate")

            return json.dumps({
                "server": server,
                "diagnostic_summary": diag,
                "top_processes": ps["processes"][:3],
                "recommended_patch_script": patch,
                "action_plan": plan
            }, indent=2)

        return json.dumps({"response": "Mock agent completed"})


# ─── Live Gemini GenAI Agent (API key, no ADK) ─────────────────────────────────

class GenAIAgent:
    """Agent backed by google-generativeai SDK when ADK is unavailable."""

    TOOL_MAP = {
        "check_disk_space":               check_disk_space,
        "check_db_connections":           check_db_connections,
        "get_process_list":               get_process_list,
        "search_incident_knowledge_base": search_incident_knowledge_base,
    }

    def __init__(self, name: str, instruction: str, tools=None):
        self.name = name
        self.instruction = instruction
        self.tool_fns = tools or []
        self.model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=instruction,
            tools=self.tool_fns if self.tool_fns else None
        )

    def run(self, prompt: str) -> str:
        try:
            chat = self.model.start_chat()
            resp = chat.send_message(prompt)

            # Execute any requested tool calls and feed results back
            for _ in range(5):  # max tool call rounds
                calls = [p.function_call for p in resp.candidates[0].content.parts
                         if hasattr(p, "function_call") and p.function_call.name]
                if not calls:
                    break
                tool_responses = []
                for call in calls:
                    fn = self.TOOL_MAP.get(call.name)
                    result = fn(**dict(call.args)) if fn else f"Unknown tool: {call.name}"
                    tool_responses.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=call.name,
                                response={"result": result}
                            )
                        )
                    )
                resp = chat.send_message(tool_responses)

            return resp.text
        except Exception as e:
            print(f"[GenAIAgent:{self.name}] Error: {e} - falling back to mock")
            return MockAgent(self.name, self.instruction, self.tool_fns).run(prompt)


# ─── Live ADK Agent ─────────────────────────────────────────────────────────────

class ADKAgent:
    """Google ADK-backed agent with Gemini reasoning and registered tools."""

    def __init__(self, name: str, instruction: str, tools=None):
        self.name = name
        self.instruction = instruction
        self.tool_fns = tools or []
        self._agent = None
        self._runner = None
        self._session_service = None
        self._build()

    def _build(self):
        try:
            all_tools = list(self.tool_fns)
            self._agent = Agent(
                name=self.name,
                model=GEMINI_MODEL,
                instruction=self.instruction,
                tools=all_tools,
            )
            self._session_service = InMemorySessionService()
            self._runner = Runner(
                agent=self._agent,
                app_name=f"syssentinel_{self.name}",
                session_service=self._session_service,
            )
        except Exception as e:
            print(f"[ADKAgent:{self.name}] Build failed: {e}")
            self._runner = None

    def run(self, prompt: str) -> str:
        if not self._runner:
            return MockAgent(self.name, self.instruction, self.tool_fns).run(prompt)
        try:
            session = asyncio.run(
                self._session_service.create_session(
                    app_name=f"syssentinel_{self.name}",
                    user_id="syssentinel",
                )
            )
            content = Content(role="user", parts=[Part(text=prompt)])
            events = list(asyncio.run(
                self._collect_events(session.id, content)
            ))
            # Return the last text response from the agent
            for event in reversed(events):
                if hasattr(event, "content") and event.content:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            return part.text
            return json.dumps({"response": "ADK agent produced no text output"})
        except Exception as e:
            print(f"[ADKAgent:{self.name}] Runtime error: {e} - falling back to mock")
            return MockAgent(self.name, self.instruction, self.tool_fns).run(prompt)

    async def _collect_events(self, session_id: str, content):
        events = []
        async for event in self._runner.run_async(
            user_id="syssentinel",
            session_id=session_id,
            new_message=content
        ):
            events.append(event)
        return events


# ─── Agent Factory ─────────────────────────────────────────────────────────────

def create_agent(name: str, instruction: str, tools=None):
    """Instantiate the appropriate agent class based on available credentials."""
    if RUN_MODE == "LIVE_ADK":
        return ADKAgent(name, instruction, tools)
    elif RUN_MODE == "LIVE_GENAI":
        return GenAIAgent(name, instruction, tools)
    else:
        return MockAgent(name, instruction, tools)


def get_run_mode() -> str:
    return RUN_MODE


def is_elastic_active() -> bool:
    return MCP_ELASTIC_ACTIVE
