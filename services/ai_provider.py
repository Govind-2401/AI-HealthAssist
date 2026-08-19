import os
import logging
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower()

# ---------------------------------------------------------------------------
# Logging (safe)
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
_log = logging.getLogger("ai_provider")
_log.info("Active AI provider: %s", _AI_PROVIDER)

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_provider_name() -> str:
    """Return the human-readable name of the currently configured AI provider."""
    if _AI_PROVIDER == "gemini":
        return "Google Gemini"
    if _AI_PROVIDER == "watsonx":
        return "IBM watsonx.ai"
    return _AI_PROVIDER


def get_first_aid_guidance(situation: str) -> dict:
    """
    Route to the configured AI provider's first-aid guidance function.

    Returns a structured dict or {"error": "<message>"}.
    """
    if _AI_PROVIDER == "gemini":
        from services.gemini_service import get_first_aid_guidance as _fn
        return _fn(situation)

    if _AI_PROVIDER == "watsonx":
        from services.watsonx_service import get_first_aid_guidance as _fn
        return _fn(situation)

    return {"error": f"Unknown AI provider: '{_AI_PROVIDER}'. Set AI_PROVIDER=gemini or AI_PROVIDER=watsonx in .env."}


def get_medicine_info(medicine_name: str) -> dict:
    """
    Route to the configured AI provider's medicine information function.

    Returns a structured dict or {"error": "<message>"}.
    """
    if _AI_PROVIDER == "gemini":
        from services.gemini_service import get_medicine_info as _fn
        return _fn(medicine_name)

    if _AI_PROVIDER == "watsonx":
        from services.watsonx_service import get_medicine_info as _fn
        return _fn(medicine_name)

    return {"error": f"Unknown AI provider: '{_AI_PROVIDER}'. Set AI_PROVIDER=gemini or AI_PROVIDER=watsonx in .env."}
