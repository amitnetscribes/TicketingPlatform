# Enterprise Ticketing Platform

A comprehensive ticketing system blueprint and implementation starter that supports:

- Incident/faulty system tickets
- Service requests
- Subscription purchase requests
- Asset management
- Inventory management
- Configurable approval workflows by ticket type

## Core capabilities

### 1) Multi-purpose ticketing
Ticket types included:
- `incident` (faulty systems/outages)
- `service_request`
- `subscription` (new subscription, renewal, upgrade)
- `asset_issue`
- `inventory`

Each ticket has status, priority, requester, optional asset linkage, optional inventory linkage, and approval metadata.

### 2) Approval flows per ticket type
Administrators can configure ticket-type specific flows:

- Example subscription flow: Finance → Security → IT Admin
- Example hardware flow: Team Lead → Procurement

API endpoint:
- `POST /approval-flows`

### 3) Asset management
Maintain a register of business assets (laptops, servers, licenses, devices):

- Owner assignment
- Category and status
- Optional serial number

API endpoints:
- `POST /assets`
- `GET /assets`

### 4) Inventory management
Track inventory and stock movements:

- SKU tracking
- Quantity on hand
- Reorder threshold alerts

API endpoints:
- `POST /inventory`
- `POST /inventory/{item_id}/adjust`

## Advanced features recommended

To make this production-grade, add:

1. **SLA policy engine**
   - Per ticket type/priority SLA clocks
   - Breach warnings and escalations

2. **AI-assisted triage**
   - Suggest category, priority, and assignee from ticket text
   - Auto-summarization for long issue reports

3. **Knowledge base + deflection**
   - Suggest solutions before ticket submission
   - Reduce repetitive requests

4. **Event-driven automation**
   - Trigger webhooks to Slack/Teams/Jira/ERP/CMDB
   - Auto-create procurement requests when inventory is low

5. **Role-based access control (RBAC)**
   - Fine-grained permissions for submitter, approver, resolver, auditor

6. **Audit & compliance ledger**
   - Immutable trail for approvals, status transitions, and comments

7. **Service catalog & dynamic forms**
   - Different forms by request type
   - Conditional fields and validation rules

8. **Reporting layer**
   - MTTR, FCR, SLA compliance, backlog aging, approval bottlenecks

9. **Multi-channel intake**
   - Email, portal, API, chat, and voice bot integration

10. **Subscription lifecycle orchestration**
    - Renewal reminders
    - Vendor/license mapping
    - Cost center approvals

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pydantic
uvicorn app.main:app --reload
```

Open API docs:
- http://127.0.0.1:8000/docs

## Suggested production architecture

- **API layer**: FastAPI (or Node/NestJS)
- **Data**: PostgreSQL + Redis
- **Workflow**: Temporal/Camunda or internal rules engine
- **Search**: OpenSearch/Elasticsearch
- **Async**: Kafka/SQS + worker services
- **Auth**: SSO via OIDC/SAML
- **Observability**: OpenTelemetry + Prometheus + Grafana

## Example flow setup

1. Configure approval flow:
```json
{
  "ticket_type": "subscription",
  "steps": [
    {"order": 1, "approver_role": "team_manager"},
    {"order": 2, "approver_role": "finance"},
    {"order": 3, "approver_role": "security"}
  ]
}
```

2. Create subscription ticket:
```json
{
  "title": "Need Adobe Creative Cloud",
  "description": "Designer onboarding requires subscription.",
  "requester_id": "u_145",
  "ticket_type": "subscription",
  "priority": "medium"
}
```

3. Approvers process the workflow at `/tickets/{ticket_id}/approval`.

---

This repository now includes a functional starter backend (`app/main.py`) that demonstrates the complete requested capabilities and can be extended into an enterprise-grade platform.
