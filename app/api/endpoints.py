from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.stock import StockPrice, TradingSignal
from app.schemas.stock import StockPriceCreate, StockPriceResponse, TradingSignalResponse
from app.strategies.moving_average import generate_trading_signals
from app.utils.notifier import send_telegram_alert
from app.utils.shioaji_trader import place_simulated_order

router = APIRouter()

@router.post("/prices", response_model=List[StockPriceResponse], status_code=status.HTTP_201_CREATED)
def bulk_upload_prices(prices_data: List[StockPriceCreate], db: Session = Depends(get_db)):
    """
    Bulk upload historical stock price records.
    """
    if not prices_data:
        raise HTTPException(status_code=400, detail="Price data list cannot be empty")
        
    db_prices = [
        StockPrice(
            symbol=p.symbol,
            date=p.date,
            open_price=p.open_price,
            high_price=p.high_price,
            low_price=p.low_price,
            close_price=p.close_price,
            volume=p.volume
        )
        for p in prices_data
    ]
    
    try:
        db.add_all(db_prices)
        db.commit()
        for p in db_prices:
            db.refresh(p)
        return db_prices
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/signals/{symbol}", response_model=List[TradingSignalResponse])
def get_historical_signals(symbol: str, db: Session = Depends(get_db)):
    """
    Get all historical trading signals for a specific stock symbol.
    """
    signals = db.query(TradingSignal).filter(
        TradingSignal.symbol == symbol
    ).order_by(TradingSignal.date.asc()).all()
    
    return signals

@router.post("/backtest/{symbol}", response_model=List[TradingSignalResponse], status_code=status.HTTP_200_OK)
def run_backtest(symbol: str, db: Session = Depends(get_db)):
    """
    Run the 20MA quantitative trading strategy backtest for a specific stock symbol.
    Generates BUY, SELL, and REDUCE signals from historical price data,
    clears any previously stored signals for this stock, and saves the new signals.
    """
    # 1. Fetch historical prices sorted by date ascending
    prices = db.query(StockPrice).filter(
        StockPrice.symbol == symbol
    ).order_by(StockPrice.date.asc()).all()
    
    if not prices:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No historical price data found for symbol '{symbol}'. Please upload prices first."
        )
        
    if len(prices) < 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient price data (found {len(prices)} days). Need at least 20 days of data to compute 20MA."
        )
        
    # 2. Convert database models to dictionaries for the strategy engine
    price_dicts = [
        {
            "symbol": p.symbol,
            "date": p.date,
            "close_price": p.close_price
        }
        for p in prices
    ]
    
    # 3. Run the strategy engine
    generated_signals = generate_trading_signals(price_dicts)
    
    try:
        # 4. Clear any existing signals for this stock to avoid duplication on re-run
        db.query(TradingSignal).filter(TradingSignal.symbol == symbol).delete()
        
        # 5. Insert new signals
        db_signals = [
            TradingSignal(
                symbol=sig["symbol"],
                date=sig["date"],
                signal_type=sig["signal_type"],
                price=sig["price"],
                reason=sig["reason"]
            )
            for sig in generated_signals
        ]
        
        if db_signals:
            db.add_all(db_signals)
            db.commit()
            for sig in db_signals:
                db.refresh(sig)
                
            # Send Telegram alert if the latest signal was triggered on the most recent price date
            latest_price_date = prices[-1].date
            sorted_signals = sorted(db_signals, key=lambda x: x.date)
            latest_signal = sorted_signals[-1]
            
            if latest_signal.date == latest_price_date:
                send_telegram_alert(
                    signal_type=latest_signal.signal_type,
                    symbol=latest_signal.symbol,
                    price=latest_signal.price,
                    reason=latest_signal.reason
                )
                
                # Automatically place simulated order for BUY or SELL signals
                if latest_signal.signal_type in ["BUY", "SELL"]:
                    shioaji_action = "Buy" if latest_signal.signal_type == "BUY" else "Sell"
                    place_simulated_order(
                        action=shioaji_action,
                        symbol=latest_signal.symbol,
                        price=latest_signal.price
                    )
        else:
            db.commit()
            
        return db_signals
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during backtesting: {str(e)}")
