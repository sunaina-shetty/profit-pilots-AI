from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import time

class PriceTick(BaseModel):
    symbol: str
    price: float
    timestamp: float = Field(default_factory=time.time)
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    is_stale: bool = False

class NewsItem(BaseModel):
    headline: str
    source: str
    timestamp: float = Field(default_factory=time.time)
    credibility: float = 1.0  # 0.0 to 1.0
    sentiment_score: Optional[float] = None # -1.0 to +1.0
    is_stale: bool = False

class AgentVote(BaseModel):
    agent_name: str
    vote: str            # "BUY", "SELL", "HOLD"
    confidence: float    # 0.0 to 1.0
    reasons: List[str]
    timestamp: float = Field(default_factory=time.time)

class DecisionResult(BaseModel):
    symbol: str
    action: str          # "BUY", "SELL", "HOLD"
    size_tier: str       # "FULL", "HALF", "ZERO"
    confidence: float
    reason: str
    suggested_entry: float
    suggested_stop: float
    suggested_target: float
    agent_votes: Dict[str, Any]
    timestamp: float = Field(default_factory=time.time)

class RiskEvaluationRequest(BaseModel):
    symbol: str
    side: str            # "BUY", "SELL"
    entry_price: float
    stop_loss: float
    size_tier: str       # "FULL", "HALF"
    data_fresh: bool = True
    news_fresh: bool = True

class RiskVerdict(BaseModel):
    approved: bool
    symbol: str
    side: str
    qty: int
    entry_price: float
    stop_loss: float
    approval_token: Optional[str] = None
    reason: str
    timestamp: float = Field(default_factory=time.time)

class OrderRequest(BaseModel):
    symbol: str
    side: str
    qty: int
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    approval_token: str

class FillResult(BaseModel):
    order_id: str
    symbol: str
    side: str
    qty: int
    fill_price: float
    fees: float
    slippage: float
    stop_loss: float
    take_profit: Optional[float]
    status: str
    timestamp: float = Field(default_factory=time.time)

