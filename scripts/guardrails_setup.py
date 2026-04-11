import logging
from guardrails.hub import ToxicLanguage, DetectPII, DetectJailbreak
from guardrails import Guard

logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)

def initialize_guardrails() -> Guard:
    validators = [
        ToxicLanguage(threshold=0.5, validation_method="sentence", on_fail="refrain"),
        DetectPII(pii_entities="pii", on_fail="fix"),
        DetectJailbreak(threshold=0.74, device='cpu', on_fail='refrain'),
    ]

    guard = Guard().use(validators=validators)
    
    return guard
