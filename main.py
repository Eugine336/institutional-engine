from config import *
from datetime import datetime, timezone

from infrastructure.api_client import APIFootballClient
from infrastructure.execution_sandbox import ExecutionSandbox
from infrastructure.backup_engine import GoogleBackupEngine
from infrastructure.telegram_notifier import TelegramNotifier
from infrastructure.slip_generator import SlipGenerator
from infrastructure.cache_manager import CacheManager
from infrastructure.state_manager import StateManager

from core.rating_engine import RatingEngine
from core.pricing_engine import PricingEngine
from core.portfolio_engine import PortfolioEngine
from core.risk_engine import RiskEngine
from core.meta_engine import MetaEngine
from core.player_adjustment_engine import PlayerAdjustmentEngine
from core.validation_engine import ValidationEngine


def main():

    print("\n================ ENGINE START =================\n")

    api = APIFootballClient(API_KEY)
    cache = CacheManager()
    state_manager = StateManager()

    sandbox = ExecutionSandbox()
    backup = GoogleBackupEngine()
    telegram = TelegramNotifier()
    slip = SlipGenerator()

    rating = RatingEngine()
    pricing = PricingEngine()
    portfolio = PortfolioEngine()
    risk = RiskEngine(INITIAL_BANKROLL)
    meta = MetaEngine()
    validation = ValidationEngine()
    player_adjustment = PlayerAdjustmentEngine()

    today = "2026-03-02"
    print("Trading Date (UTC):", today)

    # --------------------------------------------------
    # LOAD STATE
    # --------------------------------------------------

    saved = state_manager.load()

    if saved:
        risk.bankroll = saved["bankroll"]
        risk.peak = saved["peak"]
        risk.kelly_fraction = saved["kelly_fraction"]
        meta.state = saved["meta_state"]
        meta.edges = saved["edges"]
        meta.returns = saved["returns"]
        meta.clv_history = saved["clv"]

    risk.reset_daily()
    opportunities = []

    # --------------------------------------------------
    # FETCH FIXTURES (CACHED)
    # --------------------------------------------------

    data = cache.load_fixtures(today)

    if not data:
        try:
            data = api.get_fixtures(today)
            cache.save_fixtures(today, data)
        except Exception as e:
            print("Fixture fetch failed:", e)
            return

    fixtures = data.get("response", [])
    print("Total fixtures:", len(fixtures))

    # --------------------------------------------------
    # SCAN MARKETS
    # --------------------------------------------------

    for f in fixtures:

        league = f["league"]["id"]
        if league not in APPROVED_LEAGUES:
            continue

        fixture_id = f["fixture"]["id"]
        home = f["teams"]["home"]["name"]
        away = f["teams"]["away"]["name"]

        lambda_home, lambda_away = rating.get_lambdas(
            league,
            f["teams"]["home"]["id"],
            f["teams"]["away"]["id"]
        )

        markets = pricing.price_match(lambda_home, lambda_away)

        odds_data = cache.load_odds(fixture_id)

        if not odds_data:
            try:
                odds_data = api.get_odds(fixture_id)
                cache.save_odds(fixture_id, odds_data)
            except:
                continue

        bookmakers = odds_data.get("response", [])
        if not bookmakers:
            continue

        try:
            bets = bookmakers[0]["bookmakers"][0]["bets"]
        except:
            continue

        for bet in bets:
            for val in bet["values"]:

                odds = float(val["odd"])

                if bet["name"] == "Match Winner":
                    mapping = {
                        "Home": "1X2:Home",
                        "Draw": "1X2:Draw",
                        "Away": "1X2:Away"
                    }
                    key = mapping.get(val["value"])
                    if not key:
                        continue

                elif bet["name"] == "Both Teams To Score":
                    mapping = {
                        "Yes": "BTTS:Yes",
                        "No": "BTTS:No"
                    }
                    key = mapping.get(val["value"])
                    if not key:
                        continue

                elif "Over/Under" in bet["name"]:
                    parts = val["value"].split(" ")
                    if len(parts) != 2:
                        continue
                    side = parts[0]
                    line = parts[1]
                    key = f"OU:{line}:{side}"
                else:
                    continue

                if key not in markets:
                    continue

                prob = markets[key]
                implied = 1 / odds
                edge = prob - implied

                if edge > MIN_EDGE:
                    opportunities.append({
                        "fixture_id": fixture_id,
                        "league": league,
                        "home": home,
                        "away": away,
                        "market": key,
                        "odds": odds,
                        "prob": prob,
                        "edge": edge
                    })

                    meta.record_edge(edge)

    selected = portfolio.optimize(opportunities)

    # --------------------------------------------------
    # EXECUTION
    # --------------------------------------------------

    for bet in selected:

        stake = risk.compute_stake(
            bet["edge"],
            bet["stake_fraction"]
        )

        if stake <= 0:
            continue

        trade_id = sandbox.place_order(
            fixture_id=bet["fixture_id"],
            league=bet["league"],
            market=bet["market"],
            odds=bet["odds"],
            stake=stake,
            model_prob=bet["prob"],
            edge=bet["edge"]
        )

        if trade_id is None:
            continue

        telegram.send_trade(
            bet["league"],
            f"{bet['home']} vs {bet['away']}",
            bet["market"],
            today,
            bet["odds"],
            stake
        )

        slip.add_bet(
            bet["league"],
            bet["home"],
            bet["away"],
            bet["market"],
            today
        )

    # --------------------------------------------------
    # SETTLEMENT + VALIDATION
    # --------------------------------------------------

    open_trades = sandbox.get_open_trades()

    for trade in open_trades:

        trade_id, fixture_id, market, odds, stake, model_prob, edge = trade

        try:
            result = api.get_fixtures(today)
        except:
            continue

        for f in result.get("response", []):

            if f["fixture"]["id"] != fixture_id:
                continue

            if f["fixture"]["status"]["short"] != "FT":
                continue

            home_goals = f["goals"]["home"]
            away_goals = f["goals"]["away"]

            win = False

            if market == "1X2:Home":
                win = home_goals > away_goals
            elif market == "1X2:Draw":
                win = home_goals == away_goals
            elif market == "1X2:Away":
                win = home_goals < away_goals

            pnl = sandbox.settle_bet(trade_id, win)

            if pnl is not None:

                risk.settle_trade(pnl)

                validation.record(
                    prob=model_prob,
                    outcome=1 if win else 0,
                    entry_odds=odds,
                    closing_odds=odds,
                    edge=edge
                )

                meta.record_return(pnl)

    metrics = validation.summary()
    print("Validation metrics:", metrics)

    meta.adapt(risk)

    telegram.send_summary(
        risk.bankroll,
        risk.kelly_fraction,
        meta.state
    )

    state_manager.save(risk, meta)
    backup.backup_database()

    print("\n================ ENGINE END =================\n")


if __name__ == "__main__":
    main()
