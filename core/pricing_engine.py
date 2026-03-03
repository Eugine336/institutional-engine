import numpy as np
from scipy.stats import nbinom
from config import *

class PricingEngine:

    def __init__(self):

        self.calibration_factor = CALIBRATION_FACTOR
        self.low_score_history = []
        self.window = 200

    # --------------------------------
    # ADAPTIVE DISPERSION
    # --------------------------------
    def get_dispersion(self, lambda_home, lambda_away):

        total_lambda = lambda_home + lambda_away
        base_k = 2.0
        adjustment = max(0.5, 3.0 - total_lambda)
        k = base_k * adjustment

        return np.clip(k, 0.8, 4.0)

    # --------------------------------
    # NEGATIVE BINOMIAL PMF
    # --------------------------------
    def negbin_pmf(self, goals, lam, k):

        p = k / (k + lam)
        r = k

        return nbinom.pmf(goals, r, p)

    # --------------------------------
    # DYNAMIC RHO
    # --------------------------------
    def estimate_rho(self):

        if len(self.low_score_history) < 50:
            return DEFAULT_RHO

        recent = self.low_score_history[-self.window:]
        freq = np.mean(recent)

        rho = -0.15 + (freq * 0.20)
        return np.clip(rho, -0.25, 0.15)

    # --------------------------------
    # BUILD MATRIX
    # --------------------------------
    def build_matrix(self, lambda_home, lambda_away):

        max_goals = MAX_GOALS
        goals = np.arange(max_goals + 1)

        k = self.get_dispersion(lambda_home, lambda_away)
        rho = self.estimate_rho()

        home_probs = np.array(
            [self.negbin_pmf(g, lambda_home, k) for g in goals]
        )

        away_probs = np.array(
            [self.negbin_pmf(g, lambda_away, k) for g in goals]
        )

        matrix = np.outer(home_probs, away_probs)

        adjustment = np.ones_like(matrix)

        adjustment[0, 0] *= (1 - lambda_home * lambda_away * rho)
        adjustment[0, 1] *= (1 + lambda_home * rho)
        adjustment[1, 0] *= (1 + lambda_away * rho)
        adjustment[1, 1] *= (1 - rho)

        matrix *= adjustment
        matrix /= matrix.sum()

        return matrix

    # --------------------------------
    # DERIVE MARKETS
    # --------------------------------
    def derive_markets(self, matrix):

        markets = {}
        max_goals = matrix.shape[0]

        p_home = 0
        p_draw = 0
        p_away = 0

        for i in range(max_goals):
            for j in range(max_goals):

                if i > j:
                    p_home += matrix[i, j]
                elif i == j:
                    p_draw += matrix[i, j]
                else:
                    p_away += matrix[i, j]

        markets["1X2:Home"] = p_home
        markets["1X2:Draw"] = p_draw
        markets["1X2:Away"] = p_away

        btts_yes = 0
        for i in range(1, max_goals):
            for j in range(1, max_goals):
                btts_yes += matrix[i, j]

        markets["BTTS:Yes"] = btts_yes
        markets["BTTS:No"] = 1 - btts_yes

        for line in np.arange(0.5, MAX_GOALS, 1.0):

            over = 0
            for i in range(max_goals):
                for j in range(max_goals):
                    if (i + j) > line:
                        over += matrix[i, j]

            markets[f"OU:{line}:Over"] = over
            markets[f"OU:{line}:Under"] = 1 - over

        return markets

    # --------------------------------
    # CALIBRATION
    # --------------------------------
    def calibrate(self, prob):

        return (
            prob * self.calibration_factor +
            (1 - self.calibration_factor) * 0.5
        )

    # --------------------------------
    # PIPELINE
    # --------------------------------
    def price_match(self, lambda_home, lambda_away):

        matrix = self.build_matrix(lambda_home, lambda_away)
        markets = self.derive_markets(matrix)

        return {k: self.calibrate(v) for k, v in markets.items()}
