"""Film Room: weekly review of completed weeks + learned 'smash' signal.
For each completed week: top actual DK scorers and biggest value smashes, explained with data
(role/snap change, vacated opportunity, defense vs position, implied total / game script, red zone, big plays, weather).
Historical DK salaries are not freely archived, so past-week salaries are a PROXY: a per-position fit of the current
real DK salaries on each player's pre-week DK average (last season's average in week 1).
Smash = >= 4.0 DK pts per $1k (proxy) and >= 12 pts. A logistic model on PRE-WEEK features is fit, validated
leave-one-week-out vs a salary/average-only baseline, then applied to the upcoming slates with real salaries."""
import os, sys, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import model as M

POS = ("QB", "RB", "WR", "TE")
MINSAL = {"QB": 4000, "RB": 4000, "WR": 3000, "TE": 2500}
FEATS = [("vac", "Teammate at his position out (vacated opportunity)"), ("dvp", "Soft matchup: opponent allows 10%+ above avg DK pts to his position"),
         ("itt", "Team implied total 24+"), ("exp", "Expanding role (last game share above his average)"), ("rz", "Red-zone role (20%+ of team RZ opportunities)"),
         ("cheap", "Salary $4.5k or less"), ("fav", "Team favored by 3+"), ("wind", "Wind 15+ mph (outdoors)")]
FK = [k for k, _ in FEATS]
opp_sh = lambda g: g.get("ts", 0) + 0.6 * g.get("cs", 0)

def sal_fit(slates):
    """salary = a + b * season-avg DK pts per position, from the REAL current DK salaries"""
    fit = {}
    for pos in POS:
        X, Y = [], []
        for sl in slates:
            if sl.get("type") == "showdown": continue
            for p in sl["players"]:
                if p["pos"] == pos and p.get("log") and len(p["log"]) >= 2:
                    X.append(sum(p["log"]) / len(p["log"])); Y.append(p["sal"])
        if len(X) >= 8:
            b, a = np.polyfit(X, Y, 1); fit[pos] = (float(a), float(b))
        else: fit[pos] = ({"QB": 4500, "RB": 4000, "WR": 3200, "TE": 2800}[pos], {"QB": 160, "RB": 300, "WR": 280, "TE": 250}[pos])
    return fit

def proxy_sal(fit, pos, avg):
    a, b = fit[pos]
    return int(round(min(10000, max(MINSAL[pos], a + b * avg)) / 100) * 100)

def dvp_upto(D, w):
    """DK pts allowed per game by each defense to each position, weeks < w"""
    tot, gp = {}, {}
    for r in D.wk:
        wk = int(r["week"])
        if wk >= w or r["position"] not in POS: continue
        o = M.T(r["opponent_team"]); tot[(o, r["position"])] = tot.get((o, r["position"]), 0) + M.dk_row(r); gp.setdefault(o, set()).add(wk)
    dv = {k: v / max(1, len(gp.get(k[0], ()))) for k, v in tot.items()}
    lg = {p: np.mean([v for (o, pp), v in dv.items() if pp == p] or [1]) for p in POS}
    return dv, lg

def gameinfo(sched):
    G = {}
    for g in sched:
        if not g.get("week"): continue
        w = int(g["week"]); tot = float(g["total_line"] or 0); sp = float(g["spread_line"] or 0)
        for tm, home in ((M.T(g["home_team"]), True), (M.T(g["away_team"]), False)):
            hs, as_ = g.get("home_score"), g.get("away_score")
            G[(tm, w)] = {"opp": M.T(g["away_team"] if home else g["home_team"]), "itt": (tot + sp) / 2 if home else (tot - sp) / 2,
                          "spread": sp if home else -sp, "total": tot, "roof": g.get("roof"), "wind": float(g["wind"]) if g.get("wind") else None,
                          "temp": float(g["temp"]) if g.get("temp") else None,
                          "score": (int(hs), int(as_)) if hs not in (None, "") and as_ not in (None, "") else None, "home": home, "gameday": g.get("gameday")}
            if G[(tm, w)]["score"] and not home: G[(tm, w)]["score"] = G[(tm, w)]["score"][::-1]
    return G

