# Witcher Magentic

A fun, lighthearted Witcher project made to learn and experiment with
Microsoft Agent Framework. The idea is simple: give a few AI agents their own
specialties and let them work together to prepare for a monster hunt.

This is a learning playground for agent tools, parallel workflows, model
integration, and Azure deployment. It started with Magentic's sequential manager
loop and grew into a parallel research workflow with a dashboard to watch the
agents work. The Witcher theme gives the experiments a bit of character.

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

## How we set it up in Azure

We also deployed the app to Azure to experiment with running the same agents
against an Azure AI Foundry model instead of local Ollama. The Python app runs
the agent workflow; Foundry provides the model inference for the manager and
all three specialists.

1. **Create the hosting resources.** We used [Bicep templates](infra/main.bicep)
   to create a resource group in East US 2, a Basic Azure Container Registry,
   and an Azure Container Apps Consumption environment. The registry stores
   our application image.
2. **Deploy the Foundry model.** [model.bicep](infra/model.bicep) creates the
   Azure AI Services account and deploys **GPT-4.1 mini**, version `2025-04-14`,
   with the deployment name `witcher-mini`. We used GlobalStandard inference,
   billed by token usage.
3. **Build and run the container.** The [Dockerfile](Dockerfile) builds the
   React frontend and packages it with the Python server. We built the image
   in Azure Container Registry with `az acr build`, then deployed it to
   Azure Container Apps using [app.bicep](infra/app.bicep) and the
   [deployment helper](scripts/deploy_app.py). The app serves the UI and API
   from one container and is configured to scale from zero to one replica.
4. **Connect the app to Foundry.** The container sets `MODEL_PROVIDER=foundry`,
   `FOUNDRY_ENDPOINT` to the model account's endpoint, and `FOUNDRY_MODEL=witcher-mini`.
   The model client calls the account's `/openai/v1/` endpoint. A user-assigned
   managed identity gets `AcrPull` access to the registry and the
   `Cognitive Services OpenAI User` role on the model account.

Authentication uses `DefaultAzureCredential` and Microsoft Entra tokens through
the managed identity. Model key authentication is disabled on the Azure account.
Live hunts have a separate test access key stored as a Container Apps secret;
the local copy stays in the ignored `.azure/` directory. The scripted sample
works without a model call or an access key.

To use a deployed Foundry model from your local checkout, run `az login` with
an account that has model inference access, then set these values in your local
`.env` and restart the app:

```dotenv
MODEL_PROVIDER=foundry
FOUNDRY_ENDPOINT=https://YOUR-MODEL-ACCOUNT.cognitiveservices.azure.com
FOUNDRY_MODEL=witcher-mini
```

Use your own deployment name if it differs. This direct inference setup uses
`FOUNDRY_ENDPOINT`; the project endpoint option above is an alternative client
path. See the [Azure deployment notes](infra/README.md) for the deployment
commands, validation steps, and recorded test results. The templates and helper
currently reflect our test resource names and subscription; adapt them for your
own Azure account before deploying.

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
