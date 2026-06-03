import logging
import shioaji as sj
from app.config import settings

logger = logging.getLogger("app.shioaji_trader")

def place_simulated_order(action: str, symbol: str, price: float, reason: str = None) -> dict:
    """
    Connects to Shioaji (simulation mode), determines correct order lot (Common/Odd),
    places a limit buy/sell order, logs results, and logs out safely.
    """
    api_key = settings.SHIOAJI_API_KEY
    secret_key = settings.SHIOAJI_SECRET_KEY
    
    if not api_key or not secret_key:
        logger.warning("Shioaji trading skipped: API Key or Secret Key is not configured.")
        return {"status": "skipped", "message": "Keys not configured"}

    # 1. Initialize API with simulation setting
    is_simulation = settings.SHIOAJI_SIMULATION
    logger.info(f"Initializing Shioaji API (simulation={is_simulation})...")
    api = sj.Shioaji(simulation=is_simulation)
    
    try:
        # 2. Login
        api.login(api_key=api_key, secret_key=secret_key)
        logger.info("Shioaji login successful.")
        
        # Verify account
        if not api.stock_account:
            logger.error("No valid stock account found for Shioaji API Key.")
            return {"status": "failed", "message": "No stock account found"}
            
        # 3. Retrieve stock contract
        # Standard code matching (e.g. if symbol is '2330.TW', Shioaji expects '2330')
        clean_symbol = symbol.split(".")[0]
        contract = api.Contracts.Stocks[clean_symbol]
        if not contract:
            logger.error(f"Stock contract for {clean_symbol} not found on Shioaji.")
            return {"status": "failed", "message": f"Contract for {clean_symbol} not found"}
            
        # 4. Calculate shares and decide order lot
        action = action.capitalize()  # 'Buy' or 'Sell'
        if action == "Buy":
            budget = settings.DEFAULT_TRADE_BUDGET
            shares = int(budget // price) if price > 0 else 0
            if shares <= 0:
                logger.error(f"Cannot place buy order: calculated shares {shares} <= 0.")
                return {"status": "failed", "message": "Invalid shares count"}
        else:
            # For SELL or REDUCE, we can place a mock order.
            # E.g. for SELL, we sell all we bought. Let's assume we sell 1000 shares (or 1張) or 100 shares for testing.
            # In real system, we'd look up current portfolio. Here we can use a default or mock quantity (e.g. 1000 shares/1張)
            shares = 1000 
            
        # Decision: Common (整股, >= 1000 shares, quantity in 張) or Odd (零股, < 1000 shares, quantity in 股)
        if shares < 1000:
            order_lot = "Odd"
            quantity = shares  # odd lot quantity is in shares (股)
        else:
            order_lot = "Common"
            quantity = shares // 1000  # common lot quantity is in sheets (張)
            
        # 5. Build order object
        logger.info(f"Building order: {action} {quantity} ({order_lot}) of {clean_symbol} at ${price}")
        order = api.Order(
            price=price,
            quantity=quantity,
            action=action,            # 'Buy' or 'Sell'
            price_type="LMT",          # Limit price
            order_type="ROD",          # Rest of Day
            order_lot=order_lot,       # 'Common' or 'Odd'
            account=api.stock_account
        )
        
        # 6. Submit order
        trade = api.place_order(contract, order)
        logger.info(f"Order submitted successfully: {trade}")
        
        return {
            "status": "success",
            "order_id": trade.order.id if hasattr(trade, "order") else "unknown",
            "trade": str(trade)
        }
        
    except Exception as e:
        logger.error(f"Shioaji trading failed with exception: {str(e)}")
        return {"status": "error", "message": str(e)}
        
    finally:
        # Always logout to free up connection quota
        logger.info("Logging out of Shioaji API...")
        try:
            api.logout()
            logger.info("Logout completed.")
        except Exception as ex:
            logger.warning(f"Error during logout: {str(ex)}")
