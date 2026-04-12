import logging
import subprocess

import litellm
from guardrails import Guard
from guardrails.hub import (
    DetectPII,
    PromptInjectionDetector,
    ToxicLanguage,
    UnusualPrompt,
)
from guardrails.hub.install import install

from config import GUARDRAILS_LLM_ENDPOINT, GUARDRAILS_MODEL

logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)
logging.getLogger("LiteLLM").setLevel(logging.ERROR)

kwargs = {
    "llm_api": litellm.completion,
    "model": GUARDRAILS_MODEL,
    "api_base": GUARDRAILS_LLM_ENDPOINT,
    }


# def initialize_guardrails():
#     install("hub://guardrails/toxic_language", install_local_models=True)
#     install("hub://guardrails/detect_pii", install_local_models=True)
#     install("hub://guardrails/unusual_prompt", install_local_models=True)
#     subprocess.run(["cp", "-f", "/app/guardrails-ai_setup/prompt_injection/.guardrails/hub_registry.json", "/app/.guardrails/hub_registry.json"], check=True)
#     subprocess.run(["cp", "-f", "/app/guardrails-ai_setup/prompt_injection/__init__.pyi", "/usr/local/lib/python3.12/site-packages/guardrails/hub/__init__.pyi"], check=True)
#     print("[Guardrails] Completed setup.")


def create_guardrail() -> Guard:
    validators = [
        ToxicLanguage(threshold=0.5, validation_method="sentence", on_fail="refrain"),
        DetectPII(pii_entities="pii", on_fail="fix"),
        UnusualPrompt(on_fail="refrain", **kwargs),
        PromptInjectionDetector(threshold=0.8, on_fail="refrain", **kwargs),
    ]

    guard = Guard().use(validators=validators)
    return guard
