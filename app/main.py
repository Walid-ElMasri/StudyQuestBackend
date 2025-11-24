from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.database import init_db
from app.routers import bossbattle, home, progress, users

try:
    from app.routers import quests
except ImportError:
    quests = None
try:
    from app.routers import cosmetics
except ImportError:
    cosmetics = None
try:
    from app.routers import text_ai
except ImportError:
    text_ai = None
try:
    from app.routers import socialfeatures as social
except ImportError:
    social = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="StudyQuest Backend API",
    description=(
        "Gamified productivity app backend built with FastAPI + SQLModel.\n\n"
        "Each teammate owns one feature area — all integrated into one backend:\n"
        "- Walid: Progress Tracking + Home\n"
        "- Nour: Quests & Levels\n"
        "- Aya: Cosmetics & Rewards\n"
        "- All Team: Text AI Mentor\n"
        "- Lynn: Boss Battle\n"
        "- Mohamad: Social Features"
    ),
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(home.router)
app.include_router(progress.router)
if quests and hasattr(quests, "router"):
    app.include_router(quests.router)
app.include_router(bossbattle.router)
app.include_router(users.router)
if cosmetics and hasattr(cosmetics, "router"):
    app.include_router(cosmetics.router)
if text_ai and hasattr(text_ai, "router"):
    app.include_router(text_ai.router)
if social and hasattr(social, "router"):
    app.include_router(social.router)



@app.get("/", tags=["Root"])
def root():
    """
    StudyQuest API landing page — shows available endpoints and docs link.
    """
    return {
        "message": "Welcome to the StudyQuest Backend API",
        "status": "running",
        "main_endpoints": {
            "Home Dashboard": "/home/dashboard?user=<username>",
            "Progress Tracking": "/progress",
            "Quests & Levels": "/quests",
            "Cosmetics & Rewards": "/cosmetics",
            "AI Text Mentor": "/text-ai",
            "Daily Boss Battle": "/boss",
            "Social Features": "/social"
        },
        "docs": "/docs",
    }
