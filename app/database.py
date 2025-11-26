import os
from datetime import datetime, timedelta

from sqlmodel import SQLModel, Session, create_engine, select

from app.models import (
    Avatar,
    Badge,
    BossBattle,
    Progress,
    Quest,
    TextAIReflection,
    User,
    UserQuest,
)


def _build_engine():
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        if database_url.startswith("postgresqlpsycopg://"):
            database_url = database_url.replace("postgresqlpsycopg://", "postgresql+psycopg://", 1)
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return create_engine(database_url, echo=False)

    sqlite_file_name = "studyquest.db"
    sqlite_url = f"sqlite:///{sqlite_file_name}"
    return create_engine(sqlite_url, echo=False)


engine = _build_engine()


def init_db():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)
    seed_demo_data()


def seed_demo_data() -> None:
    """
    Ensure a ready-to-demo user exists with sample data across features.
    Safe to call repeatedly (idempotent).
    """
    with Session(engine) as session:
        # --- Core user ---
        demo_user = session.exec(select(User).where(User.username == "demo")).first()
        if not demo_user:
            demo_user = User(
                username="demo",
                email="demo@studyquest.app",
                total_xp=0,
            )
            session.add(demo_user)
            session.commit()
            session.refresh(demo_user)

        # --- Progress entries ---
        progress_entries = session.exec(select(Progress).where(Progress.user == "demo")).all()
        if not progress_entries:
            now = datetime.utcnow()
            sample_progress = [
                Progress(
                    user="demo",
                    date=now - timedelta(days=2),
                    duration_minutes=50,
                    xp_gained=20,
                    reflection="Focused on data structures with flashcards.",
                ),
                Progress(
                    user="demo",
                    date=now - timedelta(days=1),
                    duration_minutes=30,
                    xp_gained=10,
                    reflection="Reviewed algorithms cheatsheet before lecture.",
                ),
                Progress(
                    user="demo",
                    date=now,
                    duration_minutes=45,
                    xp_gained=20,
                    reflection="Watched dynamic programming video and took notes.",
                ),
            ]
            session.add_all(sample_progress)

        # --- Quests (library) ---
        quest_catalog = [
            {
                "name": "Morning Focus Sprint",
                "description": "Complete a 45-minute deep work block before noon.",
                "difficulty": "Medium",
                "xp_reward": 40,
                "quest_type": "timer",
            },
            {
                "name": "Flashcard Blitz",
                "description": "Finish 20 spaced-repetition cards.",
                "difficulty": "Easy",
                "xp_reward": 25,
                "quest_type": "flashcards",
            },
            {
                "name": "Weekly Planning",
                "description": "Plan study blocks for the coming week.",
                "difficulty": "Medium",
                "xp_reward": 35,
                "quest_type": "calendar",
            },
        ]
        quest_map: dict[str, Quest] = {}
        for quest_data in quest_catalog:
            existing = session.exec(select(Quest).where(Quest.name == quest_data["name"])).first()
            if not existing:
                existing = Quest(**quest_data)
                session.add(existing)
                session.commit()
                session.refresh(existing)
            quest_map[quest_data["name"]] = existing

        # --- Quest completion for demo ---
        completed_names = ["Morning Focus Sprint", "Flashcard Blitz"]
        for name in completed_names:
            quest = quest_map.get(name)
            if not quest:
                continue
            already_done = session.exec(
                select(UserQuest).where(UserQuest.user == "demo", UserQuest.quest_id == quest.id)
            ).first()
            if not already_done:
                quest.completed = True
                session.add(
                    UserQuest(
                        user="demo",
                        quest_id=quest.id,
                        xp_earned=quest.xp_reward,
                    )
                )
                session.add(quest)

        # --- Avatar ---
        avatar = session.exec(select(Avatar).where(Avatar.user == "demo")).first()
        if not avatar:
            avatar = Avatar(
                user="demo",
                avatar_name="Scholar Nova",
                hairstyle="Short fade",
                outfit="Hoodie + jeans",
                accessory="Headphones",
                theme="neon",
            )
            session.add(avatar)

        # --- Badges library ---
        badges = [
            {"name": "Getting Started", "description": "Log your first study session.", "xp_required": 10},
            {"name": "Consistency Champ", "description": "Maintain a 3-day streak.", "xp_required": 50},
            {"name": "Quest Crusher", "description": "Finish two quests in a week.", "xp_required": 75},
        ]
        for badge_data in badges:
            existing_badge = session.exec(select(Badge).where(Badge.name == badge_data["name"])).first()
            if not existing_badge:
                session.add(Badge(**badge_data))

        # --- Text AI reflections ---
        reflections = session.exec(select(TextAIReflection).where(TextAIReflection.user == "demo")).all()
        if not reflections:
            session.add(
                TextAIReflection(
                    user="demo",
                    date=datetime.utcnow() - timedelta(hours=6),
                    reflection_text="Reviewed linked lists and practiced reversing them without peeking.",
                    ai_feedback="Great job reinforcing fundamentals. Keep stretching your recall speed.",
                    summary="Practiced reversing linked lists to build recall speed.",
                    xp_reward=12,
                )
            )

        # --- Boss battle history ---
        boss_run = session.exec(select(BossBattle).where(BossBattle.user == "demo")).first()
        if not boss_run:
            session.add(
                BossBattle(
                    user="demo",
                    date=datetime.utcnow() - timedelta(days=1),
                    score=4,
                    total_questions=5,
                    xp_reward=80,
                    difficulty="medium",
                    completed=True,
                )
            )

        session.commit()

        # --- Align total XP for demo user ---
        progress_xp = sum(p.xp_gained for p in session.exec(select(Progress).where(Progress.user == "demo")).all())
        quest_xp = sum(q.xp_earned for q in session.exec(select(UserQuest).where(UserQuest.user == "demo")).all())
        boss_xp = sum(b.xp_reward for b in session.exec(select(BossBattle).where(BossBattle.user == "demo")).all())
        reflection_xp = sum(r.xp_reward for r in session.exec(select(TextAIReflection).where(TextAIReflection.user == "demo")).all())

        demo_user.total_xp = progress_xp + quest_xp + boss_xp + reflection_xp
        session.add(demo_user)
        session.commit()
