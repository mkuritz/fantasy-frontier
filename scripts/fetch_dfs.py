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
BETLAB = "https://raw.githubusercontent.com/mkuritz/bet-lab/main/data/"
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

def injuries():
    d = U.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries") or {}
    out = {}
    for t in d.get("injuries", []):
        for i in t.get("injuries", []):
            a = i.get("athlete") or {}
            tm = T(((a.get("team") or {}).get("abbreviation")) or "")
            out[(norm(a.get("displayName", "")), tm)] = {"status": i.get("status"), "note": i.get("shortComment")}
            out[(norm(a.get("displayName", "")), "*")] = {"status": i.get("status"), "note": i.get("shortComment")}
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
OUT_STATUSES = ("Out", "Injured Reserve", "Doubtful", "Suspension", "Physically Unable to Perform")
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

def build_slate(kind, sl, logs, dvp, lgdvp, dst, games, inj, props, td):
    show = sl["ct"] == 96
    raw = {}
    for r in sl["rows"]:
        name, tm = r["Name"].strip(), r["TeamAbbrev"]
        key = norm(name) + "|" + tm
        gi = r["Game Info"].split(" ")[0]
        a, h = (gi.split("@") + [""])[:2]
        p = raw.setdefault(key, {"key": key, "name": name, "team": tm, "pos": r["Position"], "opp": h if tm == a else a, "game": gi,
                                 "avg": f(r["AvgPointsPerGame"]), "dkstatus": r.get("Status") or ""})
        if show:
            if r["Roster Position"] == "CPT": p["cid"], p["csal"] = r["ID"], int(r["Salary"])
            else: p["id"], p["sal"] = r["ID"], int(r["Salary"])
        else: p["id"], p["sal"], p["rp"] = r["ID"], int(r["Salary"]), r["Roster Position"]
    players = [p for p in raw.values() if p.get("sal")]
    for p in players:
        ij = inj.get((norm(p["name"]), p["team"])) or ({} if p["pos"] == "DST" else inj.get((norm(p["name"]), "*"))) or {}
        p["status"] = ij.get("status") or p["dkstatus"] or ""
        if ij.get("note"): p["inj"] = ij["note"][:220]
    cas, notes = cascades(players, logs, inj)
    for p in players:
        g = games.get(p["game"]) or {}
        ctx = {"game": g, "dvp": dvp, "lgdvp": lgdvp, "dst": dst, "props": props, "td": td, "cascade": cas}
        gl = logs.get((norm(p["name"]), p["team"])) or logs.get((norm(p["name"]), "*")) or []
        if p["pos"] == "DST": pr = project_dst(p, ctx)
        elif p["pos"] == "K": pr = project_k(p, gl, ctx)
        else: pr = project_player(p, gl, ctx)
        p.update(pr)
        if p["status"] in OUT_STATUSES: p.update(proj=0, floor=0, ceil=0); p["edges"] = ["Ruled %s" % p["status"]]
        elif p["status"] == "Questionable":
            for k in ("proj", "floor", "ceil"): p[k] = round(p[k] * 0.88, 2)
            p["edges"] = p["edges"] + ["Questionable: projection trimmed 12%"]
        p["val"] = round(p["proj"] / (p["sal"] / 1000.0), 2)
        p.pop("dkstatus", None); p.pop("avg_", None)
    own_proxy(players, show)
    gl = sorted({p["game"] for p in players})
    gm = [dict(games.get(k) or {"away": k.split("@")[0], "home": (k.split("@") + [""])[1]}, key=k) for k in gl]
    players.sort(key=lambda p: -p["proj"])
    start = sl["start"]
    return {"kind": kind, "type": "showdown" if show else "classic", "dg": sl["dg"], "start": start, "label": sl.get("label"),
            "games": gm, "players": players, "cascades": notes, "fetched": NOW.isoformat(timespec="minutes"), "stale": False}

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
    inj = injuries(); props, td, an = betlab()
    meta = U.load("meta.json", {})
    meta.update(updated=NOW.isoformat(timespec="minutes"), scoring=SCORE, season=SEASON, slates=meta.get("slates", {}),
                sources={"salaries": "DraftKings public lobby + salary CSV", "stats": "nflverse weekly player stats %d" % SEASON,
                         "odds": "ESPN (DraftKings lines)", "injuries": "ESPN", "weather": "Open-Meteo", "props": "Bet Lab (DraftKings props via ESPN)"},
                lgdvp={k: round(v, 2) for k, v in lgdvp.items()}, log_weeks=sorted({int(r["week"]) for r in rows}) if rows else [])
    for kind in ("thu", "sun", "mon"):
        if kind in slates:
            out = build_slate(kind, slates[kind], logs, dvp, lgdvp, dst, games, inj, props, td)
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
    U.save("meta.json", meta)

if __name__ == "__main__":
    main()
