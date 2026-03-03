import numpy as np


class MetaEngine:

    def __init__(self):

        # -----------------------------
        # Tracking Buffers
        # -----------------------------
        self.edges = []
        self.returns = []
        self.clv_history = []
        self.outcomes = []
        self.probs = []

        self.window = 50

        # -----------------------------
        # Regime State
        # -----------------------------
        self.state = "NORMAL"
        self.state_duration = 0
        self.cooldown_period = 20

        # -----------------------------
        # Smoothed Metrics
        # -----------------------------
        self.smoothed_sharpe = 0
        self.smoothed_clv = 0
        self.smoothed_brier = 0

    # ==========================================================
    # RECORDING INPUTS
    # ==========================================================

    def record_edge(self, edge):
        self.edges.append(edge)

    def record_return(self, pnl):
        self.returns.append(pnl)

    def record_clv(self, model_prob, closing_odds):
        if closing_odds and closing_odds > 0:
            implied_close = 1 / closing_odds
            self.clv_history.append(model_prob - implied_close)

    def record_prediction(self, prob, outcome):
        self.probs.append(prob)
        self.outcomes.append(outcome)

    # ==========================================================
    # METRICS
    # ==========================================================

    def rolling_sharpe(self):

        if len(self.returns) < self.window:
            return 0

        r = np.array(self.returns[-self.window:])
        if r.std() == 0:
            return 0

        raw = r.mean() / r.std()

        alpha = 0.2
        self.smoothed_sharpe = (
            alpha * raw +
            (1 - alpha) * self.smoothed_sharpe
        )

        return self.smoothed_sharpe

    def profit_factor(self):

        if len(self.returns) < self.window:
            return 1.0

        r = np.array(self.returns[-self.window:])
        gains = r[r > 0].sum()
        losses = -r[r < 0].sum()

        if losses == 0:
            return 2.0

        return gains / losses

    def brier_score(self):

        if len(self.probs) < self.window:
            return 0.25  # neutral

        p = np.array(self.probs[-self.window:])
        o = np.array(self.outcomes[-self.window:])

        raw = np.mean((p - o) ** 2)

        alpha = 0.2
        self.smoothed_brier = (
            alpha * raw +
            (1 - alpha) * self.smoothed_brier
        )

        return self.smoothed_brier

    def edge_decay(self):

        if len(self.edges) < 2 * self.window:
            return 0

        recent = np.mean(self.edges[-self.window:])
        older = np.mean(self.edges[-2*self.window:-self.window])

        return recent - older

    def clv_score(self):

        if len(self.clv_history) < self.window:
            return 0

        raw = np.mean(self.clv_history[-self.window:])

        alpha = 0.2
        self.smoothed_clv = (
            alpha * raw +
            (1 - alpha) * self.smoothed_clv
        )

        return self.smoothed_clv

    # ==========================================================
    # ADAPTIVE GOVERNANCE
    # ==========================================================

    def adapt(self, risk):

        sharpe = self.rolling_sharpe()
        pf = self.profit_factor()
        brier = self.brier_score()
        decay = self.edge_decay()
        clv = self.clv_score()

        drawdown = (risk.peak - risk.bankroll) / risk.peak

        self.state_duration += 1

        # ------------------------------------------------------
        # REGIME CLASSIFICATION
        # ------------------------------------------------------

        if drawdown > 0.25 or sharpe < -0.5:
            new_state = "DEFENSIVE"

        elif sharpe > 0.6 and pf > 1.3 and clv > 0:
            new_state = "AGGRESSIVE"

        else:
            new_state = "NORMAL"

        # Hysteresis
        if new_state != self.state:
            if self.state_duration >= self.cooldown_period:
                self.state = new_state
                self.state_duration = 0
        # else remain

        # ------------------------------------------------------
        # MULTIPLIER LOGIC
        # ------------------------------------------------------

        multiplier = 1.0

        # Regime baseline
        if self.state == "DEFENSIVE":
            multiplier *= 0.65
        elif self.state == "AGGRESSIVE":
            multiplier *= 1.20

        # Sharpe scaling
        multiplier *= max(0.6, min(1.4, 1 + sharpe * 0.25))

        # Profit factor scaling
        multiplier *= max(0.7, min(1.3, 1 + (pf - 1) * 0.3))

        # Brier penalty (model accuracy)
        # Lower Brier is better
        if brier > 0:
            multiplier *= max(0.6, min(1.2, 1 - (brier - 0.25) * 2))

        # CLV scaling
        multiplier *= max(0.7, min(1.4, 1 + clv * 30))

        # Edge decay penalty
        if decay < 0:
            multiplier *= 0.85

        # Drawdown compression
        if drawdown > 0.15:
            multiplier *= 0.75

        # Hard capital protection
        if drawdown > 0.30:
            multiplier = 0.4

        # Bound
        multiplier = max(0.4, min(multiplier, 1.6))

        # ------------------------------------------------------
        # APPLY TO RISK ENGINE
        # ------------------------------------------------------

        risk.adjust_kelly(multiplier)

    # ==========================================================
    # EXPORT METRICS (FOR DASHBOARD / TELEGRAM)
    # ==========================================================

    def metrics(self):

        return {
            "state": self.state,
            "sharpe": round(self.smoothed_sharpe, 3),
            "clv": round(self.smoothed_clv, 4),
            "brier": round(self.smoothed_brier, 4),
            "profit_factor": round(self.profit_factor(), 3)
        }
