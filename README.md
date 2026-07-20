# Idea Validator Agent

An AI agent that evaluates startup ideas. You give it an idea; it runs a multi-step
pipeline (analyze → research → retrieve → evaluate) and returns a **structured,
scored verdict** (`pursue` / `pivot` / `drop`).

Built to demonstrate applied **AI-engineering** skills: agentic tool use, forced
structured output, RAG, retries, and a real evaluation harness.

---

## What it does (architecture)

```
POST /validate  {"idea": "..."}
      │
      ▼
1. ANALYZE   forced structured output → {problem, audience, solution}
2. RESEARCH  agentic loop: the model calls search_web when it needs market facts
3. RETRIEVE  RAG: pull the most relevant evaluation frameworks from a vector DB
4. EVALUATE  forced structured output → scores + verdict + reasoning (validated JSON)
```

Each step is separate on purpose: it can be tested, debugged, and measured on its own.

---

## Requirements

- **Python 3.10 or newer** (recommended). The code also runs on 3.9.
  Check your version with `python3 --version` (Mac/Linux) or `python --version` (Windows).
- An **Anthropic API key** from https://console.anthropic.com/ (new accounts usually
  get starter credits — enough for this whole project).

---

## Setup — macOS / Linux

Open Terminal and run these **one at a time**, reading the output after each.

```bash
# 1. Go INTO the project folder (adjust the path to where you unzipped it)
cd ~/Desktop/idea-validator

# 2. Confirm the files are here — you should see app/, requirements.txt, .env.example
ls

# 3. Create and activate a virtual environment
#    NOTE: on Mac the command is python3, not python
python3 -m venv venv
source venv/bin/activate
#    Your prompt should now start with (venv). That means it worked.

# 4. Install dependencies (takes a couple of minutes)
pip install -r requirements.txt

# 5. Create your .env file and add your key
cp .env.example .env
open -e .env
#    TextEdit opens: replace sk-ant-... with your real key, save (Cmd+S), close.

# 6. Build the knowledge-base index (once)
python scripts/ingest_kb.py

# 7. Run the service
uvicorn app.main:app --reload
```

When you see `Uvicorn running on http://127.0.0.1:8000`, open that address + `/docs`
in your browser: **http://127.0.0.1:8000/docs**

To **stop the server**: press **Ctrl + C** in the terminal (that's Control, not Cmd).

---

## Setup — Windows

Open **PowerShell** and run these one at a time.

```powershell
# 1. Go INTO the project folder (adjust the path to where you unzipped it)
cd $HOME\Desktop\idea-validator

# 2. Confirm the files are here
dir

# 3. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate
#    Your prompt should now start with (venv).
#    If activation is blocked, run this once, then retry the activate line:
#    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create your .env file and add your key
copy .env.example .env
notepad .env
#    Notepad opens: replace sk-ant-... with your real key, save, close.

# 6. Build the knowledge-base index (once)
python scripts\ingest_kb.py

# 7. Run the service
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/docs** in your browser.
To **stop the server**: press **Ctrl + C**.

---

## How to use it

On the `/docs` page, open `POST /validate`, click "Try it out", and send:

```json
{ "idea": "An AI that reviews rental contracts and flags unfair clauses for tenants." }
```

You get back a structured evaluation with scores and a verdict.

---

## Evaluations (the important part)

Open a **second terminal** (leave the server running in the first), activate the venv
again, and run:

```bash
# Mac/Linux
source venv/bin/activate
python evals/run_evals.py 3      # first 3 cases (cheap, to check it works)
python evals/run_evals.py        # full 30-case set
```

```powershell
# Windows
venv\Scripts\activate
python evals\run_evals.py 3
python evals\run_evals.py
```

It reports two metrics:
- **Schema validity** — did every response match the JSON schema? (target 100%)
- **Verdict accuracy** — did the verdict match the human label?

Use this to prove a change helped: run it, tweak a prompt, run it again, compare.

---

## Troubleshooting (real first-run issues)

**`command not found: python` / `pip`**
On Mac the commands are `python3` and `pip3` — OR activate the venv first
(`source venv/bin/activate`), after which plain `python` and `pip` work inside it.
Always activate the venv before running project commands.

**`cp: .env: Not a directory` or a zsh quoting error**
You're not inside the project folder, or you typed the command wrong. Run `ls` first —
if you don't see `.env.example`, you're in the wrong place. `cd` into `idea-validator`,
then run `cp .env.example .env` exactly.

**`TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`**
Your Python is 3.9. Either use Python 3.10+ (recommended), or use this version of the
code (already fixed to run on 3.9). To upgrade on Mac: `brew install python@3.12`,
then rebuild the venv (`deactivate; rm -rf venv; python3.12 -m venv venv; source venv/bin/activate; pip install -r requirements.txt`).

**`ModuleNotFoundError: No module named 'app'`**
You're running uvicorn from the wrong directory. Run it from the project root
(the folder that contains the `app/` folder).

**`pip install` fails on chromadb**
Upgrade pip first: `pip install --upgrade pip`, then re-run `pip install -r requirements.txt`.

**The `(venv)` prefix is missing from your prompt**
The virtual environment isn't active. Re-run the activate command:
`source venv/bin/activate` (Mac/Linux) or `venv\Scripts\activate` (Windows).

---

## Key engineering decisions (and why) — your interview talking points

- **Forced structured output via tool-calling.** The model must "call" a tool whose
  `input_schema` defines the exact JSON we need, then Pydantic validates it. Far more
  reliable than parsing free text.
- **Multi-step pipeline, not one mega-prompt.** Each step is measurable and debuggable.
- **Agentic research step.** The model autonomously decides when to call `search_web`,
  bounded by `MAX_SEARCH_ITERATIONS` so cost can't run away.
- **RAG over fine-tuning.** The knowledge base is small and changes often; RAG lets us
  edit markdown files instead of retraining, injects only relevant chunks, and is cheap.
- **Retries with exponential backoff.** All model calls go through one wrapper that
  retries transient errors (overload, rate limits).
- **Graceful degradation.** No search key? The agent still runs, using model knowledge.

---

## Project layout

```
app/
  config.py    model IDs, limits, knobs (one place)
  schema.py    Pydantic models + JSON tool schemas (the data contracts)
  llm.py       Anthropic wrapper: retries + structured-output helper
  tools.py     search_web tool (Tavily) with graceful fallback
  rag.py       ChromaDB ingest + retrieve
  agent.py     the 4-step pipeline
  main.py      FastAPI service
scripts/ingest_kb.py   build the vector index
knowledge_base/*.md    evaluation frameworks and red flags (RAG source)
evals/                 labeled dataset + eval runner
Dockerfile             containerized service
```

Verify the current model IDs at https://docs.claude.com/en/docs/about-claude/models
and update `app/config.py` if needed.
