from config import *
import numpy as np


class RiskEngine:

    def __init__(self, initial_bankroll):

        self.bankroll = initial_bankroll
        self.peak = initial_bankroll

        self.kelly_fraction = BASE_KELLY_FRACTION

        self.max_drawdown = MAX_DRAWDOWN_LIMIT
        self.max_daily_exposure = MAX_DAILY_EXPOSURE
        self.max_bet_fraction = MAX_SINGLE_BET_FRACTION

        self.daily_exposure = 0
        self.equity_curve = []

    # -----------------------------------------
    # DAILY RESET
    # -----------------------------------------
    def reset_daily(self):
        self.daily_exposure = 0

    # -----------------------------------------
    # COMPUTE STAKE
    # -----------------------------------------
    def compute_stake(self, edge, weight):

        if self.bankroll <= 0:
            return 0

        if edge <= 0:
            return 0

        stake_fraction = self.kelly_fraction * weight * edge
        stake_fraction = min(stake_fraction, self.max_bet_fraction)

        if (self.daily_exposure + stake_fraction) > self.max_daily_exposure:
            return 0

        stake = self.bankroll * stake_fraction
        self.daily_exposure += stake_fraction

        return max(stake, 0)

    # -----------------------------------------
    # SETTLE TRADE
    # -----------------------------------------
    def settle_trade(self, pnl):

        self.bankroll += pnl
        self.equity_curve.append(self.bankroll)

        if self.bankroll > self.peak:
            self.peak = self.bankroll

        drawdown = (self.peak - self.bankroll) / self.peak

        # Hard drawdown protection
        if drawdown > self.max_drawdown:
            self.kelly_fraction = MIN_KELLY_FRACTION

        # Clamp Kelly within allowed range
        self.kelly_fraction = max(
            MIN_KELLY_FRACTION,
            min(self.kelly_fraction, MAX_KELLY_FRACTION)
        )

    # -----------------------------------------
    # META ENGINE KELLY ADJUSTMENT
    # -----------------------------------------
    def adjust_kelly(self, multiplier):

        self.kelly_fraction *= multiplier

        # Clamp after adjustment
        self.kelly_fraction = max(
            MIN_KELLY_FRACTION,
            min(self.kelly_fraction, MAX_KELLY_FRACTION)
        )
