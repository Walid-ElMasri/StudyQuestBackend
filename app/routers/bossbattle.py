from fastapi import APIRouter, HTTPException, Body, Request
from pydantic import BaseModel, Field, AliasChoices
from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from app.database import engine
from app.models import BossBattle, User

# Optional OpenAI support for dynamic questions
import os
import json
import logging
from dotenv import load_dotenv, find_dotenv

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

load_dotenv(find_dotenv())
logger = logging.getLogger(__name__)

openai_api_key = os.getenv("OPENAI_API_KEY")
ai_client = OpenAI(api_key=openai_api_key) if (OpenAI and openai_api_key) else None


router = APIRouter(prefix="/boss", tags=["Boss Battle"])


_ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}


_QUESTIONS = [
    {
        "question": "What is the time complexity of binary search?",
        "choices": ["O(n)", "O(log n)", "O(n log n)", "O(1)"],
        "answer_idx": 1,
    },
    {
        "question": "Which HTTP method is idempotent?",
        "choices": ["POST", "PUT", "PATCH", "CONNECT"],
        "answer_idx": 1,
    },
    {
        "question": "What does SQL stand for?",
        "choices": [
            "Simple Query Language",
            "Structured Query Language",
            "Sequential Query Language",
            "System Query Language",
        ],
        "answer_idx": 1,
    },
    {
        "question": "Which data structure uses FIFO order?",
        "choices": ["Stack", "Queue", "Tree", "Heap"],
        "answer_idx": 1,
    },
    {
        "question": "Which status code means 'Not Found'?",
        "choices": ["200", "301", "404", "500"],
        "answer_idx": 2,
    },
]

def _generate_ai_questions(total: int) -> List[Dict[str, Any]]:
    """Try to generate multiple-choice questions with OpenAI; fallback to static set."""
    if not ai_client:
        return _QUESTIONS[:total]

    prompt = (
        "Create a short quiz for coding students. "
        "Return EXACTLY this JSON shape: "
        '{"questions":[{"question":"string","choices":["A","B","C","D"],"answer_idx":0}]}. '
        "Use clear, beginner-friendly tech topics. Ensure four choices and answer_idx points to the correct choice."
    )
    try:
        resp = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Generate {total} questions."},
            ],
        )
        data = json.loads(resp.choices[0].message.content)
        questions = data.get("questions", []) if isinstance(data, dict) else []
        # Basic validation
        cleaned = []
        for q in questions:
            if not isinstance(q, dict):
                continue
            question = q.get("question")
            choices = q.get("choices")
            answer_idx = q.get("answer_idx")
            if question and isinstance(choices, list) and len(choices) >= 2:
                try:
                    answer_idx = int(answer_idx)
                except Exception:
                    answer_idx = 0
                cleaned.append({"question": question, "choices": choices[:4], "answer_idx": answer_idx})
            if len(cleaned) >= total:
                break
        if cleaned:
            return cleaned[:total]
    except Exception as e:
        logger.warning("AI question generation failed, falling back to static set: %s", e)
    return _QUESTIONS[:total]


class StartRequest(BaseModel):
    user: str = Field(validation_alias=AliasChoices("user", "username"))
    difficulty: Optional[str] = "medium"  # easy | medium | hard
    total_questions: Optional[int] = Field(
        default=5, validation_alias=AliasChoices("total_questions", "totalQuestions")
    )
    time_limit_seconds: Optional[int] = Field(
        default=180, validation_alias=AliasChoices("time_limit_seconds", "timeLimitSeconds")
    )  # timer per session


class AnswerRequest(BaseModel):
    user: str = Field(validation_alias=AliasChoices("user", "username"))
    choice_idx: int = Field(validation_alias=AliasChoices("choice_idx", "choiceIdx", "choice"))


def _ensure_user_exists(username: str) -> None:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found. Please register first.")


def _get_session(user: str) -> Dict[str, Any]:
    sess = _ACTIVE_SESSIONS.get(user)
    if not sess:
        raise HTTPException(status_code=404, detail="No active boss battle. Start one first.")
    return sess


def _time_remaining(sess: Dict[str, Any]) -> int:
    now = datetime.utcnow()
    elapsed = (now - sess["started_at"]).total_seconds()
    remaining = max(0, int(sess["time_limit_seconds"] - elapsed))
    return remaining


def _end_session(user: str, status: str) -> Dict[str, Any]:
    sess = _ACTIVE_SESSIONS.get(user)
    if not sess:
       
        return {"message": "Session closed."}

    xp_reward = sess["score"] * 20

    with Session(engine) as db:
        user_obj = db.exec(select(User).where(User.username == user)).first()
        if user_obj:
            user_obj.total_xp = (user_obj.total_xp or 0) + xp_reward

        record = BossBattle(
            user=user,
            date=datetime.utcnow(),
            score=sess["score"],
            total_questions=sess["total_questions"],
            xp_reward=xp_reward,
            difficulty=sess["difficulty"],
            completed=True,
        )
        db.add(record)
        db.add(user_obj) if user_obj else None
        db.commit()
        db.refresh(record)

    result = {
        "status": status,
        "score": sess["score"],
        "xp_reward": xp_reward,
        "total_questions": sess["total_questions"],
        "lives_remaining": sess["lives"],
        "ended": True,
    }
    _ACTIVE_SESSIONS.pop(user, None)
    return result

