#!/usr/bin/env python3
"""Test provider health checks"""
import asyncio
from app.services.llm import LLMProviderFactory
from app.services.council.model_selector import ModelSelector


async def main():
    print("=" * 60)
    print("PROVIDER HEALTH CHECK TEST")
    print("=" * 60)

    # List all registered providers
    providers = LLMProviderFactory.list_providers()
    print(f"\n[INFO] Registered providers: {providers}\n")

    # Check each provider's health
    print("-" * 60)
    print("Checking individual provider health...")
    print("-" * 60)

    for provider_name in providers:
        try:
            provider = LLMProviderFactory.get_provider(provider_name)
            is_healthy = await provider.health_check()
            status = "[HEALTHY]" if is_healthy else "[UNHEALTHY]"
            print(f"{status} {provider_name}")

            # If Ollama, also check available models
            if provider_name == "ollama" and is_healthy:
                try:
                    models = await provider.list_models()
                    print(f"    -> Ollama models: {models}")
                except Exception as e:
                    print(f"    -> Ollama models error: {e}")

        except Exception as e:
            print(f"[ERROR] {provider_name}: {e}")

    # Check council model selection
    print("\n" + "=" * 60)
    print("COUNCIL MODEL SELECTION TEST")
    print("=" * 60)

    try:
        council_models = await ModelSelector.select_council_models()
        print(
            f"\n[INFO] Selected council models ({len(council_models)}): {council_models}"
        )

        if len(council_models) < 3:
            print(
                f"[WARNING] Council needs at least 3 models, only {len(council_models)} available"
            )
        else:
            print(f"[SUCCESS] Council has sufficient models ({len(council_models)})")

        chairman = await ModelSelector.select_chairman_model()
        print(f"[INFO] Selected chairman: {chairman}")

    except Exception as e:
        print(f"[ERROR] Council selection failed: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
