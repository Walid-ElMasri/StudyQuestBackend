from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ------------------------------------------------------------------
# 🔹 Common User Schema
# ------------------------------------------------------------------
class UserBase(BaseModel):
    username: str
    email: Optional[str] = None

class UserCreate(UserBase):
    total_xp: int = 0

class UserRead(UserBase):
    id: int
    join_date: datetime
    total_xp: int

    class Config:
        orm_mode = True


# ------------------------------------------------------------------
# 🔹 Walid — Progress Tracking
# ------------------------------------------------------------------
class ProgressBase(BaseModel):
    user: str
    date: datetime
    duration_minutes: int
    reflection: Optional[str] = None

class ProgressCreate(ProgressBase):
    pass

class ProgressRead(ProgressBase):
    id: int
    xp_gained: int

    class Config:
        orm_mode = True


# ------------------------------------------------------------------
# 🔹 Aya — Quests & Levels
# ------------------------------------------------------------------

class QuestBase(BaseModel):
    name: str
    description: str
    difficulty: str
    xp_reward: int
    completed: bool = False
    assigned_to: Optional[str] = None
    is_daily: bool = False
    deadline: Optional[datetime] = None

class QuestCreate(QuestBase):
    pass

class QuestRead(QuestBase):
    id: int

    class Config:
        orm_mode = True


class LevelBase(BaseModel):
    user: str
    current_level: int = 1
    total_xp: int = 0
    xp_to_next: int = 100

class LevelRead(LevelBase):
    id: int

    class Config:
        orm_mode = True


# ------------------------------------------------------------------
# 🔹 Nour — Cosmetics & Rewards
# ------------------------------------------------------------------
class AvatarBase(BaseModel):
    user: str
    avatar_name: Optional[str] = None
    hairstyle: Optional[str] = None
    outfit: Optional[str] = None
    accessory: Optional[str] = None
    theme: str = "default"

class AvatarCreate(AvatarBase):
    pass

class AvatarRead(AvatarBase):
    id: int

    class Config:
        orm_mode = True


class BadgeBase(BaseModel):
    name: str
    description: str
    xp_required: int
    icon_url: Optional[str] = None

class BadgeCreate(BadgeBase):
    pass

class BadgeRead(BadgeBase):
    id: int

    class Config:
        orm_mode = True


# ------------------------------------------------------------------
# 🔹 All Team — Text AI Mentor
# ------------------------------------------------------------------
class TextAIReflectionBase(BaseModel):
    user: str
    date: datetime
    reflection_text: str

class TextAIReflectionCreate(TextAIReflectionBase):
    pass

class TextAIReflectionRead(TextAIReflectionBase):
    id: int
    ai_feedback: Optional[str] = None
    summary: Optional[str] = None
    xp_reward: int = 0

    class Config:
        orm_mode = True


# ------------------------------------------------------------------
# 🔹 Lynn — Daily Boss Battle
# ------------------------------------------------------------------
class BossBattleBase(BaseModel):
    user: str
    date: datetime
    score: int = 0
    total_questions: int = 5
    xp_reward: int = 0
    difficulty: str = "medium"
    completed: bool = False

class BossBattleCreate(BossBattleBase):
    pass

class BossBattleRead(BossBattleBase):
    id: int

    class Config:
        orm_mode = True


# ------------------------------------------------------------------
# 🔹 Mohamad — Social Features
# ------------------------------------------------------------------
class FriendBase(BaseModel):
    user: str
    friend_username: str
    since: Optional[datetime] = None
    status: str = "accepted"

class FriendCreate(FriendBase):
    pass

class FriendRead(FriendBase):
    id: int

    class Config:
        orm_mode = True


class LeaderboardBase(BaseModel):
    user: str
    total_xp: int = 0
    current_streak: int = 0
    last_updated: datetime = datetime.utcnow()

class LeaderboardRead(LeaderboardBase):
    id: int

    class Config:
        orm_mode = True
