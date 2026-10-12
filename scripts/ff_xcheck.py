"""Fantasy Frontier cross-check: our blended projection vs Sleeper vs ESPN, plus nflverse NGS/PFR/FTN/depth context."""
import json, os, sys, statistics as st, collections
sys.path.insert(0, os.path.dirname(__file__))
from xlib import Src, f, norm, verdict, write
import nflx
D = os.path.join(os.path.dirname(__file__), "..", "data")
S = Src()
sl = {}
for k in ("thu", "sun", "mon"):
    p = os.path.join(D, "slate_%s.json" % k)
    if os.path.exists(p): sl[k] = json.load(open(p))
base = sl.get("sun") or next(iter(sl.values()))
season = int(base["start"][:4]) if base.get("start") else 2026
LBL = {"thu": "Thursday", "sun": "Sunday main", "mon": "Monday"}
wk = {}
for k, s in sl.items():
    try: wk[k] = nflx.week_of(s["start"])
    except Exception: pass
def _ep():
    o = {}
    for w in sorted(set(wk.values())): o[w] = nflx.espn_proj(season, w)
    return o if any(o.values()) else {}
epw = S.get("ESPN fantasy projections (PPR)", "https://fantasy.espn.com/football/players/projections", "Third independent weekly projection, compared with Sleeper and our model", _ep) or {}
for x in S.list:
    if x["name"].startswith("ESPN fantasy"): x["rows"] = sum(len(v) for v in epw.values())
rec = S.get("nflverse Next Gen Stats: receiving", "https://github.com/nflverse/nflverse-data/releases/tag/nextgen_stats", "Separation, cushion, air-yard share and YAC over expected for pass catchers", lambda: nflx.ngs("receiving", season)) or {}
rush = S.get("nflverse Next Gen Stats: rushing", "https://github.com/nflverse/nflverse-data/releases/tag/nextgen_stats", "Rush yards over expected and stacked-box rate for RBs", lambda: nflx.ngs("rushing", season)) or {}
pas = S.get("nflverse Next Gen Stats: passing", "https://github.com/nflverse/nflverse-data/releases/tag/nextgen_stats", "Completion % over expected, aggressiveness, time to throw for QBs", lambda: nflx.ngs("passing", season)) or {}
pfr = S.get("nflverse PFR advanced receiving", "https://github.com/nflverse/nflverse-data/releases/tag/pfr_advstats", "Broken tackles and drops", lambda: nflx.pfr_rec(season)) or {}
dep = S.get("nflverse depth charts", "https://github.com/nflverse/nflverse-data/releases/tag/depth_charts", "Flags recommended players listed as backups", lambda: nflx.depth(season)) or {}
ftn = S.get("FTN charting (via nflverse)", "https://github.com/nflverse/nflverse-data/releases/tag/ftn_charting", "Team motion, play-action, screen and blitz rates", lambda: nflx.ftn_team(season)) or {}
S.list = [dict(name="Already used: DraftKings salaries, Sleeper projections + trending, FantasyCalc, ESPN injuries/news/odds, nflverse stats/schedules/snaps, Open-Meteo", status="ok", what="Core model inputs (unchanged)", new=False)] + S.list
cons, adv, n_agree, n_cmp = [], [], 0, 0
for kind, s in sl.items():
    for p in s["players"]:
        if p.get("pos") not in ("QB", "RB", "WR", "TE") or p.get("out") or (p.get("proj") or 0) < 4: continue
        nm, tm = norm(p["name"]), p["team"]; ours = p.get("proj"); sv = (p.get("srcs") or {}).get("sleeper"); ev = (epw.get(wk.get(kind)) or {}).get(nm)
        vals = [v for v in (ours, sv, ev) if v]
        rel = (max(vals) - min(vals)) / max(st.mean(vals), 1) if len(vals) >= 2 else None
        if rel is not None:
            n_cmp += 1; n_agree += rel <= .15
        d = dep.get((nm, tm)); dtxt = ("starter" if d and d[0] == 1 else "backup #%d" % d[0]) if d else "—"
        cons.append([LBL.get(kind, kind), p["name"], tm, p["pos"], p.get("sal"), round(ours or 0, 1), sv if sv is not None else "—", ev if ev is not None else "—", round(rel * 100) if rel is not None else "—", dtxt, verdict(rel) if rel is not None else "n/a"])
        if kind == "sun":
            r = rec.get((nm, tm)); ru = rush.get((nm, tm)); pa = pas.get((nm, tm)); b = pfr.get((nm, tm))
            if r or ru or pa:
                adv.append([p["name"], tm, p["pos"], p.get("sal"), round(ours or 0, 1),
                    round(f(r["avg_separation"], 0), 2) if r else "—", round(f(r["percent_share_of_intended_air_yards"], 0), 1) if r else "—",
                    round(f(r["avg_yac_above_expectation"], 0), 2) if r else "—", round(f(ru["rush_yards_over_expected_per_att"], 0), 2) if ru else "—",
                    round(f(pa["completion_percentage_above_expectation"], 0), 1) if pa else "—", int(b["btk"]) if b else "—", int(b["drop"]) if b else "—"])
