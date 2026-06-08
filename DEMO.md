# SysSentinel Three-Minute Demo

## Before Recording

1. Deploy or run the API and open `/docs`.
2. Confirm `GET /` clearly shows the intended `run_mode`.
3. Enter the private judge key in Swagger's `X-Demo-Key` field for live mode.
4. If live Gemini is unavailable, use mock mode and state that clearly.
5. Keep the terminal visible so judges can see the service mode.

## Script

### 0:00-0:30 - Problem And Architecture

Show the README architecture and explain:

> On-call engineers repeatedly classify alerts, search old incidents, inspect systems,
> and draft fixes. SysSentinel coordinates that investigation while keeping a human in
> control of remediation.

### 0:30-1:35 - Database Scenario

In Swagger UI, call `POST /resolve`:

```json
{
  "alert": "Database connection pool timeout in prod-db-01",
  "context": "production"
}
```

Show the triage classification, historical incident, diagnostic summary, proposed
PostgreSQL command, source fields, and `remediation_requires_approval: true`.

### 1:35-2:25 - Disk Scenario

Call `POST /resolve`:

```json
{
  "alert": "Disk space is critical on server prod-web-02",
  "context": "production"
}
```

Show that the same workflow produces a different classification, historical match,
diagnostic result, and remediation proposal.

### 2:25-3:00 - Technical Proof And Close

Show the Cloud Run URL or local API, test command, and repository structure. Close with:

> SysSentinel demonstrates a reproducible multi-agent workflow for faster incident
> investigation. Every result discloses its source, and every remediation stays behind
> human approval.

## Recording Checklist

- Use a readable 1080p recording.
- Do not call simulated diagnostics "live server diagnostics."
- Do not claim the generated script was executed.
- Do not claim Elastic MCP unless a separate verified MCP integration is added.
- Keep the response source fields visible for judges.
- Never show or read the private demo key in the recording.
