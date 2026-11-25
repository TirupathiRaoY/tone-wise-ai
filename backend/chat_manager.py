"""
chat_manager.py
------------------
Module 4: Chat / Q&A Manager

After a technical text is simplified (Module 2), the user might have
follow-up questions like "what does this mean for my task?" or
"can you explain that part again?"

This module:
1. Keeps track of the conversation so far (so the AI remembers context)
2. Lets the user ask a follow-up question
3. Sends the full conversation history to the AI so answers stay relevant

NOTE: This uses simple in-memory storage (a Python dictionary).
That means chat history is lost if the server restarts — Module 7
(database.py) will later save it permanently. For now, this is enough
to build and test the chat feature itself.
"""

from ai_provider_manager import call_ai


# ---------------------------------------------------------------------------
# IN-MEMORY CONVERSATION STORE
# Structure: { "session_id": [ {"role": "user"/"assistant", "content": "..."} ] }
# Each "session_id" represents one user's ongoing conversation.
# ---------------------------------------------------------------------------

conversation_store = {}


# ---------------------------------------------------------------------------
# START A NEW CONVERSATION
# Called once, right after Module 2 produces the first simplified explanation.
# ---------------------------------------------------------------------------

def start_conversation(
    session_id: str,
    original_text: str,
    simplified_explanation: str,
    language: str = "English",
    role_context: str | None = None,
) -> None:
    """
    Initializes a conversation with the original text + first AI explanation,
    so follow-up questions have full context.
    """
    conversation_store[session_id] = [
        {
            "role": "system_context",
            "user_type": role_context,
            "content": (
                f"Output language: {language}\n"
                f"User context: {role_context or 'General'}\n\n"
                f"Original text:\n{original_text}"
            ),
        },
        {
            "role": "assistant",
            "content": simplified_explanation,
        },
    ]


def restore_conversation(
    session_id: str,
    original_text: str,
    simplified_explanation: str,
    saved_messages: list[dict],
    language: str = "English",
    role_context: str | None = None,
) -> None:
    """Restore a saved conversation after the web server restarts.

    Module 7 stores the messages permanently in SQLite. This function puts
    them back into the temporary in-memory history that ask_followup() uses.
    """
    start_conversation(
        session_id, original_text, simplified_explanation, language, role_context
    )
    for message in saved_messages:
        role = message.get("sender_role")
        content = message.get("content")
        if role in ("user", "assistant") and content:
            conversation_store[session_id].append({"role": role, "content": content})


# ---------------------------------------------------------------------------
# ASK A FOLLOW-UP QUESTION
# ---------------------------------------------------------------------------

def ask_followup(session_id: str, question: str) -> dict:
    """
    Sends a follow-up question to the AI, including the full conversation
    history, so the answer stays relevant to the original text and
    previous explanation.

    Returns the same dict shape as call_ai():
        {"success": True/False, "provider_used": ..., "response": ..., "errors": [...]}
    """
    if session_id not in conversation_store:
        return {
            "success": False,
            "provider_used": None,
            "response": None,
            "errors": ["No conversation found for this session. Call start_conversation() first."],
        }

    if not question or not question.strip():
        return {
            "success": False,
            "provider_used": None,
            "response": None,
            "errors": ["Follow-up question is empty."],
        }

    history = conversation_store[session_id]

    # Build one combined prompt that includes the full history + new question.
    # (Simple approach — works with all providers in Module 1, since some
    # free APIs don't support multi-turn "messages" the same way.)
    history_text = ""
    for turn in history:
        if turn["role"] == "system_context":
            history_text += f"[Original text the user is asking about]:\n{turn['content']}\n\n"
        elif turn["role"] == "assistant":
            history_text += f"[Previous explanation given]:\n{turn['content']}\n\n"
        elif turn["role"] == "user":
            history_text += f"[User previously asked]: {turn['content']}\n\n"

    assistant_context = (
        "You are ToneWise AI, helping a job seeker understand career and recruitment information. "
        "Use relevant terms such as job responsibilities, required and preferred qualifications, "
        "technical and soft skills, transferable skills, recruiter, interview rounds, STAR method, "
        "and offer terms when useful; briefly explain unfamiliar terms. Clearly separate facts "
        "stated in the source from advice or inference. Do not invent the user's experience, "
        "employer requirements, interview outcome, or offer details."
        if history[0].get("user_type") == "Job Seeker"
        else "You are ToneWise AI, continuing a conversation with a non-technical employee "
        "about a piece of technical text."
    )
    followup_prompt = f"""{assistant_context}

CONVERSATION SO FAR:
{history_text}

NEW QUESTION FROM USER:
{question}

Answer the new question in plain, simple language, using the same context
as before. If the question can't be answered from the original text, say so
honestly rather than making something up."""

    result = call_ai(followup_prompt)

    # Save this turn into history (whether it succeeded or not, we log the question)
    conversation_store[session_id].append({"role": "user", "content": question})
    if result["success"]:
        conversation_store[session_id].append({"role": "assistant", "content": result["response"]})

    return result


# ---------------------------------------------------------------------------
# GET FULL HISTORY (useful for displaying the chat window later)
# ---------------------------------------------------------------------------

def get_conversation_history(session_id: str) -> list:
    return conversation_store.get(session_id, [])


# ---------------------------------------------------------------------------
# QUICK TEST — run this file directly to check Module 4 works:
#   python chat_manager.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_session = "test_user_1"

    start_conversation(
        session_id=test_session,
        original_text="The API's p99 latency spiked to 850ms due to an N+1 query.",
        simplified_explanation="This means the app got slow for some users because of an inefficient database request after a recent update.",
    )

    print("Asking a follow-up question...\n")
    result = ask_followup(test_session, "Does this mean customers lost data?")

    if result["success"]:
        print(f"✅ Success using: {result['provider_used']}\n")
        print("Answer:", result["response"])
    else:
        print("❌ All providers failed:", result["errors"])

    print("\nFull conversation history:")
    for turn in get_conversation_history(test_session):
        print(turn)
