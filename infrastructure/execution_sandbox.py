import sqlite3
import random
from datetime import datetime, timezone


class ExecutionSandbox:

    def __init__(self):

        self.conn = sqlite3.connect("data/execution_log.db")
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._init_db()

        self.commission_rate = 0.02

    # -----------------------------------------
    # DATABASE INIT (WITH MODEL STORAGE)
    # -----------------------------------------
    def _init_db(self):

        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                fixture_id INTEGER,
                league INTEGER,
                market TEXT,
                odds REAL,
                model_prob REAL,
                edge REAL,
                stake REAL,
                filled_stake REAL,
                closing_odds REAL,
                status TEXT,
                pnl REAL,
                UNIQUE(fixture_id, market)
            )
        """)

        self.conn.commit()

    # -----------------------------------------
    # PLACE ORDER (STORE MODEL DATA)
    # -----------------------------------------
    def place_order(
        self,
        fixture_id,
        league,
        market,
        odds,
        stake,
        model_prob,
        edge
    ):

        fill_ratio = random.uniform(0.85, 1.0)
        filled_stake = stake * fill_ratio

        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO trades (
                    timestamp,
                    fixture_id,
                    league,
                    market,
                    odds,
                    model_prob,
                    edge,
                    stake,
                    filled_stake,
                    closing_odds,
                    status,
                    pnl
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                fixture_id,
                league,
                market,
                odds,
                model_prob,
                edge,
                stake,
                filled_stake,
                None,
                "OPEN",
                None
            ))

            self.conn.commit()
            return cursor.lastrowid

        except sqlite3.IntegrityError:
            return None

    # -----------------------------------------
    # GET OPEN TRADES (VALIDATION READY)
    # -----------------------------------------
    def get_open_trades(self):

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT id,
                   fixture_id,
                   market,
                   odds,
                   filled_stake,
                   model_prob,
                   edge
            FROM trades
            WHERE status='OPEN'
        """)

        return cursor.fetchall()

    # -----------------------------------------
    # SETTLE TRADE
    # -----------------------------------------
    def settle_bet(self, trade_id, win, closing_odds=None):

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT odds, filled_stake
            FROM trades
            WHERE id=? AND status='OPEN'
        """, (trade_id,))

        row = cursor.fetchone()

        if not row:
            return None

        odds, stake = row

        if win:
            gross_profit = stake * (odds - 1)
            commission = gross_profit * self.commission_rate
            pnl = gross_profit - commission
        else:
            pnl = -stake

        cursor.execute("""
            UPDATE trades
            SET status='CLOSED',
                pnl=?,
                closing_odds=?
            WHERE id=?
        """, (pnl, closing_odds, trade_id))

        self.conn.commit()

        return pnl

    # -----------------------------------------
    # FETCH CLOSED TRADES
    # -----------------------------------------
    def get_closed_trades(self):

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT odds,
                   model_prob,
                   edge,
                   closing_odds,
                   pnl
            FROM trades
            WHERE status='CLOSED'
        """)

        return cursor.fetchall()
