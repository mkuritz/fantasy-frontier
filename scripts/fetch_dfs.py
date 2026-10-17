"""Fantasy Frontier data build: DraftKings NFL salaries (public lobby + CSV export) -> stat-based DK-point projections.
Sources (all free): DK lobby/getcontests + lineup/getavailableplayerscsv (salaries, positions, CPT/FLEX ids),
nflverse weekly player stats (usage, game logs, defense-vs-position), ESPN scoreboard/odds (DK spreads & totals),
ESPN injuries, Open-Meteo weather, and Bet Lab's live props/analyst files (prop-implied medians, anytime-TD odds).
Every projection is an estimate."""
import csv, io, json, math, re, statistics as st, datetime as dt, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import util as U
import weather as W

NOW = dt.datetime.now(dt.timezone.utc)
ET = dt.timezone(dt.timedelta(hours=-4))  # EDT; good enough for slate-day bucketing during the season
SEASON = NOW.year if NOW.month >= 8 else NOW.year - 1
BETLAB = "https://betlab.sportslabshq.com/data/"
NFLV = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_%d.csv"
TEAMFIX = {"LA": "LAR", "WSH": "WAS", "JAC": "JAX"}
SCORE = "DK: 4pt pass TD, .04/pass yd, -1 INT, +3 at 300 pass yds; .1/rush+rec yd, 6pt rush/rec TD, +3 at 100 rush or rec yds; 1 PPR; -1 fumble lost; 2 for 2-pt"

def T(a): return TEAMFIX.get(a, a)
def norm(n):
    n = re.sub(r"[^a-z ]", "", n.lower().replace("-", " "))
    return " ".join(w for w in n.split() if w not in ("jr", "sr", "ii", "iii", "iv", "v"))
def f(x):
    try: return float(x)
    except Exception: return 0.0

def dk_pts(s):
    p = s["py"] * .04 + s["ptd"] * 4 - s["int"] + (3 if s["py"] >= 300 else 0)
    p += s["ry"] * .1 + s["rtd"] * 6 + (3 if s["ry"] >= 100 else 0)
    p += s["rec"] + s["recy"] * .1 + s["rectd"] * 6 + (3 if s["recy"] >= 100 else 0)
    return round(p - s["fl"] + 2 * s["two"] + 6 * s["sttd"], 2)

# ---------------- DraftKings slates ----------------
def pick_groups(groups):
    """earliest upcoming TNF showdown, Sunday main (Featured classic), MNF showdown"""
    pick = {}
    for g in groups:
        ct, start = g.get("ContestTypeId"), g.get("StartDateEst") or ""
        suf = (g.get("ContestStartTimeSuffix") or "").strip()
        try: d = dt.datetime.fromisoformat(start[:19])
        except Exception: continue
        wd = d.weekday()  # Mon=0 Thu=3 Sun=6
        if ct == 96 and g.get("GameCount") == 1 and not re.search(r"Snake|2H|4Q|Total|Madden", suf):
            kind = {3: "thu", 0: "mon"}.get(wd)
        elif ct == 21 and wd == 6 and (g.get("GameCount") or 0) >= 6 and suf in ("", "None") :
            kind = "sun"
        else: kind = None
        if not kind: continue
        # earliest upcoming group per kind; prefer the Featured main slate on Sunday
        key = (0 if g.get("DraftGroupTag") == "Featured" else 1, start)
        if kind not in pick or key < pick[kind][0]: pick[kind] = (key, g)
    return {k: v[1] for k, v in pick.items()}

def dk_slates():
    lob = U.get("https://www.draftkings.com/lobby/getcontests?sport=NFL") or {}
    out = {}
    for kind, g in pick_groups(lob.get("DraftGroups") or []).items():
        b = U.raw("https://www.draftkings.com/lineup/getavailableplayerscsv?contestTypeId=%d&draftGroupId=%d" % (g["ContestTypeId"], g["DraftGroupId"]))
        if not b: continue
        rows = list(csv.DictReader(io.StringIO(b.decode("utf-8-sig"))))
        if not rows: continue
        out[kind] = {"dg": g["DraftGroupId"], "ct": g["ContestTypeId"], "start": g["StartDateEst"], "games": g["GameCount"],
                     "label": g.get("ContestStartTimeSuffix"), "rows": rows}
        print("DK", kind, g["DraftGroupId"], len(rows))
    return out

# ---------------- nflverse game logs ----------------
def nflverse():
    b = U.raw(NFLV % SEASON)
    if not b: return [], {}
    rows = [r for r in csv.DictReader(io.StringIO(b.decode("utf-8"))) if r.get("season_type") == "REG"]
    logs = {}
    for r in rows:
        s = {"py": f(r["passing_yards"]), "ptd": f(r["passing_tds"]), "int": f(r["passing_interceptions"]),
             "ry": f(r["rushing_yards"]), "rtd": f(r["rushing_tds"]), "car": f(r["carries"]), "att": f(r["attempts"]),
             "rec": f(r["receptions"]), "recy": f(r["receiving_yards"]), "rectd": f(r["receiving_tds"]), "tgt": f(r["targets"]),
             "ts": f(r["target_share"]), "fl": f(r["rushing_fumbles_lost"]) + f(r["receiving_fumbles_lost"]) + f(r["sack_fumbles_lost"]),
             "two": f(r["passing_2pt_conversions"]) + f(r["rushing_2pt_conversions"]) + f(r["receiving_2pt_conversions"]),
             "sttd": f(r["special_teams_tds"]),
             "fg": f(r["fg_made"]), "fg40": f(r["fg_made_40_49"]), "fg50": f(r["fg_made_50_59"]) + f(r["fg_made_60_"]), "pat": f(r["pat_made"]),
             "sk": f(r["def_sacks"]), "dint": f(r["def_interceptions"]), "dfr": f(r["fumble_recovery_opp"]), "dtd": f(r["def_tds"])}
        s["dk"] = dk_pts(s)
        g = {"w": int(r["week"]), "t": T(r["team"]), "o": T(r["opponent_team"]), "pos": r["position"], "s": s}
        logs.setdefault((norm(r["player_display_name"]), T(r["team"])), []).append(g)
        logs.setdefault((norm(r["player_display_name"]), "*"), []).append(g)
    return rows, logs

