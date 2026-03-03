import random
import numpy as np
from collections import defaultdict

from core.rating_engine import RatingEngine
from core.pricing_engine import PricingEngine
from core.portfolio_engine import PortfolioEngine
from core.risk_engine import RiskEngine
from core.meta_engine import MetaEngine


def stress_test(num_matches=500):

    rating = RatingEngine()
    pricing = PricingEngine()
    portfolio = PortfolioEngine()
    risk = RiskEngine(100000)
    meta = MetaEngine()

    opportunities = []

    # League inefficiency multipliers
    league_bias = {
        39: 0.01,   # EPL efficient
        140: 0.015,
        78: 0.025,  # Bundesliga more volatile
        135: 0.02,
        61: 0.03    # Ligue 1 slightly inefficient
    }

    for i in range(num_matches):

        league = random.choice([39, 140, 78, 135, 61])
        home_id = random.randint(1, 300)
        away_id = random.randint(301, 600)

        config = rating.league_config[league]

        lambda_home, lambda_away = rating.get_lambdas(
            league,
            home_id,
            away_id
        )

        markets = pricing.price_match(
            lambda_home,
            lambda_away,
            config["rho"]
        )

        for key, prob in markets.items():

            if prob <= 0:
                continue

            fair_odds = 1 / prob

            # -----------------------------
            # REAL WORLD INEFFICIENCIES
            # -----------------------------

            noise = random.uniform(-0.05, 0.05)

            # Favorite-longshot bias
            if fair_odds < 1.8:
                noise -= 0.02
            elif fair_odds > 3.5:
                noise += 0.03

            # League structural inefficiency
            noise += league_bias[league]

            # Over/Under shading
            if "Over" in key:
                noise -= 0.015

            # Regime shift (goal environment change)
            regime = random.choice([-0.02, 0, 0.02])
            noise += regime

            simulated_odds = fair_odds * (1 + noise)

            implied = 1 / simulated_odds
            edge = prob - implied

            opportunities.append({
                "fixture_id": i,
                "league": league,
                "market": key,
                "prob": prob,
                "odds": simulated_odds,
                "edge": edge
            })

            meta.record_edge(edge)

    print("Total raw opportunities:", len(opportunities))

    # -----------------------------------
    # FILTERING (Institutional scaling)
    # -----------------------------------

    opportunities = [o for o in opportunities if o["edge"] > 0.02]

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

    opportunities = filtered[:300]

    print("After filtering:", len(opportunities))

    # -----------------------------------
    # OPTIMIZATION
    # -----------------------------------

    selected = portfolio.optimize(opportunities)

    print("Selected bets:", len(selected))

    # -----------------------------------
    # EXECUTION SIMULATION (Correlated outcomes)
    # -----------------------------------

    for bet in selected:

        stake = risk.compute_stake(
            bet["edge"],
            bet["stake_fraction"]
        )

        if stake <= 0:
            continue

        # Correlated environment
        variance_boost = random.uniform(-0.05, 0.05)
        adjusted_prob = min(max(bet["prob"] + variance_boost, 0), 1)

        win = random.random() < adjusted_prob
        pnl = stake * (bet["odds"] - 1) if win else -stake

        risk.settle_trade(pnl)

    meta.adapt(risk, portfolio)

    print("====================================")
    print("REALISTIC INEFFICIENCY STRESS TEST")
    print("Matches simulated:", num_matches)
    print("Final bankroll:", round(risk.bankroll, 2))
    print("Kelly fraction:", round(risk.kelly_fraction, 3))
    print("====================================")


if __name__ == "__main__":
    stress_test(500)
