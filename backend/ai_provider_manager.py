"""
ai_provider_manager.py
------------------------
Module 1: AI Provider Manager

This is the heart of the "use free AI bots and auto-switch when one hits
its limit" system.

HOW IT WORKS:
1. You call one single function: call_ai(prompt)
2. It tries providers in the order set in config.PROVIDER_ORDER
   (default: Gemini -> Groq -> OpenRouter -> HuggingFace)
3. If a provider fails (rate limit, error, timeout), it automatically
   moves to the next one in the list.
4. If ALL providers fail, it returns a clear error message instead of crashing.

You don't need to touch this file when building other modules —
just import call_ai() and use it everywhere you need an AI response.
"""

import requests
from config import (
    GEMINI_API_KEY,
    GROQ_API_KEY,
    OPENROUTER_API_KEY,
    HUGGINGFACE_API_KEY,
    PROVIDER_ORDER,
)


# ---------------------------------------------------------------------------
# INDIVIDUAL PROVIDER FUNCTIONS
# Each function takes a prompt (string) and returns the AI's text response.
# Each one RAISES an exception if it fails, so the manager knows to fall back.
# ---------------------------------------------------------------------------

def call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("Gemini API key not set")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    response = requests.post(url, json=payload, timeout=30)

    if response.status_code == 429:
        raise RuntimeError("Gemini rate limit hit")
    response.raise_for_status()

    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def call_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        raise ValueError("Groq API key not set")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)

    if response.status_code == 429:
        raise RuntimeError("Groq rate limit hit")
    response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"]


def call_openrouter(prompt: str) -> str:
    if not OPENROUTER_API_KEY:
        raise ValueError("OpenRouter API key not set")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    # Using a free model available on OpenRouter
    payload = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": [{"role": "user", "content": prompt}],
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)

    if response.status_code == 429:
        raise RuntimeError("OpenRouter rate limit hit")
    response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"]


def call_huggingface(prompt: str) -> str:
    if not HUGGINGFACE_API_KEY:
        raise ValueError("HuggingFace API key not set")

    # Example free model — you can swap this for any free HF model
    url = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    payload = {"inputs": prompt}

    response = requests.post(url, headers=headers, json=payload, timeout=30)

    if response.status_code == 429:
        raise RuntimeError("HuggingFace rate limit hit")
    response.raise_for_status()

    data = response.json()
    # HF's response shape can vary by model; this handles the common case
    if isinstance(data, list) and "generated_text" in data[0]:
        return data[0]["generated_text"]
    return str(data)


# Maps the provider name (string) to its function.
# This lets us loop through PROVIDER_ORDER generically.
PROVIDER_FUNCTIONS = {
    "gemini": call_gemini,
    "groq": call_groq,
    "openrouter": call_openrouter,
    "huggingface": call_huggingface,
}


# ---------------------------------------------------------------------------
# MAIN FUNCTION — this is the ONLY function other modules should call
# ---------------------------------------------------------------------------

def call_ai(prompt: str) -> dict:
    """
    Tries each AI provider in order until one succeeds.

    Returns a dict:
        {
            "success": True/False,
            "provider_used": "gemini" / "groq" / etc, or None,
            "response": "<AI's answer>" or None,
            "errors": [list of errors from providers that failed]
        }
    """
    errors = []

    for provider_name in PROVIDER_ORDER:
        provider_function = PROVIDER_FUNCTIONS.get(provider_name)
        if provider_function is None:
            continue

        try:
            print(f"[AI Manager] Trying provider: {provider_name} ...")
            result_text = provider_function(prompt)
            print(f"[AI Manager] Success with: {provider_name}")
            return {
                "success": True,
                "provider_used": provider_name,
                "response": result_text,
                "errors": errors,
            }

        except Exception as error:
            error_message = f"{provider_name} failed: {str(error)}"
            print(f"[AI Manager] {error_message}")
            errors.append(error_message)
            continue  # move to next provider in the list

    # If we reach here, every provider failed
    return {
        "success": False,
        "provider_used": None,
        "response": None,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# QUICK TEST — run this file directly to check your setup:
#   python ai_provider_manager.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_prompt = "Explain what an API is, in one simple sentence."
    result = call_ai(test_prompt)

    if result["success"]:
        print("\n✅ AI responded successfully!")
        print(f"Provider used: {result['provider_used']}")
        print(f"Response: {result['response']}")
    else:
        print("\n❌ All providers failed. Errors:")
        for e in result["errors"]:
            print(" -", e)
