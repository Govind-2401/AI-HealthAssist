import os
import json
import time
import logging
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_API_KEY   = os.getenv("GEMINI_API_KEY", "")
_MODEL_ID  = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

# ---------------------------------------------------------------------------
# Logging (safe — never prints the API key)
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
_log = logging.getLogger("gemini_service")
_log.info("Gemini provider initialised. Model: %s  API key present: %s", _MODEL_ID, bool(_API_KEY))

# ---------------------------------------------------------------------------
# JSON schemas for structured output
# ---------------------------------------------------------------------------
_FIRST_AID_SCHEMA = {
    "type": "object",
    "properties": {
        "immediate_steps": {
            "type": "string",
            "description": "Immediate basic first-aid steps the person can take right now."
        },
        "things_to_avoid": {
            "type": "string",
            "description": "Common mistakes or harmful actions to avoid in this situation."
        },
        "warning_signs": {
            "type": "string",
            "description": "Signs or symptoms indicating the situation may be more serious."
        },
        "when_to_seek_help": {
            "type": "string",
            "description": "When to call emergency services or seek professional medical attention."
        }
    },
    "required": ["immediate_steps", "things_to_avoid", "warning_signs", "when_to_seek_help"]
}

_MEDICINE_SCHEMA = {
    "type": "object",
    "properties": {
        "what_it_is": {
            "type": "string",
            "description": "General description of the medicine — drug class and type."
        },
        "common_uses": {
            "type": "string",
            "description": "General conditions or symptoms this medicine is commonly associated with."
        },
        "general_precautions": {
            "type": "string",
            "description": "General precautions and considerations people should be aware of."
        },
        "important_warnings": {
            "type": "string",
            "description": "Significant warnings, contraindications, or serious side effects."
        },
        "when_to_consult": {
            "type": "string",
            "description": "When to consult a qualified healthcare professional about this medicine."
        }
    },
    "required": ["what_it_is", "common_uses", "general_precautions", "important_warnings", "when_to_consult"]
}

# ---------------------------------------------------------------------------
# System instructions
# ---------------------------------------------------------------------------
_FIRST_AID_SYSTEM = (
    "You are a general health education assistant. Your role is to provide basic, general, "
    "educational first-aid information ONLY. You must follow these rules absolutely:\n"
    "1. You do NOT diagnose any medical condition.\n"
    "2. You do NOT prescribe or recommend any medication or dosage.\n"
    "3. You do NOT provide personalised medical treatment instructions.\n"
    "4. You DO provide general, situation-specific educational first-aid guidance.\n"
    "5. You DO identify warning signs that may indicate a more serious situation.\n"
    "6. You DO clearly advise calling emergency services (e.g. 911, 999, 112) when the "
    "situation may be life-threatening.\n"
    "7. You DO recommend consulting a qualified healthcare professional when appropriate.\n"
    "8. Keep all responses concise, clear, and suitable for a general adult audience.\n"
    "9. Base your response specifically on the situation the user has described — "
    "do not give generic responses.\n"
    "IMPORTANT: This is for educational purposes only, not for emergency medical advice. "
    "Always direct users to emergency services for life-threatening situations."
)

_MEDICINE_SYSTEM = (
    "You are a general health education assistant providing basic medicine information for "
    "educational purposes only. You must follow these rules absolutely:\n"
    "1. You do NOT prescribe medication or recommend any dosage.\n"
    "2. You do NOT tell users to start, stop, or change any medication.\n"
    "3. You do NOT make any treatment decisions or personalised recommendations.\n"
    "4. You do NOT diagnose any medical condition.\n"
    "5. You DO provide general educational information about well-known medicines.\n"
    "6. If you cannot confidently identify the medicine the user asked about, state that "
    "clearly and advise them to verify the medicine using its packaging, official leaflet, "
    "pharmacist, or doctor — do not invent information.\n"
    "7. You DO encourage users to consult a qualified healthcare professional.\n"
    "8. Keep responses clear and suitable for a general adult audience.\n"
    "IMPORTANT: This is for general educational purposes only and is not a substitute for "
    "professional medical or pharmaceutical advice."
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_client():
    """Create and return a Gemini client. Raises ValueError if API key is missing."""
    if not _API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please add it to your .env file."
        )
    from google import genai
    return genai.Client(api_key=_API_KEY)


