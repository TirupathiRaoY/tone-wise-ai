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
7. Fill in your free API keys inside `.env` (see links below). For Gemini or
   Groq, you can set `GEMINI_API_KEYS` or `GROQ_API_KEYS` to a comma-separated
   list; the app tries the next key when one is rejected or rate-limited.
   Keep `.env` private and rotate any key shared in chat, logs, or source control.
8. Test Module 1 works: `python ai_provider_manager.py`

### Local voice input

Voice recordings are transcribed on this computer with the multilingual
Whisper `base` model. The model downloads automatically on the first
transcription (about 150 MB); recordings are not sent to a speech provider.
Allow microphone access in your browser and choose the language you are
speaking in before dictating in the workspace.

### Role-tailored workspaces

The workspace adapts its guidance and examples to the role selected during
onboarding. Students can select optional study tools after uploading a file:
simple concept explanations, real-life examples, a quiz, and diagram
explanations based on text and captions extracted from the document.

Business Owner workspaces include optional report and document analysis
checklists on uploaded files, plus a separate formal letter assistant for
sender/recipient details, subject, dates, and key points. Business tools are
available only to Business Owner accounts.

Working Professional workspaces can upload PDF, DOCX, or TXT files, ask an
optional question about the document, and select any combination of table
creation, key-point extraction, and deadline/responsibility extraction.

Job Seeker dashboards include four separate career workflows: job-description
analysis from pasted text or an uploaded file; skill-based interview lessons
and quizzes; aptitude lessons and quizzes; and recruitment-message explanations
selected by message type. Interview and aptitude quizzes offer beginner,
intermediate, and advanced difficulty, answer selection, scoring, and
post-submission explanations. These routes and their AI endpoint are restricted
to Job Seeker accounts. The general workspace remains available and uses
job-search terminology in follow-up chat.

### Local Ollama

Install and start Ollama, then download the configured model from the backend
terminal with `ollama pull llama3.2:1b`. Configured online providers are tried
first; Ollama is the final local fallback if they fail. Set `OLLAMA_HOST`,
`OLLAMA_MODEL`, or `PROVIDER_ORDER` in `backend/.env` to use a different local
model or provider order. Restart the backend after changing these settings.

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
