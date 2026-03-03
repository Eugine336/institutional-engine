import numpy as np


class ValidationEngine:

    def __init__(self, window=200):

        self.window = window

        self.probs = []
        self.outcomes = []
        self.entry_odds = []
        self.closing_odds = []
        self.edges = []

    # --------------------------------
    # RECORD TRADE
    # --------------------------------
    def record(self, prob, outcome, entry_odds, closing_odds, edge):

        self.probs.append(prob)
        self.outcomes.append(outcome)
        self.entry_odds.append(entry_odds)
        self.closing_odds.append(closing_odds)
        self.edges.append(edge)

        # keep rolling window
        if len(self.probs) > self.window:
            self.probs.pop(0)
            self.outcomes.pop(0)
            self.entry_odds.pop(0)
            self.closing_odds.pop(0)
            self.edges.pop(0)

    # --------------------------------
    # BRIER SCORE
    # --------------------------------
    def brier_score(self):

        if not self.probs:
            return 0

        p = np.array(self.probs)
        y = np.array(self.outcomes)

        return np.mean((p - y) ** 2)

    # --------------------------------
    # LOG LOSS
    # --------------------------------
    def log_loss(self):

        if not self.probs:
            return 0

        eps = 1e-9
        p = np.clip(np.array(self.probs), eps, 1 - eps)
        y = np.array(self.outcomes)

        return -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))

    # --------------------------------
    # CLV
    # --------------------------------
    def average_clv(self):

        if not self.closing_odds:
            return 0

        entry_implied = 1 / np.array(self.entry_odds)
        close_implied = 1 / np.array(self.closing_odds)

        return np.mean(close_implied - entry_implied)

    # --------------------------------
    # REALIZED EDGE
    # --------------------------------
    def realized_edge(self):

        if not self.probs:
            return 0

        expected = np.mean(self.probs)
        actual = np.mean(self.outcomes)

        return actual - expected

    # --------------------------------
    # SUMMARY
    # --------------------------------
    def summary(self):

        return {
            "brier": self.brier_score(),
            "log_loss": self.log_loss(),
            "avg_clv": self.average_clv(),
            "edge_gap": self.realized_edge()
        }
