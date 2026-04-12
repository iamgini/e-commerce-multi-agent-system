from typing import Optional
from scripts.guardrails_setup import create_guardrail

guard = create_guardrail()

def parse_text(input_text: str) -> Optional[str]:
    """
    Validates the input text string.
    If input is not safe, guardrails will be applied to the text.
    DetectPII -> Fixes the text by sanitizing PII
    ToxicLanguage or DetectJailbreak -> Returns None
    """
    response = guard.parse(input_text)
    return response.validated_output
    