# Campus Customs Multi-Agent Operations (MGT 409 · HW 5)

A five-agent team (Boss, Inventory, Accounting, Facilities, Customer Service) that works the ticket board for Campus Customs, a small Yale apparel shop. The agents read and change the shop only through an **MCP server**, a **FastAPI backend** runs them, and a **React desk** lets a human watch the agents and approve every payment.

```
React desk (frontend/, :5173) ──HTTP──► FastAPI (backend/main.py, :8000) ──► PydanticAI agents (gpt-6-luna via Portkey)
                                               │                                   │
                                               └──────────── MCP ──────────────────┘
                                                             ▼
                                         mcp_server/server.py ──► data/campus_customs_new.db
```

- `data/campus_customs.db`: the **original** shop database. Never edited.
- `data/campus_customs_new.db`: the **working copy** every tool reads and writes. Committed in its state after the full three-ticket run (checking = $152.00).
- Full documentation: [`output/harness.md`](output/harness.md) (tables, MCP tools, agents, routes, dashboard, safety). Design notes: [`output/design.md`](output/design.md).

## Setup (once)

You need Python 3.12+ and Node.js 20+.

```bash
# 1. API key: copy the example and paste your Portkey key
cp .env.example .env

# 2. Python packages (in a local virtual environment)
python -m venv .venv
# Windows:
.venv\Scripts\python -m pip install -r requirements.txt
# macOS/Linux:
.venv/bin/python -m pip install -r requirements.txt

# Activate it so every `python` command below uses it:
#   Windows:      .venv\Scripts\activate
#   macOS/Linux:  source .venv/bin/activate

# 3. Frontend packages
cd frontend
npm install
cd ..
```

Every agent uses only `gpt-6-luna` through Portkey (`backend/llm.py`).

## 1. Copy the original DB to the working copy (clean run)

Whenever you want a clean shop, copy the original over the working copy:

```bash
# any OS (Python script)
python backend/reset_db.py

# or by hand
cp data/campus_customs.db data/campus_customs_new.db          # macOS/Linux/Git Bash
copy data\campus_customs.db data\campus_customs_new.db        # Windows cmd
```

Once the backend is running you can also use the **Reset the shop** button on the desk, or `POST http://localhost:8000/api/reset`. Both log the reset in the audit trail.

## 2. Start the MCP server

The backend attaches the MCP server **in-process** (`backend/mcp_link.py`), so the agents work without a separate terminal. To run it on its own (for example, to inspect the tools):

```bash
cd mcp_server
python server.py          # stdio
python server.py --http   # http://127.0.0.1:8001/mcp
```

(Use the `.venv` Python: `../.venv/Scripts/python` on Windows, `../.venv/bin/python` on macOS/Linux.)

To use the tools from Claude Code, `.mcp.json` at the project root registers the server as `campus-customs`. Open Claude Code in this folder and approve the server. The paths in it are for Windows (`.venv/Scripts/python.exe`); on macOS/Linux, change the command to `.venv/bin/python`.

## 3. Start the FastAPI backend

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

The API runs at http://localhost:8000 (interactive docs at http://localhost:8000/docs). It allows the Vite origin `http://localhost:5173`. Routes are listed in `output/harness.md`.

## 4. Start the React board

In a second terminal:

```bash
cd frontend
npm run dev
```

Open http://localhost:5173. Pick a ticket on the left, press **Send to the team**, and watch the agents on the floor. Type your name in **Signing as** to approve or reject the payments, purchase orders, discounts, and drafts that show up in the in-tray. The checking balance drops only when you approve a payment.

## 5. Reset the DB before a full three-ticket run

Always start a full run from the original books:

1. Reset (step 1, or **Reset the shop** on the desk). Checking goes back to **$3,400.00** and all three tickets reopen.
2. Run ticket **101**, approve its items, then **102**, then **103**.
3. Compare with `output/desk_tickets.html` (Expected vs Actual, Cash tab) and `output/resolved_tickets.json`.

Without the dashboard: `python backend/run_tickets.py --all --reset` runs all open tickets from the command line. Approvals still have to be made by a human on the desk or through the approve route.

## Shop rules the system enforces

- A human approves every payment; agents can only prepare requests. The approve route is the only place cash changes.
- Payments that would make cash negative are refused. Vendors with an open invoice can't be paid for new stock. Discounts can't go to or below cost.
- Customer messages are drafts only; nothing is ever emailed.
- Every agent step is appended to `output/audit_trail.json` (never wiped).

## Repository layout

```
├── AI_prompts.md          prompts I typed to the vibe coder, per problem
├── requirements.txt       Python packages
├── .env.example           copy to .env and add PORTKEY_API_KEY
├── .mcp.json              registers the MCP server with Claude Code
├── data/                  campus_customs.db (original) + campus_customs_new.db (working copy)
├── mcp_server/            server.py (FastMCP tools) + README.md
├── backend/               main.py (FastAPI), team.py (agent loops), models.py, agents/, prompts/
├── frontend/              React + Vite + TypeScript desk
└── output/                harness, smoke test, plan vs actual, design, results, audit trail, screenshots
```
