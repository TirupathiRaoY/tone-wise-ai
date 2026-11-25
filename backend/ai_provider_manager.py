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

import re
import requests
import ssl

# Fix Windows SSL certificate verification by injecting the Windows system cert store
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass  # truststore not installed; will use certifi bundle instead


from config import (
    GEMINI_API_KEYS,
    GROQ_API_KEYS,
    OPENROUTER_API_KEY,
    HUGGINGFACE_API_KEY,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    OLLAMA_HOST,
    OLLAMA_MODEL,
    PROVIDER_ORDER,
)


# ---------------------------------------------------------------------------
# INDIVIDUAL PROVIDER FUNCTIONS
# Each function takes a prompt (string) and returns the AI's text response.
# Each one RAISES an exception if it fails, so the manager knows to fall back.
# ---------------------------------------------------------------------------

def call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEYS:
        raise ValueError("Gemini API key not set")

    # Try each configured key, with the alternate model as a fallback.
    for api_key in GEMINI_API_KEYS:
        for model in ["gemini-1.5-flash", "gemini-2.0-flash"]:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={api_key}"
            )
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code in (401, 403, 429):
                break
            if response.ok:
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]

    raise RuntimeError("All configured Gemini API keys and models failed")


def call_groq(prompt: str) -> str:
    if not GROQ_API_KEYS:
        raise ValueError("Groq API key not set")

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "qwen/qwen3.8-27b",  # Updated to current available Groq model
        "messages": [{"role": "user", "content": prompt}],
    }

    for api_key in GROQ_API_KEYS:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code in (401, 403, 429):
            continue
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    raise RuntimeError("All configured Groq API keys were rejected or rate limited")


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


def call_openai(prompt: str) -> str:
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API key not set")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)

    if response.status_code == 429:
        raise RuntimeError("OpenAI rate limit hit")
    response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"]


def call_anthropic(prompt: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise ValueError("Anthropic API key not set")

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "claude-haiku-4-5",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)

    if response.status_code == 429:
        raise RuntimeError("Anthropic rate limit hit")
    response.raise_for_status()

    data = response.json()
    return data["content"][0]["text"]


def call_ollama(prompt: str) -> str:
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    try:
        response = requests.post(url, json=payload, timeout=180)
    except requests.ConnectionError as error:
        raise RuntimeError(
            f"Could not connect to Ollama at {OLLAMA_HOST}. Start the Ollama app and try again."
        ) from error
    except requests.Timeout as error:
        raise RuntimeError(
            f"Ollama did not finish responding within 180 seconds using model {OLLAMA_MODEL}."
        ) from error
    if response.status_code == 404:
        raise RuntimeError(
            f"Ollama model '{OLLAMA_MODEL}' is not installed. Run `ollama pull {OLLAMA_MODEL}`."
        )
    response.raise_for_status()

    data = response.json()
    if isinstance(data.get("response"), str) and data["response"].strip():
        return data["response"].strip()
    if data.get("error"):
        raise RuntimeError(f"Ollama error: {data['error']}")
    raise RuntimeError(f"Unexpected response format from Ollama: {data}")


def get_ollama_status() -> dict:
    """Report whether Ollama is reachable and has the configured model."""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        response.raise_for_status()
        models = response.json().get("models", [])
    except requests.RequestException:
        return {"available": False, "model": OLLAMA_MODEL, "model_installed": False}
    except (ValueError, AttributeError):
        return {"available": False, "model": OLLAMA_MODEL, "model_installed": False}

    installed_models = {model.get("name") for model in models if isinstance(model, dict)}
    return {
        "available": True,
        "model": OLLAMA_MODEL,
        "model_installed": OLLAMA_MODEL in installed_models,
    }


# Maps the provider name (string) to its function.
# This lets us loop through PROVIDER_ORDER generically.
PROVIDER_FUNCTIONS = {
    "gemini": call_gemini,
    "groq": call_groq,
    "openrouter": call_openrouter,
    "openai": call_openai,
    "anthropic": call_anthropic,
    "huggingface": call_huggingface,
    "ollama": call_ollama,
}

RESPONSE_STYLE_INSTRUCTIONS = """For prose responses, use concise plain-text headings on
their own lines, short paragraphs separated by blank lines, and standard hyphen bullets
when listing items. Do not use emojis or decorative symbols (including star symbols) as
headings, bullets, separators, or emphasis. Do not use asterisks for emphasis or output
HTML tags such as <br>; use real line breaks. Keep the writing natural, professional, and
easy to scan. If a table is requested, return a Markdown pipe table with a header row and
separator row. Preserve any explicitly required output format, including JSON, tables,
letters, or exact headings."""

DECORATIVE_STAR_PATTERN = re.compile(
    r"[\u2b50\u2605\u2606\u2726-\u2734\u2b51\u2b52\U0001f31f\U0001f320\U0001f7c4]\ufe0f?"
)
DECORATIVE_STAR_LINE_PATTERN = re.compile(
    r"(?m)^[ \t]*(?:[\u2b50\u2605\u2606\u2726-\u2734\u2b51\u2b52\U0001f31f\U0001f320\U0001f7c4]\ufe0f?)+[ \t]*"
)
MARKDOWN_STAR_BULLET_PATTERN = re.compile(r"(?m)^[ \t]*\*[ \t]+(?=\S)")
MARKDOWN_STAR_EMPHASIS_PATTERN = re.compile(r"\*{1,3}([^\n*]+?)\*{1,3}")
STAR_SEPARATOR_LINE_PATTERN = re.compile(r"(?m)^[ \t]*(?:\*[ \t]*){3,}$")
HTML_BREAK_PATTERN = re.compile(r"(?i)(?:<br\s*/?>|&lt;br\s*/?&gt;)")


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
    formatted_prompt = f"{prompt.rstrip()}\n\n{RESPONSE_STYLE_INSTRUCTIONS}"

    for provider_name in PROVIDER_ORDER:
        provider_function = PROVIDER_FUNCTIONS.get(provider_name)
        if provider_function is None:
            continue

        try:
            print(f"[AI Manager] Trying provider: {provider_name} ...")
            result_text = provider_function(formatted_prompt)
            if not isinstance(result_text, str) or not result_text.strip():
                raise RuntimeError("Provider returned an empty response")
            result_text = HTML_BREAK_PATTERN.sub("\n\n", result_text)
            result_text = DECORATIVE_STAR_LINE_PATTERN.sub("", result_text)
            result_text = DECORATIVE_STAR_PATTERN.sub("", result_text)
            result_text = STAR_SEPARATOR_LINE_PATTERN.sub("", result_text)
            result_text = MARKDOWN_STAR_BULLET_PATTERN.sub("- ", result_text)
            result_text = MARKDOWN_STAR_EMPHASIS_PATTERN.sub(r"\1", result_text)
            result_text = re.sub(r"[ \t]+\n", "\n", result_text)
            result_text = re.sub(r"\n{3,}", "\n\n", result_text).strip()
            if not result_text:
                raise RuntimeError("Provider returned an empty response after removing decorative symbols")
            print(f"[AI Manager] Success with: {provider_name}")
            return {
                "success": True,
                "provider_used": provider_name,
                "response": result_text,
                "errors": errors,
            }

        except Exception as error:
            message = str(error)
            for api_key in (
                *GEMINI_API_KEYS,
                *GROQ_API_KEYS,
                OPENROUTER_API_KEY,
                HUGGINGFACE_API_KEY,
                OPENAI_API_KEY,
                ANTHROPIC_API_KEY,
            ):
                if api_key:
                    message = message.replace(api_key, "[redacted]")
            error_message = f"{provider_name} failed: {message}"
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
