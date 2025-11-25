from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select, SQLModel
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
            return {"message": "No quests found."}
        return quests


@router.get("/available")
def list_available_quests(user: str):
    """List quests the user hasn't completed yet."""
    try:
        with Session(engine) as session:
            # Fetch user
            user_obj = session.exec(
                select(User).where(User.username == user)
            ).first()
            if not user_obj:
                raise HTTPException(status_code=404, detail="User not found.")

            # All quests
            all_quests = session.exec(select(Quest)).all()

            # Get completed quest IDs for this username
            completed_rows = session.exec(
                select(UserQuest).where(UserQuest.user == user)
            ).all()
            completed_ids = [uq.quest_id for uq in completed_rows]

            # Filter available quests
            available = [q for q in all_quests if q.id not in completed_ids]

            if not available:
                return {"message": "You’ve completed all available quests. Well done!"}

            return {"available_quests": available, "remaining": len(available)}
    except Exception as e:
        # TEMP: show the real error so we can fix it
        raise HTTPException(
            status_code=500,
            detail=f"Error in /quests/available: {e}"
        )



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
            quest_type=data.quest_type,
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

        # Check completion for this username
        completed = session.exec(
            select(UserQuest).where(
                UserQuest.user == user,
                UserQuest.quest_id == quest_id
            )
        ).first()
        if completed:
            raise HTTPException(status_code=400, detail="Quest already completed.")

        # Reward XP
        user_obj.total_xp += quest.xp_reward
        new_level = calculate_level(user_obj.total_xp)

        if hasattr(type(user_obj), "current_level"):
            user_obj.current_level = new_level

        # Save completion record (user is a string, like before)
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
        user_obj = session.exec(
            select(User).where(User.username == user)
        ).first()
        if not user_obj:
            raise HTTPException(status_code=404, detail="User not found.")

        total_xp = getattr(user_obj, "total_xp", 0)
        stored_level = getattr(user_obj, "current_level", None)

        current_level = stored_level if stored_level is not None else calculate_level(total_xp)

        next_level_xp = current_level * 100
        xp_to_next = next_level_xp - total_xp

        return {
            "user": user,
            "current_level": current_level,
            "total_xp": total_xp,
            "xp_to_next_level": max(0, xp_to_next),
        }


# ---------- TEMPORARY DB INIT ENDPOINT ----------
@router.get("/debug/init-db")
def init_db():
    """Initialize database tables (useful for Vercel). Call once after deploy."""
    SQLModel.metadata.create_all(engine)
    return {"message": "DB initialized"}
