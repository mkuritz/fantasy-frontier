"""Backtest the usage x efficiency simulation on completed weeks: project week w using only weeks < w
(+ that week's closing Vegas lines from the nflverse schedule), compare to actual DK points.
Baselines: season-to-date average DK points, and last-game DK points. (Historical DK salaries are not freely
archived, so a salary-implied baseline can't be backtested.)"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import util as U, model as M, extras as X

def run(D, sched):
    rng = np.random.default_rng(11)
    out = {"weeks": [], "rows": 0}
    allp, allb, alll, alla, alls = [], [], [], [], []
    for w in [x for x in D.weeks if x >= 3]:
        F = M.Filtered(D, w)
        actual = {}
        for r in D.wk:
            if int(r["week"]) == w and r["position"] in ("QB", "RB", "WR", "TE"):
                actual[(M.norm(r["player_display_name"]), M.T(r["team"]))] = M.dk_row(r)
        P, B, L, A, SL = [], [], [], [], []
        try: spw, _ = X.sleeper(D.season, w)
        except Exception: spw = {}
        for g in sched:
            if int(g["week"]) != w or not g.get("total_line"): continue
            tot, sp = float(g["total_line"]), float(g["spread_line"] or 0)  # spread_line: + = home favored
            teams = {}
            for tm, home in ((M.T(g["away_team"]), False), (M.T(g["home_team"]), True)):
                itt = (tot + sp) / 2 if home else (tot - sp) / 2
                spt = -sp if home else sp
                names = {k[0] for k in F.by_player if k[1] == tm and F.by_player[k]}
                ps = []
                for n in names:
                    rows = F.by_player[(n, tm)]
                    pos = rows[-1]["position"]
                    if pos not in ("QB", "RB", "WR", "TE"): continue
                    p = {"key": n + "|" + tm, "name": rows[-1]["player_display_name"], "team": tm, "pos": pos}
                    p["games"] = M.player_usage(F, p["name"], tm); p["u"] = M.usage_summary(p["games"]); p["eff"] = M.eff(p["games"], pos, D.lg)
                    if p["u"]: ps.append(p)
                qbs = [p for p in ps if p["pos"] == "QB"]
                st = max(qbs, key=lambda q: M.wavg(q["games"][:2], "att"), default=None)
                ps = [p for p in ps if p["pos"] != "QB" or p is st]
                if st: st["u"]["ts"] = 0.0
                v = M.team_volume(F, tm)
                v["tgt_proj"] = v["tgt"] * (tot / 44.5) ** 0.45 * (1 + 0.011 * spt); v["car_proj"] = v["car"] * (tot / 44.5) ** 0.35 * (1 - 0.016 * spt)
                teams[tm] = {"vol": v, "itt": itt, "players": ps}
            M_NS = M.NS; M.NS = 1000
            res = M.simulate_game(g, teams, rng); M.NS = M_NS
            for t in teams.values():
                for p in t["players"]:
                    k = (M.norm(p["name"]), p["team"])
                    if k not in actual or p["key"] not in res: continue
                    rows = F.by_player.get(k, [])
                    if not rows: continue
                    hist = [M.dk_row(r) for r in sorted(rows, key=lambda r: int(r["week"]))]
                    pr = float(res[p["key"]][0].mean())
                    if pr < 5 and actual[k] < 5: continue  # score fantasy-relevant players only
                    SL.append((spw.get(k) or {}).get("pts"))
                    P.append(pr); B.append(sum(hist) / len(hist)); L.append(hist[-1]); A.append(actual[k])
        if not P: continue
        f = lambda xs: (round(float(np.mean(np.abs(np.array(xs) - np.array(A)))), 2), round(float(np.corrcoef(xs, A)[0, 1]), 3))
        out["weeks"].append({"week": w, "n": len(P), "model": f(P), "season_avg": f(B), "last_game": f(L)})
        allp += P; allb += B; alll += L; alla += A; alls.extend(SL)
    if allp:
        g = lambda xs: {"mae": round(float(np.mean(np.abs(np.array(xs) - np.array(alla)))), 2), "r": round(float(np.corrcoef(xs, alla)[0, 1]), 3)}
        out.update(n=len(allp), model=g(allp), season_avg=g(allb), last_game=g(alll))
        idx = [i for i, v in enumerate(alls) if v is not None]
        if len(idx) > 50:
            sub = lambda xs: [xs[i] for i in idx]; A2 = np.array(sub(alla))
            h = lambda xs: {"mae": round(float(np.mean(np.abs(np.array(xs) - A2))), 2), "r": round(float(np.corrcoef(xs, A2)[0, 1]), 3)}
            best = min(((wt, h([wt * a + (1 - wt) * b for a, b in zip(sub(allp), sub(alls))])["mae"]) for wt in [0, .1, .2, .3, .4, .5, .6, .75, 1]), key=lambda x: x[1])
            curve = {str(wt): h([wt * a + (1 - wt) * b for a, b in zip(sub(allp), sub(alls))])["mae"] for wt in [0, .1, .2, .3, .4, .5, .6, .75, 1]}
            out["sleeper_subset"] = {"curve": curve, "n": len(idx), "model": h(sub(allp)), "sleeper": h(sub(alls)),
                                     "blend": h([best[0] * a + (1 - best[0]) * b for a, b in zip(sub(allp), sub(alls))]), "best_model_weight": best[0]}
    return out

if __name__ == "__main__":
    import fetch_dfs as FD
    D = M.Data(FD.SEASON); sched = X.schedule(FD.SEASON)
    r = run(D, sched); r["note"] = __doc__.strip().replace("\n", " ")
    U.save("backtest.json", r); print(json.dumps({k: v for k, v in r.items() if k != "note"}, indent=1))