def defense_tables(logs):
    """DK points allowed per game to each offensive position (DvP), and team defensive event rates for DST."""
    allowed, gp, dst = {}, {}, {}
    seen = set()
    for (n, t), gl in logs.items():
        if t == "*": continue
        for g in gl:
            pos = g["pos"]
            if pos in ("QB", "RB", "WR", "TE"):
                allowed.setdefault(g["o"], {}).setdefault(pos, {}).setdefault(g["w"], 0)
                allowed[g["o"]][pos][g["w"]] += g["s"]["dk"]
            d = dst.setdefault(g["t"], {"sk": 0, "int": 0, "fr": 0, "td": 0, "w": set()})
            d["sk"] += g["s"]["sk"]; d["int"] += g["s"]["dint"]; d["fr"] += g["s"]["dfr"]; d["td"] += g["s"]["dtd"]; d["w"].add(g["w"])
    dvp = {}
    for tm, pp in allowed.items():
        dvp[tm] = {pos: round(sum(w.values()) / max(1, len(w)), 2) for pos, w in pp.items()}
    lg = {pos: st.mean([v[pos] for v in dvp.values() if pos in v]) for pos in ("QB", "RB", "WR", "TE")}
    for tm, d in dst.items():
        n = max(1, len(d["w"])); dst[tm] = {k: round(d[k] / n, 2) for k in ("sk", "int", "fr", "td")}; dst[tm]["g"] = n
    return dvp, lg, dst

# ---------------- ESPN odds/venue/weather, injuries ----------------
def espn_games(days):
    out = {}
    for d in sorted(days):
        sb = U.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=" + d.replace("-", "")) or {}
        for e in sb.get("events", []):
            c = e["competitions"][0]
            tm = {x["homeAway"]: T(x["team"]["abbreviation"]) for x in c["competitors"]}
            g = {"id": e["id"], "time": e["date"], "home": tm.get("home"), "away": tm.get("away"), "state": e["status"]["type"]["state"]}
            o = (c.get("odds") or [{}])[0]
            if o.get("overUnder"):
                tot = float(o["overUnder"]); sp = o.get("spread")
                if sp is None:
                    m = re.match(r"([A-Z]+) (-?[\d.]+)", o.get("details") or "")
                    if m: sp = float(m.group(2)) if T(m.group(1)) == g["home"] else -float(m.group(2))
                g.update(total=tot, spread=sp, details=o.get("details"))
                if sp is not None: g.update(itt_home=round((tot - sp) / 2, 2), itt_away=round((tot + sp) / 2, 2))
            v = c.get("venue") or {}; a = v.get("address") or {}
            g["venue"] = v.get("fullName")
            try:
                if g["home"] in W.ROOF_NFL and a.get("country") in (None, "USA"): g["wx"] = {"dome": W.ROOF_NFL[g["home"]]}
                elif v.get("indoor"): g["wx"] = {"dome": "indoor"}
                elif a.get("city"): g["wx"] = W.forecast(W.geo(a["city"], "" if a.get("country") in (None, "USA") else a["country"]), e["date"])
            except Exception as ex: print("wx", ex)
            out[g["away"] + "@" + g["home"]] = g
    return out

GAMEDAY = {"checked": None, "games": 0, "changes": []}
def gameday_injuries(games, out):
    """Game day: re-pull each game's own injury/inactive report (ESPN game summary) for games within 8h of kickoff.
    These override the league-wide report, so a late scratch/inactive drops the player and the cascade boosts his backups."""
    nowu = dt.datetime.now(dt.timezone.utc)
    for g in (games.values() if isinstance(games, dict) else games):
        try: t = dt.datetime.fromisoformat(g["time"].replace("Z", "+00:00"))
        except Exception: continue
        if g.get("state") != "pre" or not (0 <= (t - nowu).total_seconds() <= 8 * 3600): continue
        d = U.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event=%s" % g["id"]) or {}
        GAMEDAY["games"] += 1
        for tb in d.get("injuries", []):
            tm = T((tb.get("team") or {}).get("abbreviation") or "")
            for i in tb.get("injuries", []):
                a = i.get("athlete") or {}; nm = norm(a.get("displayName", ""))
                st_ = (i.get("type") or {}).get("description") or i.get("status")
                st_ = {"inactive": "Inactive", "out": "Out", "questionable": "Questionable", "doubtful": "Doubtful", "active": "Active"}.get(str(st_).lower(), i.get("status"))
                old = (out.get((nm, tm)) or {}).get("status")
                if st_ and st_ != old: GAMEDAY["changes"].append({"name": a.get("displayName"), "team": tm, "from": old, "to": st_})
                out[(nm, tm)] = out[(nm, "*")] = {"status": st_, "note": "Game-day report (ESPN game page)"}
    GAMEDAY["checked"] = nowu.isoformat(timespec="minutes")

def injuries():
    d = U.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries") or {}
    out = {}
    for t in d.get("injuries", []):
        for i in t.get("injuries", []):
            a = i.get("athlete") or {}
            tm = T(((a.get("team") or {}).get("abbreviation")) or "")
            v = {"status": i.get("status"), "note": (i.get("shortComment") or "") + " " + (i.get("longComment") or "")}
            out[(norm(a.get("displayName", "")), tm)] = v; out[(norm(a.get("displayName", "")), "*")] = v
    return out

def betlab():
    props = U.get(BETLAB + "props_nfl.json") or []
    an = U.get(BETLAB + "analyst_nfl.json") or {}
    pm = {}
    for p in props:
        pm.setdefault((norm(p["player"]), p.get("team"), p.get("oa")), {})[p["market"]] = p["line"]
    td = {}
    for t in an.get("top_td", []) or []:
        td[(norm(t["player"]), t.get("team"), (t.get("opp") or "").split(" ")[-1])] = {"prob": t.get("prob"), "why": t.get("why", [])[:3]}
    for q in an.get("qb_plays", []) or []:
        if q.get("atd"): td.setdefault((norm(q["player"]), q.get("team"), q.get("opp")), {"prob": q["atd"].get("prob"), "why": q.get("why", [])[:3]})
    return pm, td, an

# ---------------- projection model ----------------
OUT_STATUSES = ("Out", "Inactive", "Injured Reserve", "Doubtful", "Suspension", "Physically Unable to Perform")
def wmean(vals):  # recency-weighted (most recent weighted most)
    if not vals: return 0.0
    w = [0.75 ** i for i in range(len(vals))]
    return sum(v * x for v, x in zip(reversed(vals), w)) / sum(w)