def history_rows(D, sched, fit):
    """one row per player-week (weeks 1..last), with pre-week features and post-game explanations"""
    G = gameinfo(sched); rows = []
    for w in D.weeks:
        F = M.Filtered(D, w); dv, lg = dvp_upto(D, w)
        # usage before week w, per team
        team_pl = {}
        for (n, tm), rr in D.by_player.items():
            pos = rr[-1]["position"]
            if pos not in POS: continue
            pre = M.player_usage(F, rr[-1]["player_display_name"], tm) if F.weeks else []
            team_pl.setdefault(tm, []).append((n, pos, rr, pre))
        for tm, pls in team_pl.items():
            gi = G.get((tm, w))
            if not gi: continue
            played_w = {n for n, pos, rr, pre in pls if any(int(r["week"]) == w for r in rr)}
            for n, pos, rr, pre in pls:
                cur = [r for r in rr if int(r["week"]) == w]
                if not cur: continue
                r = cur[0]; pts = M.dk_row(r)
                prev_dk = [M.dk_row(x) for x in rr if int(x["week"]) < w]
                prior = np.mean(prev_dk) if prev_dk else None
                if prior is None:
                    pv = [M.dk_row(x) for x in D.prev_by.get(n, []) if M.fl(x["targets"]) + M.fl(x["carries"]) + M.fl(x["attempts"]) > 0]
                    prior = float(np.mean(pv)) if pv else 0.0
                    if pv: prior *= 0.9
                sal = proxy_sal(fit, pos, prior)
                pl = [g for g in pre if g.get("played")]
                u = M.usage_summary(pre) if pl else None
                sh_avg = np.mean([opp_sh(g) for g in pl]) if pl else 0
                # vacated: same-position teammate with real role before w who did not play in w
                vac_names = []
                for n2, pos2, rr2, pre2 in pls:
                    if n2 == n or pos2 != pos or n2 in played_w: continue
                    pl2 = [g for g in pre2 if g.get("played")]
                    if pl2 and np.mean([opp_sh(g) for g in pl2]) >= (0.12 if pos != "QB" else 0) and (pos != "QB" or np.mean([g.get("att", 0) for g in pl2]) > 15):
                        vac_names.append(rr2[-1]["player_display_name"])
                ratio = dv.get((gi["opp"], pos), lg[pos]) / lg[pos] if w > 1 else 1.0
                wind = (gi["wind"] or 0) >= 15 and gi["roof"] in ("outdoors", "open")
                f = {"vac": int(bool(vac_names)), "dvp": int(ratio >= 1.10), "itt": int(gi["itt"] >= 24), "exp": int(bool(pl) and opp_sh(pl[0]) > sh_avg * 1.15 and len(pl) >= 2),
                     "rz": int(bool(u) and u["rz"] >= 0.2), "cheap": int(sal <= 4500), "fav": int(gi["spread"] >= 3), "wind": int(wind)}
                # post-game facts
                snap = D.snap.get((n, tm, w)); snaps_pre = [g["snap"] for g in pl if g.get("snap") is not None]
                pid = r["player_id"]; te = D.team.get((tm, w), {})
                rzo = D.rz.get((pid, w, "p"), 0) + D.rz.get((pid, w, "r"), 0)
                rows.append({"w": w, "name": r["player_display_name"], "team": tm, "pos": pos, "opp": gi["opp"], "pts": pts, "sal": sal, "prior": round(prior, 1),
                             "val": round(pts / sal * 1000, 2), "f": f, "vac_names": vac_names, "dvp_ratio": round(ratio, 2), "itt": round(gi["itt"], 1),
                             "spread": gi["spread"], "score": gi["score"], "wind": gi["wind"], "temp": gi["temp"], "roof": gi["roof"],
                             "snap": snap, "snap_pre": round(float(np.mean(snaps_pre)), 2) if snaps_pre else None, "rzo": rzo, "rz_team": te.get("rz", 0),
                             "big": D.big.get((pid, w), 0), "tgt": M.fl(r["targets"]), "car": M.fl(r["carries"]),
                             "td": M.fl(r["rushing_tds"]) + M.fl(r["receiving_tds"]) + M.fl(r["passing_tds"]),
                             "sh": round(opp_sh({"ts": M.fl(r["targets"]) / max(1, D.tt[(tm, w)]["tgt"]), "cs": M.fl(r["carries"]) / max(1, D.tt[(tm, w)]["car"])}), 3),
                             "sh_pre": round(float(sh_avg), 3)})
    for x in rows: x["smash"] = int(x["val"] >= 4.0 and x["pts"] >= 12)
    return rows

