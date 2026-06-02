import pandas as pd
from typing import List, Dict, Any
from datetime import date

def calculate_20ma(prices_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the 20-day Simple Moving Average (20MA) of the close price.
    Assumes prices_df has 'close_price' column and is sorted by date ascending.
    """
    df = prices_df.copy()
    df['ma20'] = df['close_price'].rolling(window=20).mean()
    return df

def generate_trading_signals(prices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generates BUY, SELL, and REDUCE signals based on 20MA and wave profit.
    
    Rules:
    - BUY: Price crosses above 20MA and we have no active position.
    - SELL: Price falls below 20MA while we have an active position.
    - REDUCE: Wave profit reaches or exceeds 20% of entry price. Triggered only once per position.
    
    Input elements should have:
    - 'symbol': str
    - 'date': datetime.date or str
    - 'close_price': float
    """
    if not prices or len(prices) < 20:
        return []
        
    # Convert to DataFrame
    df = pd.DataFrame(prices)
    # Ensure date is sorted
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    # Calculate 20MA
    df = calculate_20ma(df)
    
    signals = []
    has_position = False
    entry_price = 0.0
    has_reduced = False
    
    for i in range(len(df)):
        row = df.iloc[i]
        curr_price = row['close_price']
        curr_ma = row['ma20']
        curr_date = row['date'].date()
        symbol = row['symbol']
        
        # Skip if 20MA is not yet calculated (first 19 periods)
        if pd.isna(curr_ma):
            continue
            
        # Get previous row values if available
        prev_price = df.iloc[i-1]['close_price'] if i > 0 else None
        prev_ma = df.iloc[i-1]['ma20'] if i > 0 else None
        
        if not has_position:
            # Check for BUY signal: Price crosses above 20MA
            is_cross_above = False
            if prev_price is not None and prev_ma is not None and not pd.isna(prev_ma):
                if prev_price <= prev_ma and curr_price > curr_ma:
                    is_cross_above = True
            elif curr_price > curr_ma:
                is_cross_above = True
                
            if is_cross_above:
                has_position = True
                entry_price = curr_price
                has_reduced = False
                signals.append({
                    "symbol": symbol,
                    "date": curr_date,
                    "signal_type": "BUY",
                    "price": float(curr_price),
                    "reason": f"價格 ({curr_price}) 站上 20MA ({round(curr_ma, 2)})"
                })
        else:
            # We have a position. Check for SELL or REDUCE signals.
            
            # Check SELL first: Price falls below 20MA
            if curr_price < curr_ma:
                signals.append({
                    "symbol": symbol,
                    "date": curr_date,
                    "signal_type": "SELL",
                    "price": float(curr_price),
                    "reason": f"價格 ({curr_price}) 跌破 20MA ({round(curr_ma, 2)})，執行停損/出場"
                })
                has_position = False
                entry_price = 0.0
                has_reduced = False
                
            # Check REDUCE: Profit >= 20% and we haven't reduced yet in this wave
            elif not has_reduced:
                profit_pct = (curr_price - entry_price) / entry_price
                if profit_pct >= 0.20:
                    signals.append({
                        "symbol": symbol,
                        "date": curr_date,
                        "signal_type": "REDUCE",
                        "price": float(curr_price),
                        "reason": f"波段獲利達 {round(profit_pct * 100, 2)}% (進場價: {entry_price}，當前價: {curr_price})，執行波段減碼"
                    })
                    has_reduced = True
                    
    return signals
