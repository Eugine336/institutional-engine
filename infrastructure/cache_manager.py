import os
import json


class CacheManager:

    def __init__(self, base_path="data/cache"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    # ==========================================================
    # INTERNAL UTIL
    # ==========================================================

    def _safe_load(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Cache corrupted, deleting: {path}")
            try:
                os.remove(path)
            except:
                pass
            return None

    def _safe_save(self, path, data):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Cache save failed: {path}", str(e))

    # ==========================================================
    # FIXTURE CACHE
    # ==========================================================

    def _fixture_path(self, date):
        return os.path.join(self.base_path, f"fixtures_{date}.json")

    def load_fixtures(self, date):
        path = self._fixture_path(date)

        if not os.path.exists(path):
            return None

        print("Loaded fixtures from cache.")
        return self._safe_load(path)

    def save_fixtures(self, date, data):
        path = self._fixture_path(date)
        self._safe_save(path, data)
        print("Fixtures cached locally.")

    # ==========================================================
    # ODDS CACHE
    # ==========================================================

    def _odds_path(self, fixture_id):
        return os.path.join(self.base_path, f"odds_{fixture_id}.json")

    def load_odds(self, fixture_id):
        path = self._odds_path(fixture_id)

        if not os.path.exists(path):
            return None

        return self._safe_load(path)

    def save_odds(self, fixture_id, data):
        path = self._odds_path(fixture_id)
        self._safe_save(path, data)

    # ==========================================================
    # OPTIONAL: CLEAR CACHE
    # ==========================================================

    def clear_cache(self):
        for file in os.listdir(self.base_path):
            file_path = os.path.join(self.base_path, file)
            try:
                os.remove(file_path)
            except:
                pass
        print("Cache cleared.")
