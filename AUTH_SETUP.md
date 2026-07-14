# Authentication and onboarding setup

This module is free to run: it uses the project's existing local SQLite file
and free Google/GitHub OAuth registrations. Email-and-password accounts work
immediately after installation; OAuth needs the optional configuration below.

## 1. Install the new packages

Open a terminal in `backend` and run:

```powershell
pip install -r requirements.txt
```

## 2. Add secrets to `backend/.env`

Generate a long random `SESSION_SECRET` (do not publish it). For local HTTP
development use `SESSION_HTTPS_ONLY=false`; set it to `true` before a real
HTTPS deployment.

```env
SESSION_SECRET=replace-with-a-long-random-secret
SESSION_HTTPS_ONLY=false
# Leave blank for local development. In production, set this to the public
# origin registered with both providers, e.g. https://app.example.com.
APP_PORT=8001
APP_URL=http://127.0.0.1:8001
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
```

## 3. Start the project

From `backend`, run `python main.py`, then open `http://127.0.0.1:8001/signup`.
The sequence is: sign up -> onboarding (once) -> main ToneWise AI page.

## 4. Optional: enable Google sign-in

In Google Cloud Console, create an **OAuth client ID** of type **Web
application**. Add this exact authorized redirect URI for local development:

`http://127.0.0.1:8001/api/auth/oauth/google/callback`

Copy its client ID and secret into `.env`. For a deployed site, add the same
path under your HTTPS domain as another redirect URI.

## 5. Optional: enable GitHub sign-in

In GitHub Settings -> Developer settings -> OAuth Apps, create an OAuth App.
Set its Authorization callback URL to:

`http://127.0.0.1:8001/api/auth/oauth/github/callback`

Copy its client ID and generated client secret into `.env`.

## Files added

- `backend/auth.py` — email auth, signed sessions, OAuth and onboarding API
- `frontend/signin.html`, `signup.html`, `onboarding.html` — the three screens
- `frontend/auth.css`, `auth.js` — isolated UI styling and behaviour

The database creates `users` and `user_onboarding` automatically at next start;
it does not alter existing conversation records.
