"""Publish the one-way weekly DFS snapshot consumed by Fantasy Front Office.
Display-only fields; no model internals, no inputs from Front Office."""
import json, os, datetime
SRC = next((f"data/slate_{k}.json" for k in ("sun","thu","mon") if os.path.exists(f"data/slate_{k}.json")), None)
def main():
    if not SRC: return
    d = json.load(open(SRC)); P = [p for p in d.get("players",[]) if p.get("elig") and not p.get("out")]
    games = {g["key"]: g for g in d.get("games",[])}
    def row(p, note):
        return {"name":p["name"],"team":p["team"],"pos":p["pos"],"opp":p.get("opp"),"game":p.get("game"),
                "proj":round(p.get("proj",0),1),"own":p.get("own"),"status":p.get("status"),"note":note}
    popular = [row(p, f"~{p['own']:.0f}% projected roster rate (estimate)") for p in sorted(P,key=lambda p:-(p.get("own") or 0))[:12]]
    core = []
    for pos,n in (("QB",2),("RB",3),("WR",4),("TE",2),("DST",1)):
        for p in sorted([x for x in P if x["pos"]==pos], key=lambda p:-(p.get("val") or 0))[:n]:
            core.append(row(p, "Optimal-lineup core: top projected value at the position"))
    adv = []
    for p in sorted([x for x in P if (x.get("mf") or 1)>=1.08 and x["pos"]!="DST"], key=lambda p:-p["mf"])[:12]:
        g = games.get(p.get("game"),{}); itt = g.get("itt_home") if g.get("home")==p["team"] else g.get("itt_away")
        adv.append(row(p, f"Favorable matchup vs {p.get('opp')}" + (f"; team implied total {itt}" if itt else "")))
    out = {"generated":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
           "slate":d.get("kind"),"slate_start":d.get("start"),"source_fetched":d.get("fetched"),
           "popular":popular,"core":core,"matchups":adv,
           "disclaimer":"Weekly DraftKings snapshot from Fantasy Frontier. Roster rates and projections are estimates."}
    json.dump(out, open("data/weekly_snapshot.json","w"), indent=1)
    print("snapshot", len(popular), len(core), len(adv))
if __name__ == "__main__": main()
