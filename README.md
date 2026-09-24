# Lead Manager

A working admission lead management app with a FastAPI backend, responsive React frontend, and SQLite/PostgreSQL support. It manages lead assignment, lifecycle status changes, course preferences, follow-ups, activity history, and manager reporting.

## Current Features

- Store users, lead sources, courses, and admission leads.
- Prevent duplicate leads by normalizing phone numbers to their last 10 digits.
- Track lead status through controlled transitions.
- Assign leads to counsellors.
- Associate a lead with multiple course preferences.
- Schedule and track calls, WhatsApp messages, visits, and emails.
- Keep an audit trail of lead changes and follow-up activity.
- Calculate overdue follow-ups from their pending status and due date.
- Auto-assign new leads to the active counsellor with the fewest open leads.
- Provide dashboard summaries for managers.

## Project Structure

```text
.
├── schema.sql          # PostgreSQL tables, indexes, and seed data
└── app/
    ├── database.py      # SQLite/PostgreSQL engine and sessions
    ├── dashboard.py     # Dashboard route
    ├── follow_ups.py    # Follow-up routes
    ├── leads.py         # Lead routes and filters
    ├── main.py          # FastAPI application
    ├── models.py        # SQLAlchemy models and status rules
    ├── schemas.py       # Pydantic request and response schemas
    ├── seed.py          # 30 demo leads
    └── services.py      # Business logic and transactions
tests/
└── test_services.py    # In-memory SQLite tests
frontend/
├── src/main.jsx        # React screens and API interactions
└── src/styles.css      # Responsive UI styles
```

## Architecture

```text
FastAPI routes (app/leads.py, app/follow_ups.py, app/dashboard.py)
                |
       services.py (business rules and transactions)
                |
      SQLAlchemy models + database.py session factory
                |
    SQLite by default, PostgreSQL via DATABASE_URL
```

Routes stay thin and translate service exceptions into HTTP responses. The service layer owns assignment, duplicate detection, status transitions, reassignment, follow-up changes, audit events, and dashboard calculations. This keeps the core behavior directly testable without starting a web server.

## Requirements

- Python 3.10 or newer
- Node.js and npm for the frontend
- SQLAlchemy 2.x
- Pydantic 2.x
- `email-validator` for Pydantic's `EmailStr`

The API defaults to a local SQLite database (`lead_manager.db`), so no database server is needed for the basic workflow. PostgreSQL remains supported by setting `DATABASE_URL`.

```bash
python -m venv .venv
```

Activate the environment on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
python -m app.seed
```

## Backend Setup

Install the Python dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Initialize the SQLite database and load 30 deterministic demo leads:

```powershell
.\.venv\Scripts\python.exe -m app.seed
```

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open the API documentation at <http://127.0.0.1:8000/docs>.

### PostgreSQL option

On Windows, install PostgreSQL first from the official PostgreSQL installer. Make sure the installer includes the command-line tools and remember the password you set for the `postgres` user. Open a new PowerShell window after installation so the PostgreSQL `bin` directory is added to `PATH`.

Verify that the tools are available:

```powershell
psql --version
createdb --version
```

Create a PostgreSQL database, then run the schema file against it:

```bash
createdb lead_manager
psql -d lead_manager -f schema.sql
```

Set the API connection string before starting Uvicorn. Encode special password characters in the URL, such as `@` as `%40`:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/lead_manager"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

If PostgreSQL is installed but the commands are still not found, run them using the full path, replacing `<version>` with the installed version:

```powershell
& "C:\Program Files\PostgreSQL\<version>\bin\createdb.exe" -U postgres lead_manager
& "C:\Program Files\PostgreSQL\<version>\bin\psql.exe" -U postgres -d lead_manager -f schema.sql
```

The schema creates the tables, indexes, and initial users, lead sources, and courses. It expects PostgreSQL because it uses PostgreSQL-specific types and syntax such as `SERIAL`, `TIMESTAMPTZ`, and partial indexes.

## Assumptions

- Each normalized phone number represents one lead; duplicate submissions return the existing lead.
- Counsellors are pre-created users, and only active counsellors can receive new or reassigned leads.
- The current sample data and phone normalization assume Indian 10-digit phone numbers.

## Domain Rules

### Lead statuses

Leads can use these statuses:

`new` -> `contacted` -> `interested` -> `follow_up` -> `applied` -> `converted`

The allowed transitions are enforced in `app/models.py`. An open lead can be marked `lost`, and a lost lead can be reopened as `contacted`. A converted lead is final.

When a lead is marked as lost, `lost_reason` is required.

### Phone normalization

`normalize_phone()` removes non-digit characters and keeps the last 10 digits. This allows values such as `+91 98765 43210` and `09876543210` to be recognized as the same phone number. Numbers with fewer than 10 digits are rejected.

### Follow-ups

Follow-ups support these types:

- `call`
- `whatsapp`
- `visit`
- `email`

Their status can be `pending`, `done`, or `cancelled`. A pending follow-up is overdue when its `due_at` value is earlier than the current time.

## API Surface

- `GET /health`
- `GET /leads?status=new&source_id=1&assigned_to=2`
- `POST /leads`
- `PATCH /leads/{lead_id}/status`
- `PATCH /leads/{lead_id}/reassign`
- `DELETE /leads/{lead_id}`
- `GET /leads/{lead_id}/activities`
- `GET /leads/{lead_id}/follow-ups`
- `POST /leads/{lead_id}/follow-ups`
- `PATCH /follow-ups/{follow_up_id}`
- `GET /dashboard?stale_days=7`

## Frontend

The Vite React frontend provides:

- Lead list filters for status, source, and counsellor
- Ten-row pagination for leads
- Add lead form with automatic assignment
- Lead detail view with valid status transitions, reassignment, follow-ups, activity timeline, and confirmed deletion
- Manager dashboard with status pagination, source/counsellor counts, ageing, conversion, overdue follow-ups, and stale leads

Run it in a second terminal while the API is running:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>.

## Tests

The service tests use an isolated in-memory SQLite database:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

They cover duplicate phone formats, invalid status jumps, lost reasons, inactive reassignment, converted leads, and overdue follow-ups.

## Example

```python
from app.models import LeadStatus, can_transition, normalize_phone

phone = normalize_phone("+91 98765 43210")
assert phone == "9876543210"
assert can_transition(LeadStatus.NEW, LeadStatus.CONTACTED)
```

## Trade-offs and Edge Cases

- SQLite is the zero-setup default; PostgreSQL is available for deployment through `DATABASE_URL`.
- Assignment counts only open statuses, so converted and lost leads do not affect workload balancing.
- Deactivating a counsellor does not redistribute their existing leads; this is documented future work.
- Phone duplicate detection keeps the last 10 digits, which is suitable for the current India-focused sample data but may need country-aware normalization for a multi-country deployment.
- Stale leads are returned when `last_activity_at` is older than the requested `stale_days` value.
- Pending follow-ups remain visible as overdue even when their lead is marked lost; they must be explicitly completed or cancelled.
- Deleting a lead cascades its course links, follow-ups, and activity rows. Because the audit rows belong to the deleted lead, deletion intentionally removes that lead's audit history as well.
- Authentication and authorization are intentionally not included in this MVP.

## Next Steps

Authentication and authorization, migrations, counsellor deactivation workflows, and production deployment configuration remain future work.

