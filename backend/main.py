"""The FastAPI web server for ToneWise AI (Module 9)."""

from pathlib import Path
from io import BytesIO
import os
import tempfile
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel, Field
from docx import Document

from chat_manager import ask_followup, get_conversation_history, restore_conversation, start_conversation
from database import (
    get_admin_summary,
    get_conversation,
    get_team_comments,
    initialize_database,
    save_conversation,
    save_feedback,
    save_message,
    save_team_comment,
)
from input_handler import handle_pasted_text, handle_uploaded_file
from prompt_engine import simplify_text
from selector_options import get_selector_options, validate_selection
from auth import current_user, router as auth_router
from dashboard_routes import router as dashboard_router
from config import APP_PORT, SESSION_HTTPS_ONLY, SESSION_SECRET


PROJECT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_DIR / "frontend"
ADMIN_DIR = PROJECT_DIR / "admin"
ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB

app = FastAPI(title="ToneWise AI", version="1.0.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="tonewise_session",
    same_site="lax",
    https_only=SESSION_HTTPS_ONLY,
    max_age=60 * 60 * 24 * 14,
)
app.include_router(auth_router)
app.include_router(dashboard_router)


class ChatRequest(BaseModel):
    session_id: str
    question: str = Field(min_length=1, max_length=4_000)


class FeedbackRequest(BaseModel):
    session_id: str
    was_clear: bool
    comment: str | None = Field(default=None, max_length=1_000)


class TeamCommentRequest(BaseModel):
    author_name: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=2_000)


@app.on_event("startup")
def start_up() -> None:
    """Create SQLite tables before the first request reaches the app."""
    initialize_database()


@app.get("/", include_in_schema=False, response_model=None)
def home_page(request: Request) -> FileResponse | RedirectResponse:
    """Keep the ToneWise workspace private until sign-in and onboarding finish."""
    user = current_user(request)
    if user is None:
        return RedirectResponse("/signin", status_code=303)
    if not user["onboarding_complete"]:
        return RedirectResponse("/onboarding", status_code=303)
    return RedirectResponse("/dashboard", status_code=303)


@app.get("/dashboard", include_in_schema=False, response_model=None)
def dashboard_page(request: Request) -> FileResponse | RedirectResponse:
    user = current_user(request)
    if user is None:
        return RedirectResponse("/signin", status_code=303)
    if not user["onboarding_complete"]:
        return RedirectResponse("/onboarding", status_code=303)
    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/workspace", include_in_schema=False, response_model=None)
def workspace_page(request: Request) -> FileResponse | RedirectResponse:
    user = current_user(request)
    if user is None:
        return RedirectResponse("/signin", status_code=303)
    if not user["onboarding_complete"]:
        return RedirectResponse("/onboarding", status_code=303)
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/team-feed", include_in_schema=False, response_model=None)
def team_feed_page(request: Request) -> FileResponse | RedirectResponse:
    user = current_user(request)
    if user is None:
        return RedirectResponse("/signin", status_code=303)
    if not user["onboarding_complete"]:
        return RedirectResponse("/onboarding", status_code=303)
    return FileResponse(FRONTEND_DIR / "team_feed.html")


@app.get("/team-settings", include_in_schema=False, response_model=None)
def team_settings_page(request: Request) -> FileResponse | RedirectResponse:
    user = current_user(request)
    if user is None:
        return RedirectResponse("/signin", status_code=303)
    if not user["onboarding_complete"]:
        return RedirectResponse("/onboarding", status_code=303)
    return FileResponse(FRONTEND_DIR / "team_settings.html")


@app.get("/profile", include_in_schema=False, response_model=None)
def profile_page(request: Request) -> RedirectResponse:
    user = current_user(request)
    if user is None:
        return RedirectResponse("/signin", status_code=303)
    return RedirectResponse("/dashboard", status_code=303)


@app.get("/style.css", include_in_schema=False)
def stylesheet() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "style.css", media_type="text/css")


@app.get("/auth.css", include_in_schema=False)
def auth_stylesheet() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "auth.css", media_type="text/css")


@app.get("/auth.js", include_in_schema=False)
def auth_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "auth.js", media_type="application/javascript")


@app.get("/dashboard.css", include_in_schema=False)
def dashboard_stylesheet() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "dashboard.css", media_type="text/css")