def why(x):
    out = []
    if x["snap"] is not None and x["snap_pre"] is not None and x["snap"] - x["snap_pre"] >= 0.12:
        out.append("Role jump: %d%% snaps vs %d%% before" % (x["snap"] * 100, x["snap_pre"] * 100))
    if x["pos"] != "QB" and x["sh"] - x["sh_pre"] >= 0.07 and x["sh_pre"] > 0:
        out.append("Opportunity share %.0f%% vs %.0f%% before" % (x["sh"] * 100, x["sh_pre"] * 100))
    if x["vac_names"]: out.append("Vacated opportunity: %s out" % ", ".join(x["vac_names"][:2]))
    if x["f"]["dvp"]: out.append("Soft matchup: %s allowed %.0f%% above avg to %ss" % (x["opp"], (x["dvp_ratio"] - 1) * 100, x["pos"]))
    if x["score"]:
        tf, ta = x["score"]
        out.append("Game script: %s %d-%d (implied %.1f, %s)" % ("won" if tf > ta else "lost" if tf < ta else "tied", tf, ta, x["itt"],
                   "shootout" if tf + ta >= 55 else "low-scoring" if tf + ta <= 35 else "total %d" % (tf + ta)))
    if x["rzo"] >= 3: out.append("Red zone: %d of team's %d RZ plays" % (x["rzo"], x["rz_team"]))
    if x["big"]: out.append("%d play%s of 20+ yards" % (x["big"], "s" if x["big"] > 1 else ""))
    if x["td"] >= 2 and x["pos"] != "QB": out.append("%d TDs (TD-dependent - hard to repeat)" % x["td"])
    if x["wind"] and x["wind"] >= 15 and x["roof"] in ("outdoors", "open"): out.append("Weather: %d mph wind" % x["wind"])
    return out

def logit_fit(X, y, l2=1.0, it=400):
    X = np.c_[np.ones(len(X)), X]; b = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ b)); g = X.T @ (p - y) / len(y) + l2 * np.r_[0, b[1:]] / len(y)
        H = (X.T * (p * (1 - p))) @ X / len(y) + np.diag(np.r_[1e-6, [l2 / len(y)] * (X.shape[1] - 1)])
        b -= np.linalg.solve(H, g)
    return b
def logit_pred(b, X): return 1 / (1 + np.exp(-(np.c_[np.ones(len(X)), X] @ b)))
def auc(p, y):
    o = np.argsort(p); r = np.empty(len(p)); r[o] = np.arange(1, len(p) + 1); n1 = y.sum(); n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / max(1, n1 * n0))

def design(rows, full=True):
    base = [[math.log1p(max(0, x["prior"])), min(5.0, x["prior"] / max(1, x["sal"]) * 1000)] for x in rows]
    if not full: return np.array(base)
    return np.array([b + [x["f"][k] for k in FK] for b, x in zip(base, rows)])

