from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, select
from datetime import datetime
from typing import List

from app.database import engine
from app.models import User, Friend, Leaderboard
from app.schemas import FriendCreate, FriendRead, LeaderboardRead

router = APIRouter(prefix="/social", tags=["Social Features"])

# ------------------------------------------------------------------
# 🔹 Helper Functions
# ------------------------------------------------------------------

def get_user(session: Session, username: str) -> User:
    """Fetch a user by username or raise 404."""
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found.")
    return user


# ------------------------------------------------------------------
# 🔹 Friend System
# ------------------------------------------------------------------

@router.post("/friends/add", response_model=FriendRead)
def add_friend(request: FriendCreate):
    """
    Send a friend request from one user to another.
    If accepted immediately, status will be 'accepted'.
    """
    with Session(engine) as session:
        sender = get_user(session, request.user)
        receiver = get_user(session, request.friend_username)

        # Check if friendship already exists
        existing = session.exec(
            select(Friend).where(
                ((Friend.user == request.user) & (Friend.friend_username == request.friend_username))
                | ((Friend.user == request.friend_username) & (Friend.friend_username == request.user))
            )
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Friendship already exists or pending.")

        friendship = Friend(
            user=request.user,
            friend_username=request.friend_username,
            status="pending",
            since=datetime.utcnow()
        )
        session.add(friendship)
        session.commit()
        session.refresh(friendship)
        return friendship


@router.patch("/friends/respond", response_model=FriendRead)
def respond_to_request(
    user: str = Query(...),
    friend_username: str = Query(...),
    action: str = Query(..., regex="^(accept|decline|block)$")
):
    """
    Respond to a friend request.
    Actions: 'accept', 'decline', 'block'
    """
    with Session(engine) as session:
        request_obj = session.exec(
            select(Friend).where(
                (Friend.user == friend_username) & (Friend.friend_username == user)
            )
        ).first()

        if not request_obj:
            raise HTTPException(status_code=404, detail="Friend request not found.")

        if action == "accept":
            request_obj.status = "accepted"
            request_obj.since = datetime.utcnow()
        elif action == "decline":
            session.delete(request_obj)
            session.commit()
            return {"message": "Friend request declined and removed."}
        elif action == "block":
            request_obj.status = "blocked"

        session.add(request_obj)
        session.commit()
        session.refresh(request_obj)
        return request_obj


@router.get("/friends/list", response_model=List[FriendRead])
def list_friends(user: str):
    """
    List all accepted friends for a given user.
    """
    with Session(engine) as session:
        get_user(session, user)  # validate existence
        results = session.exec(
            select(Friend).where(
                ((Friend.user == user) | (Friend.friend_username == user))
                & (Friend.status == "accepted")
            )
        ).all()
        return results


@router.delete("/friends/remove")
def remove_friend(user: str, friend_username: str):
    """
    Remove a friendship between two users.
    """
    with Session(engine) as session:
        friendship = session.exec(
            select(Friend).where(
                ((Friend.user == user) & (Friend.friend_username == friend_username))
                | ((Friend.user == friend_username) & (Friend.friend_username == user))
            )
        ).first()

        if not friendship:
            raise HTTPException(status_code=404, detail="Friendship not found.")

        session.delete(friendship)
        session.commit()
        return {"message": f"{friend_username} removed from friends."}


# ------------------------------------------------------------------
# 🔹 Leaderboard
# ------------------------------------------------------------------

@router.get("/leaderboard", response_model=List[LeaderboardRead])
def get_leaderboard(limit: int = 10):
    """
    Fetch the top users by XP (and streak if available).
    """
    with Session(engine) as session:
        users = session.exec(select(User).order_by(User.total_xp.desc())).all()
        if not users:
            raise HTTPException(status_code=404, detail="No users found.")

        leaderboard_entries = []
        for rank, user in enumerate(users[:limit], start=1):
            entry = Leaderboard(
                id = rank,
                user=user.username,
                total_xp=user.total_xp,
                current_streak=0,  # placeholder if streak not tracked globally
                last_updated=datetime.utcnow(),
            )
            leaderboard_entries.append(entry)

        return leaderboard_entries


# ------------------------------------------------------------------
# 🔹 Quick Check Endpoint
# ------------------------------------------------------------------

@router.get("/")
def social_root():
    """Landing route for Social Features section."""
    return {
        "message": "Welcome to StudyQuest Social Features 🧩",
        "available_endpoints": {
            "Add Friend": "/social/friends/add",
            "Respond to Request": "/social/friends/respond",
            "List Friends": "/social/friends/list",
            "Remove Friend": "/social/friends/remove",
            "Leaderboard": "/social/leaderboard"
        }
    }
