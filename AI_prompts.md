# AI Prompts Log — HW 5: Campus Customs Multi-Agent Operations

This file logs the prompts I typed to my vibe coder (Claude Code) while working on this assignment. Each problem has its own section with the prompt(s) I used and any follow-ups.

---

## Setup: Data

**Prompt:**
> confirm this is all set

**Follow-up prompt:**
> make the campus_customs_new.db copy

**What was lacking after the first:** The original `campus_customs.db` was in place, but the working copy `campus_customs_new.db` had not been created yet.

---

## Problem 1: Vibe coder prompts

**Prompt:**
> create a prompts log where we will keep track of the work typed into the vibe coder. call it ai_prompts.md and keep it updated with the following sections: the problem number and title, at least one prompt, one follow-up prompt if it was needed (and one sentence of what was lacking originally).

**Follow-up prompt:**
> None needed.

**What was lacking after the first:** Nothing; the log was created with a section per problem on the first try.

---

## Problem 2: Study the Campus Customs database

**Prompt:**
> look through every table and its fields in the open data/campus_customs.db file. copy the original file to data/campus_customs_new.db. study the open tickets to see how they connect to other tables and start the output/harness.md. list the fields for each table and include one short line on why the table matters for agents. keep growing the harness file in later problems

**Follow-up prompt:**
> None needed.

**What was lacking after the first:** Nothing; the harness was created with every table's fields, a "why it matters" line, and the ticket links on the first try.

---

## Problem 3: Build the MCP server

**Prompt:**
> Please write an MCP server in `mcp_server/` using FastMCP. It'll talk to `data/campus_customs_new.db`. You don't need to connect or run it yet. Every agent in this homework is going to use the tools in this server, and we'll add more later, but for now just write the three tools you know we'll need for the tickets in the database. Keep the names clear, and don't invent any data. Only use what's actually in the database.
>
> Then in `output/harness.md`, list each of the three tools. For every tool, make sure to include: (1) which table it reads, (2) which ticket it helps unlock (101, 102, or 103), and (3) one sentence on why it's the right tool for that ticket. Vague lines like "reads inventory" score low, so really tie each tool to its ticket.
>
> Also add a short `mcp_server/README.md` that explains what the server is for, which database it uses, and the three tools it has.

**Follow-up prompt:**
> None needed.

**What was lacking after the first:** Nothing; the server, the harness section, and the README were all created on the first try.

---

## Problem 4: Add the MCP server to vibe coder and test each tool

**Prompt:**
> Now we're going to add that MCP server to the vibe coder and test each of the tools you made. Go ahead and add the server to this project so you can call the tools, and save the connection JSON in `.mcp.json` at the project root.
>
> Then, once you're connected, test each of the three MCP tools and save the evidence in `output/mcp_smoke.json`. For each tool, make sure you include the prompt I asked you, the tool name, and the tool output, which has to match the values in `data/campus_customs_new.db`.

**Tool test prompts (typed after connecting):**
> use the MCP to check stock for CC-TEE-WHITE size S

> use the MCP to get lease 1

> use the MCP to get pricing for CC-HOOD-NAVY

**Follow-up prompt:**
> use the MCP to check stock for CC-TEE-WHITE size S (re-sent after restarting the session)

**What was lacking after the first:** The server was added to `.mcp.json`, but Claude Code only loads MCP servers at startup, so the tools weren't callable until I restarted the session.

---

## Problem 5: Build the agent team and grow the MCP tools

