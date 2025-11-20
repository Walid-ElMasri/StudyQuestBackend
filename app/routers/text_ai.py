from fastapi import APIRouter, HTTPException, Body, Request
from sqlmodel import Session, select
from datetime import datetime
from app.database import engine
from app.models import TextAIReflection, User
from app.schemas import TextAIReflectionCreate, TextAIReflectionRead

# NEW: OpenAI imports
import os
import json
import logging
from dotenv import load_dotenv, find_dotenv

# Load environment variables from a local .env file if present
load_dotenv(find_dotenv())

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/text-ai", tags=["Text AI Mentor"])

# ------------------------------------------------------------------
# 🧠 OpenAI Client
# ------------------------------------------------------------------

# Reads key from environment variable OPENAI_API_KEY
# - Locally:  export OPENAI_API_KEY="sk-...."
# - Vercel:   set it in Project → Settings → Environment Variables
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key) if OpenAI and openai_api_key else None
if not client:
    missing = "OpenAI package" if not OpenAI else "OPENAI_API_KEY"
    logger.warning("Text AI mentor running in fallback mode (missing %s).", missing)


# ------------------------------------------------------------------
# 🧠 Helper — AI Logic (OpenAI + safe fallback)
# ------------------------------------------------------------------

def generate_ai_feedback(reflection_text: str) -> dict:
    """
    Generate feedback, summary, and XP reward using OpenAI.
    Falls back to simple heuristic if key is missing or API fails.
    Returns a dict: { "feedback": str, "summary": str, "xp_reward": int }
    """

    # If no key is configured, fall back to the old mock logic
    if not client:
        return _mock_ai_feedback(reflection_text)

    try:
        # Ask OpenAI to respond in JSON so we can parse it reliably
        system_prompt = (
            "You are a friendly study mentor for students using a gamified app. "
            "Given the student's reflection about their study session, "
            "return a SHORT feedback message, a one-sentence summary, "
            "and an integer XP reward between 5 and 25.\n\n"
            "Respond ONLY in JSON with this exact shape:\n"
            "{\n"
            '  "feedback": "string",\n'
            '  "summary": "string",\n'
            '  "xp_reward": 10\n'
            "}"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": reflection_text},
            ],
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        feedback = data.get("feedback") or "Keep going – each reflection helps you improve."
        summary = data.get("summary") or (
            reflection_text[:120] + "..." if len(reflection_text) > 120 else reflection_text
        )

        xp_reward = data.get("xp_reward", 10)
        try:
            xp_reward = int(xp_reward)
        except (ValueError, TypeError):
            xp_reward = 10

        # clamp XP to reasonable range
        xp_reward = max(5, min(25, xp_reward))

        return {"feedback": feedback, "summary": summary, "xp_reward": xp_reward}

    except Exception as e:
        # If OpenAI fails for any reason, do NOT crash the endpoint.
        # Fallback to simple heuristic logic.
        return _mock_ai_feedback(reflection_text)


def _mock_ai_feedback(reflection_text: str) -> dict:
    """
    Simple heuristic fallback when OpenAI is not available.
    (Your previous mock logic, kept as backup.)
    """
    text = reflection_text.lower()

    if any(word in text for word in ["tired", "hard", "struggle", "stuck"]):
        feedback = "It sounds like you faced challenges today — remember, progress is built through persistence."
    elif any(word in text for word in ["happy", "productive", "focused", "good", "great"]):
        feedback = "Fantastic work! Keep maintaining that focused mindset."
    else:
        feedback = "Keep reflecting — awareness is the key to consistent improvement."

    summary = (
        reflection_text[:120] + "..."
        if len(reflection_text) > 120
        else reflection_text
    )

    xp_reward = 10  # default XP for completing a reflection

    return {"feedback": feedback, "summary": summary, "xp_reward": xp_reward}


# ------------------------------------------------------------------
# 📘 ROUTES
# ------------------------------------------------------------------


@router.post("/", response_model=TextAIReflectionRead)
async def add_reflection(
    request: Request,
    data: TextAIReflectionCreate | dict | None = Body(default=None),
    user: str | None = None,
    text: str | None = None,
):
    """
    Add a new text reflection entry and analyze it using AI feedback logic.
    Returns feedback, summary, and XP reward.
    """
    # Accept both JSON body and query/form fallbacks to avoid 422s from clients
    incoming: dict = {}
    if isinstance(data, TextAIReflectionCreate):
        incoming.update(data.model_dump(exclude_none=True))
    elif isinstance(data, dict):
        incoming.update(data)
    else:
        try:
            incoming.update(await request.json())
        except Exception:
            try:
                form_data = await request.form()
                incoming.update(form_data)
            except Exception:
                pass

    username = incoming.get("user") or incoming.get("username") or user
    reflection_text = (
        incoming.get("reflection_text")
        or incoming.get("reflectionText")
        or incoming.get("text")
        or incoming.get("reflection")
        or text
    )

    if not username:
        raise HTTPException(status_code=400, detail="user is required.")
    if not reflection_text:
        raise HTTPException(status_code=400, detail="reflection_text is required.")

    with Session(engine) as session:
        user_exists = session.exec(select(User).where(User.username == username)).first()
        if not user_exists:
            raise HTTPException(status_code=404, detail="User not found. Please register first.")

        # Step 1: Generate AI feedback and summary (OpenAI + fallback)
        ai_result = generate_ai_feedback(str(reflection_text))
        reflection_date = incoming.get("date") or (data.date if data else None) or datetime.utcnow()

        # Step 2: Create and save new record
        reflection = TextAIReflection(
            user=username,
            date=reflection_date,
            reflection_text=str(reflection_text),
            ai_feedback=ai_result["feedback"],
            summary=ai_result["summary"],
            xp_reward=ai_result["xp_reward"],
        )

        session.add(reflection)
        session.commit()
        session.refresh(reflection)

        return reflection


@router.get("/", response_model=list[TextAIReflectionRead])
def list_reflections(user: str):
    """
    Get all text reflections submitted by a specific user.
    """
    with Session(engine) as session:
        user_exists = session.exec(select(User).where(User.username == user)).first()
        if not user_exists:
            raise HTTPException(status_code=404, detail="User not found. Please register first.")

        reflections = session.exec(
            select(TextAIReflection).where(TextAIReflection.user == user)
        ).all()
        if not reflections:
            raise HTTPException(status_code=404, detail="No reflections found for this user.")
        return reflections


@router.get("/{reflection_id}", response_model=TextAIReflectionRead)
def get_reflection(reflection_id: int):
    """
    Retrieve a specific reflection by ID.
    """
    with Session(engine) as session:
        reflection = session.get(TextAIReflection, reflection_id)
        if not reflection:
            raise HTTPException(status_code=404, detail="Reflection not found.")
        return reflection


@router.delete("/{reflection_id}")
def delete_reflection(reflection_id: int):
    """
    Delete a specific text reflection entry.
    """
    with Session(engine) as session:
        reflection = session.get(TextAIReflection, reflection_id)
        if not reflection:
            raise HTTPException(status_code=404, detail="Reflection not found.")
        session.delete(reflection)
        session.commit()
        return {"message": f"Reflection {reflection_id} deleted successfully."}
