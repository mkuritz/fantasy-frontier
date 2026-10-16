"""Post-game grading for the pre-lock lineup snapshots in data/track/lineups.jsonl.
Actual DK points come from ESPN's public game summary (box score + scoring plays), the same feed Bet Lab uses.
Writes data/track/results.json. Never edits the snapshot log. Field benchmarks (contest cash line / winning score)
are not published in a permitted feed, so they are recorded as unavailable rather than guessed."""
import json, os, re, sys, itertools, datetime as dt, unicodedata
sys.path.insert(0, os.path.dirname(__file__))
import util as U
TR = os.path.join(U.DATA, "track")
SUM = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event=%s"
def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z ]", "", s); return " ".join(w for w in s.split() if w not in ("jr", "sr", "ii", "iii", "iv", "v"))
def num(x):
    try: return float(x)
    except Exception: return 0.0
def actuals(summ):
    """DK points per player (norm name|team) from ESPN box score. Returns (pts, notes)."""
    pts, notes, teams = {}, [], {}
    comp = summ["header"]["competitions"][0]
    for c in comp["competitors"]: teams[c["team"]["abbreviation"]] = int(c.get("score") or 0)
    defn = {t: {"sk": 0, "int": 0, "fr": 0, "td": 0} for t in teams}
    for tb in summ["boxscore"].get("players", []):
        t = tb["team"]["abbreviation"]
        for cat in tb["statistics"]:
            keys = cat.get("keys") or []
            for a in cat.get("athletes", []):
                k = norm(a["athlete"]["displayName"]) + "|" + t; v = dict(zip(keys, a.get("stats", [])))
                p = pts.setdefault(k, {"name": a["athlete"]["displayName"], "team": t, "pts": 0.0})
                n = cat["name"]
                if n == "passing":
                    y = num(v.get("passingYards")); p["pts"] += .04 * y + 4 * num(v.get("passingTouchdowns")) - num(v.get("interceptions")) + (3 if y >= 300 else 0)
                elif n == "rushing":
                    y = num(v.get("rushingYards")); p["pts"] += .1 * y + 6 * num(v.get("rushingTouchdowns")) + (3 if y >= 100 else 0)
                elif n == "receiving":
                    y = num(v.get("receivingYards")); p["pts"] += num(v.get("receptions")) + .1 * y + 6 * num(v.get("receivingTouchdowns")) + (3 if y >= 100 else 0)
                elif n == "fumbles":
                    p["pts"] -= num(v.get("fumblesLost"))
                elif n == "defensive":
                    defn[t]["sk"] += num(v.get("sacks")); defn[t]["td"] += num(v.get("defensiveTouchdowns"))
                elif n == "interceptions":
                    defn[t]["int"] += num(v.get("interceptions")); defn[t]["td"] += num(v.get("interceptionTouchdowns") or 0)
                elif n in ("kickReturns", "puntReturns"):
                    td = num(v.get("kickReturnTouchdowns") or v.get("puntReturnTouchdowns")); p["pts"] += 6 * td; defn[t]["td"] += td
    for tb in summ["boxscore"].get("players", []):  # fumble recoveries = opponent fumbles lost
        t = tb["team"]["abbreviation"]; opp = [o for o in teams if o != t][0]
        for cat in tb["statistics"]:
            if cat["name"] == "fumbles":
                defn[opp]["fr"] += sum(num(dict(zip(cat.get("keys") or [], a.get("stats", []))).get("fumblesLost")) for a in cat.get("athletes", []))
    # kickers: FG distance from scoring plays, XP from "(X Kick)" text
    for sp in summ.get("scoringPlays", []):
        t = sp["team"]["abbreviation"]; txt = sp.get("text", "")
        m = re.match(r"(.+?) (\d+) (?:Yd|Yard) Field Goal", txt)
        if m:
            d = int(m.group(2)); k = norm(m.group(1)) + "|" + t
            pts.setdefault(k, {"name": m.group(1), "team": t, "pts": 0.0})["pts"] += 3 if d < 40 else 4 if d < 50 else 5
        m = re.search(r"\((.+?) Kick\)", txt)
        if m:
            k = norm(m.group(1)) + "|" + t; pts.setdefault(k, {"name": m.group(1), "team": t, "pts": 0.0})["pts"] += 1
    notes.append("2-pt conversions and offensive fumble-recovery TDs are not in the box score and are not counted")
    for t, d in defn.items():
        pa = teams[[o for o in teams if o != t][0]]
        pab = 10 if pa == 0 else 7 if pa <= 6 else 4 if pa <= 13 else 1 if pa <= 20 else 0 if pa <= 27 else -1 if pa <= 34 else -4
        pts["dst|" + t] = {"name": t + " DST", "team": t, "pts": d["sk"] + 2 * d["int"] + 2 * d["fr"] + 6 * d["td"] + pab, "approx": True}
    notes.append("DST points are approximate (sacks, INTs, fumble recoveries, return/defensive TDs, final points allowed; safeties and blocked kicks not counted)")
    for p in pts.values(): p["pts"] = round(p["pts"], 2)
    return pts, notes, teams
