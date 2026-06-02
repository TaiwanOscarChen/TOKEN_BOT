from datetime import date, datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class StockPriceBase(BaseModel):
    symbol: str
    date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int

class StockPriceCreate(StockPriceBase):
    pass

class StockPriceResponse(StockPriceBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)

class TradingSignalResponse(BaseModel):
    id: int
    symbol: str
    date: date
    signal_type: str
    price: float
    timestamp: datetime
    reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