def project_player(pl, gl, ctx):
    pos = pl["pos"]
    gl = sorted(gl, key=lambda g: g["w"])[-8:]
    edges, n = [], len(gl)
    comp = {k: wmean([g["s"][k] for g in gl]) for k in ("py", "ptd", "int", "ry", "rtd", "car", "rec", "recy", "rectd", "tgt", "fl", "att")}
    dkl = [g["s"]["dk"] for g in gl]
    # usage trend: last 3 vs season
    if n >= 4:
        for k, lab in (("tgt", "targets"), ("car", "carries")):
            l3 = st.mean([g["s"][k] for g in gl[-3:]]); sz = st.mean([g["s"][k] for g in gl])
            if sz >= 3 and l3 >= sz * 1.2 and l3 - sz >= 1.5: edges.append("Usage up: %.1f %s/g last 3 vs %.1f season" % (l3, lab, sz))
            if sz >= 4 and l3 <= sz * 0.75: edges.append("Usage down: %.1f %s/g last 3 vs %.1f season" % (l3, lab, sz))
    src = ["game logs (%d g)" % n] if n else []
    # Bet Lab prop lines -> implied medians replace the log-based component
    pm = ctx["props"].get((norm(pl["name"]), pl["team"], pl["opp"])) or {}
    used = []
    for mk, k in (("Passing Yards", "py"), ("Passing Touchdowns", "ptd"), ("Passing Interceptions", "int"), ("Rushing Yards", "ry"),
                  ("Receptions", "rec"), ("Receiving Yards", "recy"), ("Carries", "car")):
        if mk in pm:
            comp[k] = 0.65 * pm[mk] + 0.35 * comp[k] if n else pm[mk]; used.append(mk)
    tdp = ctx["td"].get((norm(pl["name"]), pl["team"], pl["opp"]))
    # Vegas & matchup scaling
    g = ctx["game"] or {}
    home = g.get("home") == pl["team"]
    itt = g.get("itt_home" if home else "itt_away")
    vegas = (1 + 0.6 * (itt / 22.5 - 1)) if itt else 1.0
    dv = ctx["dvp"].get(pl["opp"], {}).get(pos); lg = ctx["lgdvp"].get(pos)
    mf = 1 + 0.5 * ((dv / lg) - 1) if dv and lg else 1.0
    mf = max(0.85, min(1.18, mf))
    wx = g.get("wx") or {}
    wxf = 1.0
    if wx.get("wind", 0) and wx["wind"] > 15 and pos in ("QB", "WR", "TE"): wxf *= 0.92; edges.append("Wind %d mph: passing downgrade" % wx["wind"])
    if (wx.get("pop") or 0) >= 60 and pos in ("QB", "WR", "TE"): wxf *= 0.96
    if (wx.get("pop") or 0) >= 60 and pos == "RB": wxf *= 1.02; edges.append("Rain likely: run-heavy script")
    # cascade bump from vacated opportunity
    cas = ctx["cascade"].get(pl["key"])
    if cas:
        comp["tgt"] += cas.get("tgt", 0); comp["car"] += cas.get("car", 0)
        ypt = comp["recy"] / max(1, comp["tgt"] - cas.get("tgt", 0)); cr = comp["rec"] / max(1, comp["tgt"] - cas.get("tgt", 0))
        comp["recy"] += cas.get("tgt", 0) * ypt; comp["rec"] += cas.get("tgt", 0) * cr
        comp["ry"] += cas.get("car", 0) * comp["ry"] / max(1, comp["car"] - cas.get("car", 0))
        if cas.get("tgt", 0) >= 1.2 or cas.get("car", 0) >= 2: edges.append(cas["why"])
    yard_scale = (0.5 + 0.5 * vegas) * mf * wxf
    td_scale = (vegas ** 1.3) * mf * wxf
    py, ry, recy = comp["py"] * yard_scale, comp["ry"] * yard_scale, comp["recy"] * yard_scale
    rec = comp["rec"] * (0.6 + 0.4 * yard_scale)
    ptd = comp["ptd"] * td_scale
    # regress TDs toward an opportunity-based rate (TDs are noisy in small samples)
    opp_td = comp["car"] * (0.04 if pos == "QB" else 0.032) + comp["tgt"] * 0.045
    skill_td = ((n * (comp["rtd"] + comp["rectd"]) + 4 * opp_td) / (n + 4)) * td_scale
    ptd = ((n * comp["ptd"] + 3 * comp["att"] * 0.045) / (n + 3)) * td_scale if pos == "QB" else ptd
    if tdp and tdp.get("prob"):
        lam = -math.log(max(0.01, 1 - tdp["prob"]))
        skill_td = 0.6 * lam + 0.4 * skill_td if n else lam
        used.append("Anytime TD")
        if tdp["prob"] >= 0.45: edges.append("Bet Lab TD model: %d%% anytime TD" % round(100 * tdp["prob"]))
    rtd_share = comp["rtd"] / max(0.01, comp["rtd"] + comp["rectd"]) if (comp["rtd"] + comp["rectd"]) > 0 else (0.7 if pos in ("RB", "QB") else 0.05)
    # bonus probabilities from game-log hit rates (normal approx around projected mean)
    def p_over(mean, thr, cv=0.45):
        if mean <= 0: return 0.0
        z = (thr - mean) / (cv * mean); return 0.5 * math.erfc(z / math.sqrt(2))
    bonus = 3 * (p_over(py, 300, 0.25) + p_over(ry, 100, 0.5) + p_over(recy, 100, 0.5))
    mean = py * .04 + ptd * 4 - comp["int"] + ry * .1 + rec + recy * .1 + skill_td * 6 - comp["fl"] + bonus
    if n and pos in ("QB", "RB", "WR", "TE"):
        prior = pl["sal"] / 1000.0 * (2.75 if pos == "QB" else 2.45)  # salary-implied prior (DK prices encode role)
        k = 2.5 if not used else 1.5
        if mean >= 0.45 * prior:  # only regress real roles; backups keep their own (low) numbers
            mean = (n * mean + k * prior) / (n + k)
    if not n and not used:
        mean = f(pl.get("avg")) * 0.9 * (0.6 + 0.4 * vegas); src = ["DK season avg (no logs)"]
    if used: src.append("Bet Lab props: " + ", ".join(used))
    # spread of outcomes
    sd_hist = st.pstdev(dkl) if n >= 3 else None
    prior_cv = {"QB": 0.38, "RB": 0.55, "WR": 0.62, "TE": 0.68}.get(pos, 0.6)
    sd = (0.5 * sd_hist + 0.5 * prior_cv * mean) if sd_hist else prior_cv * mean
    floor = max(0.0, mean - 0.84 * sd); ceil = mean + 1.28 * sd * (1.08 if pos in ("WR", "TE") else 1.0)
    if itt and itt >= 26: edges.append("Team implied total %.1f (top-tier script)" % itt)
    if dv and lg and dv / lg >= 1.15: edges.append("%s allows %.1f DK pts/g to %ss (+%d%% vs avg)" % (pl["opp"], dv, pos, round(100 * (dv / lg - 1))))
    if dv and lg and dv / lg <= 0.85: edges.append("Tough matchup: %s allows %.1f DK pts/g to %ss" % (pl["opp"], dv, pos))
    stats = {"py": round(py), "ptd": round(ptd, 2), "ry": round(ry, 1), "rec": round(rec, 1), "recy": round(recy, 1), "td": round(skill_td, 2),
             "tgt": round(comp["tgt"], 1), "car": round(comp["car"], 1)}
    return {"proj": round(mean, 2), "floor": round(floor, 2), "ceil": round(ceil, 2), "sd": round(sd, 2), "edges": edges[:5], "src": src,
            "st": stats, "log": [round(x, 1) for x in dkl][-6:], "mf": round(mf, 3), "vegas": round(vegas, 3)}

