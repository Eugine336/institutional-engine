from datetime import datetime, timezone

class SlipGenerator:

    def __init__(self):
        self.bets = []

    def add_bet(self, league, home, away, market, kickoff):
        time = kickoff.split("T")[1][:5] if "T" in kickoff else kickoff
        self.bets.append({
            "league": league,
            "match": f"{home} vs {away}",
            "market": market,
            "kickoff": time
        })

    def generate(self):
        if not self.bets:
            return None

        header = (
            f"🔥 INSTITUTIONAL MATCH SLIP 🔥\n\n"
            f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"
        )

        body = ""
        for i, bet in enumerate(self.bets, 1):
            body += (
                f"{i}. {bet['match']}\n"
                f"   League: {bet['league']}\n"
                f"   Market: {bet['market']}\n"
                f"   Kickoff: {bet['kickoff']}\n\n"
            )

        return header + body + "— Engine Generated\n"

    def reset(self):
        self.bets = []
