import os
from pathlib import Path

# Manual dotenv loader to avoid external dependency issues
def load_dotenv():
    # Look for .env in the project root directory
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    # Set in os.environ if not already set (standard dotenv behavior)
                    if key not in os.environ:
                        os.environ[key] = val

load_dotenv()

class Settings:
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    DEFAULT_TRADE_BUDGET: float = float(os.getenv("DEFAULT_TRADE_BUDGET", "100000"))

settings = Settings()
