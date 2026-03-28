import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from routers import economics, markets, news, signals, watchlist


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Nexus Intelligence Platform starting...")
    yield
    print("🛑 Nexus shutting down.")


app = FastAPI(
    title="Nexus Intelligence API",
    description="Palantir-style macro and geopolitical intelligence platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news.router)
app.include_router(economics.router)
app.include_router(markets.router)
app.include_router(watchlist.router)
app.include_router(signals.router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "news_api": bool(os.getenv("NEWS_API_KEY")),
        "fred_api": bool(os.getenv("FRED_API_KEY")),
        "groq_api": bool(os.getenv("GROQ_API_KEY")),
    }
