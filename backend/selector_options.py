"""
selector_options.py
-------------------
Module 5: Role & Tone Selector

This file is the single bridge between the dropdowns in the future web page
and the valid tone/role choices in prompt_engine.py.

Keeping this logic separate means the frontend never has to guess which
options are valid.  When you add a tone or role to prompt_engine.py later,
it automatically becomes available here too.
"""

from prompt_engine import AVAILABLE_LANGUAGES, AVAILABLE_ROLES, AVAILABLE_TONES


# The choices pre-selected when a user opens ToneWise AI.
DEFAULT_TONE = "Casual"
DEFAULT_ROLE = "General Non-Technical Staff"
DEFAULT_LANGUAGE = "English"


def get_selector_options() -> dict:
    """Return all valid dropdown choices and their default selections.

    The FastAPI app (built later) will send this dictionary to script.js,
    which will use it to create the two dropdown menus.
    """
    return {
        "tones": AVAILABLE_TONES,
        "roles": AVAILABLE_ROLES,
        "languages": AVAILABLE_LANGUAGES,
        "default_tone": DEFAULT_TONE,
        "default_role": DEFAULT_ROLE,
        "default_language": DEFAULT_LANGUAGE,
    }


def validate_selection(tone: str | None, role: str | None, language: str | None = None) -> dict:
    """Check dropdown values received from the webpage.

    A browser request can be edited manually, so we always validate again on
    the backend. Invalid or blank values are safely changed to the defaults.
    """
    selected_tone = tone if tone in AVAILABLE_TONES else DEFAULT_TONE
    selected_role = role if role in AVAILABLE_ROLES else DEFAULT_ROLE
    selected_language = language if language in AVAILABLE_LANGUAGES else DEFAULT_LANGUAGE

    return {
        "tone": selected_tone,
        "role": selected_role,
        "language": selected_language,
    }


if __name__ == "__main__":
    # Optional quick check: run `python selector_options.py` in backend/.
    print("Available selector options:")
    print(get_selector_options())
    print("\nExample of invalid values being made safe:")
    print(validate_selection("Unknown tone", "Unknown role"))