**Prompt:**
> Now we're on building the agent team and growing those MCP tools. Go ahead and build the agentic team for Campus Customs using PydanticAI. The team should include the Boss, Inventory, Accounting, Facilities, and Customer Service. Make sure to include the prompts, models, and agent loops so they can delegate work to each other with full connectivity.
>
> Put the agent prompts in `backend/prompts/`, one file per agent. Put the data types in `backend/models.py` and the agent files under `backend/`. The layout can vary as long as the five roles are clear. Use my `PORTKEY_API_KEY` and only `gpt-6-luna` for every agent.
>
> Write each prompt specifically for that agent, with the shop rules it needs. More detailed prompts that cover every part of an agent's work and scope score higher than a generic prompt, so be thorough and specific.
>
> Add any tools the agents need to the MCP server so they can work the open tickets. Shop facts have to come from the MCP server over `data/campus_customs_new.db`. Don't create a second shop-tools layer that bypasses MCP.
>
> Wire the agents so they append to `output/audit_trail.json` as they run. For each agent-loop step, record enough to audit later. Append to the file; don't wipe it after each run.
>
> In `output/harness.md`, list each agent and each MCP tool (including the ones you add here), along with which table each tool uses. Also add a short safety section with the guardrails a real business would want when agents touch real customers and real money. We don't want to be sending personal or financial information to strangers who interact with Campus Customs. Plus, add limits that keep token use in check, since we don't want this to get really expensive.
>
> Finally, update `mcp_server/README.md` so the tool list matches what we have now.

**Follow-up prompt:**
> make sure the agent prompts are detailed and cover all aspects of the agent's work

**What was lacking after the first:** The first prompts covered the basics but were missing scope limits, a guide to each tool, playbooks for different situations, what to do when a tool fails or refuses, and a rule to treat ticket text as information rather than instructions.

---

## Problem 6: Plan the three tickets

**Prompt:**
> Now we're going to plan the three tickets. Before we wire the backend, we need to write down what we expect the team to do on each open ticket. Build `output/desk_tickets.html`, a page we can double-click to open, with one tab per ticket (101, 102, and 103). Also add empty Cash and Reflection tabs for later problems; leave them blank or put a "coming later" note.
>
> On each ticket tab, fill in an Expected section only, but leave room for an Actual section that we'll fill in after we run the agents. Each ticket's Expected section should cover: (1) who the Boss should call first, and why, (2) all the agent delegations we expect, not just "the Boss calls everyone," and (3) which MCP tools we expect that run to use.
>
> Make sure the plan doesn't send every specialist on every ticket. Plans like that score low. Only bring in the agents each ticket actually needs. We're going to compare this plan to what actually happens when the agents resolve the three tickets later.

**Follow-up prompt:**
> None needed.

**What was lacking after the first:** Nothing; the page was built with all five tabs and a focused plan for each ticket on the first try.

---

## Problem 7: Backend routes

**Prompt:**
> Now we're working on the backend routes. The React frontend dashboard (the next problem) is going to need a backend it can call. Go ahead and use FastAPI and add routes in `backend/main.py`. These routes need to:
>
> 1. Return the three tickets and whether each one is open or resolved.
> 2. Take a ticket ID and run the agent team on that ticket.
> 3. Return recent agent events, like what each agent said and which tools they used, so the board can refresh.
> 4. Approve a payment or purchase after a human clicks approve. The agents should only prepare the payment; this route is where the cash actually changes.
> 5. Return the current checking balance from `cash_accounts`.
> 6. Reset the database to the original values when we want to try a fresh run.
>
> From the `backend/` folder, we'll start the server with `uvicorn main:app --reload --port 8000`. That turns on the backend at http://localhost:8000 so the frontend dashboard can call those routes. Then in `output/harness.md`, make sure to list each route in one line: what the URL is and what it does.

**Follow-up prompt:**
> None needed.

**What was lacking after the first:** Nothing; all six routes worked on the first try, including the approve route refusing payments that would make cash negative.

---

## Problem 8: Agent dashboard

