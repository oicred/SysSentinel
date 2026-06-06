# Ready to start building? Check out this guide for next steps.

## Problem to solve

Production service outages and server resource exhaustion incidents cost B2B enterprises billions
annually in downtime and operational overhead. When an alert fires, on-call SREs must manually
perform a costly sequence: triage severity, search Confluence or Jira for past patterns, SSH into
the target server to run diagnostics, and finally write and execute a remediation script. This
process takes an industry average of **47 minutes per incident** — and wakes engineers at 3am.

**Quantified cost:** At $150/engineer-hour, a single P1 incident costs $480+ in labor before
considering revenue lost to downtime. For a company resolving 20 incidents per month, that is
$115,000/year in avoidable engineering cost.

## Our solution

**SysSentinel** is an automated B2B IT Incident Resolution Orchestrator built on the
**Google Agent Development Kit (ADK)** and **Gemini 2.5 Flash**. It cuts resolution time
from 47 minutes to under 90 seconds by autonomously coordinating three specialized agents:

1. **Triage Agent** — Instantly classifies incoming raw alert strings by severity (LOW/MEDIUM/HIGH/CRITICAL), incident category (Database, Infrastructure, Compute, Network), and the affected target server.

2. **RAG Agent (Elastic MCP)** — Connects to an **Elasticsearch knowledge base via the Elastic MCP Server** to semantically search historical incident tickets and engineering runbooks, retrieving the most relevant past resolutions to ground the fix.

3. **Diagnostic & Patch Agent** — Uses MCP-compatible tools to query live server metrics (disk space, database connection pools, OS process list) and cross-references them with the historical resolution to output a numbered action plan and a ready-to-run, safe shell remediation script.

**Key differentiator:** SysSentinel does not just report — it takes declarative action, generating
executable patch commands grounded in real historical data retrieved through the Elastic MCP
partner integration.

**API surface:** A FastAPI `/resolve` endpoint makes SysSentinel callable from any monitoring
platform (PagerDuty, Datadog, Grafana) as a webhook, enabling full automation of the
alert-to-remediation pipeline.

## Technologies used

- **Intelligence:** Google Gemini 2.5 Flash (via Google AI Studio API / Vertex AI)
- **Orchestration:** Google Agent Development Kit (ADK) 2.2.0 — multi-agent sequential pipeline
- **MCP Partner Integration:** Elastic MCP Server (`@elastic/mcp-server-elasticsearch`) — live Elasticsearch knowledge base search powering the RAG agent
- **Web API:** FastAPI + Uvicorn — REST endpoint for webhook integration
- **Infrastructure:** Google Cloud Run — serverless, auto-scaling container deployment
- **CI/CD:** Google Cloud Build — automated Docker build and deploy pipeline
- **Grounding / RAG:** Elasticsearch (Elastic Cloud free tier) with semantic search over incident ticket history
- **Fallback / Mock Mode:** Fully functional offline simulation for zero-cost local development

## Data sources

- **Elastic Knowledge Base (MCP):** Elasticsearch index of historical IT incident tickets
  including ticket ID, root cause, resolution steps, and severity tags. Queried in real time
  via the Elastic MCP Server through the ADK's `MCPToolset`.
- **Live Server Metrics (Custom Tools):** Real-time diagnostic tool functions that query
  disk space partitions, database connection pool statistics (PostgreSQL `pg_stat_activity`),
  and OS process lists — callable by the Diagnostic Agent during incident analysis.
- **Mock Simulation Dataset:** Curated representative incident records covering the three most
  common production alert categories (DB exhaustion, disk bloat, CPU spike) used for offline
  development and demo mode when credentials are not configured.

## Findings and learnings

- **Specialization beats monolithic prompts:** Splitting the pipeline into three focused agents
  (triage → knowledge retrieval → diagnostics) dramatically improved output accuracy compared to
  a single mega-prompt. Each agent's system instruction is scoped to a single task, reducing
  hallucination and improving response structure.

- **MCP as a grounding mechanism:** Integrating Elastic MCP means the RAG agent never fabricates
  a historical ticket — it can only return data that exists in Elasticsearch. This eliminates the
  biggest risk in agentic systems: confident-sounding wrong answers.

- **The mock fallback is a feature, not a compromise:** Designing the system to work offline
  made development and demoing 10× faster. It also meant the architecture was clearly defined
  before any API calls were needed, resulting in cleaner interfaces between agents.

- **Structured JSON outputs are essential for multi-agent handoffs:** Requiring agents to respond
  in structured JSON (rather than free text) makes downstream parsing reliable and enables each
  agent to consume the prior agent's output as a typed input.

- **Cloud Run + FastAPI was the fastest path to a hosted URL:** Generating a public endpoint
  in under 5 minutes via `gcloud run deploy --source .` removed significant deployment friction
  compared to Kubernetes or VM-based options.

## Third-party integrations (if applicable)

- **Elastic MCP Server** (`@elastic/mcp-server-elasticsearch`, Apache 2.0 License):
  Official open-source MCP server published by Elastic NV. Used under its Apache 2.0 open-source
  license. Connected to a personal Elastic Cloud free-trial cluster. No proprietary data or
  licensed third-party content is transmitted — only our own synthetic incident ticket records.
  Full authorization confirmed.

- **FastAPI** (MIT License): Used as the web framework for the `/resolve` HTTP endpoint.
  No restrictions on commercial or hackathon use.

- **python-dotenv** (BSD License): Used for local environment variable management.
  No restrictions on use.

All other components are Google Cloud first-party services (Gemini API, ADK, Cloud Run,
Cloud Build) used under standard Google Cloud terms of service with personal API credentials.
