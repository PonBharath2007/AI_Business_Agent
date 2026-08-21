# REST API Reference: AI Business Operations Agent

Base URL: https://ai-business-agent-ui7z.onrender.com/api

---

## 1. Authentication & Users
- `POST /api/auth/register` – Register business owner and initialize business profile.
- `POST /api/auth/login` – Login with email and password, returns JWT token.
- `GET /api/auth/me` – Retrieve currently authenticated user profile.

---

## 2. Dashboard
- `GET /api/dashboard/summary` – Summary metrics (KPI counts, pending amounts, overdue total, approval count).
- `GET /api/dashboard` – Full composite dashboard data (KPIs, Today's Business Brief, overdue accounts, urgent tasks, recent activities).

---

## 3. Documents & AI Extraction
- `POST /api/documents/upload` – Multipart file upload (PDF, PNG, JPG, DOCX). Performs text extraction and optional automated AI workflow.
- `GET /api/documents` – List uploaded documents with status and metadata.
- `GET /api/documents/{id}` – Get document record and extracted JSON.
- `POST /api/documents/{id}/analyze` – Re-run AI Document Intelligence workflow.
- `DELETE /api/documents/{id}` – Remove document.

---

## 4. Invoices & Overdue Tracking
- `GET /api/invoices` – List invoices with optional `?status=overdue|pending|paid` filters.
- `POST /api/invoices` – Create new invoice.
- `GET /api/invoices/{id}` – Retrieve invoice details.
- `PUT /api/invoices/{id}` – Update invoice.
- `DELETE /api/invoices/{id}` – Delete invoice.
- `POST /api/invoices/{id}/reminder` – Auto-draft payment reminder email and queue in Approval Center.

---

## 5. Customers
- `GET /api/customers` – List all customer accounts with outstanding and overdue balances.
- `POST /api/customers` – Create customer profile.
- `GET /api/customers/{id}` – Single customer details and communication records.
- `PUT /api/customers/{id}` – Update customer details.
- `DELETE /api/customers/{id}` – Delete customer.

---

## 6. Operations Tasks
- `GET /api/tasks` – List operational tasks with priority and status filters.
- `POST /api/tasks` – Create new task.
- `GET /api/tasks/{id}` – Retrieve task.
- `PUT /api/tasks/{id}` – Update task fields.
- `POST /api/tasks/{id}/complete` – Mark task as resolved/completed.
- `DELETE /api/tasks/{id}` – Delete task.

---

## 7. Approval Center (Human-in-the-Loop)
- `GET /api/approvals` – List AI generated actions waiting for approval.
- `GET /api/approvals/{id}` – Single approval item with action payload.
- `PUT /api/approvals/{id}` – Edit action payload (e.g. modified subject/body).
- `POST /api/approvals/{id}/approve` – Approve and execute action.
- `POST /api/approvals/{id}/reject` – Reject action with optional decline reason.

---

## 8. AI Agent Endpoints
- `POST /api/ai/chat` – ChatGPT-style Command Center with real database querying and function assistance.
- `GET /api/ai/daily-brief` – Generates live executive summary of business health and priority alerts.
- `GET /api/ai/recommendations` – Next best recommended actions.
- `POST /api/ai/generate-email` – Context-aware email assistant generator.

---

## 9. Analytics & Audit
- `GET /api/analytics/overview` – Overview metrics, cash flow charts, aging distributions, hours saved.
- `GET /api/activities` – Searchable activity and audit timeline.
- `GET /api/notifications` – Real-time alerts and warnings.
- `PUT /api/notifications/{id}/read` – Mark notification as read.
- `PUT /api/notifications/read-all` – Clear all unread notifications.

---

## 10. Settings & Demo Management
- `GET /api/settings/profile` – Business profile and operational terms.
- `PUT /api/settings/profile` – Update business profile.
- `POST /api/settings/reset-demo` – 1-Click reset database to the pristine Golden Demo state.
