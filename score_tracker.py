import os
import json
from espn_api.football import League
from datetime import datetime
import pandas as pd

# ---- Credential Loading ----
espn_s2 = os.getenv("ESPN_S2")
swid = os.getenv("SWID")

print("[DEBUG] Checking environment variables...")
print(f"  ESPN_S2: {'SET' if espn_s2 else 'NOT SET'}")
print(f"  SWID: {'SET' if swid else 'NOT SET'}")

if not espn_s2 or not swid:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    print(f"[DEBUG] Loading config.json from {config_path}...")
    with open(config_path) as f:
        config = json.load(f)
        espn_s2 = config["espn_s2"]
        swid = config["swid"]
    print("[DEBUG] Loaded credentials from config.json")

print(f"[DEBUG] Using credentials:")
print(f"  ESPN_S2 (first 20 chars): {espn_s2[:20]}...")
print(f"  SWID: {swid}")

# ---- League Initialization ----
try:
    print("[DEBUG] Initializing League...")
    league = League(league_id=31028552, year=2024, espn_s2=espn_s2, swid=swid)
    print(f"[DEBUG] League initialized. Name: {league.settings.name}")
except Exception as e:
    print("[ERROR] League initialization failed:", e)
    raise

# ---- Scoreboard Fetch ----
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"[DEBUG] Current timestamp: {timestamp}")

rows = []
try:
    scoreboard = league.scoreboard()
    print(f"[DEBUG] Scoreboard returned {len(scoreboard)} matchups")
    for m in scoreboard:
        home = m.home_team
        away = m.away_team
        print(f"[DEBUG] Matchup: {home.team_name} ({home.scores}) vs {away.team_name} ({away.scores})")
        rows.append({
            "timestamp": timestamp,
            "home_team": home.team_name,
            "home_score": home.scores[-1] if home.scores else None,
            "away_team": away.team_name,
            "away_score": away.scores[-1] if away.scores else None,
        })
except Exception as e:
    print("[ERROR] Failed to fetch scoreboard:", e)
    raise

# ---- DataFrame and CSV ----
df = pd.DataFrame(rows)
print("[DEBUG] DataFrame created:")
print(df)

script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, "scores.csv")
header = not os.path.exists(csv_path)
print(f"[DEBUG] Writing to {csv_path} (header={header})")
df.to_csv(csv_path, mode="a", index=False, header=header)
print("[DEBUG] Write complete")