@router.get("/")
def info():
    return {
        "message": "Boss Battle API ready",
        "routes": {
            "start": "POST /boss/start",
            "question": "GET /boss/question?user=<username>",
            "answer": "POST /boss/answer",
            "status": "GET /boss/status?user=<username>",
            "forfeit": "POST /boss/forfeit?user=<username>",
        },
    }


@router.post("/start")
def start_boss_battle(payload: StartRequest):
    """
    Start a new boss battle session.
    - Initializes timer, 3 lives, score 0
    - Limits questions to `total_questions` from the bank
    - Difficulty is informational for now
    """
    _ensure_user_exists(payload.user)

    if payload.total_questions < 1:
        raise HTTPException(status_code=400, detail="total_questions must be >= 1")

    if payload.user in _ACTIVE_SESSIONS:
        raise HTTPException(status_code=409, detail="An active boss battle already exists.")

    total = min(payload.total_questions, len(_QUESTIONS)) if payload.total_questions else len(_QUESTIONS)
    questions = _generate_ai_questions(total)
    _ACTIVE_SESSIONS[payload.user] = {
        "difficulty": payload.difficulty or "medium",
        "started_at": datetime.utcnow(),
        "time_limit_seconds": payload.time_limit_seconds or 180,
        "lives": 3,
        "score": 0,
        "index": 0,
        "total_questions": total,
        "questions": questions,
    }

    q = questions[0]
    return {
        "message": "Boss battle started.",
        "user": payload.user,
        "timer_seconds": payload.time_limit_seconds or 180,
        "lives": 3,
        "current_question": {
            "number": 1,
            "total": total,
            "question": q["question"],
            "choices": q["choices"],
        },
    }


@router.get("/question")
def get_current_question(user: str):
    sess = _get_session(user)

    if _time_remaining(sess) == 0:
        return _end_session(user, status="timeout")
    if sess["lives"] <= 0:
        return _end_session(user, status="out_of_lives")

    idx = sess["index"]
    if idx >= sess["total_questions"]:
        return _end_session(user, status="completed")

    q = sess["questions"][idx]
    return {
        "question": q["question"],
        "choices": q["choices"],
        "number": idx + 1,
        "total": sess["total_questions"],
        "lives": sess["lives"],
        "timer_remaining": _time_remaining(sess),
        "score": sess["score"],
    }


@router.post("/answer")
async def submit_answer(
    request: Request,
    payload: AnswerRequest | None = Body(default=None),
    user: str | None = None,
    choice_idx: int | None = None,
):
    # Accept JSON body, form, or query params to minimize 422s.
    if payload:
        username = payload.user
        choice = payload.choice_idx
    else:
        body: dict = {}
        try:
            body.update(await request.json())
        except Exception:
            try:
                form_data = await request.form()
                body.update(form_data)
            except Exception:
                pass
        username = body.get("user") or body.get("username") or user
        choice_raw = body.get("choice_idx") or body.get("choiceIdx") or body.get("choice") or choice_idx
        try:
            choice = int(choice_raw) if choice_raw is not None else None
        except Exception:
            choice = None

    if not username:
        raise HTTPException(status_code=400, detail="user is required.")
    if choice is None:
        raise HTTPException(status_code=400, detail="choice_idx is required.")

    sess = _get_session(username)


    if _time_remaining(sess) == 0:
        return _end_session(username, status="timeout")

    idx = sess["index"]
    if idx >= sess["total_questions"]:
        return _end_session(username, status="completed")

    q = sess["questions"][idx]
    correct_idx = q["answer_idx"]
    is_correct = choice == correct_idx

    if is_correct:
        sess["score"] += 1
        feedback = "Correct! +20 XP"
    else:
        sess["lives"] -= 1
        feedback = "Wrong! -1 life"

    sess["index"] += 1

    if sess["lives"] <= 0:
        return _end_session(username, status="out_of_lives")

    if sess["index"] >= sess["total_questions"]:
        return _end_session(username, status="completed")

    next_q = sess["questions"][sess["index"]]
    return {
        "correct": is_correct,
        "feedback": feedback,
        "lives": sess["lives"],
        "score": sess["score"],
        "timer_remaining": _time_remaining(sess),
        "next_question": {
            "number": sess["index"] + 1,
            "total": sess["total_questions"],
            "question": next_q["question"],
            "choices": next_q["choices"],
        },
    }


@router.get("/status")
def get_status(user: str):
    sess = _get_session(user)
    remaining = _time_remaining(sess)
    if remaining == 0:
        return _end_session(user, status="timeout")
    status = {
        "lives": sess["lives"],
        "score": sess["score"],
        "question_number": min(sess["index"] + 1, sess["total_questions"]),
        "total_questions": sess["total_questions"],
        "timer_remaining": remaining,
        "completed": False,
    }
    return status


@router.post("/forfeit")
def forfeit(user: str):
    _ = _get_session(user)
    return _end_session(user, status="forfeit")
