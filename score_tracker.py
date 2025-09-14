# score_tracker.py
import os
import json
from datetime import datetime
import pandas as pd
from espn_api.football import League


def load_config_and_env():
    """Load credentials and options from env, then config.json (if present)."""
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")
    year_env = os.getenv("YEAR")
    week_env = os.getenv("WEEK")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")

    print("[DEBUG] Checking environment variables...")
    print(f"  ESPN_S2: {'SET' if espn_s2 else 'NOT SET'}")
    print(f"  SWID: {'SET' if swid else 'NOT SET'}")
    print(f"  YEAR: {year_env if year_env else 'NOT SET'}")
    print(f"  WEEK: {week_env if week_env else 'NOT SET'}")

    cfg = {}
    if os.path.exists(config_path):
        try:
            print(f"[DEBUG] Loading config.json from {config_path}...")
            with open(config_path, "r") as f:
                cfg = json.load(f)
            print("[DEBUG] Loaded credentials/options from config.json")
        except Exception as e:
            print(f"[WARN] Could not read config.json: {e}")

    espn_s2 = espn_s2 or cfg.get("espn_s2")
    swid = swid or cfg.get("swid")
    year = year_env or cfg.get("year")
    week = week_env or cfg.get("week")

    if not espn_s2 or not swid:
        raise RuntimeError("Missing ESPN_S2/SWID; set env vars or put them in config.json")

    # If year isn't provided, assume current calendar year as a reasonable default
    if not year:
        year = str(datetime.now().year)
        print(f"[DEBUG] YEAR not provided; defaulting to {year}")

    # Normalize types
    year_int = int(year)
    week_int = int(week) if (week is not None and str(week).isdigit()) else None

    print("[DEBUG] Using credentials/options:")
    print(f"  ESPN_S2 (first 20): {espn_s2[:20]}...")
    print(f"  SWID: {swid}")
    print(f"  YEAR: {year_int}")
    if week_int:
        print(f"  WEEK: {week_int}")

    return espn_s2, swid, year_int, week_int, script_dir


def get_week_candidates(league, week_hint=None):
    """Build a list of week candidates to try (hint, current, current-1)."""
    try:
        current_week = getattr(league, "current_week", None)
    except Exception:
        current_week = None

    print(f"[DEBUG] League name: {league.settings.name}")
    print(f"[DEBUG] current_week from API: {current_week}")

    candidates = []
    if week_hint:
        candidates.append(week_hint)
    if current_week and current_week not in candidates:
        candidates.append(current_week)
    # Fallback: try previous week so you see data outside live windows
    if current_week and current_week - 1 > 0 and (current_week - 1) not in candidates:
        candidates.append(current_week - 1)

    if not candidates:
        candidates = [None]  # final fallback

    print(f"[DEBUG] Week candidates to try (in order): {candidates}")
    return candidates


def fetch_matchup_rows(league, week_candidates):
    """
    Prefer live totals from box_scores(). If b.home_score/b.away_score are
    missing/zero, compute from starters' lineups (sum of player.points).
    Fall back to scoreboard() only if needed.
    """
    from math import isfinite
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def sum_starter_points(lineup):
        total = 0.0
        for p in lineup:
            # slot_position 'BE' (bench) should not count; 'IR' also excluded
            slot = getattr(p, "slot_position", None)
            if slot in ("BE", "IR"):
                continue
            pts = getattr(p, "points", 0.0) or 0.0
            # guard against NaN
            try:
                if not isfinite(pts):
                    pts = 0.0
            except Exception:
                pass
            total += float(pts)
        return round(total, 2)

    # 1) Try box_scores first (best for live)
    for w in week_candidates:
        try:
            bs = league.box_scores(week=w) if w else league.box_scores()
            print(f"[DEBUG] box_scores(week={w}) -> {len(bs)} matchups")

            rows = []
            for b in bs:
                h, a = b.home_team, b.away_team

                # ESPN sometimes gives zeros/None mid-refresh; compute from lineup as backup
                hs = b.home_score if (b.home_score is not None and b.home_score > 0) else sum_starter_points(b.home_lineup)
                as_ = b.away_score if (b.away_score is not None and b.away_score > 0) else sum_starter_points(b.away_lineup)

                print(f"[DEBUG] Live: {h.team_name} {hs} vs {a.team_name} {as_}")
                rows.append({
                    "timestamp": ts,
                    "week": w if w is not None else getattr(league, "current_week", None),
                    "home_team": h.team_name,
                    "home_score": hs,
                    "away_team": a.team_name,
                    "away_score": as_,
                })
            if rows:
                return rows, w
        except Exception as e:
            print(f"[ERROR] box_scores(week={w}) failed: {e}")

    # 2) Fallback to scoreboard (useful for completed weeks / after boxscore downtime)
    for w in week_candidates:
        try:
            sb = league.scoreboard(week=w) if w else league.scoreboard()
            print(f"[DEBUG] scoreboard(week={w}) -> {len(sb)} matchups")
            rows = []
            for m in sb:
                h, a = m.home_team, m.away_team
                print(f"[DEBUG] Scoreboard: {h.team_name} {m.home_score} vs {a.team_name} {m.away_score}")
                rows.append({
                    "timestamp": ts,
                    "week": w if w is not None else getattr(league, "current_week", None),
                    "home_team": h.team_name,
                    "home_score": m.home_score,
                    "away_team": a.team_name,
                    "away_score": m.away_score,
                })
            if rows:
                return rows, w
        except Exception as e:
            print(f"[ERROR] scoreboard(week={w}) failed: {e}")

    print("[DEBUG] No matchup data found from box_scores or scoreboard.")
    return [], None


def main():
    espn_s2, swid, year, week_hint, script_dir = load_config_and_env()

    print("[DEBUG] Initializing League...")
    league = League(league_id=31028552, year=year, espn_s2=espn_s2, swid=swid)
    print("[DEBUG] League initialized.")

    week_candidates = get_week_candidates(league, week_hint)
    rows, used_week = fetch_matchup_rows(league, week_candidates)

    df = pd.DataFrame(rows, columns=[
        "timestamp", "week", "home_team", "home_score", "away_team", "away_score"
    ])
    print("[DEBUG] DataFrame:")
    print(df if not df.empty else "[DEBUG] (empty)")

    csv_path = os.path.join(script_dir, "scores.csv")
    header = not os.path.exists(csv_path)
    print(f"[DEBUG] Writing to {csv_path} (header={header})")
    df.to_csv(csv_path, mode="a", index=False, header=header)
    print("[DEBUG] Write complete")

    if used_week is None:
        print("[INFO] Tip: Set WEEK explicitly (env or config.json) if you want a specific week.")


if __name__ == "__main__":
    main()