def project_dst(pl, ctx):
    g = ctx["game"] or {}; home = g.get("home") == pl["team"]
    oitt = g.get("itt_away" if home else "itt_home") or 22.5
    d = ctx["dst"].get(pl["team"], {"sk": 2.4, "int": .7, "fr": .5, "td": .12})
    # points-allowed tier expectation (normal around opponent implied total, sd 9)
    tiers = [(-0.5, 0.5, 10), (0.5, 6.5, 7), (6.5, 13.5, 4), (13.5, 20.5, 1), (20.5, 27.5, 0), (27.5, 34.5, -1), (34.5, 99, -4)]
    cdf = lambda x: 0.5 * math.erfc(-(x - oitt) / (9 * math.sqrt(2)))
    pa = sum((cdf(b) - cdf(a)) * v for a, b, v in tiers) + cdf(-0.5) * 10
    scale = 22.5 / max(12, oitt)
    mean = pa + d["sk"] * scale ** .5 + 2 * (d["int"] + d["fr"]) * scale ** .5 + 6 * (d["td"] + 0.04)
    sd = 5.0
    edges = []
    if oitt <= 19.5: edges.append("Opponent implied for just %.1f pts" % oitt)
    if d["sk"] >= 3: edges.append("Pass rush: %.1f sacks/g" % d["sk"])
    return {"proj": round(mean, 2), "floor": round(max(-2, mean - 0.84 * sd), 2), "ceil": round(mean + 1.6 * sd, 2), "sd": sd, "edges": edges,
            "src": ["opp implied total", "season sacks/turnovers (nflverse)"], "st": {"oitt": oitt, "sk": d["sk"], "to": round(d["int"] + d["fr"], 2)}, "log": []}

def project_k(pl, gl, ctx):
    g = ctx["game"] or {}; home = g.get("home") == pl["team"]; itt = g.get("itt_home" if home else "itt_away") or 22.5
    gl = gl[-8:]
    base = wmean([g2["s"]["fg"] * 3 + g2["s"]["fg40"] + 2 * g2["s"]["fg50"] + g2["s"]["pat"] for g2 in gl]) if gl else 7.5
    mean = base * (0.5 + 0.5 * itt / 22.5)
    return {"proj": round(mean, 2), "floor": round(max(0, mean - 3.5), 2), "ceil": round(mean + 5.5, 2), "sd": 4.2, "edges": [], "src": ["kicking logs", "implied total"], "st": {}, "log": []}

def cascades(players, logs, inj):
    """If a player with a real role is ruled out, push his recent targets/carries to healthy teammates at that position group."""
    out, notes = {}, []
    by_team = {}
    for p in players: by_team.setdefault(p["team"], []).append(p)
    for tm, ps in by_team.items():
        for p in ps:
            if p.get("status") not in OUT_STATUSES or p["pos"] not in ("RB", "WR", "TE"): continue
            gl = logs.get((norm(p["name"]), tm)) or []
            if not gl: continue
            tg = st.mean([g["s"]["tgt"] for g in gl[-4:]]); ca = st.mean([g["s"]["car"] for g in gl[-4:]])
            for k, vac, grp in (("tgt", tg, ("WR", "TE", "RB")), ("car", ca if p["pos"] == "RB" else 0, ("RB",))):
                if vac < 3: continue
                mates = [(m, st.mean([g["s"][k] for g in (logs.get((norm(m["name"]), tm)) or [])[-4:]] or [0])) for m in ps
                         if m["pos"] in grp and m["key"] != p["key"] and m.get("status") not in OUT_STATUSES]
                tot = sum(v for _, v in mates if v > 0)
                if tot <= 0: continue
                for m, v in mates:
                    if v <= 0: continue
                    add = 0.8 * vac * v / tot
                    if add < 0.6: continue
                    c = out.setdefault(m["key"], {"tgt": 0, "car": 0, "why": ""})
                    c[k] += add
                    c["why"] = "%s out: +%.1f vacated %s/g projected" % (p["name"], c[k], "targets" if k == "tgt" else "carries")
                notes.append({"team": tm, "out": p["name"], "pos": p["pos"], "vac": round(vac, 1), "kind": "targets" if k == "tgt" else "carries"})
    return out, notes

def own_proxy(players, showdown):
    """Estimated ownership PROXY (not real ownership): value + salary-tier popularity, normalized to typical slot totals."""
    byp = {}
    for p in players:
        if p["proj"] <= 0.5: p["own"] = 0.1; continue
        v = min(4.0, p["proj"] / (p["sal"] / 1000.0))
        byp.setdefault("ALL" if showdown else p["pos"], []).append((p, math.exp(0.8 * v) * (p["proj"] ** 1.5)))
    tot_slot = {"QB": 100, "RB": 250, "WR": 380, "TE": 120, "DST": 100, "ALL": 600}
    cap = 70 if showdown else 55
    for k, arr in byp.items():
        s = sum(w for _, w in arr) or 1
        for p, w in arr: p["own"] = round(min(cap, tot_slot.get(k, 100) * w / s), 1)


