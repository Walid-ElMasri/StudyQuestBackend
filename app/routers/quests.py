from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from datetime import datetime

from app.database import engine
from app.models import Quest, User, UserQuest
from app.schemas import QuestCreate

router = APIRouter(prefix="/quests", tags=["Quests & Levels"])


# ---------- Helper ----------
def calculate_level(total_xp: int) -> int:
    """Simple leveling rule: +1 level every 100 XP."""
    return (total_xp // 100) + 1


# ---------- ROUTES ----------
@router.get("/")
def list_quests():
    """List all quests."""
    with Session(engine) as session:
        quests = session.exec(select(Quest)).all()
        if not quests:
            raise HTTPException(status_code=404, detail="No quests found.")
        return quests


@router.get("/available")
def list_available_quests(user: str):
    """List quests the user hasn't completed yet."""
    with Session(engine) as session:
        user_obj = session.exec(select(User).where(User.username == user)).first()
        if not user_obj:
            raise HTTPException(status_code=404, detail="User not found.")

        all_quests = session.exec(select(Quest)).all()
        completed_ids = [
            uq.quest_id
            for uq in session.exec(select(UserQuest).where(UserQuest.user == user)).all()
        ]

        available = [q for q in all_quests if q.id not in completed_ids]

        if not available:
            return {"message": "You’ve completed all available quests. Well done!"}

        return {"available_quests": available, "remaining": len(available)}


@router.post("/")
def create_quest(data: QuestCreate):
    """Create a new quest."""
    with Session(engine) as session:
        quest = Quest(
            name=data.name,
            description=data.description,
            difficulty=data.difficulty,
            xp_reward=data.xp_reward,
            is_daily=data.is_daily,
            deadline=data.deadline,
            quest_type=data.quest_type,  # ⬅️ IMPORTANT
        )
        session.add(quest)
        session.commit()
        session.refresh(quest)
        return {"message": "Quest created successfully.", "quest": quest}



@router.post("/complete/{quest_id}")
def complete_quest(user: str, quest_id: int):
    """
    Mark a quest as completed and reward XP.

    Called from Android as:
    POST /quests/complete/{quest_id}?user=username
    """
    with Session(engine) as session:
        quest = session.get(Quest, quest_id)
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found.")

        user_obj = session.exec(
            select(User).where(User.username == user)
        ).first()
        if not user_obj:
            raise HTTPException(status_code=404, detail="User not found.")

        # Check if already completed
        completed = session.exec(
            select(UserQuest).where(
                UserQuest.user == user, UserQuest.quest_id == quest_id
            )
        ).first()
        if completed:
            raise HTTPException(status_code=400, detail="Quest already completed.")

        # Reward XP
        user_obj.total_xp += quest.xp_reward

        # Compute level from total XP (even if User model has no current_level field)
        new_level = calculate_level(user_obj.total_xp)

        # Only persist current_level if the model actually has that field
        if hasattr(type(user_obj), "current_level"):
            user_obj.current_level = new_level

        # Save completion record
        user_quest = UserQuest(
            user=user,
            quest_id=quest_id,
            xp_earned=quest.xp_reward,
        )
        session.add(user_quest)
        session.add(user_obj)
        session.commit()

        return {
            "message": f"Quest '{quest.name}' completed!",
            "earned_xp": quest.xp_reward,
            "total_xp": user_obj.total_xp,
            "current_level": new_level,
        }

@router.get("/levels")
def get_level_info(user: str):
    """Get user's level and XP progress."""
    with Session(engine) as session:
        user_obj = session.exec(select(User).where(User.username == user)).first()
        if not user_obj:
            raise HTTPException(status_code=404, detail="User not found.")

        # Safely read total XP (or default 0)
        total_xp = getattr(user_obj, "total_xp", 0)

        # Use stored current_level if it exists, otherwise compute it
        stored_level = getattr(user_obj, "current_level", None)
        if stored_level is not None:
            current_level = stored_level
        else:
            current_level = calculate_level(total_xp)

        next_level_xp = current_level * 100
        xp_to_next = next_level_xp - total_xp

        return {
            "user": user,
            "current_level": current_level,
            "total_xp": total_xp,
            "xp_to_next_level": max(0, xp_to_next),
        }
