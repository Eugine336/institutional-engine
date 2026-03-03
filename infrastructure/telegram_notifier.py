import requests
from config import *


class TelegramNotifier:

    def __init__(self):

        self.enabled = TELEGRAM_ENABLED

        if not self.enabled:
            print("Telegram disabled.")
            return

        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("Telegram config missing.")
            self.enabled = False
            return

        self.base_url = (
            f"https://api.telegram.org/"
            f"bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        )

        print("Telegram notifier initialized.")

    # ------------------------------------------------
    # INTERNAL SEND (SAFE VERSION)
    # ------------------------------------------------
    def _send(self, text):

        if not self.enabled:
            return

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }

        try:
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=10
            )

            if response.status_code != 200:
                print("\n⚠ TELEGRAM ERROR")
                print("Status:", response.status_code)
                print("Response:", response.text)
            else:
                print("Telegram sent successfully.")

        except Exception as e:
            print("\n⚠ TELEGRAM EXCEPTION")
            print(str(e))

    # ------------------------------------------------
    # TRADE ALERT
    # ------------------------------------------------
    def send_trade(self, league, match, market, kickoff, odds, stake):

        message = (
            f"🔥 NEW TRADE\n\n"
            f"⚽ {match}\n"
            f"🏆 League: {league}\n"
            f"📊 Market: {market}\n"
            f"🕒 Kickoff: {kickoff}\n"
            f"🎯 Odds: {odds}\n"
            f"💰 Stake: {round(stake, 2)}"
        )

        self._send(message)

    # ------------------------------------------------
    # TRADE SETTLEMENT
    # ------------------------------------------------
    def send_settlement(self, market, pnl, bankroll):

        emoji = "✅" if pnl > 0 else "❌"

        message = (
            f"{emoji} TRADE SETTLED\n\n"
            f"📊 Market: {market}\n"
            f"💵 PnL: {round(pnl, 2)}\n"
            f"💰 Bankroll: {round(bankroll, 2)}"
        )

        self._send(message)

    # ------------------------------------------------
    # DAILY SUMMARY
    # ------------------------------------------------
    def send_summary(self, bankroll, kelly, state):

        message = (
            f"📊 ENGINE SUMMARY\n\n"
            f"💰 Bankroll: {round(bankroll, 2)}\n"
            f"⚙ Kelly: {round(kelly, 3)}\n"
            f"🧠 Meta State: {state}"
        )

        self._send(message)