team = collections.defaultdict(collections.Counter)
for gid, c in ftn.items():
    parts = gid.split("_")
    for t in parts[2:4]: team[t].update(c)  # game-level; both offenses share a game id, so this is a pace/style proxy
tteam = [[t, c["n"], round(100 * c["is_motion"] / c["n"], 1), round(100 * c["is_play_action"] / c["n"], 1), round(100 * c["is_screen_pass"] / c["n"], 1), round(100 * c["blitz"] / c["n"], 1)] for t, c in sorted(team.items()) if c["n"]]
cons.sort(key=lambda r: -(r[8] if isinstance(r[8], (int, float)) else -1))
tables = [dict(title="Projection consensus: our model vs Sleeper vs ESPN", note="Spread = (highest − lowest) ÷ average of the three. ESPN is PPR scoring, which runs ~1–2 pts below DraftKings for high-volume players (DK adds 100-yard/300-yard bonuses). 'disagree' = over 30% apart: check news before locking.", cols=["Slate", "Player", "Team", "Pos", "Salary", "Ours", "Sleeper", "ESPN", "Spread %", "Depth chart", "Verdict"], rows=cons, flag=10),
          dict(title="Advanced usage (Next Gen Stats + PFR), Sunday slate", note="Season-to-date. Separation and air-yard share predict target volume; YAC over expected and rush yards over expected separate real skill from scheme. Drops and broken tackles from PFR.", cols=["Player", "Team", "Pos", "Salary", "Ours", "Separation (yd)", "Air-yard share %", "YAC over exp", "Rush YOE/att", "CPOE %", "Broken tackles", "Drops"], rows=adv),
          dict(title="Game style from FTN charting", note="Share of charted plays in that team's games (both offenses), season-to-date: high motion/play-action games tend to produce more explosive passing.", cols=["Team", "Plays", "Motion %", "Play-action %", "Screen %", "Blitz %"], rows=tteam)]
summ = [["Players cross-checked", n_cmp, "with 2+ projections"], ["Sources agree (≤15%)", "%d%%" % round(100 * n_agree / max(n_cmp, 1)), ""], ["Big disagreements", sum(1 for r in cons if r[10] == "disagree"), "over 30% apart"], ["Sources OK", "%d/%d" % (sum(s["status"] == "ok" for s in S.list), len(S.list)), "this refresh"]]
write(os.path.join(D, "xcheck.json"), "Fantasy Frontier · data sources & cross-check", S, tables, summ)
print("xcheck:", n_cmp, "compared;", [(s["name"][:30], s["status"], s.get("rows")) for s in S.list])
