import numpy as np


class PortfolioEngine:

    def __init__(self):

        self.max_daily_exposure = 0.15
        self.max_match_exposure = 0.02
        self.max_bets_per_day = 12
        self.max_league_exposure = 0.06

        self.min_edge_threshold = 0.02
        self.risk_aversion = 5.0

    # --------------------------------
    # EXPECTED RETURN
    # --------------------------------
    def expected_returns(self, opportunities):

        mu = []

        for opp in opportunities:
            p = opp["prob"]
            o = opp["odds"]

            ev = p * (o - 1) - (1 - p)
            mu.append(ev)

        return np.array(mu)

    # --------------------------------
    # STRUCTURAL COVARIANCE
    # --------------------------------
    def covariance_matrix(self, opportunities):

        n = len(opportunities)

        if n == 0:
            return np.array([])

        base_var = 0.02
        cov = np.zeros((n, n))

        for i in range(n):
            for j in range(n):

                if i == j:
                    cov[i, j] = base_var
                else:
                    same_fixture = (
                        opportunities[i]["fixture_id"]
                        == opportunities[j]["fixture_id"]
                    )

                    same_league = (
                        opportunities[i]["league"]
                        == opportunities[j]["league"]
                    )

                    if same_fixture:
                        cov[i, j] = base_var * 0.8
                    elif same_league:
                        cov[i, j] = base_var * 0.5
                    else:
                        cov[i, j] = base_var * 0.2

        return cov

    # --------------------------------
    # PRE-FILTER BY EDGE
    # --------------------------------
    def filter_opportunities(self, opportunities):

        return [
            opp for opp in opportunities
            if opp["edge"] >= self.min_edge_threshold
        ]

    # --------------------------------
    # BEST MARKET PER FIXTURE
    # --------------------------------
    def best_per_fixture(self, opportunities):

        best = {}

        for opp in opportunities:

            fixture_id = opp["fixture_id"]

            if fixture_id not in best:
                best[fixture_id] = opp
            else:
                if opp["edge"] > best[fixture_id]["edge"]:
                    best[fixture_id] = opp

        return list(best.values())

    # --------------------------------
    # OPTIMIZATION
    # --------------------------------
    def optimize(self, opportunities):

        # Step 1: Edge filter
        opportunities = self.filter_opportunities(opportunities)

        if not opportunities:
            return []

        # Step 2: One best market per fixture
        opportunities = self.best_per_fixture(opportunities)

        n = len(opportunities)

        if n == 0:
            return []

        # Step 3: Mean–Variance Optimization
        mu = self.expected_returns(opportunities)
        cov = self.covariance_matrix(opportunities)

        if cov.size == 0:
            return []

        inv_cov = np.linalg.pinv(cov)
        raw_weights = inv_cov @ mu
        raw_weights = np.maximum(raw_weights, 0)

        if raw_weights.sum() == 0:
            return []

        weights = raw_weights / raw_weights.sum()
        weights *= self.max_daily_exposure

        # --------------------------------
        # Apply Structural Caps
        # --------------------------------
        selected = []
        league_exposure = {}
        total_exposure = 0

        ranked_indices = np.argsort(-weights)

        for idx in ranked_indices:

            if len(selected) >= self.max_bets_per_day:
                break

            stake_fraction = min(
                weights[idx],
                self.max_match_exposure
            )

            league = opportunities[idx]["league"]
            league_used = league_exposure.get(league, 0)

            if league_used + stake_fraction > self.max_league_exposure:
                continue

            if total_exposure + stake_fraction > self.max_daily_exposure:
                continue

            if stake_fraction <= 0:
                continue

            league_exposure[league] = league_used + stake_fraction
            total_exposure += stake_fraction

            selected.append({
                **opportunities[idx],
                "stake_fraction": stake_fraction
            })

        return selected
