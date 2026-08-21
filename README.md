# AI Business Operations Agent
### *An Intelligent Digital Employee for Small Businesses*

An intelligent, full-stack AI-powered digital employee for small and medium businesses (SMEs). It connects business documents, invoice management, priority task detection, automated customer email generation, and conversational business intelligence with a robust **Human-in-the-Loop Approval Workflow**.

---

## 🌟 Key Features

1. **Understand → Analyze → Decide → Plan → Request Approval → Execute → Track**
   - Autonomous multi-step operations workflow.
2. **AI Document Intelligence & OCR**:
   - Ingests Invoices, PDFs, Receipts, Contracts, and DOCX documents with PyMuPDF and Google Gemini.
   - Extracts customer name, invoice #, amounts, due dates, terms, and line items.
3. **Automated Overdue Detection & Task Creation**:
   - Detects late payments, creates High-Priority tasks, and formulates action plans.
4. **AI Email Assistant & Dispatch Studio**:
   - Drafts polite, professional, or urgent payment reminders and customer follow-ups.
5. **Approval Center (Human-in-the-Loop Safety)**:
   - Sensitive business communications and dispatches require explicit owner review, editing, or approval.
6. **AI Command Center (ChatGPT for Business Ops)**:
   - Natural language queries (*"What needs my attention today?"*, *"Show all unpaid invoices"*, *"Which payments are overdue?"*) querying real live database state.
7. **Executive Dashboard & Daily Briefing**:
   - Instant morning overview with alerts, KPIs, and recommended next best actions.
8. **Comprehensive Analytics & Audit Trail**:
   - Real-time cash flow trends, invoice aging distributions, and automated vs manual hours saved.

---

## 🛠️ Technology Stack

- **Frontend**: React.js 19 + Vite 8 + Tailwind CSS + Lucide Icons + Recharts
- **Backend**:      
- **Database / ORM**: Supabase PostgreSQL / local SQLite + SQLAlchemy ORM
- **AI Engine**: Google Gemini API (`gemini-1.5-flash`) + Intelligent Contextual Fallback Agent
- **Document Processing**: PyMuPDF (`fitz`), Pillow, python-docx

---

## 🚀 Getting Started Locally

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 2. Backend Setup
```bash
# Navigate to project root
cd AI_Business_Agent

# Copy backend/.env.example to backend/.env and set DATABASE_URL to the
# Supabase Session Pooler connection string when using Supabase.
# Run supabase/schema.sql in Supabase Dashboard -> SQL Editor first.
# (Optional) Set up your Gemini API key in backend/.env
# GEMINI_API_KEY=your_gemini_api_key_here

# Start FastAPI backend server
python -m uvicorn backend.app.main:app --reload --port 8000
```
Backend API will be available at: `http://localhost:8000` (API Docs at `http://localhost:8000/docs`).

### Supabase database setup

The application includes a complete PostgreSQL migration at
`supabase/schema.sql`. It matches the current FastAPI models and creates the
tables, foreign keys, indexes, update triggers, and private document storage
bucket. Run it once in the Supabase SQL Editor, then set `DATABASE_URL` in
`backend/.env` to the Supabase Session Pooler URL using the `psycopg` driver.

The current application keeps its existing FastAPI custom JWT authentication,
so the migration uses integer IDs for compatibility. Supabase Auth, UUID user
IDs, and `auth.uid()` Row Level Security policies should be introduced as a
separate migration after the database connection is verified. Do not expose a
Supabase service-role key in the frontend.

### 3. Frontend Setup
```bash
# In a second terminal in the project root:
npm run dev
```
Frontend Web Application will be live at: `http://localhost:5173`.

---

## 🏆 Golden Demonstration Walkthrough

1. **Sign In**:
   - Open `http://localhost:5173` and click **"1-Click Demo Login"** (Pre-configured for *Summit Digital Agency*).
2. **Dashboard Overview**:
   - View **Today's Business Brief** highlighting overdue accounts and high-priority alerts.
3. **Upload Invoice**:
   - Navigate to **Documents & OCR**.
   - Click **"Quick Demo: Upload ABC Ltd Invoice"** or drag & drop a PDF invoice.
4. **AI Analysis & Overdue Detection**:
   - Watch the AI extract customer `ABC Ltd`, amount `$5,000.00`, and detect overdue payment status.
   - The system automatically registers a **High-Priority Task** and drafts an email notice.
5. **Review in Approval Center**:
   - Navigate to **Approval Center**.
   - Inspect the pending action: Review the recipient, subject, and body text.
   - Click **Edit Draft** to tweak words if desired, or click **Approve & Execute Action**.
6. **Execution & Audit**:
   - The action executes, dispatches the email record, resolves the task, and logs an entry in **Activity & Audit Log**.
7. **Ask AI Command Center**:
   - Open **AI Command Center** and type:
     > *"What needs my attention today?"*
   - Observe the live database retrieval providing a crisp, actionable operational summary.
