class PlayerAdjustmentEngine:

    def __init__(self):
        pass

    def lineup_adjustment(self, team_news=None):

        if not team_news:
            return 1.0, 1.0

        attack_penalty = 1 - (0.07 * team_news.get("missing_attackers", 0))
        defense_penalty = 1 + (0.05 * team_news.get("missing_defenders", 0))
        rotation_penalty = 1 - team_news.get("rotation", 0)

        attack_factor = attack_penalty * rotation_penalty
        defense_factor = defense_penalty

        return max(0.75, attack_factor), min(1.30, defense_factor)

    def fatigue_adjustment(self, days_rest):

        if days_rest >= 6:
            return 1.02
        if days_rest <= 3:
            return 0.95
        return 1.0
