from pydantic import BaseModel, ConfigDict, Field, AliasChoices
from typing import Optional, List
from datetime import datetime

# Shared config to enable attribute-based (ORM) reading in Pydantic v2.
common_config = ConfigDict(from_attributes=True, populate_by_name=True)

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

    model_config = common_config


# ------------------------------------------------------------------
# 🔹 Walid — Progress Tracking
# ------------------------------------------------------------------
class ProgressBase(BaseModel):
    user: str = Field(validation_alias=AliasChoices("user", "username"))
    date: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(
        default=None, validation_alias=AliasChoices("duration_minutes", "durationMinutes", "duration")
    )
    reflection: Optional[str] = Field(default=None, validation_alias=AliasChoices("reflection", "note", "text"))

class ProgressCreate(ProgressBase):
    pass

class ProgressRead(ProgressBase):
    id: int
    xp_gained: int

    model_config = common_config


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

    model_config = common_config


class LevelBase(BaseModel):
    user: str
    current_level: int = 1
    total_xp: int = 0
    xp_to_next: int = 100

class LevelRead(LevelBase):
    id: int

    model_config = common_config


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

    model_config = common_config


class BadgeBase(BaseModel):
    name: str
    description: str
    xp_required: int
    icon_url: Optional[str] = None

class BadgeCreate(BadgeBase):
    pass

class BadgeRead(BadgeBase):
    id: int

    model_config = common_config


# ------------------------------------------------------------------
# 🔹 All Team — Text AI Mentor
# ------------------------------------------------------------------
class TextAIReflectionBase(BaseModel):
    user: str = Field(validation_alias=AliasChoices("user", "username"))
    date: Optional[datetime] = None
    reflection_text: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("reflection_text", "reflectionText", "text", "reflection")
    )

class TextAIReflectionCreate(TextAIReflectionBase):
    user: str
    reflection_text: str
    date: Optional[datetime] = None

class TextAIReflectionRead(TextAIReflectionBase):
    id: int
    ai_feedback: Optional[str] = None
    summary: Optional[str] = None
    xp_reward: int = 0

    model_config = common_config


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

    model_config = common_config


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

    model_config = common_config


class LeaderboardBase(BaseModel):
    user: str
    total_xp: int = 0
    current_streak: int = 0
    last_updated: datetime = datetime.utcnow()

class LeaderboardRead(LeaderboardBase):
    id: int

    model_config = common_config
