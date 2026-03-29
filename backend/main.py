from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from supply_chain_intel.router import router as supply_chain_router


env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

frontend_build_dir = Path(__file__).parent.parent / "frontend" / "build"
frontend_index = frontend_build_dir / "index.html"


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
        "frontend_built": frontend_index.exists(),
    }


if frontend_build_dir.exists():
    app.mount("/static", StaticFiles(directory=frontend_build_dir / "static"), name="static")

    @app.get("/")
    def website() -> FileResponse:
        return FileResponse(frontend_index)

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith("supply-chain") or full_path == "health":
            return {"detail": "Not Found"}
        asset_path = frontend_build_dir / full_path
        if asset_path.exists() and asset_path.is_file():
            return FileResponse(asset_path)
        return FileResponse(frontend_index)