def run(D, sched, slates):
    fit = sal_fit(slates)
    rows = [x for x in history_rows(D, sched, fit) if x["prior"] > 0 or x["pts"] >= 5]
    y = np.array([x["smash"] for x in rows]); base_rate = float(y.mean())
    weeks = sorted({x["w"] for x in rows})
    out = {"weeks": [], "salary_note": "Past-week DK salaries are not freely archived: salaries shown for weeks %d-%d are a PROXY fit from current real DK salaries vs pre-week DK average (per position)." % (weeks[0], weeks[-1]),
           "smash_def": "Smash = 4.0+ DK pts per $1k of (proxy) salary and 12+ pts", "base_rate": round(base_rate, 3), "n": len(rows)}
    for w in weeks:
        R = [x for x in rows if x["w"] == w]
        top = sorted(R, key=lambda x: -x["pts"])[:10]; sm = sorted([x for x in R if x["pts"] >= 12], key=lambda x: -x["val"])[:10]
        slim = lambda x: {k: x[k] for k in ("name", "team", "pos", "opp", "pts", "sal", "val", "prior")} | {"why": why(x)}
        out["weeks"].append({"w": w, "top": [slim(x) for x in top], "smash": [slim(x) for x in sm], "n_smash": int(sum(x["smash"] for x in R)), "n": len(R)})
    # hit rates by feature
    pats = []
    for k, label in FEATS:
        on = [x for x in rows if x["f"][k]]; off = [x for x in rows if not x["f"][k]]
        if len(on) < 15: continue
        h1 = np.mean([x["smash"] for x in on]); h0 = np.mean([x["smash"] for x in off])
        se = math.sqrt(max(1e-9, base_rate * (1 - base_rate) * (1 / len(on) + 1 / len(off))))
        by_w = {w: round(float(np.mean([x["smash"] for x in on if x["w"] == w] or [0])), 3) for w in weeks}
        pats.append({"k": k, "label": label, "n": len(on), "hit": round(float(h1), 3), "hit_off": round(float(h0), 3), "lift": round(float(h1 / max(1e-9, base_rate)), 2), "z": round((h1 - h0) / se, 2), "by_week": by_w})
    out["patterns"] = sorted(pats, key=lambda p: -p["lift"])
    # leave-one-week-out validation (weeks 2+), baseline = prior average + prior value only
    PF, PB, YY, top_f, top_b = [], [], [], [], []
    for w in [x for x in weeks if x >= 2]:
        tr = [x for x in rows if x["w"] != w]; te = [x for x in rows if x["w"] == w]
        ytr = np.array([x["smash"] for x in tr]); yte = np.array([x["smash"] for x in te])
        bf = logit_fit(design(tr), ytr); bb = logit_fit(design(tr, False), ytr)
        pf = logit_pred(bf, design(te)); pb = logit_pred(bb, design(te, False))
        PF += list(pf); PB += list(pb); YY += list(yte)
        k = 25; top_f.append(float(yte[np.argsort(-pf)[:k]].mean())); top_b.append(float(yte[np.argsort(-pb)[:k]].mean()))
    PF, PB, YY = map(np.array, (PF, PB, YY))
    ll = lambda p: float(-np.mean(YY * np.log(p + 1e-9) + (1 - YY) * np.log(1 - p + 1e-9)))
    out["validation"] = {"method": "leave-one-week-out on weeks 2-%d" % weeks[-1], "auc_signal": round(auc(PF, YY), 3), "auc_baseline": round(auc(PB, YY), 3),
                         "logloss_signal": round(ll(PF), 4), "logloss_baseline": round(ll(PB), 4),
                         "top25_hit_signal": round(float(np.mean(top_f)), 3), "top25_hit_baseline": round(float(np.mean(top_b)), 3), "base_rate": round(base_rate, 3)}
    v = out["validation"]; v["adds_lift"] = bool(v["auc_signal"] > v["auc_baseline"] + 0.005 and v["logloss_signal"] < v["logloss_baseline"])
    b = logit_fit(design(rows), y); out["coef"] = {n: round(float(c), 3) for n, c in zip(["const", "log_prior", "prior_value"] + FK, b)}
    return out, b, fit

def apply(slate, b, D, dvp_full, lgdvp, enabled=True, classic=None):
    """smash likelihood for upcoming players, using REAL salaries"""
    gm = {g["key"]: g for g in slate["games"]}
    res = []
    for p in slate["players"]:
        if p["pos"] not in POS or p.get("out") or not p.get("elig", True): continue
        g = gm.get(p["game"], {}); home = g.get("home") == p["team"]
        itt = g.get("itt_home" if home else "itt_away") or 0; spread = -(g.get("spread") or 0) if home else (g.get("spread") or 0)
        u = p.get("usage") if isinstance(p.get("usage"), dict) else {}
        prior = (sum(p["log"]) / len(p["log"])) if p.get("log") else (p.get("avg") or 0)
        wind = ((g.get("wx") or {}).get("wind") or 0) >= 15 and not (g.get("wx") or {}).get("dome")
        sal = (classic or {}).get(p["key"]) or p["sal"]  # showdown: use the player's classic salary scale when known
        f = {"vac": int(bool(p.get("shot")) or any("out" in (c or "").lower() and "vacated" in (c or "").lower() for c in p.get("edges", []))),
             "dvp": int(dvp_full.get(p["opp"], {}).get(p["pos"], 0) >= 1.10 * lgdvp.get(p["pos"], 99)), "itt": int(itt >= 24),
             "exp": int(bool(u.get("expanding")) or (u.get("trend") or 0) > 0.03), "rz": int((u.get("rz") or 0) >= 0.2),
             "cheap": int(sal <= 4500), "fav": int(spread >= 3), "wind": int(wind)}
        x = np.array([[math.log1p(max(0, prior)), min(5.0, prior / max(1, sal) * 1000)] + [f[k] for k in FK]])
        pr = float(logit_pred(b, x)[0])
        lab = dict(FEATS)
        p["smash"] = {"p": round(pr * 100, 1), "f": [lab[k] for k in FK if f[k] and k != "wind"] + (["Wind 15+ mph (negative)"] if f["wind"] else []), "on": enabled}
        res.append(p)
    top = sorted(res, key=lambda p: -p["smash"]["p"])[:15]
    return [{"name": p["name"], "team": p["team"], "pos": p["pos"], "opp": p["opp"], "game": p["game"], "sal": p["sal"], "proj": p["proj"],
             "p": p["smash"]["p"], "f": p["smash"]["f"], "time": gm.get(p["game"], {}).get("time")} for p in top]
