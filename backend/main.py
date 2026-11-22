from contextlib import asynccontextmanager
import os
from pathlib import Path
import threading

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from cache_manager import close_cached_clients, create_cache_manager
from data_provider import DataProvider
from orchestrator import Orchestrator
from schemas import BacktestRequest

_APP_INIT_LOCK = threading.Lock()


def parse_cors_settings(raw_origins: str | None) -> tuple[list[str], bool]:
    if raw_origins is None:
        raw_origins = "*"
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    allow_credentials = bool(origins) and ("*" not in origins)
    return origins, allow_credentials


def _init_app_orchestrator(target_app: FastAPI) -> Orchestrator:
    with _APP_INIT_LOCK:
        orchestrator = getattr(target_app.state, "orchestrator", None)
        if orchestrator is None:
            cache = create_cache_manager()
            orchestrator = Orchestrator(data_provider=DataProvider(cache=cache))
            target_app.state.orchestrator = orchestrator
        return orchestrator


@asynccontextmanager
async def lifespan(target_app: FastAPI):
    _init_app_orchestrator(target_app)
    try:
        yield
    finally:
        close_cached_clients()
        if hasattr(target_app.state, "orchestrator"):
            delattr(target_app.state, "orchestrator")


def get_orchestrator(request: Request) -> Orchestrator:
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        return _init_app_orchestrator(request.app)
    return orchestrator


app = FastAPI(lifespan=lifespan)

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
def run_backtest(
    req: BacktestRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
):
    return orchestrator.execute(req)


frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
