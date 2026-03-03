import requests
import time
import sqlite3
from datetime import datetime, timezone


class APIFootballClient:

    def __init__(self, api_key):

        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {"x-apisports-key": api_key}

        # ----------------------------
        # Rate Control
        # ----------------------------
        self.per_minute_limit = 10
        self.minute_window = []

        self.server_limit = None
        self.server_remaining = None

        # ----------------------------
        # Infrastructure DB
        # ----------------------------
        self.conn = sqlite3.connect("data/api_cache.db")
        self._init_db()
        self._load_server_quota()

    # --------------------------------
    # DATABASE
    # --------------------------------
    def _init_db(self):

        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quota (
                day TEXT PRIMARY KEY,
                limit_total INTEGER,
                remaining INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_log (
                timestamp TEXT,
                endpoint TEXT,
                status INTEGER
            )
        """)

        self.conn.commit()

    def _today(self):
        return str(datetime.now(timezone.utc).date())

    def _load_server_quota(self):

        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT limit_total, remaining
            FROM quota WHERE day=?
        """, (self._today(),))

        row = cursor.fetchone()

        if row:
            self.server_limit, self.server_remaining = row

    def _save_server_quota(self):

        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO quota
            VALUES (?, ?, ?)
        """, (
            self._today(),
            self.server_limit,
            self.server_remaining
        ))

        self.conn.commit()

    def _log_request(self, endpoint, status):

        cursor = self.conn.cursor()

        cursor.execute("""
            INSERT INTO request_log
            VALUES (?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            endpoint,
            status
        ))

        self.conn.commit()

    # --------------------------------
    # THROTTLE
    # --------------------------------
    def _throttle(self):

        now = time.time()

        self.minute_window = [
            t for t in self.minute_window if now - t < 60
        ]

        if len(self.minute_window) >= self.per_minute_limit:
            sleep_time = 60 - (now - self.minute_window[0])
            if sleep_time > 0:
                time.sleep(sleep_time)

        self.minute_window.append(time.time())

    # --------------------------------
    # QUOTA CHECK
    # --------------------------------
    def _check_server_quota(self):

        if self.server_remaining is not None:
            if self.server_remaining <= 0:
                raise Exception("Daily API quota exhausted.")

    # --------------------------------
    # REQUEST CORE (WITH RETRY)
    # --------------------------------
    def request(self, endpoint, params, retries=3):
        print(f"Calling API:{endpoint}|Params:{params}")

        self._check_server_quota()
        self._throttle()

        url = f"{self.base_url}/{endpoint}"

        for attempt in range(retries):

            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=10
                )
                print("Response status:",response.status_code)

                self._log_request(endpoint, response.status_code)

                # Handle rate limiting
                if response.status_code == 429:
                    time.sleep(5 * (attempt + 1))
                    continue

                response.raise_for_status()

                self._update_quota_from_headers(response.headers)
                return response.json()

            except requests.exceptions.RequestException:

                if attempt == retries - 1:
                    raise

                time.sleep(2 * (attempt + 1))

        raise Exception("API request failed after retries.")

    # --------------------------------
    # HEADER PARSING
    # --------------------------------
    def _update_quota_from_headers(self, headers):

        if "x-ratelimit-requests-limit" in headers:
            self.server_limit = int(
                headers["x-ratelimit-requests-limit"]
            )

        if "x-ratelimit-requests-remaining" in headers:
            self.server_remaining = int(
                headers["x-ratelimit-requests-remaining"]
            )

        self._save_server_quota()

    # --------------------------------
    # WRAPPERS
    # --------------------------------
    def get_fixtures(self, date, league=None):

        year = int(date[:4])

        params = {
            "date": date
        }

        return self.request("fixtures", params)

    def get_odds(self, fixture_id):

        return self.request(
            "odds",
            {"fixture": fixture_id}
        )
