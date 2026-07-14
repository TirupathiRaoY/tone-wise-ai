"""
role_tone_selector.py

Central place to manage available Roles and Tones.
Other modules should import these lists instead of hardcoding them.
"""

# -------------------------
# Available Tones
# -------------------------

AVAILABLE_TONES = [
    "Formal",
    "Casual",
    "Very Simple (ELI5)",
    "Encouraging"
]

# -------------------------
# Available Roles
# -------------------------

AVAILABLE_ROLES = [
    "General Staff",
    "HR",
    "Sales",
    "Admin",
    "Customer Support"
]


def get_available_tones():
    """
    Returns all supported tones.
    """
    return AVAILABLE_TONES


def get_available_roles():
    """
    Returns all supported roles.
    """
    return AVAILABLE_ROLES


def validate_tone(tone: str) -> str:
    """
    Ensures the selected tone is valid.
    Falls back to Formal if not.
    """

    if tone in AVAILABLE_TONES:
        return tone

    return "Formal"


def validate_role(role: str) -> str:
    """
    Ensures the selected role is valid.
    Falls back to General Staff if not.
    """

    if role in AVAILABLE_ROLES:
        return role

    return "General Staff"


def get_default_settings():
    """
    Returns default selections.
    """

    return {
        "tone": "Formal",
        "role": "General Staff"
    }