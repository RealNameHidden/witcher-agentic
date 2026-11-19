# Azure hosting: the first deployment slice

Live application: https://witcher-test.greenmeadow-610fd3f8.eastus2.azurecontainerapps.io

Current image: `20261102-05` (parallel specialists and automatically opened findings).
Verified real Katakan run: all three specialists start at 6.44–6.45 seconds;
finish at 11.65–13.07 seconds; manager reviews afterward and returns the final
answer at 18.9 seconds. These are one run's observed timings, not a latency guarantee.

Open `.azure/test-access.txt` locally and copy the key into the UI's test access
field, then start a live Katakan run. On 2026-11-02 the deployed tag
`20261102-03` completed the full manager/specialist workflow in 38.3 seconds.
This confirms the execution pipeline; game-specific lore and citation adherence
still need evaluation. The observed answer omitted citations, and the potion
specialist used inventory/bestiary without consulting its lore tool.

`main.bicep` describes the resource group at **subscription scope**. Its
`hosting` module runs at **resource-group scope** and describes two resources:

| Resource | Why it exists | Billing |
|---|---|---|
| `rg-witcher-test` | Groups this project's resources for inspection and cleanup | Group itself is free |
| Basic Container Registry | Stores the Docker image; can build it in Azure | Standing registry charge, plus build/storage usage |
| `cae-witcher-test` | Consumption Container Apps environment | No dedicated workers; app compute is billed when replicas run |

A Container Apps environment is where apps run; it is not an app or a public
website itself. `model.bicep` adds a Foundry account and GPT-4.1 mini metered
deployment. `app.bicep` runs our actual image with zero to one replicas, protects
paid requests, and gives a managed identity permission to pull images and call
the model. No hosted Foundry agent, GPU, or project runtime is required: our
existing Python process continues to orchestrate the Magentic agents.

The registry has its admin login disabled. Image pulls will use managed identity
when the app is deployed. No model key or `.env` file is uploaded with source.
Container log forwarding is not configured for this inexpensive testing foundation.

Commands below target the user's active **Learning** subscription explicitly.
Recompile before each deployment so the ARM file matches the current source:

```bash
az bicep build --file infra/main.bicep --outfile /private/tmp/witcher-hosting-template.json

az deployment sub validate \
  --subscription 296247d8-59ad-4429-8a9b-7f153faebf2d \
  --location eastus2 --name witcher-hosting-check \
  --template-file /private/tmp/witcher-hosting-template.json \
  --parameters location=eastus2

az deployment sub what-if \
  --subscription 296247d8-59ad-4429-8a9b-7f153faebf2d \
  --location eastus2 --name witcher-hosting \
  --template-file /private/tmp/witcher-hosting-template.json \
  --parameters location=eastus2
```

After validating and reviewing the preview, replace `what-if` with `create` to
provision. This incremental template does not delete unrelated resources.
Keep the registry's standing charge in mind while paused between learning slices.

## Application and model deployment

`Dockerfile` builds React in a Node stage, then copies only compiled assets into
a Python runtime. `FRONTEND_DIST` tells the installed package where those files
live; `HOST=0.0.0.0` lets Azure ingress reach the server on port 8000. Local
development continues to default to loopback.

The verified model is GPT-4.1 mini 2025-04-14 on GlobalStandard. This is billed
by token usage; the capacity value of 100 is a rate allocation, not a reserved
GPU or PTU purchase. Global deployments may process inference outside East US 2.
Nano and 4o-mini chat models had zero available quota in this subscription when
checked. The model account disables key authentication: Python gets Entra tokens
through DefaultAzureCredential, which selects the app's managed identity in Azure.

The UI is public. Live runs require a separate test access key in the Authorization
header. The key is generated in `.azure/test-access.txt` with owner-only file
permissions. It is excluded from image uploads and source control, and passed to
ARM as a secure parameter through a temporary private file. Enter it into the
UI's password field; the UI retains it only in memory until refresh. This is a
single-tester gate, not a complete multi-user login system.

Only one workflow runs at a time per replica. Each run has a 180-second timeout,
a fixed plan → three concurrent specialists → review graph, and a single replica ceiling. These
limits bound individual runs; they are not a total monthly spending cap.
The manager no longer chooses one specialist at a time. All three research
branches must finish before its review begins. Verify actual overlap with
`scripts/check_deployment.py https://YOUR-APP-HOSTNAME --require-parallel`.
No database or trace persistence is configured. Refresh clears browser traces.

Build and deploy subsequent versions with a new immutable image tag:

```bash
az acr build --subscription 296247d8-59ad-4429-8a9b-7f153faebf2d \
  --registry witchercm7jzkadzmih2 --image witcher:YOUR-NEW-TAG \
  --platform linux/amd64 .

.venv/bin/python scripts/deploy_app.py validate \
  --image witchercm7jzkadzmih2.azurecr.io/witcher:YOUR-NEW-TAG

# After validation succeeds:
.venv/bin/python scripts/deploy_app.py deploy \
  --image witchercm7jzkadzmih2.azurecr.io/witcher:YOUR-NEW-TAG

# Uses the local test key without printing it:
.venv/bin/python scripts/check_deployment.py https://YOUR-APP-HOSTNAME
```

All three resource templates are incremental. Avoid deleting the whole resource
group unless you intend to remove the app, registry, model and its identity.