# ---------------- news (ESPN team news + injury blurbs) ----------------
UP = [r"expected to play", r"full participant", r"no limitations", r"(increased|bigger|expanded|larger) role", r"more (snaps|touches|work|targets)",
      r"(lead|top|starting|No\. ?1|clear No\. 2) (back|role|option|receiver|tight end|running back|job)", r"promoted", r"will start", r"take over", r"step into", r"figures to (operate|see|handle|lead)", r"cleared"]
DOWN = [r"limited (practice|participant|snaps)", r"snap count", r"(reduced|smaller|limited) role", r"demoted", r"benched", r"split (work|carries|reps)",
        r"committee", r"game-time decision", r"pitch count", r"workload (will be )?managed", r"not expected to"]
def news(teams_abbr):
    tl = U.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams") or {}
    ids = {T(t["team"]["abbreviation"]): t["team"]["id"] for t in tl.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])}
    out = {}
    cut = (NOW - dt.timedelta(days=6)).isoformat()
    for tm in teams_abbr:
        if tm not in ids: continue
        d = U.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/news?limit=25&team=" + ids[tm]) or {}
        for a in d.get("articles", []):
            if (a.get("published") or "") < cut[:19]: continue
            txt = (a.get("headline") or "") + ". " + (a.get("description") or "")
            for c in a.get("categories", []):
                if c.get("type") == "athlete" and c.get("description"):
                    out.setdefault((norm(c["description"]), tm), []).append({"t": txt[:220], "d": a.get("published", "")[:10]})
    return out
def classify(txt):
    t = txt.lower(); u = sum(1 for p in UP if re.search(p, t)); d = sum(1 for p in DOWN if re.search(p, t))
    return (1 if u > d else -1 if d > u else 0)

def ros(players, sched, week, dvp, lgdvp, games, D):
    """Rest-of-season weekly DK estimates: neutral per-game baseline x opponent DvP x implied total (closing line if posted,
    else the team's season scoring pace)."""
    if not week: return
    pts = {}
    for r in sched:
        if r.get("home_score"):
            for tm, sc in ((T(r["home_team"]), r["home_score"]), (T(r["away_team"]), r["away_score"])): pts.setdefault(tm, []).append(float(sc))
    pace = {t: sum(v) / len(v) for t, v in pts.items()}
    rem = {}
    for r in sched:
        w = int(r["week"])
        if w < week: continue
        for tm, opp, home in ((T(r["home_team"]), T(r["away_team"]), True), (T(r["away_team"]), T(r["home_team"]), False)):
            itt = None
            if r.get("total_line") and r.get("spread_line"):
                t, s_ = float(r["total_line"]), float(r["spread_line"]); itt = (t + s_) / 2 if home else (t - s_) / 2
            rem.setdefault(tm, []).append([w, opp, itt or pace.get(tm, 22.0)])
    for p in players:
        if not p.get("elig") and not p.get("proj"): continue
        if p["proj"] <= 0 or p["pos"] == "K": continue
        g = games.get(p["game"]) or {}
        itt_now = g.get("itt_home" if g.get("home") == p["team"] else "itt_away") or pace.get(p["team"], 22.0)
        base = p["proj"] / max(0.8, p.get("mf", 1.0)) / ((itt_now / 22.5) ** 0.5)
        out = []
        for w, opp, itt in rem.get(p["team"], []):
            if w == week: continue
            dv, lg = dvp.get(opp, {}).get(p["pos"]), lgdvp.get(p["pos"])
            mf = max(0.9, min(1.12, 1 + 0.4 * (dv / lg - 1))) if dv and lg and p["pos"] != "DST" else 1.0
            out.append([w, opp, round(base * mf * (itt / 22.5) ** 0.5, 1)])
        p["ros"] = out; p["ros_total"] = round(sum(x[2] for x in out), 1)

