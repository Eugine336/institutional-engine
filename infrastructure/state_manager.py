import os
import json


class StateManager:

    def __init__(self, path="data/system_state.json", history_cap=300):
        self.path = path
        self.history_cap = history_cap

        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    # --------------------------------------------------
    # LOAD STATE
    # --------------------------------------------------

    def load(self):

        if not os.path.exists(self.path):
            print("No previous system state found.")
            return None

        try:
            with open(self.path, "r") as f:
                state = json.load(f)

            print("Persistent state loaded.")
            return state

        except Exception as e:
            print("State load failed (corrupt file):", str(e))
            return None

    # --------------------------------------------------
    # SAVE STATE
    # --------------------------------------------------

    def save(self, risk, meta):

        try:
            state = {
                "bankroll": risk.bankroll,
                "peak": risk.peak,
                "kelly_fraction": risk.kelly_fraction,
                "meta_state": meta.state,
                "edges": meta.edges[-self.history_cap:],
                "returns": meta.returns[-self.history_cap:],
                "clv": meta.clv_history[-self.history_cap:]
            }

            with open(self.path, "w") as f:
                json.dump(state, f, indent=4)

            print("Persistent state saved.")

        except Exception as e:
            print("State save failed:", str(e))
