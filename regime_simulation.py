import random
import numpy as np
from collections import defaultdict

from core.rating_engine import RatingEngine
from core.pricing_engine import PricingEngine
from core.portfolio_engine import PortfolioEngine
from core.risk_engine import RiskEngine
from core.meta_engine import MetaEngine


def regime_simulation(days=100, matches_per_day=10):

    rating = RatingEngine()
    pricing = PricingEngine()
    portfolio = PortfolioEngine()
    risk = RiskEngine(100000)
    meta = MetaEngine()

    equity_curve = []

    # Regime definitions
    regimes = {
        "efficient": {"bias": 0.005, "variance": 0.02},
        "loose": {"bias": 0.03, "variance": 0.05},
        "adverse": {"bias": -0.02, "variance": 0.04},
        "volatile": {"bias": 0.01, "variance": 0.10}
    }

    regime_names = list(regimes.keys())

    for day in range(days):

        regime_name = random.choice(regime_names)
        regime = regimes[regime_name]

        opportunities = []

        for m in range(matches_per_day):

            league = random.choice([39, 140, 78, 135, 61])
            home_id = random.randint(1, 300)
            away_id = random.randint(301, 600)

            config = rating.league_config[league]

            lambda_home, lambda_away = rating.get_lambdas(
                league, home_id, away_id
            )

            markets = pricing.price_match(
                lambda_home, lambda_away, config["rho"]
            )

            for key, prob in markets.items():

                if prob <= 0:
                    continue

                fair_odds = 1 / prob

                noise = random.uniform(
                    -regime["variance"],
                    regime["variance"]
                )

                # Apply regime bias
                noise += regime["bias"]

                simulated_odds = fair_odds * (1 + noise)

                implied = 1 / simulated_odds
                edge = prob - implied

                opportunities.append({
                    "fixture_id": f"{day}_{m}",
                    "league": league,
                    "market": key,
                    "prob": prob,
                    "odds": simulated_odds,
                    "edge": edge
                })

                meta.record_edge(edge)

        # ----------------------------
        # Institutional Filtering
        # ----------------------------

        opportunities = [o for o in opportunities if o["edge"] > 0.035]

        opportunities = sorted(
            opportunities,
            key=lambda x: x["edge"],
            reverse=True
        )

        per_fixture = defaultdict(int)
        filtered = []

        for o in opportunities:
            if per_fixture[o["fixture_id"]] < 2:
                filtered.append(o)
                per_fixture[o["fixture_id"]] += 1

        opportunities = filtered[:200]

        selected = portfolio.optimize(opportunities)

        # ----------------------------
        # Execute & Settle
        # ----------------------------

        for bet in selected:

            stake = risk.compute_stake(
                bet["edge"],
                bet["stake_fraction"]
            )

            if stake <= 0:
                continue

            adjusted_prob = min(
                max(bet["prob"] + random.uniform(-0.03, 0.03), 0),
                1
            )

            win = random.random() < adjusted_prob

            pnl = (
                stake * (bet["odds"] - 1)
                if win else -stake
            )

            risk.settle_trade(pnl)

        # Adapt system daily
        meta.adapt(risk)

        equity_curve.append(risk.bankroll)

        print(
            f"Day {day+1} | Regime: {regime_name} | "
            f"Bankroll: {round(risk.bankroll,2)} | "
            f"Kelly: {round(risk.kelly_fraction,3)}"
        )

    # ----------------------------
    # Final Summary
    # ----------------------------

    print("\n====================================")
    print("MULTI-DAY REGIME SIMULATION COMPLETE")
    print("Final Bankroll:", round(risk.bankroll, 2))
    print("Peak:", round(max(equity_curve), 2))
    print("Trough:", round(min(equity_curve), 2))
    print("====================================")


if __name__ == "__main__":
    regime_simulation(100, 10)