def build_slate(kind, sl, D, logs, dvp, lgdvp, dst, games, inj, props, td, newsmap, ext):
    import numpy as np
    import model as M
    show = sl["ct"] == 96
    raw = {}
    for r in sl["rows"]:
        name, tm = r["Name"].strip(), r["TeamAbbrev"]
        key = norm(name) + "|" + tm
        gi = r["Game Info"].split(" ")[0]
        a, h = (gi.split("@") + [""])[:2]
        p = raw.setdefault(key, {"key": key, "name": name, "team": tm, "pos": r["Position"], "opp": h if tm == a else a, "game": gi, "avg": f(r["AvgPointsPerGame"])})
        if show:
            if r["Roster Position"] == "CPT": p["cid"], p["csal"] = r["ID"], int(r["Salary"])
            else: p["id"], p["sal"] = r["ID"], int(r["Salary"])
        else: p["id"], p["sal"] = r["ID"], int(r["Salary"])
    players = [p for p in raw.values() if p.get("sal")]
    missing = [p["name"] for p in raw.values() if not p.get("sal")]
    if missing: print("WARN no FLEX row for", missing[:5])
    for p in players:
        ij = inj.get((norm(p["name"]), p["team"])) or ({} if p["pos"] == "DST" else inj.get((norm(p["name"]), "*"))) or {}
        p["status"] = ij.get("status") or ""
        p["inj"] = (ij.get("note") or "")[:240]
        p["out"] = p["status"] in OUT_STATUSES
        p["edges"], p["flags"] = [], []
    byteam = {}
    for p in players: byteam.setdefault(p["team"], []).append(p)
    notes = []
    for tm, ps in byteam.items():
        for p in ps:
            if p["pos"] in ("QB", "RB", "WR", "TE"):
                p["games"] = M.player_usage(D, p["name"], tm)
                p["u"] = M.usage_summary(p["games"])
                p["eff"] = M.eff(p["games"], p["pos"], D.lg)
        qbs = [p for p in ps if p["pos"] == "QB" and p.get("u") and not p["out"]]
        starter = max(qbs, key=lambda q: M.wavg(q["games"][:2], "att"), default=None)
        for q in ps:
            if q["pos"] == "QB" and q is not starter: q["u"] = None; q["backup"] = True
        if starter: starter["u"]["ts"] = 0.0
        outs = [p for p in ps if p["out"] and p.get("u")]
        notes += M.redistribute([p for p in ps if p.get("u")], outs)
        for p in ps:
            if p["status"] == "Questionable" and p.get("u"):
                for k in ("ts", "cs", "rz"): p["u"][k] *= 0.9
                p["flags"].append("Questionable"); p["edges"].append("Questionable: usage trimmed 10%")
    import extras as X
    rssmap = X.match_news(ext["rss"], players)
    # news -> role nudges
    for p in players:
        items = ((newsmap.get((norm(p["name"]), p["team"])) or []) + rssmap.get(p["key"], []))[:4]
        txt = " ".join(i["t"] for i in items) + " " + p.get("inj", "")
        c = classify(txt) if txt.strip() else 0
        if c and p.get("u") and not p["out"]:
            for k in ("ts", "cs", "rz"): p["u"][k] *= (1.07 if c > 0 else 0.92)
            p["edges"].append(("News: role trending up — " if c > 0 else "News: usage risk — ") + ((items[0]["t"] if items else p["inj"])[:150]))
            if c > 0 and re.search(r"will start|start(ing)? (at|in place)|promoted|take over|lead (back|role)|first start|step into|clear No", txt.lower()): p["spike_news"] = True
        p["news"] = items[:2]
    # opportunity spike ("their shot")
    week = ext.get("week"); sp_map, trend = ext.get("sleeper", {}), ext.get("trend", {})
    for tm, ps in byteam.items():
        outs = [o for o in ps if o["out"] and o.get("games")]
        for p in ps:
            if not p.get("u") or p["out"] or p["pos"] == "QB": continue
            gain = sum(x for _, _, x in p.get("gain", []))
            tr = trend.get((norm(p["name"]), tm))
            same_out = [o for o in outs if o["pos"] == p["pos"]]
            trig = gain >= 0.04 or p.get("spike_news") or (tr and tr["rank"] <= 25 and same_out)
            if not trig: continue
            sp = M.opportunity_spike(p, outs, D)
            if not sp: continue
            why = []
            if sp["dk_e"] and sp["dk_o"] and sum(sp["dk_e"]) / len(sp["dk_e"]) < sum(sp["dk_o"]) / len(sp["dk_o"]): continue  # no evidence he produces more with more role
            if sp["elev"]:
                ev = {k: sum(x.get(k) or 0 for x in sp["elev"]) / len(sp["elev"]) for k in ("ts", "cs", "rz", "rzt", "rzr")}
                for k, v in ev.items():
                    if v > p["u"].get(k, 0): p["u"][k] = 0.6 * v + 0.4 * p["u"][k]
            if sp["dk_e"]: why.append("%.1f DK pts/g in his %d expanded-role games this season%s" % (sum(sp["dk_e"]) / len(sp["dk_e"]), len(sp["dk_e"]), (" vs %.1f otherwise" % (sum(sp["dk_o"]) / len(sp["dk_o"]))) if sp["dk_o"] else ""))
            if len(sp["prev_e"]) >= 2: why.append("%.1f DK pts/g in %d high-volume games last season" % (sum(sp["prev_e"]) / len(sp["prev_e"]), len(sp["prev_e"])))
            why += sp["ev"][:2]
            if tr: why.append("Sleeper trending add #%d (%s adds/48h)" % (tr["rank"], format(tr["adds"], ",")))
            reason = "teammate out" if gain >= 0.04 or same_out else ("depth chart/news" if p.get("spike_news") else "expanding role")
            p["shot"] = {"reason": reason, "why": why}
            p["flags"].append("Their shot")
            p["edges"].insert(0, "Their shot (%s): %s" % (reason, "; ".join(why[:2]) or "role opening up"))
    # matchup, weather, Bet Lab ATD, vs-opponent history
    for p in players:
        g = games.get(p["game"]) or {}
        dv = dvp.get(p["opp"], {}).get(p["pos"]); lg = lgdvp.get(p["pos"])
        p["mf"] = round(max(0.9, min(1.12, 1 + 0.4 * (dv / lg - 1))) if dv and lg else 1.0, 3)
        if dv and lg and dv / lg >= 1.15: p["edges"].append("%s allows %.1f DK pts/g to %ss this season (+%d%% vs avg)" % (p["opp"], dv, p["pos"], round(100 * (dv / lg - 1))))
        if dv and lg and dv / lg <= 0.85: p["edges"].append("Tough matchup: %s allows %.1f DK pts/g to %ss" % (p["opp"], dv, p["pos"]))
        wx = g.get("wx") or {}
        if p.get("eff") and (wx.get("wind") or 0) > 15 and p["pos"] in ("QB", "WR", "TE"):
            p["eff"]["ypr"] *= 0.93; p["eff"]["cr"] *= 0.97; p["edges"].append("Wind %d mph: passing downgrade" % wx["wind"])
        t = td.get((norm(p["name"]), p["team"], p["opp"]))
        if t and t.get("prob"): p["atd"] = t["prob"]; p["edges"].append("Bet Lab anytime TD: %d%%" % round(100 * t["prob"]))
        prev = [r for r in D.prev_by.get(norm(p["name"]), []) + D.by_player.get((norm(p["name"]), p["team"]), []) if T(r["opponent_team"]) == p["opp"]]
        if len(prev) >= 2 and p["pos"] != "DST":
            avg = sum(f(r["fantasy_points_ppr"]) for r in prev) / len(prev)
            p["vs_opp"] = [len(prev), round(avg, 1)]
            if p.get("avg") and avg >= 1.3 * p["avg"] and avg >= 12:
                p["edges"].append("Owns %s: %.1f PPR pts/g in %d meetings" % (p["opp"], avg, len(prev))); p["tdm"] = 1.04
        u = p.get("u")
        if u:
            if u.get("expanding"): p["flags"].append("Expanding role"); p["edges"].insert(0, "Expanding role: opportunity share %+.0f pts, snaps %+.0f pts over the last 2 games" % (100 * u["trend"], 100 * (u.get("dsnap") or 0)))
            if u.get("shrinking"): p["flags"].append("Shrinking role")
        for nm, lab, x in p.get("gain", []):
            p["edges"].append("%s out: +%.1f%% %s share vacated to him" % (nm, 100 * x, "target" if lab == "targets" else "carry"))
    # DST / K inputs
    for p in players:
        if p["pos"] == "DST":
            d = dst.get(p["team"], {}); p["dstrate"] = {"sk": d.get("sk", 2.4), "to": d.get("int", .7) + d.get("fr", .5), "td": d.get("td", .1)}
        if p["pos"] == "K":
            gl = (logs.get((norm(p["name"]), p["team"])) or [])[-6:]
            p["kbase"] = (sum(g["s"]["fg"] * 3 + g["s"]["fg40"] + 2 * g["s"]["fg50"] + g["s"]["pat"] for g in gl) / len(gl)) if gl else 7.0
    # simulate each game
    rng = np.random.default_rng(abs(hash(sl["dg"])) % 2**32)
    keep_idx = np.arange(M.KEEP)
    sims = {}
    for gk in sorted({p["game"] for p in players}):
        g = games.get(gk) or {}
        a, h = gk.split("@")
        teams = {}
        for tm in (a, h):
            home = tm == h
            itt = g.get("itt_home" if home else "itt_away") or 22.0
            sp = g.get("spread"); sp = (sp if home else -sp) if sp is not None else 0.0  # + = underdog
            tot = g.get("total") or 44.5
            v = M.team_volume(D, tm)
            v["tgt_proj"] = v["tgt"] * (tot / 44.5) ** 0.45 * (1 + 0.011 * sp)
            v["car_proj"] = v["car"] * (tot / 44.5) ** 0.35 * (1 - 0.016 * sp)
            ps = [p for p in byteam.get(tm, []) if not p["out"] and (p.get("u") or p["pos"] in ("DST", "K"))]
            teams[tm] = {"vol": v, "itt": itt, "players": ps}
        res = M.simulate_game(g, teams, rng)
        for k, (pts, st_) in res.items():
            sims[k] = (pts, st_)
    for p in players:
        if p["key"] in sims:
            pts, st_ = sims[p["key"]]
            p["proj"] = round(float(pts.mean()), 2); p["floor"] = round(float(np.percentile(pts, 20)), 2); p["ceil"] = round(float(np.percentile(pts, 90)), 2)
            p["sd"] = round(float(pts.std()), 2); p["st"] = {k: round(float(v), 2) for k, v in st_.items()}
            p["sims"] = [round(float(x), 1) for x in pts[keep_idx]]
            p["_pts"] = pts
        else:
            p.update(proj=0.0, floor=0.0, ceil=0.0, sd=0.0, st={})
        # cross-reference: Sleeper (RotoWire) projection; backtest-weighted blend (model 30% / consensus 70%)
        spj = (sp_map.get((norm(p["name"]), p["team"])) or {}).get("pts") if p["pos"] != "DST" else None
        fc = ext.get("fc", {}).get((norm(p["name"]), p["team"]))
        p["srcs"] = {"model": p["proj"], "sleeper": spj, "fc_rank": fc and fc["rank"], "trend": (trend.get((norm(p["name"]), p["team"])) or {}).get("rank")}
        if spj is not None and p["proj"] > 0 and not p["out"]:
            w = ext.get("model_w", 0.3)
            if p.get("shot") and p["shot"]["reason"] != "expanding role": w = 0.6  # consensus projections often lag a role change
            new = w * p["proj"] + (1 - w) * spj
            r = new / p["proj"] if p["proj"] > 0.5 else 1
            if "sims" in p: p["sims"] = [round(x * r, 1) for x in p["sims"]]
            if "_pts" in p: p["_pts"] = p["_pts"] * r
            p["floor"], p["ceil"] = round(p["floor"] * r, 2), round(p["ceil"] * r, 2); p["proj"] = round(new, 2)
            d = (p["srcs"]["model"] - spj)
            p["srcs"]["agree"] = round(100 - min(100, 100 * abs(d) / max(5, (p["srcs"]["model"] + spj) / 2)))
            if abs(d) >= 4 and abs(d) / max(5, spj) >= 0.3:
                p["flags"].append("Sources disagree")
                p["edges"].append("Sources disagree: our usage model %.1f vs Sleeper/RotoWire %.1f" % (p["srcs"]["model"], spj))
        elif spj and spj >= 6 and not p["out"] and not p.get("backup") and p["proj"] == 0 and p["pos"] != "DST":
            p["proj"], p["floor"], p["ceil"] = round(spj, 2), round(spj * 0.55, 2), round(spj * 1.6, 2)
            p["sims"] = [round(max(0, spj * (1 + 0.45 * z)), 1) for z in np.random.default_rng(len(p["key"])).normal(0, 1, M.KEEP)]
            p["src"] = ["Sleeper/RotoWire projection only (thin sample)"]
            p["thin"] = True
        # player history for charts
        p["hist"] = [[int(r["week"]), M.dk_row(r)] for r in sorted(D.by_player.get((norm(p["name"]), p["team"]), []), key=lambda r: int(r["week"]))]
        p["hist_prev"] = [[int(r["week"]), M.dk_row(r)] for r in sorted(D.prev_by.get(norm(p["name"]), []), key=lambda r: int(r["week"]))] if p["pos"] != "DST" else []
        gl = logs.get((norm(p["name"]), p["team"])) or []
        p["log"] = [round(g["s"]["dk"], 1) for g in sorted(gl, key=lambda g: g["w"])][-6:]
        p["val"] = round(p["proj"] / (p["sal"] / 1000.0), 2)
        # eligibility: real role only (no cheap-but-useless plays)
        u = p.get("u") or {}
        g = games.get(p["game"]) or {}
        if p["out"]: elig, why = False, "Ruled " + p["status"]
        elif p["pos"] == "DST": 
            elig, why = True, ""
            if show and (g.get("total") or 0) >= 49: elig, why = False, "Shootout environment (total %.1f): DSTs faded" % g["total"]
        elif p["pos"] == "K": elig, why = show, "" if show else "No K in DK classic"
        elif p.get("backup"): elig, why = False, "Backup QB"
        elif not u: elig, why = (True, "") if p.get("thin") and p["proj"] >= 8 else (False, "No snaps this season")
        else:
            recent_played = any(x.get("played") for x in (p.get("games") or [])[:2])
            role = (u.get("snap") or 0) >= 0.35 or u["ts"] >= 0.10 or u["cs"] >= 0.25 or (p["pos"] == "QB")
            role = role or bool(p.get("shot"))
            elig = role and (recent_played or u.get("expanding") or bool(p.get("gain"))) and p["proj"] >= (3.0 if show else 5.0)
            why = "" if elig else ("Low role: %d%% snaps, %d%% tgt share, %d%% carry share" % (100 * (u.get("snap") or 0), 100 * u["ts"], 100 * u["cs"]) if not role else "Not active recently / low projection")
        p["elig"], p["why_not"] = elig, why
        if p.get("u"):
            uu = p["u"]; p["usage"] = {k: uu.get(k) for k in ("snap", "ts", "cs", "rz", "trend", "dsnap", "expanding", "weeks", "n")}
        p["src"] = ["nflverse %d usage (%d g)" % (SEASON, u.get("n", 0))] if u else (["opp implied total, sacks/takeaways"] if p["pos"] == "DST" else [])
        if p.get("atd"): p["src"].append("Bet Lab ATD")
        for k in ("games", "u", "eff", "gain", "dstrate", "kbase", "backup", "tdm"): p.pop(k, None)
    ros(players, ext.get("sched") or [], ext.get("week"), dvp, lgdvp, games, D)
    own_proxy([p for p in players if p["elig"]], show)
    for p in players:
        if not p["elig"]: p["own"] = 0.0
    # captain rankings (showdown): 1.5x points; share of sims where he is the slate's top scorer
    cpt = []
    if show:
        el = [p for p in players if p["elig"] and "_pts" in p and p.get("csal")]
        if el:
            mat = np.vstack([p["_pts"] for p in el]); top = mat.argmax(axis=0)
            for i, p in enumerate(el):
                c = 1.5 * p["_pts"]
                cpt.append({"id": p["id"], "name": p["name"], "pos": p["pos"], "team": p["team"], "csal": p["csal"], "proj": round(float(c.mean()), 1),
                            "ceil": round(float(np.percentile(c, 90)), 1), "top": round(float((top == i).mean()) * 100, 1),
                            "val": round(float(c.mean()) / (p["csal"] / 1000), 2)})
            cpt.sort(key=lambda x: -(x["proj"] + 0.35 * (x["ceil"] - x["proj"]) + 0.15 * x["top"]))
    for p in players: p.pop("_pts", None)
    gm = [dict(games.get(k) or {"away": k.split("@")[0], "home": (k.split("@") + [""])[1]}, key=k) for k in sorted({p["game"] for p in players})]
    players.sort(key=lambda p: (not p["elig"], -p["proj"]))
    return {"kind": kind, "type": "showdown" if show else "classic", "dg": sl["dg"], "start": sl["start"], "label": sl.get("label"), "nsims": M.NS, "keep": M.KEEP,
            "games": gm, "players": players, "cascades": notes, "cpt": cpt[:12], "fetched": NOW.isoformat(timespec="minutes"), "stale": False}

