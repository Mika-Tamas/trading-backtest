from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from orchestrator import Orchestrator

app = FastAPI()

class BacktestRequest(BaseModel):
    ticker:str
    start_date:str
    end_date:str
    initial_cash:float
    strategy_name:str
    strategy_params:list[float]

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

    results = orchestrator.execute(
        req.ticker, req.start_date, req.end_date, 
        req.initial_cash, req.strategy_name, *req.strategy_params
    )
    return results