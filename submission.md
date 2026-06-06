# Ready to start building? Check out this guide for next steps.

## Problem to solve
Production service outages and server resource exhaustion incidents cost B2B enterprises billions in downtime and operational overhead. When an IT alert fires, on-call Site Reliability Engineers (SREs) must manually perform a repetitive sequence of actions: triage the severity, search historical logs and post-mortem tickets for previous patterns, log into the target machine to run diagnostic checks, and finally write and run remediation scripts. This manual resolution process typically takes 30-90 minutes, leading to extended downtime and fatigue for engineering teams.

## Our solution
**SysSentinel** is an automated, multi-agent IT Incident Resolution Orchestrator that cuts incident resolution time from hours to seconds. Built on the Google Cloud Agent Development Kit (ADK), SysSentinel automates the entire triage-to-remediation workflow by coordinating three specialized, collaborative agents:
1. **Triage Agent:** Instantly processes incoming raw alert strings (e.g. CPU spikes or DB connection failures), determines severity levels, isolates the affected target server, and classifies the category.
2. **Knowledge Base (RAG) Agent:** Connects to internal systems (support ticket history and runbooks) using search queries formulated from the triage data to discover previous occurrences and resolutions.
3. **Diagnostic & Patch Agent:** Connects securely to the target system via custom tooling to run diagnostic checks (e.g. disk space inspection, memory limits, and process analysis). It cross-references these live metrics with the historical resolutions to output a step-by-step action plan and a ready-to-execute, safe bash shell remediation patch script.

Instead of a simple chatbot, SysSentinel acts as a production-grade action engine that moves from static reporting to declarative intent, generating automated fixes that can be safely applied to keep business infrastructure running.

## Technologies used
* **Intelligence:** Google Gemini 2.5 Flash model, driving high-speed and accurate classification, semantic search formulation, and code generation.
* **Orchestration:** Google Cloud Agent Development Kit (ADK) Python SDK, enabling structured multi-agent collaboration, state sharing, and modular agent execution graphs.
* **Infrastructure:** Designed for deployment on Google Cloud Run (containerized microservice) to achieve elastic scalability.
* **Integrations:** Vertex AI Search (grounding and RAG implementation), and Model Context Protocol (MCP) for secure tool connections.

## Data sources
* **Incident History Database:** Mocked RAG data source simulating internal Jira Service Desk or ServiceNow historic ticket logs containing past resolutions.
* **Server Metrics & System API:** Live tool connection to target servers, retrieving CPU load, disk partitions, active database connections, and active OS process lists.

## Findings and learnings
* **Multi-Agent Specialization:** Designing specialized agents with single-focus scopes (Triage vs. Diagnostics) drastically improves overall accuracy compared to a single monolithic agent attempting to parse files, search documentation, and write scripts in one prompt.
* **The Power of Grounding:** Injecting historical runbook contexts into the diagnostic generator's prompt eliminates model hallucination, ensuring that proposed bash commands conform to company safety standards and previous successful practices.
* **State Management:** Using ADK's session execution allowed seamless handoffs of structured metadata (like target server hostname and severity levels) between different agents, showing how complex multi-step developer operations can be reliably automated.

## Third-party integrations (if applicable)
No third-party SDKs or unauthorized content were utilized. The solution relies exclusively on standard Python libraries, standard Google Cloud Vertex AI / ADK frameworks, and simulated local metrics tools.