@app.get("/dashboard.js", include_in_schema=False)
def dashboard_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "dashboard.js", media_type="application/javascript")


@app.get("/team.css", include_in_schema=False)
def team_stylesheet() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "team.css", media_type="text/css")


@app.get("/team-feed.js", include_in_schema=False)
def team_feed_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "team_feed.js", media_type="application/javascript")


@app.get("/team-settings.js", include_in_schema=False)
def team_settings_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "team_settings.js", media_type="application/javascript")


@app.get("/signin", include_in_schema=False, response_model=None)
def signin_page(request: Request) -> FileResponse | RedirectResponse:
    user = current_user(request)
    if user is not None:
        return RedirectResponse("/dashboard" if user["onboarding_complete"] else "/onboarding", status_code=303)
    return FileResponse(FRONTEND_DIR / "signin.html")


@app.get("/signup", include_in_schema=False, response_model=None)
def signup_page(request: Request) -> FileResponse | RedirectResponse:
    user = current_user(request)
    if user is not None:
        return RedirectResponse("/dashboard" if user["onboarding_complete"] else "/onboarding", status_code=303)
    return FileResponse(FRONTEND_DIR / "signup.html")


@app.get("/forgot-password", include_in_schema=False, response_model=None)
def forgot_password_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "forgot_password.html")


@app.get("/reset-password", include_in_schema=False, response_model=None)
def reset_password_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "reset_password.html")


@app.get("/onboarding", include_in_schema=False, response_model=None)
def onboarding_page(request: Request) -> FileResponse | RedirectResponse:
    user = current_user(request)
    if user is None:
        return RedirectResponse("/signin", status_code=303)
    if user["onboarding_complete"]:
        return RedirectResponse("/dashboard", status_code=303)
    return FileResponse(FRONTEND_DIR / "onboarding.html")


@app.get("/script.js", include_in_schema=False)
def frontend_script() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "script.js", media_type="application/javascript")


@app.get("/admin", include_in_schema=False)
def admin_page_shortcut() -> RedirectResponse:
    return RedirectResponse("/admin/dashboard.html")


@app.get("/admin/dashboard.html", include_in_schema=False)
def admin_page() -> FileResponse:
    return FileResponse(ADMIN_DIR / "dashboard.html")


@app.get("/api/options")
def selector_options() -> dict:
    """Give the webpage the same valid tone/role choices as Module 2."""
    return get_selector_options()


@app.post("/api/simplify", response_model=None)
async def simplify_content(
    request: Request,
    text: str = Form(default=""),
    tone: str = Form(default="Casual"),
    language: str = Form(default="English"),
    file: UploadFile | None = File(default=None),
) -> dict | JSONResponse:
    """Read pasted/uploaded content, simplify it, and save a conversation."""
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in to simplify content.")
    if text.strip() and file is not None:
        raise HTTPException(status_code=400, detail="Please use either pasted text or one file, not both.")

    if file is None:
        input_result = handle_pasted_text(text)
    else:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Please upload a TXT, PDF, or DOCX file.")

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")
        if len(file_bytes) > MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="Please upload a file smaller than 10 MB.")

        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
                temporary_file.write(file_bytes)
                temporary_path = temporary_file.name
            input_result = handle_uploaded_file(temporary_path)
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.remove(temporary_path)

    if not input_result["success"]:
        raise HTTPException(status_code=400, detail=input_result["error"])

    # The workspace uses one clear, general audience rather than asking people
    # to choose a role for every simplification.
    selection = validate_selection(tone, "General Non-Technical Staff", language)
    ai_result = simplify_text(
        input_result["text"],
        selection["tone"],
        selection["role"],
        selection["language"],
    )
    if not ai_result["success"]:
        return JSONResponse(status_code=502, content=ai_result)

    session_id = str(uuid4())
    start_conversation(
        session_id,
        input_result["text"],
        ai_result["response"],
        selection["language"],
    )
    save_conversation(
        session_id=session_id,
        original_text=input_result["text"],
        simplified_explanation=ai_result["response"],
        tone=selection["tone"],
        role=selection["role"],
        language=selection["language"],
        provider_used=ai_result["provider_used"],
        user_id=user["id"],
    )

    return {**ai_result, "session_id": session_id}


