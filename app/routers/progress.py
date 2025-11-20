from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from datetime import datetime, timedelta

from app.database import engine
from app.models import Progress, User
from app.schemas import ProgressCreate

router = APIRouter(prefix="/progress", tags=["Progress Tracking"])


# ---------- Helper Functions ----------
def _ensure_user_exists(session: Session, username: str) -> User:
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please register first.")
    return user

def calculate_xp(duration_minutes: int) -> int:
    """Give 10 XP for every 25 minutes studied."""
    return (duration_minutes // 25) * 10


def calculate_streak(latest_session_date: datetime, all_sessions: list[Progress]) -> int:
    """Calculate how many consecutive days the user has studied."""
    dates = sorted({p.date.date() for p in all_sessions})
    if not dates:
        return 0

    streak = 1
    for i in range(len(dates) - 1, 0, -1):
        if (dates[i] - dates[i - 1]).days == 1:
            streak += 1
        else:
            break
    return streak


# ---------- Routes ----------

@router.get("/")
def list_progress(user: str):
    """Return all progress sessions for a specific user."""
    with Session(engine) as session:
        _ensure_user_exists(session, user)
        progress = session.exec(select(Progress).where(Progress.user == user)).all()
        if not progress:
            raise HTTPException(status_code=404, detail="No progress found for this user.")
        return progress


@router.post("/")
def add_progress(data: ProgressCreate):
    """
    Add a new progress entry.
    - Calculates XP based on duration.
    - Computes user's current streak.
    """
    with Session(engine) as session:
        _ensure_user_exists(session, data.user)
        duration = data.duration_minutes or 0
        xp = calculate_xp(duration)
        progress_date = data.date or datetime.utcnow()
        new_entry = Progress(
            user=data.user,
            date=progress_date,
            duration_minutes=duration,
            xp_gained=xp,
            reflection=data.reflection,
        )

        session.add(new_entry)
        session.commit()
        session.refresh(new_entry)

        # Retrieve all user sessions to recalculate streak
        user_sessions = session.exec(select(Progress).where(Progress.user == data.user)).all()
        streak = calculate_streak(progress_date, user_sessions)

        return {
            "message": "Progress added successfully.",
            "session": new_entry,
            "streak_days": streak,
        }


@router.get("/stats")
def get_statistics(user: str):
    """
    Returns user's overall progress statistics:
    - Total study sessions
    - Total XP
    - Average session duration
    - Current streak
    """
    with Session(engine) as session:
        _ensure_user_exists(session, user)
        sessions = session.exec(select(Progress).where(Progress.user == user)).all()

        if not sessions:
            raise HTTPException(status_code=404, detail="No progress data found.")

        total_xp = sum(s.xp_gained for s in sessions)
        total_sessions = len(sessions)
        avg_duration = sum(s.duration_minutes for s in sessions) / total_sessions

        streak = calculate_streak(datetime.now(), sessions)

        return {
            "user": user,
            "total_sessions": total_sessions,
            "total_xp": total_xp,
            "average_duration_minutes": round(avg_duration, 2),
            "current_streak_days": streak,
        }


@router.delete("/{progress_id}")
def delete_progress(progress_id: int):
    """Allow user to delete a progress entry."""
    with Session(engine) as session:
        progress = session.get(Progress, progress_id)
        if not progress:
            raise HTTPException(status_code=404, detail="Progress entry not found.")
        session.delete(progress)
        session.commit()
        return {"message": f"Progress entry {progress_id} deleted successfully."}
