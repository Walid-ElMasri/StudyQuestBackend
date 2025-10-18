from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime


# ------------------------------------------------------------------
# 🔹 Common User Model
# ------------------------------------------------------------------
class User(SQLModel, table=True):
    """
    Represents a StudyQuest user.
    Used as the base for all other features.
    """
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: Optional[str] = None
    join_date: datetime = Field(default_factory=datetime.utcnow)
    total_xp: int = 0


# ------------------------------------------------------------------
# 🔹 Walid — Progress Tracking
# ------------------------------------------------------------------
class Progress(SQLModel, table=True):
    """
    Stores user study sessions and reflection data.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user: str = Field(index=True)
    date: datetime = Field(default_factory=datetime.utcnow)
    duration_minutes: int
    xp_gained: int = 0
    reflection: Optional[str] = None


# ------------------------------------------------------------------
# 🔹 Aya — Quests & Levels
# ------------------------------------------------------------------
class Quest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    difficulty: str  # "Easy", "Medium", "Hard"
    xp_reward: int
    completed: bool = False
    assigned_to: Optional[str] = Field(default=None, foreign_key="user.username")
    is_daily: bool = False
    deadline: Optional[datetime] = None


class UserQuest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user: str = Field(index=True, foreign_key="user.username")
    quest_id: int = Field(foreign_key="quest.id")
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    xp_earned: int = 0


class Level(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user: str = Field(index=True)
    current_level: int = 1
    total_xp: int = 0
    xp_to_next: int = 100

# ------------------------------------------------------------------
# 🔹 Nour — Cosmetics & Rewards
# ------------------------------------------------------------------
class Avatar(SQLModel, table=True):
    """
    Customizable avatar (theme, outfit, accessories).
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user: str = Field(index=True)
    avatar_name: Optional[str] = None
    hairstyle: Optional[str] = None
    outfit: Optional[str] = None
    accessory: Optional[str] = None
    theme: str = "default"  # e.g., "dark", "fantasy", "neon"


class Badge(SQLModel, table=True):
    """
    Achievements and badges unlocked by users.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    xp_required: int
    icon_url: Optional[str] = None


# ------------------------------------------------------------------
# 🔹 All Team — Text AI Mentor
# ------------------------------------------------------------------
class TextAIReflection(SQLModel, table=True):
    """
    Stores text reflections analyzed by the AI mentor.
    Used by all team members to provide feedback and summaries.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user: str = Field(index=True)
    date: datetime = Field(default_factory=datetime.utcnow)
    reflection_text: str
    ai_feedback: Optional[str] = None
    summary: Optional[str] = None
    xp_reward: int = 0


# ------------------------------------------------------------------
# 🔹 Lynn — Daily Boss Battle
# ------------------------------------------------------------------
class BossBattle(SQLModel, table=True):
    """
    End-of-day AI quiz challenge for XP and leaderboard ranking.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user: str = Field(index=True)
    date: datetime = Field(default_factory=datetime.utcnow)
    score: int = 0
    total_questions: int = 5
    xp_reward: int = 0
    difficulty: str = "medium"
    completed: bool = False


# ------------------------------------------------------------------
# 🔹 Mohamad — Social Features
# ------------------------------------------------------------------
class Friend(SQLModel, table=True):
    """
    Represents friendship between users.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user: str = Field(index=True)
    friend_username: str = Field(index=True)
    since: datetime = Field(default_factory=datetime.utcnow)
    status: str = "accepted"  # pending | accepted | blocked


class Leaderboard(SQLModel, table=True):
    """
    Tracks top users by total XP and streak.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user: str = Field(index=True)
    total_xp: int = 0
    current_streak: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)
