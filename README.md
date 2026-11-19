# Witcher Magentic

A fun, lighthearted Witcher project I built to learn and experiment with
Microsoft Agent Framework. The idea: give AI agents their own specialties and
let them work together to prepare for a monster hunt.

## How it works

A manager plans the hunt, then three specialist agents research in parallel:

- **PotionAgent** researches potions and inventory.
- **OilAgent** researches blade oils and inventory.
- **RitualAgent** researches rituals and curse lore.

The agents use bestiary data and live Witcher Wiki tools. Once all three finish,
the manager reviews their findings and writes the final encounter plan.

A React dashboard shows agent activity, tool calls, findings, and the final
answer. A scripted sample demonstrates the workflow without calling a model.

## My Azure setup

I packaged the React frontend and Python backend into one Docker image, stored
it in Azure Container Registry, and deployed it to Azure Container Apps in
East US 2. I defined the infrastructure with Bicep.

The agents use **GPT-4.1 mini through Azure AI Foundry**. The Python app
orchestrates the workflow and calls the deployed model for inference.
Authentication uses a managed identity and Microsoft Entra tokens rather than
model API keys. Live hunts require a separate test access key, and local
credentials stay out of Git.

The app can also use local Ollama. This project is my playground for exploring
agent collaboration, tools, model integration, and cloud hosting.

Implementation details are in the [Azure deployment notes](infra/README.md).
