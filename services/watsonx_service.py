import os
import re
import logging
from dotenv import load_dotenv

# load_dotenv() MUST run before any os.getenv() call.
load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_API_KEY    = os.getenv("WATSONX_API_KEY", "")
_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
_URL        = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
_MODEL_ID   = os.getenv("WATSONX_MODEL_ID", "meta-llama/llama-3-8b-instruct")

# ---------------------------------------------------------------------------
# Logging (safe — never prints secrets)
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
_log = logging.getLogger("watsonx_service")
_log.info("IBM watsonx.ai provider. Model: %s  Credentials present: %s",
          _MODEL_ID, bool(_API_KEY and _PROJECT_ID))


# ---------------------------------------------------------------------------
# IBM watsonx.ai client
# ---------------------------------------------------------------------------

def _get_model():
    """Initialise and return a ModelInference instance (IBM watsonx.ai).

    Credentials are validated at call time — not at import time — so a missing
    key only fails when the IBM provider is actually used.
    """
    if not _API_KEY or not _PROJECT_ID:
        raise ValueError(
            "IBM watsonx.ai credentials are not configured. "
            "Set WATSONX_API_KEY and WATSONX_PROJECT_ID in .env."
        )

    # Lazy import — IBM SDK is only loaded when this provider is actually called.
    from ibm_watsonx_ai import Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

    gen_params = {
        GenParams.MAX_NEW_TOKENS:      800,
        GenParams.MIN_NEW_TOKENS:      50,
        GenParams.TEMPERATURE:         0.3,
        GenParams.TOP_P:               0.9,
        GenParams.REPETITION_PENALTY:  1.1,
    }

    credentials = Credentials(url=_URL, api_key=_API_KEY)
    return ModelInference(
        model_id=_MODEL_ID,
        credentials=credentials,
        project_id=_PROJECT_ID,
        params=gen_params,
    )


# ---------------------------------------------------------------------------
# Section parser
# ---------------------------------------------------------------------------

def _parse_sections(raw_text: str, keys: list) -> dict:
    """
    Extract labelled sections from the model's text output.

    The prompt instructs the model to use headers like:
        IMMEDIATE STEPS:
        ...content...
        THINGS TO AVOID:
        ...content...

    Matches labels case-insensitively; falls back to full text in first key.
    """
    result = {key: "" for key in keys}
    label_map = {key: key.upper().replace("_", " ") for key in keys}

    pattern = r"(?i)(" + "|".join(re.escape(lbl) for lbl in label_map.values()) + r")\s*:?\s*"
    parts = re.split(pattern, raw_text)

    if len(parts) <= 1:
        result[keys[0]] = raw_text.strip()
        return result

    i = 1
    while i < len(parts) - 1:
        label_found = parts[i].upper().strip()
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        for key, lbl in label_map.items():
            if label_found == lbl:
                result[key] = content
                break
        i += 2

    return result


def _clean_text(text: str) -> str:
    """Remove excessive blank lines and strip leading/trailing whitespace."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_first_aid_guidance(situation: str) -> dict:
    """
    Return structured first-aid educational guidance using IBM watsonx.ai.

    Returns a dict with keys:
        immediate_steps, things_to_avoid, warning_signs, when_to_seek_help

    Returns {"error": "<message>"} on any failure.
    """
    situation = situation.strip()
    if not situation:
        return {"error": "Please describe the situation."}
    if len(situation) > 1000:
        return {"error": "Description is too long. Please keep it under 1000 characters."}

    prompt = (
        "You are a general health education assistant providing basic first-aid information "
        "for educational purposes only. You do NOT diagnose medical conditions, prescribe "
        "medication, or provide personalized medical treatment.\n\n"
        f'A user has described the following situation: "{situation}"\n\n'
        "Provide general educational first-aid information structured EXACTLY into these four "
        "sections. Use the exact header labels shown below, followed by a colon. Keep each "
        "section concise (2-5 sentences or bullet points).\n\n"
        "IMMEDIATE STEPS:\n"
        "List the basic general first-aid steps a person can take right away.\n\n"
        "THINGS TO AVOID:\n"
        "List common mistakes or actions that should be avoided in this situation.\n\n"
        "WARNING SIGNS:\n"
        "Describe signs or symptoms that indicate the situation may be more serious.\n\n"
        "WHEN TO SEEK HELP:\n"
        "Clearly state when the person should seek professional medical attention or call "
        "emergency services.\n\n"
        "Important: Do not diagnose. Do not recommend specific medications or dosages. "
        "For life-threatening emergencies direct the user to call emergency services immediately.\n\n"
        "Response:"
    )

    try:
        model = _get_model()
        raw = model.generate_text(prompt=prompt)
        sections = _parse_sections(
            raw, ["immediate_steps", "things_to_avoid", "warning_signs", "when_to_seek_help"]
        )
        return {k: _clean_text(v) for k, v in sections.items()}
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        _log.error("IBM watsonx.ai error (first-aid): %s", type(exc).__name__)
        return {"error": "AI service error: IBM watsonx.ai request failed. Check your credentials and connectivity."}


def get_medicine_info(medicine_name: str) -> dict:
    """
    Return structured general educational information about the named medicine
    using IBM watsonx.ai.

    Returns a dict with keys:
        what_it_is, common_uses, general_precautions, important_warnings, when_to_consult

    Returns {"error": "<message>"} on any failure.
    """
    medicine_name = medicine_name.strip()
    if not medicine_name:
        return {"error": "Please enter a medicine name."}
    if len(medicine_name) > 200:
        return {"error": "Medicine name is too long. Please enter a valid medicine name."}

    prompt = (
        "You are a general health education assistant providing basic medicine information "
        "for educational purposes only. You do NOT prescribe medication, recommend dosages, "
        "or make treatment decisions.\n\n"
        f'A user is asking about the medicine: "{medicine_name}"\n\n'
        "Provide general educational information structured EXACTLY into these five sections. "
        "Use the exact header labels, followed by a colon. Keep each section concise.\n\n"
        "WHAT IT IS:\n"
        "Describe what this medicine is in general terms (drug class, type).\n\n"
        "COMMON USES:\n"
        "Describe the general conditions or symptoms this medicine is commonly used for.\n\n"
        "GENERAL PRECAUTIONS:\n"
        "List important general precautions people should be aware of.\n\n"
        "IMPORTANT WARNINGS:\n"
        "List significant warnings, contraindications, or serious side effects.\n\n"
        "WHEN TO CONSULT:\n"
        "State clearly when a person should consult a healthcare professional.\n\n"
        "Important: Do not recommend dosages. Do not advise starting, stopping, or changing "
        "any medication. Always emphasize consulting a qualified healthcare professional.\n\n"
        "Response:"
    )

    try:
        model = _get_model()
        raw = model.generate_text(prompt=prompt)
        sections = _parse_sections(
            raw,
            ["what_it_is", "common_uses", "general_precautions", "important_warnings", "when_to_consult"],
        )
        return {k: _clean_text(v) for k, v in sections.items()}
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        _log.error("IBM watsonx.ai error (medicine): %s", type(exc).__name__)
        return {"error": "AI service error: IBM watsonx.ai request failed. Check your credentials and connectivity."}