@app.post("/api/chat", response_model=None)
def chat(request: ChatRequest) -> dict | JSONResponse:
    """Answer a follow-up and save both the question and the reply."""
    session_id = request.session_id.strip()
    question = request.question.strip()
    if not session_id or not question:
        raise HTTPException(status_code=400, detail="A conversation and question are required.")

    # After a restart, rebuild Module 4's temporary history from Module 7.
    if not get_conversation_history(session_id):
        saved_conversation = get_conversation(session_id)
        if saved_conversation is None:
            raise HTTPException(status_code=404, detail="This conversation could not be found.")
        restore_conversation(
            session_id,
            saved_conversation["original_text"],
            saved_conversation["simplified_explanation"],
            saved_conversation["messages"],
            saved_conversation["language"],
        )

    result = ask_followup(session_id, question)
    save_message(session_id, "user", question)
    if result["success"]:
        save_message(session_id, "assistant", result["response"])
        return result
    return JSONResponse(status_code=502, content=result)


@app.post("/api/feedback")
def feedback(request: FeedbackRequest) -> dict:
    """Save the user's answer to 'Was this clear?' for one conversation."""
    if get_conversation(request.session_id) is None:
        raise HTTPException(status_code=404, detail="This conversation could not be found.")
    save_feedback(request.session_id, request.was_clear, request.comment)
    return {"success": True, "message": "Thank you for your feedback."}


@app.get("/api/conversations/{session_id}")
def shared_conversation(session_id: str) -> dict:
    """Load an explanation from its shareable conversation link."""
    conversation = get_conversation(session_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="This shared explanation could not be found.")
    return {
        "success": True,
        "session_id": conversation["session_id"],
        "response": conversation["simplified_explanation"],
        "provider_used": conversation["provider_used"],
        "tone": conversation["tone"],
        "role": conversation["role"],
        "language": conversation["language"],
        "messages": conversation["messages"],
    }


@app.get("/api/conversations/{session_id}/download")
def download_conversation(session_id: str, format: str = "txt") -> Response:
    """Download the saved explanation as a TXT or DOCX file."""
    conversation = get_conversation(session_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="This explanation could not be found.")

    if format == "txt":
        content = (
            "ToneWise AI - Simplified Explanation\n"
            f"Language: {conversation['language']}\n\n"
            "SIMPLIFIED EXPLANATION\n"
            f"{conversation['simplified_explanation']}\n\n"
            "ORIGINAL CONTENT\n"
            f"{conversation['original_text']}\n"
        )
        return Response(
            content=content,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="tonewise-explanation.txt"'},
        )

    if format == "docx":
        document = Document()
        document.add_heading("ToneWise AI - Simplified Explanation", level=0)
        document.add_paragraph(f"Language: {conversation['language']}")
        document.add_heading("Simplified explanation", level=1)
        document.add_paragraph(conversation["simplified_explanation"])
        document.add_heading("Original content", level=1)
        document.add_paragraph(conversation["original_text"])
        output = BytesIO()
        document.save(output)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": 'attachment; filename="tonewise-explanation.docx"'},
        )

    raise HTTPException(status_code=400, detail="Choose either txt or docx format.")


@app.get("/api/conversations/{session_id}/comments")
def team_comments(session_id: str) -> dict:
    """Return the team notes saved for a shared explanation."""
    if get_conversation(session_id) is None:
        raise HTTPException(status_code=404, detail="This explanation could not be found.")
    return {"success": True, "comments": get_team_comments(session_id)}


@app.post("/api/conversations/{session_id}/comments")
def add_team_comment(session_id: str, request: TeamCommentRequest) -> dict:
    """Add a teammate's note to a shared explanation."""
    if get_conversation(session_id) is None:
        raise HTTPException(status_code=404, detail="This explanation could not be found.")
    try:
        comment = save_team_comment(session_id, request.author_name, request.content)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"success": True, "comment": comment}


@app.get("/api/admin/summary")
def admin_summary() -> dict:
    """Provide the statistics used by the Module 8 dashboard."""
    return get_admin_summary()


@app.get("/api/health")
def health_check() -> dict:
    """A small check confirming that the web server is running."""
    return {"status": "ok"}


if __name__ == "__main__":
    # Beginner-friendly way to start the app from the backend folder:
    # python main.py
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=APP_PORT)
