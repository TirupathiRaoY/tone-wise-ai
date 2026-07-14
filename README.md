# ToneWise AI

An AI assistant that translates industry/technical content into plain
language for non-technical staff, with adjustable tone and role-based
personalization — built entirely with FREE AI APIs.

## Project Status

| Module | File(s) | Status |
|---|---|---|
| 1. AI Provider Manager | `backend/ai_provider_manager.py`, `backend/config.py` | ✅ Done |
| 2. Prompt Engine (tone/jargon) | `backend/prompt_engine.py` | ✅ Done |
| 3. Input Handler (files/text) | `backend/input_handler.py` | ✅ Done |
| 4. Chat / Q&A Manager | `backend/chat_manager.py` | ✅ Done |
| 5. Role & Tone Selector | `backend/role_tone_selector.py` | ✅ Done |
| 6. Frontend UI | `frontend/index.html`, `frontend/style.css`, `frontend/script.js` | ✅ Done |
| 7. Storage (Feedback + History) | `backend/database.py` | ✅ Done |
| 8. Admin Dashboard | `admin/dashboard.html` | ✅ Done |

## Setup (do this once)

1. Install VS Code: https://code.visualstudio.com
2. Install Python (check "Add Python to PATH" during install): https://www.python.org/downloads/
3. Open this whole `tonewise-ai` folder in VS Code (File → Open Folder)
4. Right-click the `backend` folder → "Open in Integrated Terminal"
5. Run: `pip install -r requirements.txt`
6. Rename `backend/.env.example` to `backend/.env`
7. Fill in your free API keys inside `.env` (see links below)
8. Test Module 1 works: `python ai_provider_manager.py`

## Free API Key Links

- Gemini: https://aistudio.google.com/apikey
- Groq: https://console.groq.com/keys
- OpenRouter: https://openrouter.ai/keys
- HuggingFace: https://huggingface.co/settings/tokens

## Folder Structure

```
tonewise-ai/
│
├── backend/
│   ├── main.py                 # App entry point (Module 6 wiring)
│   ├── ai_provider_manager.py  # Module 1: multi-bot fallback logic ✅
│   ├── prompt_engine.py        # Module 2: tone/jargon prompt templates
│   ├── input_handler.py        # Module 3: file/text parsing
│   ├── chat_manager.py         # Module 4: conversation handling
│   ├── database.py             # Module 7: SQLite setup + queries
│   ├── config.py               # Loads API keys ✅
│   ├── requirements.txt        # Python packages needed ✅
│   ├── .env.example            # Template for your API keys ✅
│   └── .env                    # YOUR real keys (you create this — never share it)
│
├── frontend/
│   ├── index.html              # Module 6: main UI
│   ├── style.css
│   └── script.js
│
├── admin/
│   └── dashboard.html          # Module 8: basic admin view
│
└── README.md                   # This file
```
