import sys
import argparse
import json
from agents import create_agent, check_disk_space, check_db_connections, get_process_list

def run_incident_resolution_flow(alert_text: str):
    print("=" * 60)
    print("      SYSSENTINEL: IT ALERT RESOLUTION ORCHESTRATOR      ")
    print("=" * 60)
    print(f"[Input Alert]: {alert_text}\n")

    # 1. Triage Phase
    print("[Step 1] Initializing Triage Agent...")
    triage_instruction = (
        "You are an IT Support Triage Agent. Your task is to analyze incoming alerts, "
        "determine the severity (LOW, MEDIUM, HIGH, CRITICAL), identify the target server, "
        "and classify the category of the alert (e.g., Infrastructure, Database, Network)."
    )
    triage_agent = create_agent("triage_agent", triage_instruction)
    
    print("[Step 1] Running triage classification...")
    triage_output_raw = triage_agent.run(alert_text)
    
    try:
        triage_data = json.loads(triage_output_raw)
    except json.JSONDecodeError:
        # If real LLM returned plain text instead of JSON, we format it as a fallback
        triage_data = {
            "alert": alert_text,
            "category": "Unclassified",
            "severity": "HIGH",
            "target_server": "prod-web-02",
            "triage_summary": triage_output_raw
        }
        
    print(f"  -> Category: {triage_data.get('category')}")
    print(f"  -> Severity: {triage_data.get('severity')}")
    print(f"  -> Target Server: {triage_data.get('target_server')}")
    print(f"  -> Summary: {triage_data.get('triage_summary')}\n")

    # 2. Historical Search (RAG) Phase
    print("[Step 2] Initializing RAG Agent...")
    rag_instruction = (
        "You are a Knowledge Base Assistant. Search historical support tickets and runbooks "
        "to find past resolutions for similar issues."
    )
    rag_agent = create_agent("rag_agent", rag_instruction)
    
    query = f"{triage_data.get('category')} - {triage_data.get('alert')}"
    print(f"[Step 2] Querying knowledge base for: '{query}'...")
    rag_output_raw = rag_agent.run(query)
    
    try:
        rag_data = json.loads(rag_output_raw)
    except json.JSONDecodeError:
        rag_data = {
            "query": query,
            "historical_matches": [{"ticket_id": "INC-UNKNOWN", "title": "Generic Match", "resolution": rag_output_raw}]
        }
        
    print(f"  -> Found {len(rag_data.get('historical_matches', []))} relevant historical ticket(s).\n")

    # 3. Diagnostic & Patch Generation Phase
    print("[Step 3] Initializing Diagnostic & Patch Agent...")
    diag_instruction = (
        "You are a Senior Site Reliability Engineer. Use the diagnostic tools to gather server status, "
        "analyze log sizes, inspect CPU process parameters, and compile a safe shell command script "
        "to resolve the issue based on historical incident patterns."
    )
    # Register the tools with the diagnostic agent
    tools = [check_disk_space, check_db_connections, get_process_list]
    diagnostic_agent = create_agent("diagnostic_agent", diag_instruction, tools=tools)
    
    server_id = triage_data.get("target_server", "prod-web-02")
    diag_prompt = (
        f"Server: {server_id}. Alert: {alert_text}. "
        f"Historical solutions: {json.dumps(rag_data.get('historical_matches'))}"
    )
    print(f"[Step 3] Executing server diagnostics and compiling resolution plan...")
    diag_output_raw = diagnostic_agent.run(diag_prompt)
    
    try:
        diag_data = json.loads(diag_output_raw)
    except json.JSONDecodeError:
        diag_data = {
            "server": server_id,
            "diagnostic_run": "Diagnostics completed.",
            "recommended_patch_script": "# Check system parameters manually",
            "action_plan": diag_output_raw
        }

    # 4. Final Incident Resolution Report
    print("=" * 60)
    print("                  INCIDENT RESOLUTION REPORT             ")
    print("=" * 60)
    print(f"Target Server : {diag_data.get('server')}")
    print(f"Severity      : {triage_data.get('severity')}")
    print(f"Incident Cat  : {triage_data.get('category')}")
    print("\n--- Diagnostic Findings ---")
    print(diag_data.get("diagnostic_run"))
    
    print("\n--- Historical Knowledge Match ---")
    for match in rag_data.get("historical_matches", []):
        print(f"[{match.get('ticket_id')}] {match.get('title')}")
        print(f"  -> Resolved by: {match.get('resolution')}")
        
    print("\n--- Action Plan ---")
    print(diag_data.get("action_plan"))
    
    print("\n--- Recommended Patch Script ---")
    print("\033[92m" + diag_data.get("recommended_patch_script") + "\033[0m")
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="SysSentinel Incident Orchestration Runner")
    parser.add_argument(
        "--alert", 
        type=str, 
        help="Alert string to process (e.g. 'Disk space critical on prod-web-02')"
    )
    args = parser.parse_args()

    if args.alert:
        run_incident_resolution_flow(args.alert)
    else:
        # Interactive mode default
        default_alert = "Database connection pool timeout in prod-db-01"
        print(f"No alert specified with --alert. Using default: '{default_alert}'\n")
        run_incident_resolution_flow(default_alert)

if __name__ == "__main__":
    main()