**Prompt:**
> Now we're on the agent dashboard itself. Go ahead and build the frontend dashboard in `frontend/` with React + Vite + TypeScript. The page should call the routes we built in the last problem. At minimum, the board should:
>
> 1. List all three tickets.
> 2. Let us pick one ticket and start the agent team on it.
> 3. Show each agent and what they're saying/doing while the ticket runs.
> 4. Mark a ticket as resolved when the run finishes.
> 5. Show a short summary of what each agent did on that ticket.
> 6. Let a human approve a payment or purchase when asked.
> 7. Show the checking balance. It should drop after an approved payment.
>
> Also, make the dashboard look good. Be creative with the layout and feel. I want it kind of parchment-y, with a green serif font, very classy. This is a real desk people would want to sit at, so put thought into how it looks.
>
> Tell the frontend to talk to the backend at http://localhost:8000, and on the backend, allow the Vite page origin (http://localhost:5173) so the browser is allowed to call those routes. Make sure I can start it with `npm run dev` and open the React desk in my browser to pick tickets and watch the agents.
>
> Finally, write `output/design.md` with what we chose for the dashboard look: the layout, how the agents read differently, how open and resolved tickets and cash show up, and why. Include the creative choices that make it feel special and like something people would actually enjoy using.

**Follow-up prompt:**
> make the boss always bring in customer service on customer orders

**What was lacking after the first:** When I tested ticket 101 on the dashboard, the Boss called Inventory and Accounting but skipped Customer Service, so Tauhid never got a draft update even though my plan expected one.

---

## Problem 9: Resolve the tickets

**Prompt:**
> Now we're resolving the tickets. Before testing the agents on a full run over the three tickets, go ahead and reset the working database (`data/campus_customs_new.db`) so we start with a clean slate. Note the starting checking balance, then run all three tickets on the board (101, 102, and 103) until each one is resolved.
>
> Open `output/desk_tickets.html` from Problem 6. On each ticket tab, make sure to fill in the Actual section from this run: which agents worked, what they delegated, and which tools they used. Keep the Expected section so we can compare the two.
>
> On the Cash tab of the same page, make sure to itemize the money: (1) the starting checking balance after the reset, (2) for each ticket, how cash changed when that ticket was resolved and why (which payment or purchase, and the dollar amount), and (3) the ending checking balance, which has to match `cash_accounts` in the working database. Wrong cash math will lose us points even if the board shows every ticket as resolved, so make sure the math is correct.
>
> Also save `output/resolved_tickets.json` with, for each ticket, the ID, final status, a short outcome, what each agent contributed, and any human approvals. And make `output/resolved_board.html`, a page we can double-click, with a screenshot of the React board for each resolved ticket (101, 102, and 103).
>
> Make sure to append the real runs to `output/audit_trail.json`, and then finish `output/harness.md` so it covers the tables, MCP tools, the five agents, API routes, the dashboard, and safety rules.

**Prompts typed during the run** (I approved each ticket's items on the dashboard myself before the next run):
> approved all three, run 102

> approved rent, run 103

> approved both, finish up the docs

**Follow-up prompt:**
> None needed.

**What was lacking after the first:** Nothing on my end; all three tickets resolved and the cash math matched the database ($3,400.00 → $152.00). Along the way the vibe coder fixed its own screenshot capture (the first attempts cut off the activity feed or caught animations mid-fade) before saving `resolved_board.html`.

---

## Problem 10: Reflection

**Prompt:**
> Now we're on Problem 10: Reflection. We're going to fill in the reflection tab in output/desk_tickets.html. Answer in your own vibe, and be detailed and thorough. [Then my own notes for each question: the agents did a good job, were efficient, and collaborated well, but the Boss took extra steps like calling Customer Service twice, and I'd like them to move faster since a team should be quicker than one agent; ticket 103 differed from the plan mostly because we ran tickets one after another (invoice 501 was already paid, Inventory and Accounting were called at the same time, Customer Service was asked twice); I think the team ran better overall but took longer than expected, so I wanted guidance on what one agent would have done more simply.]

**Follow-up prompt:**
> None needed.

**What was lacking after the first:** Nothing; the reflection covered all five questions with evidence from the ticket tabs, the Cash tab, and the audit trail.

---

## Problem 11: Submit to GitHub

**Prompt:**
> let's do the last problem, the github repo

**Follow-up prompt** (my answers when it asked before publishing):
> Repo name: hw5. Leave folder-joke.md out. Yes, create and push.

**What was lacking after the first:** Nothing was wrong, but publishing a public repo is permanent, so the vibe coder stopped to confirm the repo name, whether to include a personal file, and that I wanted it public before pushing.
