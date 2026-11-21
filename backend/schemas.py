from datetime import date
import math
import re
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

MAX_TICKER_LENGTH = 12
TICKER_PATTERN = re.compile(rf"^[A-Z0-9._^=-]{{1,{MAX_TICKER_LENGTH}}}$")


def normalize_ticker(value: str) -> str:
    """Validate and uppercase-normalize a market ticker symbol."""
    if not isinstance(value, str):
        raise ValueError("Ticker must be a string.")
    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("Ticker must not be empty or whitespace.")
    if ".." in normalized or normalized.startswith(".") or normalized.endswith("."):
        raise ValueError("Ticker contains an invalid dot sequence.")
    if not TICKER_PATTERN.fullmatch(normalized):
        raise ValueError(
            f"Ticker must be 1-{MAX_TICKER_LENGTH} characters matching [A-Za-z0-9._^=-]."
        )
    return normalized


class FeeSettings(BaseModel):
    type: Literal["Percentage", "ShareFlat", "OrderFlat"]
    rate: float = Field(ge=0.0)
    min: float
    max: float

    @field_validator("rate", "min", "max")
    @classmethod
    def check_finite_fee_values(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Fee parameters must be finite numbers.")
        return v


class BacktestRequest(BaseModel):
    ticker: str = Field(min_length=1)
    risk_free_ticker: str = Field(min_length=1)
    market_ticker: str = Field(min_length=1)
    visual_comparison_ticker: str = Field(min_length=1)
    start_date: str
    end_date: str
    initial_cash: float = Field(gt=0.0)
    base_currency: str = Field(min_length=1)
    strategy_name: Literal["SMA"]
    strategy_params: list[float] = Field(min_length=1)
    fee_model: FeeSettings

    @field_validator(
        "ticker",
        "risk_free_ticker",
        "market_ticker",
        "visual_comparison_ticker",
    )
    @classmethod
    def validate_ticker_fields(cls, v: str) -> str:
        return normalize_ticker(v)

    @field_validator("base_currency")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field must not be empty or whitespace.")
        return stripped

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_iso_date(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError as exc:
            raise ValueError("Dates must be in YYYY-MM-DD ISO format.") from exc
        return v

    @field_validator("initial_cash")
    @classmethod
    def validate_finite_cash(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("initial_cash must be finite.")
        return v

    @model_validator(mode="after")
    def validate_request_logic(self) -> "BacktestRequest":
        if date.fromisoformat(self.start_date) >= date.fromisoformat(self.end_date):
            raise ValueError("start_date must be strictly before end_date.")
        if self.strategy_name == "SMA":
            if len(self.strategy_params) != 2:
                raise ValueError("SMA strategy requires exactly 2 parameters (slow, fast).")
            if any((not math.isfinite(p) or p < 1) for p in self.strategy_params):
                raise ValueError("SMA strategy parameters must be finite numbers >= 1.")
        return self

class TradeResponse(BaseModel):
    ticker: str
    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    quantity: float
    side: int
    realized_pnl: float
    fee_paid: float

class BacktestMetrics(BaseModel):
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    maximum_drawdown: float
    calmar_ratio: float
    profit_factor: float
    win_rate: float
    information_ratio: float
    beta: float
    alpha: float

class BacktestResponse(BaseModel):
    initial_cash: float
    final_cash: float
    fees_paid: float
    timestamps: list[int]
    equity_curve: list[float]
    trades: list[TradeResponse]
    comparison_curve: list[float]
    market_curve: list[float]
    metrics: BacktestMetrics

