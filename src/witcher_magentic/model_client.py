"""Select local or hosted inference without changing the agents."""
import os


def create_model_client():
    provider = os.getenv("MODEL_PROVIDER", "ollama").lower()
    if provider == "ollama":
        from agent_framework.openai import OpenAIChatCompletionClient

        return OpenAIChatCompletionClient(
            base_url=os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434/v1/"),
            api_key="ollama",
            model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        )
    if provider == "foundry":
        from agent_framework.foundry import FoundryChatClient
        from agent_framework.openai import OpenAIChatCompletionClient
        from azure.identity import DefaultAzureCredential
        from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
        from azure.identity.aio import get_bearer_token_provider

        # Direct Foundry model inference needs no hosted agent or project service.
        inference_endpoint = os.getenv("FOUNDRY_ENDPOINT")
        if inference_endpoint:
            model = os.environ["FOUNDRY_MODEL"]
            return OpenAIChatCompletionClient(
                base_url=inference_endpoint.rstrip("/") + "/openai/v1/",
                model=model,
                api_key=get_bearer_token_provider(
                    AsyncDefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
                ),
            )

        endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
        model = os.getenv("FOUNDRY_MODEL")
        if not endpoint or not model:
            raise ValueError("Set FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL in .env.")
        return FoundryChatClient(project_endpoint=endpoint, model=model, credential=DefaultAzureCredential())
    raise ValueError(f"Unknown MODEL_PROVIDER: {provider}")
