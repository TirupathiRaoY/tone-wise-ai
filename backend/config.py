"""
config.py
----------
Loads all API keys from the .env file.
NEVER hardcode your keys directly in code — always keep them in .env
so you don't accidentally share them if you upload this project anywhere.
"""

import os
from dotenv import load_dotenv

# Loads variables from a file named ".env" in the same folder
load_dotenv()

# Free AI provider keys — get these from each provider's website (links in README)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")

# Order in which providers are tried (first = highest priority)
# You can reorder this list any time without touching other code.
PROVIDER_ORDER = ["gemini", "groq", "openrouter", "huggingface"]

# Authentication settings. Generate a long random value for SESSION_SECRET in
# production; it signs the browser session cookie.
SESSION_SECRET = os.getenv("SESSION_SECRET", "change-this-local-development-secret")
SESSION_HTTPS_ONLY = os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true"
APP_PORT = int(os.getenv("APP_PORT", "8001"))
# Set this for deployments behind a proxy so OAuth always uses the registered
# public callback URL (for example, https://app.example.com).
APP_URL = os.getenv("APP_URL", "").rstrip("/")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")

# SMTP settings used for team invitations. For Gmail use smtp.gmail.com,
# port 587, your Gmail address, and a Google App Password.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USERNAME)
