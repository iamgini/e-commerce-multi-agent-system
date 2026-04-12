import logging

import litellm
from guardrails import Guard
from guardrails.hub import (
    DetectPII,
    PromptInjectionDetector,
    ToxicLanguage,
    UnusualPrompt,
)

from config import GUARDRAILS_LLM_ENDPOINT, GUARDRAILS_MODEL

logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)
logging.getLogger("LiteLLM").setLevel(logging.ERROR)

kwargs = {
    "llm_api": litellm.completion,
    "model": GUARDRAILS_MODEL,
    "api_base": GUARDRAILS_LLM_ENDPOINT,
    }


def initialize_guardrails() -> Guard:
    validators = [
        ToxicLanguage(threshold=0.5, validation_method="sentence", on_fail="refrain"),
        DetectPII(pii_entities="pii", on_fail="fix"),
        UnusualPrompt(on_fail="refrain", **kwargs),
        PromptInjectionDetector(threshold=0.8, on_fail="refrain", **kwargs),
    ]

    guard = Guard().use(validators=validators)
    
    return guard
