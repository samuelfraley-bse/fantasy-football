import os
import json
from espn_api.football import League
from datetime import datetime
import pandas as pd

# Try to get from env first
espn_s2 = os.getenv("ESPN_S2")
swid = os.getenv("SWID")

if not espn_s2 or not swid:
    with open("config.json") as f:
        config = json.load(f)
        espn_s2 = config["espn_s2"]
        swid = config["swid"]

league = League(league_id=31028552, year=2024, espn_s2=espn_s2, swid=swid)

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

rows = []
for m in league.scoreboard():
    home = m.home_team
    away = m.away_team
    rows.append({
        "timestamp": timestamp,
        "home_team": home.team_name,
        "home_score": home.scores[-1],
        "away_team": away.team_name,
        "away_score": away.scores[-1],
    })

df = pd.DataFrame(rows)

# Append to scores.csv
csv_path = "scores.csv"
header = not os.path.exists(csv_path)
df.to_csv(csv_path, mode="a", index=False, header=header)
