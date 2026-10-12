"""NFL free sources: nflverse NGS / PFR advanced / FTN charting / depth charts, ESPN fantasy projections."""
import json, collections
from xlib import fetch, js, rows, f, norm
NV = "https://github.com/nflverse/nflverse-data/releases/download/"
TFIX = {"LA": "LAR", "WSH": "WAS", "JAC": "JAX", "LV": "LV"}
def T(t): return TFIX.get(t, t)
def week_of(iso):
    """NFL week for a slate start time, from ESPN's public scoreboard."""
    d = js("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=" + iso[:10].replace("-", ""))
    return d["week"]["number"]
def ngs(kind, season):
    out = {}
    for r in rows(NV + "nextgen_stats/ngs_%s.csv.gz" % kind):
        if r["season"] == str(season) and r["season_type"] == "REG" and r["week"] == "0":
            out[(norm(r["player_display_name"]), T(r["team_abbr"]))] = r
    return out
def pfr_rec(season):
    agg = collections.defaultdict(lambda: dict(btk=0, drop=0, n=0))
    for r in rows(NV + "pfr_advstats/advstats_week_rec_%d.csv" % season):
        a = agg[(norm(r["pfr_player_name"]), T(r["team"]))]
        a["btk"] += f(r["receiving_broken_tackles"], 0) + f(r["rushing_broken_tackles"], 0); a["drop"] += f(r["receiving_drop"], 0); a["n"] += 1
    return dict(agg)
def ftn_team(season):
    """FTN charting is play-level without team; join to nflverse schedule-free form via game id + play id is heavy, so aggregate by game side using pbp-free proxy: offense rates per game id."""
    g = collections.defaultdict(lambda: collections.Counter())
    for r in rows(NV + "ftn_charting/ftn_charting_%d.csv" % season):
        c = g[r["nflverse_game_id"]]; c["n"] += 1
        for k in ("is_motion", "is_play_action", "is_screen_pass", "is_rpo", "is_no_huddle"):
            c[k] += r[k] == "TRUE"
        c["blitz"] += f(r["n_blitzers"], 0) > 0
    return g
def depth(season):
    rs = rows(NV + "depth_charts/depth_charts_%d.csv.gz" % season)
    last = max(r["dt"] for r in rs); best = {}
    for r in rs:
        if r["dt"][:10] != last[:10] or r["pos_grp"] != "3WR 1TE": continue
        k = (norm(r["player_name"]), T(r["team"])); rk = int(f(r.get("pos_rank"), 9))
        if k not in best or rk < best[k][0]: best[k] = (rk, r.get("pos_abb"), r["dt"])
    return best
def espn_proj(season, week):
    filt = {"players": {"limit": 600, "sortPercOwned": {"sortPriority": 1, "sortAsc": False},
                        "filterSlotIds": {"value": [0, 2, 4, 6, 16]}}}
    from xlib import UA
    h = dict(UA); h["X-Fantasy-Filter"] = json.dumps(filt)
    d = json.loads(fetch("https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/%d/segments/0/leaguedefaults/3?view=kona_player_info&scoringPeriodId=%d" % (season, week), hdr=h))
    out = {}
    for p in d.get("players", []):
        pl = p["player"]
        for s in pl.get("stats", []):
            if s.get("statSourceId") == 1 and s.get("scoringPeriodId") == week and s.get("appliedTotal"):
                out[norm(pl["fullName"])] = round(s["appliedTotal"], 2)
    return out
