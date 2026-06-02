import urllib.request
import json
import logging
from app.config import settings

logger = logging.getLogger("app.notifier")

def send_telegram_alert(signal_type: str, symbol: str, price: float, reason: str = None):
    """
    Sends a Telegram alert message for a stock trading signal.
    Calculates the suggested shares based on the default budget and the price.
    """
    token = settings.TELEGRAM_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    
    if not token or not chat_id:
        logger.warning("Telegram notification skipped: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID is not configured.")
        return False

    # 1. Formatting based on Signal Type
    signal_type = signal_type.upper()
    if signal_type == "BUY":
        emoji = "🟢 【買入訊號】"
        budget = settings.DEFAULT_TRADE_BUDGET
        shares = int(budget // price) if price > 0 else 0
        shares_str = f"{shares:,} 股 (預算: ${budget:,})" if shares > 0 else "計算失敗 (價格異常)"
    elif signal_type == "SELL":
        emoji = "🔴 【賣出訊號】"
        shares_str = "全部清倉 / 出場 (EXIT ALL)"
    elif signal_type == "REDUCE":
        emoji = "🟡 【減碼訊號】"
        shares_str = "波段減碼 50% (REDUCE 50%)"
    else:
        emoji = "ℹ️ 【交易訊號】"
        shares_str = "請依策略指示執行"

    # 2. Construct Message
    message = (
        f"{emoji}\n"
        f"🔹 **股票代號**: `{symbol}`\n"
        f"🔹 **交易動作**: {signal_type}\n"
        f"🔹 **建議股數**: {shares_str}\n"
        f"🔹 **觸發價格**: ${price:,.2f}\n"
    )
    if reason:
        message += f"🔹 **觸發原因**: {reason}\n"
        
    message += "\n*策略提醒：請注意部位風險管理。*"

    # 3. Send API Request
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            if res.get("ok"):
                logger.info(f"Telegram notification sent successfully for {symbol} ({signal_type}).")
                return True
            else:
                logger.error(f"Telegram API error: {res}")
                return False
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {str(e)}")
        return False
