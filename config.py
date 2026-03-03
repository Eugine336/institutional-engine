import os

# ================= SYSTEM =================
MODE = "LIVE"

# ================= API =================
API_KEY = os.getenv("API_FOOTBALL_KEY")
if not API_KEY:
    raise Exception("API_FOOTBALL_KEY not set")

# ================= TELEGRAM =================
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or ("8513150138:AAHwiknMhDPYw-od-mXRVMUsWpw2Wgp70iw")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or ("7978366659")

if TELEGRAM_ENABLED:
    if not TELEGRAM_BOT_TOKEN:
        raise Exception("TELEGRAM_BOT_TOKEN not set")
    if not TELEGRAM_CHAT_ID:
        raise Exception("TELEGRAM_CHAT_ID not set")

# ================= BANKROLL =================
INITIAL_BANKROLL = 100000
BASE_KELLY_FRACTION = 0.15
MIN_KELLY_FRACTION = 0.05
MAX_KELLY_FRACTION = 0.30

# ================= RISK =================
MAX_SINGLE_BET_FRACTION = 0.02
MAX_DAILY_EXPOSURE = 0.15
MAX_DRAWDOWN_LIMIT = 0.25

# ================= EDGE =================
MIN_EDGE = 0.005
STRONG_EDGE = 0.06

# ================= LEAGUES =================
APPROVED_LEAGUES = [39, 140, 78, 135, 61]

# ================= MODEL =================
DEFAULT_RHO = -0.10
MAX_GOALS = 8
CALIBRATION_FACTOR = 0.90

# ================= META =================
SHARPE_LOOKBACK = 50
DEFENSIVE_DRAWDOWN_TRIGGER = 0.15
AGGRESSIVE_SHARPE_TRIGGER = 0.4

# ================= EXECUTION =================
COMMISSION_RATE = 0.02
