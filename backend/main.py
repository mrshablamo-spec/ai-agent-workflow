from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from supply_chain_intel.router import router as supply_chain_router


env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Supply Chain Intelligence API starting...")
    yield
    print("Supply Chain Intelligence API shutting down.")


app = FastAPI(
    title="Mini-Palantir Supply Chain Intelligence API",
    description="10-K and news driven supply-chain dependency intelligence without paid APIs.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(supply_chain_router)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "mini-palantir-supply-chain",
    }
