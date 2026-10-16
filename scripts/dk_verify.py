"""DK-verified check: validates every logged showdown lineup (+ baselines) against DraftKings' public
draftables JSON (api.draftkings.com/draftgroups/v1/draftgroups/<dg>/draftables, served without login to the lobby).
Checks: draftable IDs on slate, not disabled/out, salary matches (CPT = 1.5x), total <= $50k, 1 CPT + 5 FLEX, both teams.
Writes data/track/verify.json keyed by snapshot logged_at. Exit 2 if the latest pre-lock snapshot fails."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import util as U
OUT_BAD = {"O", "OUT", "IR", "D", "SUSP", "PUP", "NFI"}
def check(lu, dk, teams):
    errs = []; rows = lu["rows"]; ids = [r["id"] for r in rows]
    if [r["slot"] for r in rows].count("CPT") != 1 or len(rows) != 6: errs.append("roster must be 1 CPT + 5 FLEX")
    if len(set(ids)) != 6: errs.append("duplicate player")
    tot = 0
    for r in rows:
        d = dk["by_pid"].get(r["id"])
        if not d: errs.append("%s not on DK slate" % r["name"]); continue
        sal = d["cpt"] if r["slot"] == "CPT" else d["flex"]
        tot += sal or 0
        if sal != r["sal"]: errs.append("%s %s salary %s vs DK %s" % (r["name"], r["slot"], r["sal"], sal))
        if d["disabled"] or (d["status"] or "").upper() in OUT_BAD: errs.append("%s DK status %s%s" % (r["name"], d["status"], " (locked/disabled)" if d["disabled"] else ""))
    if tot > 50000: errs.append("DK salary total $%d > $50,000" % tot)
    if len({r["team"] for r in rows}) < 2: errs.append("both teams must be represented")
    return {"ok": not errs, "dk_salary": tot, "errors": errs}
def dk_get(dg):
    import urllib.request
    for _ in range(3):
        try:
            req = urllib.request.Request("https://api.draftkings.com/draftgroups/v1/draftgroups/%s/draftables" % dg, headers={"Accept": "application/json", "User-Agent": "SportsLabs-FantasyFrontier/1.0 (+https://fantasyfrontier.sportslabshq.com/)"})
            with urllib.request.urlopen(req, timeout=40) as r: return json.loads(r.read())
        except Exception as e: print("DK fetch fail", e)
    return None
def main():
    f = os.path.join(U.DATA, "track", "lineups.jsonl")
    if not os.path.exists(f): return 0
    snaps = [json.loads(l) for l in open(f) if l.strip()]
    ver = U.load("track/verify.json", {}); rc = 0; cache = {}
    latest = {}
    for s in snaps:
        if s.get("type") == "showdown" and s["logged_at"] < s["lock"]: latest[(s["kind"], s["dg"])] = s
    for s in snaps:
        if s.get("type") != "showdown" or s["logged_at"] in ver: continue
        dg = s["dg"]
        if dg not in cache:
            j = dk_get(dg)
            by = {}
            # model ids are the FLEX draftableId (cid = CPT draftableId); group the two entries per playerId
            grp = {}
            for d in (j or {}).get("draftables", []): grp.setdefault(d["playerId"], []).append(d)
            for g in grp.values():
                g.sort(key=lambda d: d["salary"]); fl, cp = g[0], g[-1]
                info = {"flex": fl["salary"], "cpt": cp["salary"] if len(g) > 1 else None, "status": fl.get("status"), "disabled": fl.get("isDisabled"), "team": fl.get("teamAbbreviation")}
                for d in g: by[str(d["draftableId"])] = info
            cache[dg] = {"by_pid": by} if j else None
        dk = cache[dg]
        if not dk: print("DK draftables unavailable for", dg); continue
        r = {"checked_at": U_now(), "source": "DraftKings public draftables JSON, draft group %s" % dg, "lineups": {}, "baselines": {}}
        for k, lu in s["lineups"].items(): r["lineups"][k] = check(lu, dk, None)
        for k, lu in (s.get("baselines") or {}).items():
            if lu: r["baselines"][k] = check(lu, dk, None)
        r["ok"] = all(v["ok"] for v in r["lineups"].values())
        ver[s["logged_at"]] = r
        print(s["kind"], s["logged_at"], "DK-verified" if r["ok"] else "FAILED", {k: v["errors"] for k, v in {**r["lineups"], **r["baselines"]}.items() if v["errors"]})
        if latest.get((s["kind"], dg)) is s and not r["ok"]: rc = 2
    U.save("track/verify.json", ver); return rc
def U_now():
    import datetime as dt; return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
if __name__ == "__main__": sys.exit(main())
