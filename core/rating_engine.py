import numpy as np
import sqlite3
from config import *

class RatingEngine:

    def __init__(self):

        self.conn = sqlite3.connect("data/institutional_memory.db")
        self._init_db()

        # State-space parameters
        self.drift = 0.0005
        self.state_noise = 0.01
        self.learning_rate = 0.03

        # Hierarchical shrinkage
        self.shrink_strength = 0.01

        self.league_config = {
            39: {"avg": 2.8, "ha": 1.12},
            140: {"avg": 2.6, "ha": 1.10},
            78: {"avg": 3.1, "ha": 1.08},
            135: {"avg": 2.4, "ha": 1.10},
            61: {"avg": 2.3, "ha": 1.09}
        }

    # ------------------------------------------------
    # DATABASE
    # ------------------------------------------------
    def _init_db(self):
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_ratings (
                team_id INTEGER PRIMARY KEY,
                attack REAL,
                defense REAL,
                league INTEGER
            )
        """)
        self.conn.commit()

    def _get_team(self, team_id, league):

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT attack, defense
            FROM team_ratings
            WHERE team_id=?
        """, (team_id,))

        row = cursor.fetchone()

        if row:
            return row[0], row[1]

        cursor.execute("""
            INSERT INTO team_ratings
            VALUES (?, ?, ?, ?)
        """, (team_id, 1.0, 1.0, league))

        self.conn.commit()
        return 1.0, 1.0

    def _save_team(self, team_id, attack, defense, league):

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO team_ratings
            VALUES (?, ?, ?, ?)
        """, (team_id, attack, defense, league))

        self.conn.commit()

    # ------------------------------------------------
    # HIERARCHICAL LEAGUE MEAN
    # ------------------------------------------------
    def _league_mean(self, league):

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT attack, defense
            FROM team_ratings
            WHERE league=?
        """, (league,))

        rows = cursor.fetchall()

        if not rows:
            return 1.0, 1.0

        attacks = [r[0] for r in rows]
        defenses = [r[1] for r in rows]

        return np.mean(attacks), np.mean(defenses)

    # ------------------------------------------------
    # STATE EVOLUTION
    # ------------------------------------------------
    def _evolve(self, value):

        noise = np.random.normal(0, self.state_noise)
        value += self.drift + noise

        return np.clip(value, 0.4, 2.5)

    # ------------------------------------------------
    # LAMBDA GENERATION
    # ------------------------------------------------
    def get_lambdas(self, league, home_id, away_id):

        config = self.league_config.get(league)
        if not config:
            return 1.3, 1.1

        league_avg = config["avg"]
        home_adv = config["ha"]

        home_att, home_def = self._get_team(home_id, league)
        away_att, away_def = self._get_team(away_id, league)

        lambda_home = home_att * away_def * home_adv * (league_avg / 2)
        lambda_away = away_att * home_def * (league_avg / 2)

        return lambda_home, lambda_away

    # ------------------------------------------------
    # UPDATE
    # ------------------------------------------------
    def update_ratings(self, league, home_id, away_id,
                       home_goals, away_goals):

        home_att, home_def = self._get_team(home_id, league)
        away_att, away_def = self._get_team(away_id, league)

        home_att = self._evolve(home_att)
        home_def = self._evolve(home_def)
        away_att = self._evolve(away_att)
        away_def = self._evolve(away_def)

        lambda_home, lambda_away = self.get_lambdas(
            league, home_id, away_id
        )

        error_home = (home_goals - lambda_home) / max(lambda_home, 0.5)
        error_away = (away_goals - lambda_away) / max(lambda_away, 0.5)

        home_att += self.learning_rate * error_home
        away_def += self.learning_rate * error_home

        away_att += self.learning_rate * error_away
        home_def += self.learning_rate * error_away

        mean_att, mean_def = self._league_mean(league)

        home_att += self.shrink_strength * (mean_att - home_att)
        home_def += self.shrink_strength * (mean_def - home_def)

        away_att += self.shrink_strength * (mean_att - away_att)
        away_def += self.shrink_strength * (mean_def - away_def)

        home_att = np.clip(home_att, 0.4, 2.5)
        home_def = np.clip(home_def, 0.4, 2.5)
        away_att = np.clip(away_att, 0.4, 2.5)
        away_def = np.clip(away_def, 0.4, 2.5)

        self._save_team(home_id, home_att, home_def, league)
        self._save_team(away_id, away_att, away_def, league)
