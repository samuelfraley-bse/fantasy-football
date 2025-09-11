import json
from datetime import datetime
from espn_api.football import League

# Load config
with open("config.json") as f:
    cfg = json.load(f)

league = League(
    league_id=cfg["league_id"],
    year=cfg["year"],
    swid=cfg["swid"],
    espn_s2=cfg["espn_s2"]
)

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

matchups = []
for matchup in league.scoreboard():
    team_a = matchup.home_team
    team_b = matchup.away_team

    matchups.append({
        "timestamp": timestamp,
        "team_a": team_a.team_name,
        "team_a_score": team_a.scores[-1],
        "team_a_projected": team_a.projected_total,
        "team_b": team_b.team_name,
        "team_b_score": team_b.scores[-1],
        "team_b_projected": team_b.projected_total,
    })

# Print for now
for m in matchups:
    print(
        f"[{m['timestamp']}] "
        f"{m['team_a']} ({m['team_a_score']}/{m['team_a_projected']:.1f}) "
        f"vs {m['team_b']} ({m['team_b_score']}/{m['team_b_projected']:.1f})"
    )

# Optionally save JSON
with open("matchups.json", "w") as f:
    json.dump(matchups, f, indent=2)