def main():
    os.makedirs(U.DATA, exist_ok=True)
    slates = dk_slates()
    rows, logs = nflverse()
    dvp, lgdvp, dst = defense_tables(logs) if logs else ({}, {}, {})
    days = set()
    for s in slates.values():
        for r in s["rows"]:
            m = re.search(r"(\d\d)/(\d\d)/(\d{4})", r["Game Info"])
            if m: days.add("%s-%s-%s" % (m.group(3), m.group(1), m.group(2)))
    games = espn_games(days)
    inj = injuries(); gameday_injuries(games, inj); props, td, an = betlab()
    import model as M
    D = M.Data(SEASON)
    teams_all = set()
    for sl_ in slates.values():
        for r in sl_["rows"]: teams_all.add(r["TeamAbbrev"])
    newsmap = news(sorted(teams_all))
    import extras as X
    sched = X.schedule(SEASON)
    fcv = X.fantasycalc(); rss = X.rss_news()
    bt = U.load("backtest.json", {})
    def ext_for(sl_):
        day = sl_["start"][:10]; wk = X.week_of(sched, day)
        spm, tr = X.sleeper(SEASON, wk) if wk else ({}, {})
        return {"week": wk, "sleeper": spm, "trend": tr, "fc": fcv, "rss": rss, "sched": sched, "model_w": 0.3}
    meta = U.load("meta.json", {})
    meta.update(updated=NOW.isoformat(timespec="minutes"), scoring=SCORE, season=SEASON, slates=meta.get("slates", {}),
                sources={"salaries": "DraftKings public lobby + salary CSV", "stats": "nflverse weekly player stats %d" % SEASON,
                         "odds": "ESPN (DraftKings lines)", "injuries": "ESPN", "weather": "Open-Meteo", "props": "Bet Lab (DraftKings props via ESPN)"},
                lgdvp={k: round(v, 2) for k, v in lgdvp.items()}, log_weeks=sorted({int(r["week"]) for r in rows}) if rows else [])
    built = {}
    for kind in ("thu", "sun", "mon"):
        if kind in slates: built[kind] = build_slate(kind, slates[kind], D, logs, dvp, lgdvp, dst, games, inj, props, td, newsmap, ext_for(slates[kind]))
    try:  # Film Room: weekly review + learned smash signal (validated leave-one-week-out; only steers value picks if it adds lift)
        import film as FR
        fr, fb, _ = FR.run(D, sched, list(built.values()))
        fr["note"] = FR.__doc__.strip().replace("\n", " "); fr["updated"] = NOW.isoformat(timespec="minutes"); fr["upcoming"] = {}
        cls = {p["key"]: p["sal"] for o in built.values() if o.get("type") != "showdown" for p in o["players"]}
        for kind, out in built.items(): fr["upcoming"][kind] = FR.apply(out, fb, D, dvp, lgdvp, fr["validation"]["adds_lift"], cls)
        U.save("film.json", fr)
    except Exception as e: print("film room failed", e)
    for kind in ("thu", "sun", "mon"):
        if kind in slates:
            out = built[kind]
            U.save("slate_%s.json" % kind, out)
            meta["slates"][kind] = {"dg": out["dg"], "start": out["start"], "n": len(out["players"]), "games": len(out["games"]), "fetched": out["fetched"], "stale": False}
        else:
            old = U.load("slate_%s.json" % kind, None)
            if old:
                old["stale"] = True; U.save("slate_%s.json" % kind, old)
                meta["slates"][kind] = dict(meta["slates"].get(kind, {}), stale=True)
                print("kept previous", kind)
            else:
                meta["slates"][kind] = {"missing": True}
    try:
        import backtest as BT
        r = BT.run(D, sched); r["note"] = BT.__doc__.strip().replace("\n", " "); U.save("backtest.json", r)
        meta["backtest"] = {k: r.get(k) for k in ("n", "model", "season_avg", "last_game")}
    except Exception as e: print("backtest failed", e)
    meta["blend"] = "30% usage-model simulation + 70% Sleeper/RotoWire consensus (weight chosen from the weeks 3-5 backtest)"
    meta["gameday_check"] = GAMEDAY
    U.save("meta.json", meta)

if __name__ == "__main__":
    main()
