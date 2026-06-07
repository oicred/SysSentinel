# SysSentinel Hackathon Submission

## Problem To Solve

When a production alert fires, an on-call engineer must classify it, search for similar
past incidents, inspect diagnostic data, and draft a remediation. The process is
repetitive, slow under pressure, and difficult to standardize across a growing team.

## Our Solution

SysSentinel is a human-in-the-loop IT incident investigation assistant built for B2B
operations teams. It coordinates three specialized agents:

1. The Triage Agent classifies severity, category, and target host.
2. The Knowledge Agent retrieves a similar incident and its previous resolution.
3. The Diagnostic Agent evaluates diagnostic data and drafts an action plan and
   remediation script.

The API returns a structured incident report and discloses whether Gemini, mock data,
or live Elasticsearch retrieval produced each result. Remediation scripts are proposals
only and always require operator approval.

## Technologies Used

- Gemini 2.5 Flash
- Google Agent Development Kit
- FastAPI and Uvicorn
- Google Cloud Run
- Google Cloud Build
- Optional Elasticsearch REST API integration

## Data Sources

- A small synthetic incident-ticket knowledge base for reproducible demos
- Simulated disk, database connection, and process diagnostic tools
- Optional Elasticsearch index containing authorized incident records

## Findings And Learnings

- Specialized agents produced clearer handoffs than one broad prompt.
- Structured JSON makes agent outputs easier to validate and expose through an API.
- A deterministic mock mode makes demos and automated tests reliable.
- Agentic remediation needs explicit source disclosure and a human approval boundary.

## Third-Party Integrations

- Elasticsearch REST API, when configured, queries only incident records the operator
  is authorized to access.
- FastAPI, Uvicorn, HTTPX, and python-dotenv are used under their open-source licenses.

## Current Limitations

The diagnostic connectors are simulated and the service does not execute remediation
commands. Elastic MCP is not part of the current demonstrated build; Elasticsearch REST
retrieval is the optional live knowledge integration.