def key_for(r):
    return ("dst|" + r["team"]) if r["pos"] == "DST" else norm(r["name"]) + "|" + r["team"]
def score_rows(rows, A):
    tot, out = 0.0, []
    for r in rows:
        a = A.get(key_for(r)); v = (a["pts"] if a else 0.0) * (1.5 if r["slot"] == "CPT" else 1)
        out.append(dict(r, actual=round(v, 2), found=bool(a))); tot += v
    return round(tot, 2), out
def hindsight(slate_players, A):
    pool = []
    for p in slate_players:
        if not p.get("sal"): continue
        a = A.get(key_for(p)); 
        if a: pool.append((p, a["pts"]))
    pool.sort(key=lambda x: -x[1]); pool = pool[:26]; best = None
    caps = (50000, 49000, 48000, 47000, 46000, 45000); bycap = {c: None for c in caps}
    for ci, (c, cp) in enumerate(pool):
        if not c.get("cid"): continue
        rest = [x for i, x in enumerate(pool) if i != ci]
        for combo in itertools.combinations(rest, 5):
            sal = c["csal"] + sum(x[0]["sal"] for x in combo)
            if sal > 50000: continue
            if len({c["team"]} | {x[0]["team"] for x in combo}) < 2: continue
            s = 1.5 * cp + sum(x[1] for x in combo)
            if not best or s > best[0]: best = (s, c, combo, sal)
            for cap in caps:
                if sal <= cap and (bycap[cap] is None or s > bycap[cap]): bycap[cap] = s
    if not best: return None
    s, c, combo, sal = best
    rows = [{"slot": "CPT", "name": c["name"], "team": c["team"], "pos": c["pos"], "sal": c["csal"], "actual": round(1.5 * A[key_for(c)]["pts"], 2)}] + \
           [{"slot": "FLEX", "name": p["name"], "team": p["team"], "pos": p["pos"], "sal": p["sal"], "actual": round(a, 2)} for p, a in combo]
    return {"actual": round(s, 2), "sal": sal, "rows": rows,
            "best_by_cap": {str(c): (round(v, 2) if v is not None else None) for c, v in bycap.items()}}
def main():
    f = os.path.join(TR, "lineups.jsonl")
    if not os.path.exists(f): print("no snapshots"); return
    snaps = [json.loads(l) for l in open(f) if l.strip()]
    res = U.load("track/results.json", {"slates": {}})
    by = {}
    for s in snaps:
        if s["logged_at"] < s["lock"]: by.setdefault("%s-%s" % (s["kind"], s["dg"]), []).append(s)
    for key, ss in by.items():
        if res["slates"].get(key, {}).get("final"): continue
        last = sorted(ss, key=lambda s: s["logged_at"])[-1]  # official = final pre-lock version
        summ = U.get(SUM % last["espn_id"])
        if not summ: continue
        st = summ["header"]["competitions"][0]["status"]["type"]
        entry = {"kind": last["kind"], "dg": last["dg"], "game": last["game"], "label": last["label"], "lock": last["lock"],
                 "official_snapshot": last["logged_at"], "n_snapshots": len(ss), "state": st.get("state"), "final": bool(st.get("completed"))}
        if last.get("type") != "showdown":
            entry["note"] = "Classic multi-game grading is not built yet; snapshot is logged and kept."; res["slates"][key] = entry; continue
        if st.get("state") == "pre": res["slates"][key] = entry; continue
        A, notes, teams = actuals(summ); entry["score"] = teams; entry["notes"] = notes
        entry["lineups"] = {}
        for k, lu in last["lineups"].items():
            tot, rows = score_rows(lu["rows"], A)
            entry["lineups"][k] = {"proj": lu["proj"], "actual": tot, "sal": lu["sal"], "sal_left": 50000 - (lu["sal"] or 0), "rows": rows}
        entry["baselines"] = {}
        for k, lu in (last.get("baselines") or {}).items():
            if lu: tot, rows = score_rows(lu["rows"], A); entry["baselines"][k] = {"proj": lu["proj"], "actual": tot, "rows": rows}
        if entry["final"]:
            sp = U.load("slate_%s.json" % last["kind"], {})
            if str(sp.get("dg")) == str(last["dg"]): entry["hindsight"] = hindsight(sp["players"], A)
            if entry.get("hindsight"):
                for v in entry["lineups"].values(): v["pct_of_optimal"] = round(100 * v["actual"] / entry["hindsight"]["actual"], 1) if entry["hindsight"]["actual"] else None
        entry["field"] = {"status": "unavailable", "why": "DraftKings does not publish contest cash lines or winning scores in a permitted public feed; we will not scrape them. Compared against naive chalk and max-salary baselines instead."}
        entry["graded_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes")
        res["slates"][key] = entry; print(key, entry["state"], {k: v["actual"] for k, v in entry["lineups"].items()})
    os.makedirs(TR, exist_ok=True); U.save("track/results.json", res)
if __name__ == "__main__": main()
