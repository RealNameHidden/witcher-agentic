# Witcher Magentic

An educational multi-agent application built with Microsoft Agent Framework.
Originally Magentic's sequential manager loop; now a parallel research workflow.

## How it works

Three real `agent_framework.Agent` instances collaborate:

- `PotionAgent` uses the bestiary, inventory, and live Witcher Wiki potion lists.
- `OilAgent` uses the bestiary, inventory, and live Witcher Wiki blade-oil lists.
- `RitualAgent` uses the bestiary and a read-only Witcher Wiki lore tool. The
  tool reads the wiki's Rituals category plus selected curse reference pages
  and returns both article content and source URLs.

A fourth `Agent`, `MagenticManager`, first writes a research plan. A real
`WorkflowBuilder` fan-out broadcasts it to all three specialists concurrently.
A fan-in barrier waits for every report, then the manager reviews all findings
and writes the final encounter plan. This is a fixed plan → parallel research →
review workflow; it no longer uses Magentic's sequential next-speaker loop or
automatic revisits. The agents still decide which information tools to call.

The API still admits only one user hunt at a time. That hunt now contains three
concurrent specialist runs. A specialist failure fails the hunt and cancels the
other branches; the manager does not present a partial result as a complete plan.

## Set up

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env
```

Keep credentials in your local `.env` or Azure's credential store. Git ignores
real `.env` files, the entire `.azure/` directory (including the test access key),
and private key files. Only `.env.example`, with placeholder configuration,
belongs in source control. Never put API keys or Azure secrets in source files.

The default provider is local Ollama. Install and launch [Ollama](https://ollama.com/download),
then download the model with `ollama pull qwen3:8b`. The agents still fetch wiki
references over the internet.

On an 8 GB Mac, use the smaller `qwen3:4b`: run `ollama pull qwen3:4b` and
set `OLLAMA_MODEL=qwen3:4b` in `.env`. Restart the dashboard after changing `.env`.
Verify local inference and real bestiary/inventory tool calls with:

```bash
.venv/bin/python scripts/check_local_model.py
```

If Ollama is installed through Homebrew, start its server in a separate terminal:

```bash
OLLAMA_FLASH_ATTENTION=1 OLLAMA_KV_CACHE_TYPE=q8_0 OLLAMA_NUM_PARALLEL=1 OLLAMA_CONTEXT_LENGTH=8192 ollama serve
```

This uses one request at a time and an 8K context to limit memory use. Long wiki
results and multi-agent conversations may outgrow that context on a small Mac.
The server listens only on localhost; it is not registered to start at login.

Run the command-line app with:

```bash
.venv/bin/witcher-magentic Katakan
```

For Foundry, set `MODEL_PROVIDER=foundry`, `FOUNDRY_PROJECT_ENDPOINT`, and
`FOUNDRY_MODEL` in `.env`, then authenticate with `az login`.

## Agent observatory UI

The main view focuses on the pipeline and final decisions. A large status banner
and highlighted card identify the working agent. The manager's latest published
assignment, selection reason, and earlier updates show how it coordinates the
specialists. Specialist findings, tool payloads, and the full journal expand on
demand. The final answer renders headings, lists, and source links.

Frontend checks:

```bash
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:browser
```

Browser tests use simulated connection status and the scripted replay. They
make no paid model calls. Install Chromium once with
`cd frontend` then `npx playwright install chromium` before running them.

Build the React/TypeScript frontend once, then start the Python server from the
repository root:

```bash
npm --prefix frontend install
npm --prefix frontend run build
.venv/bin/python -m witcher_magentic.server
```

Open **http://127.0.0.1:8000**. **Try a sample** works without a model and is
explicitly scripted; it makes no model or wiki calls. **Start live hunt** checks
your configured provider and runs the actual Magentic workflow. Foundry status
checks configuration only; authentication is validated by the first model call.

- A specialist's **Read findings** opens automatically when its response arrives,
  even while the other specialists are still working. You can collapse it again.
- The manager's plan assigns all three specialists. Multiple cards can be
  highlighted simultaneously with independent tool activity. The manager resumes
  review after all three reports arrive. Earlier updates are expandable.
- Expand **Behind the scenes** for actual tool arguments, results, and the full
  execution log in chronological order.
- The final plan is the workflow's output, not a frontend-generated recommendation.
- Stop cancels the request; the server cancels the workflow when the connection
  closes. An already-running synchronous wiki request may finish its timeout.
- Runs default to a three-minute limit. Traces are kept in browser memory and disappear
  on refresh. Tool results shown in the UI are capped at 40,000 characters.
- Local development defaults to loopback. The Azure deployment requires a test
  access key for paid runs; see [Azure deployment notes](infra/README.md).

For frontend development, keep the Python server running and use
`npm --prefix frontend run dev` in a second terminal. Vite proxies `/api` to port
8000. The Python server serves the latest `frontend/dist` build at startup.

## Run the tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The tests verify tool data and actual Agent Framework object construction
without making paid model calls.
