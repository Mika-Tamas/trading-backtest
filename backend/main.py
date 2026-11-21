import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from orchestrator import Orchestrator
from schemas import BacktestRequest

def parse_cors_settings(raw_origins: str | None) -> tuple[list[str], bool]:
    if raw_origins is None:
        raw_origins = "*"
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    allow_credentials = bool(origins) and ("*" not in origins)
    return origins, allow_credentials


app = FastAPI()

cors_origins, cors_allow_credentials = parse_cors_settings(os.getenv("CORS_ORIGINS"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/backtest")
def run_backtest(req: BacktestRequest):
    orchestrator = Orchestrator()

    results = orchestrator.execute(req)
    return results


frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")