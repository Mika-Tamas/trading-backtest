from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from orchestrator import Orchestrator
from schemas import BacktestRequest
app = FastAPI()



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/backtest")
def run_backtest(req: BacktestRequest):
    orchestrator = Orchestrator()

    results = orchestrator.execute(req)
    return results