def _call_gemini(system_instruction: str, user_prompt: str, schema: dict) -> dict:
    """
    Send a request to Gemini and return the parsed JSON response dict.

    Uses response_mime_type='application/json' and response_json_schema for
    structured output. Retries once on transient 503 errors.

    Raises on any non-transient SDK or parsing failure.
    """
    from google import genai
    from google.genai import types

    client = _get_client()

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_json_schema=schema,
        temperature=0.4,
        max_output_tokens=2048,
    )

    last_exc = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=_MODEL_ID,
                contents=user_prompt,
                config=config,
            )

            raw_text = response.text
            _log.info("Gemini raw response length: %d chars", len(raw_text) if raw_text else 0)

            if not raw_text or not raw_text.strip():
                raise ValueError("Gemini returned an empty response.")

            parsed = json.loads(raw_text)
            return parsed

        except Exception as exc:
            last_exc = exc
            exc_str = str(exc)
            # Retry on transient 503 / 429 rate-limit errors only
            if attempt < 2 and ("503" in exc_str or "429" in exc_str or "UNAVAILABLE" in exc_str):
                wait = 5 * (2 ** attempt)  # 5s, 10s — wider window for quota recovery
                _log.warning("Gemini transient error (attempt %d/3), retrying in %ds: %s",
                             attempt + 1, wait, exc_str[:120])
                time.sleep(wait)
                continue
            # Non-retryable — re-raise immediately
            raise

    raise last_exc  # all retries exhausted


def _validate_keys(data: dict, required_keys: list) -> dict:
    """
    Ensure all required keys are present and non-empty in the parsed response.
    Fills any missing key with a fallback note rather than crashing.
    """
    for key in required_keys:
        if key not in data or not str(data.get(key, "")).strip():
            data[key] = (
                "Information for this section was not returned by the AI. "
                "Please try again or consult a healthcare professional."
            )
    return data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_first_aid_guidance(situation: str) -> dict:
    """
    Return structured first-aid educational guidance for the described situation.

    Calls Gemini with a strong safety-guardrailed prompt and returns a dict with:
        immediate_steps, things_to_avoid, warning_signs, when_to_seek_help

    Returns {"error": "<message>"} on any failure.
    """
    situation = situation.strip()
    if not situation:
        return {"error": "Please describe the situation."}
    if len(situation) > 1000:
        return {"error": "Description is too long. Please keep it under 1000 characters."}

    user_prompt = (
        f"A person is describing the following first-aid situation: \"{situation}\"\n\n"
        "Please provide general educational first-aid information specifically relevant "
        "to this situation. Respond with a JSON object using the schema provided."
    )

    try:
        data = _call_gemini(_FIRST_AID_SYSTEM, user_prompt, _FIRST_AID_SCHEMA)
        return _validate_keys(
            data,
            ["immediate_steps", "things_to_avoid", "warning_signs", "when_to_seek_help"]
        )
    except ValueError as exc:
        _log.warning("Gemini service error (first-aid): %s", exc)
        return {"error": str(exc)}
    except Exception as exc:
        _log.error("Gemini unexpected error (first-aid): %s", type(exc).__name__)
        return {"error": "AI service is currently unavailable. Please check the Gemini API configuration."}


def get_medicine_info(medicine_name: str) -> dict:
    """
    Return structured general educational information about the named medicine.

    Calls Gemini with a safety-guardrailed prompt and returns a dict with:
        what_it_is, common_uses, general_precautions, important_warnings, when_to_consult

    Returns {"error": "<message>"} on any failure.
    """
    medicine_name = medicine_name.strip()
    if not medicine_name:
        return {"error": "Please enter a medicine name."}
    if len(medicine_name) > 200:
        return {"error": "Medicine name is too long. Please enter a valid medicine name."}

    user_prompt = (
        f"A user is asking for general educational information about the medicine: \"{medicine_name}\"\n\n"
        "Provide general educational information about this medicine. "
        "If you cannot confidently identify it, state that clearly and advise the user to consult "
        "their pharmacist, doctor, or the medicine's official packaging. "
        "Respond with a JSON object using the schema provided."
    )

    try:
        data = _call_gemini(_MEDICINE_SYSTEM, user_prompt, _MEDICINE_SCHEMA)
        return _validate_keys(
            data,
            ["what_it_is", "common_uses", "general_precautions", "important_warnings", "when_to_consult"]
        )
    except ValueError as exc:
        _log.warning("Gemini service error (medicine): %s", exc)
        return {"error": str(exc)}
    except Exception as exc:
        _log.error("Gemini unexpected error (medicine): %s", type(exc).__name__)
        return {"error": "AI service is currently unavailable. Please check the Gemini API configuration."}
