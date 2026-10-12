"""Usage x efficiency projection model with game-correlated Monte Carlo (DraftKings NFL scoring).
Everything here is an estimate. This season's games drive it (recency-weighted: last 2-3 games count most);
prior-season data is only a light prior for players with almost no sample."""
import csv, gzip, io, math, re
import numpy as np
import util as U

REL = "https://github.com/nflverse/nflverse-data/releases/download/"
TEAMFIX = {"LA": "LAR", "WSH": "WAS", "JAC": "JAX"}
T = lambda a: TEAMFIX.get(a, a)
NS = 4000          # simulations per game
KEEP = 160         # sims stored per player for the browser optimizer (same index = same game scenario)
RNG = np.random.default_rng(7)

def norm(n):
    n = re.sub(r"[^a-z ]", "", (n or "").lower().replace("-", " "))
    return " ".join(w for w in n.split() if w not in ("jr", "sr", "ii", "iii", "iv", "v"))
def fl(x):
    try: return float(x)
    except Exception: return 0.0

def rwts(n):
    """recency weights, most-recent first: last game 0.32, then 0.24, 0.17, 0.12, ... (normalized)"""
    w = [0.32, 0.24, 0.17, 0.12, 0.08, 0.04, 0.03][:n] or [1]
    s = sum(w); return [x / s for x in w]

def csv_rows(path, gz=False):
    b = U.raw(REL + path)
    if not b: return []
    txt = gzip.decompress(b).decode() if gz else b.decode("utf-8")
    return list(csv.DictReader(io.StringIO(txt)))

class Data:
    def __init__(self, season):
        self.season = season
        self.wk = [r for r in csv_rows("stats_player/stats_player_week_%d.csv" % season) if r.get("season_type") == "REG"]
        self.prev = [r for r in csv_rows("stats_player/stats_player_week_%d.csv" % (season - 1)) if r.get("season_type") == "REG"]
        self.snaps = csv_rows("snap_counts/snap_counts_%d.csv" % season)
        pbp = csv_rows("pbp/play_by_play_%d.csv.gz" % season, gz=True)
        self.weeks = sorted({int(r["week"]) for r in self.wk})
        # red-zone opportunities per player-week, team rz plays, team pass/rush plays
        self.rz, self.team = {}, {}
        for r in pbp:
            if r.get("play_type") not in ("pass", "run") or not r.get("posteam"): continue
            w, tm = int(r["week"]), T(r["posteam"])
            t = self.team.setdefault((tm, w), {"pa": 0, "ru": 0, "rz": 0, "rzp": 0, "rzr": 0, "opp": T(r.get("defteam") or "")})
            rz = (fl(r.get("yardline_100")) or 99) <= 20
            if r["play_type"] == "pass": t["pa"] += 1
            else: t["ru"] += 1
            if rz:
                t["rz"] += 1; t["rzp" if r["play_type"] == "pass" else "rzr"] += 1
                if r["play_type"] == "pass" and r.get("receiver_player_id"): self.rz[(r["receiver_player_id"], w, "p")] = self.rz.get((r["receiver_player_id"], w, "p"), 0) + 1
                if r["play_type"] == "run" and r.get("rusher_player_id"): self.rz[(r["rusher_player_id"], w, "r")] = self.rz.get((r["rusher_player_id"], w, "r"), 0) + 1
        self.snap = {}
        for r in self.snaps:
            if r.get("game_type") != "REG": continue
            self.snap[(norm(r["player"]), T(r["team"]), int(r["week"]))] = fl(r["offense_pct"])
        # team-week totals from weekly stats
        self.tt = {}
        for r in self.wk:
            k = (T(r["team"]), int(r["week"]))
            t = self.tt.setdefault(k, {"tgt": 0, "car": 0, "att": 0, "ptd": 0, "rtd": 0, "py": 0, "pts_dk": 0})
            t["tgt"] += fl(r["targets"]); t["car"] += fl(r["carries"]); t["att"] += fl(r["attempts"])
            t["ptd"] += fl(r["passing_tds"]); t["rtd"] += fl(r["rushing_tds"])
        self.by_player = {}
        for r in self.wk:
            self.by_player.setdefault((norm(r["player_display_name"]), T(r["team"])), []).append(r)
        self.prev_by = {}
        for r in self.prev:
            self.prev_by.setdefault(norm(r["player_display_name"]), []).append(r)
        self.lg = self._league()

    def _league(self):
        """league efficiency priors by position (this season)"""
        agg = {}
        for r in self.wk:
            p = r["position"]
            a = agg.setdefault(p, {"tgt": 0, "rec": 0, "recy": 0, "car": 0, "ry": 0, "att": 0, "py": 0, "int": 0, "ptd": 0})
            for k, c in (("tgt", "targets"), ("rec", "receptions"), ("recy", "receiving_yards"), ("car", "carries"), ("ry", "rushing_yards"),
                         ("att", "attempts"), ("py", "passing_yards"), ("int", "passing_interceptions"), ("ptd", "passing_tds")):
                a[k] += fl(r[c])
        out = {}
        for p, a in agg.items():
            out[p] = {"cr": a["rec"] / max(1, a["tgt"]), "ypr": a["recy"] / max(1, a["rec"]), "ypc": a["ry"] / max(1, a["car"]),
                      "ypa": a["py"] / max(1, a["att"]), "intr": a["int"] / max(1, a["att"])}
        return out

    def team_games(self, tm):
        return sorted({w for (t, w) in self.tt if t == tm})

def player_usage(D, name, tm):
    """per-week usage rows (only weeks the team played), most-recent first."""
    rows = {int(r["week"]): r for r in D.by_player.get((norm(name), tm), [])}
    out = []
    for w in reversed(D.team_games(tm)):
        tt = D.tt[(tm, w)]; te = D.team.get((tm, w), {})
        r = rows.get(w)
        snap = D.snap.get((norm(name), tm, w))
        if r is None and not snap:
            out.append({"w": w, "played": False}); continue
        pid = r["player_id"] if r else None
        g = {"w": w, "played": True, "snap": snap if snap is not None else None,
             "tgt": fl(r["targets"]) if r else 0, "car": fl(r["carries"]) if r else 0,
             "ts": fl(r["targets"]) / max(1, tt["tgt"]) if r else 0, "cs": fl(r["carries"]) / max(1, tt["car"]) if r else 0,
             "rz": ((D.rz.get((pid, w, "p"), 0) + D.rz.get((pid, w, "r"), 0)) / max(1, te.get("rz", 0))) if pid else 0,
             "rzt": (D.rz.get((pid, w, "p"), 0) / max(1, te.get("rzp", 0))) if pid else 0,
             "rzr": (D.rz.get((pid, w, "r"), 0) / max(1, te.get("rzr", 0))) if pid else 0,
             "rec": fl(r["receptions"]) if r else 0, "recy": fl(r["receiving_yards"]) if r else 0, "ry": fl(r["rushing_yards"]) if r else 0,
             "rectd": fl(r["receiving_tds"]) if r else 0, "rtd": fl(r["rushing_tds"]) if r else 0,
             "att": fl(r["attempts"]) if r else 0, "py": fl(r["passing_yards"]) if r else 0, "ptd": fl(r["passing_tds"]) if r else 0,
             "int": fl(r["passing_interceptions"]) if r else 0, "opp": T(r["opponent_team"]) if r else te.get("opp")}
        if r and snap is None and (g["tgt"] + g["car"] + g["att"]) == 0: g["played"] = False
        out.append(g)
    return out

def wavg(games, key, played_only=True):
    gs = [g for g in games if g.get("played") or not played_only][:6]
    if not gs: return 0.0
    w = rwts(len(gs)); return sum(x * g.get(key, 0) or 0 for x, g in zip(w, gs))

def usage_summary(games):
    pl = [g for g in games if g.get("played")]
    if not pl: return None
    s = {k: round(wavg(games, k), 4) for k in ("ts", "cs", "rz", "rzt", "rzr")}
    s["qb"] = {k: wavg(games, k) for k in ("att", "py", "ptd", "ry", "car")}
    sn = [g["snap"] for g in pl if g.get("snap") is not None]
    s["snap"] = round(wavg([g for g in pl if g.get("snap") is not None], "snap"), 3) if sn else None
    s["n"] = len(pl)
    s["weeks"] = [{"w": g["w"], "snap": g.get("snap"), "ts": round(g.get("ts", 0), 3), "cs": round(g.get("cs", 0), 3), "rz": round(g.get("rz", 0), 3),
                   "tgt": g.get("tgt"), "car": g.get("car"), "played": g.get("played")} for g in games[:6]]
    # expanding role: last 2 played games vs earlier
    if len(pl) >= 3:
        last, early = pl[:2], pl[2:]
        f = lambda gs, k: sum(g.get(k) or 0 for g in gs) / len(gs)
        opp_l = f(last, "ts") + 0.6 * f(last, "cs"); opp_e = f(early, "ts") + 0.6 * f(early, "cs")
        snl = [g["snap"] for g in last if g.get("snap") is not None]; sne = [g["snap"] for g in early if g.get("snap") is not None]
        dsnap = (sum(snl) / len(snl) - sum(sne) / len(sne)) if snl and sne else 0
        s["trend"] = round(opp_l - opp_e, 3); s["dsnap"] = round(dsnap, 3)
        s["expanding"] = bool((opp_l >= opp_e * 1.35 and opp_l - opp_e >= 0.04) or dsnap >= 0.18)
        s["shrinking"] = bool(opp_l <= opp_e * 0.65 and opp_e >= 0.08)
    return s

def eff(games, pos, lg):
    """efficiency, shrunk toward the positional league rate by sample size"""
    pl = [g for g in games if g.get("played")]
    tg = sum(g["tgt"] for g in pl); rec = sum(g["rec"] for g in pl); recy = sum(g["recy"] for g in pl)
    car = sum(g["car"] for g in pl); ry = sum(g["ry"] for g in pl); att = sum(g["att"] for g in pl); py = sum(g["py"] for g in pl)
    L = lg.get(pos) or lg.get("WR")
    def shr(num, den, prior, k):
        return (num + prior * k) / (den + k)
    return {"cr": shr(rec, tg, L["cr"], 25), "ypr": shr(recy, rec, L["ypr"], 20), "ypc": shr(ry, car, L["ypc"], 40),
            "ypa": shr(py, att, (lg.get("QB") or L)["ypa"], 120), "intr": shr(sum(g["int"] for g in pl), att, (lg.get("QB") or L)["intr"], 200)}

def team_volume(D, tm):
    gs = list(reversed(D.team_games(tm)))[:6]
    w = rwts(len(gs))
    pa = sum(x * D.tt[(tm, g)]["tgt"] for x, g in zip(w, gs)); ru = sum(x * D.tt[(tm, g)]["car"] for x, g in zip(w, gs))
    ptd = sum(D.tt[(tm, g)]["ptd"] for g in gs); rtd = sum(D.tt[(tm, g)]["rtd"] for g in gs)
    return {"tgt": pa or 32, "car": ru or 26, "pass_td_share": (ptd + 6) / (ptd + rtd + 10)}

def redistribute(team_players, outs):
    """Vacated usage from OUT players -> healthy teammates.
    Only usage the out player actually held in the recent window is vacated (if he already missed the last games,
    the teammates' recent shares already reflect his absence). Each teammate's gain is proportional to how his share
    moved in games the out player missed (with/without split) when available, otherwise to his current share;
    same-position teammates get 55% priority, all others share the rest."""
    notes = []
    for o in outs:
        g = o["games"]; recent = g[:3]
        played_recent = sum(1 for x in recent if x.get("played")) / max(1, len(recent))
        for key, lab in (("ts", "targets"), ("cs", "carries")):
            vac = o["u"][key] * played_recent if o["u"] else 0
            if vac < 0.04: continue
            mates = [p for p in team_players if p["key"] != o["key"] and p.get("u") and not p.get("out") and (p["pos"] in ("WR", "TE", "RB") if key == "ts" else p["pos"] in ("RB", "QB"))]
            if not mates: continue
            def weight(p):
                w = p["u"][key]
                missed = [x["w"] for x in g if not x.get("played")]
                if missed:  # with/without split for this teammate
                    wo = [x for x in p["games"] if x["w"] in missed and x.get("played")]
                    wi = [x for x in p["games"] if x["w"] not in missed and x.get("played")]
                    if wo and wi:
                        d = sum(x[key] for x in wo) / len(wo) - sum(x[key] for x in wi) / len(wi)
                        w = max(0.0, w + 0.7 * d)
                if p["pos"] == "QB": w *= 0.5
                return w
            ws = {p["key"]: weight(p) for p in mates}
            same = [p for p in mates if p["pos"] == o["pos"]]
            s_same = sum(ws[p["key"]] for p in same); s_all = sum(ws.values()) or 1
            gains = []
            for p in mates:
                gshare = 0.45 * vac * ws[p["key"]] / s_all
                if same and s_same > 0 and p["pos"] == o["pos"]: gshare += 0.55 * vac * ws[p["key"]] / s_same
                elif not same or s_same <= 0: gshare += 0.55 * vac * ws[p["key"]] / s_all
                if gshare > 0.003:
                    p["u"][key] = p["u"][key] + gshare
                    p.setdefault("gain", []).append((o["name"], lab, gshare))
                    gains.append((p["name"], gshare))
            gains.sort(key=lambda x: -x[1])
            notes.append({"team": o["team"], "out": o["name"], "pos": o["pos"], "kind": lab, "vac": round(vac * 100, 1),
                          "to": [[n, round(x * 100, 1)] for n, x in gains[:5]]})
    return notes

DK = lambda py, ptd, it, ry, rtd, rec, recy, rectd: (py * .04 + ptd * 4 - it + 3 * (py >= 300) + ry * .1 + rtd * 6 + 3 * (ry >= 100)
                                                       + rec + recy * .1 + rectd * 6 + 3 * (recy >= 100))

def simulate_game(game, teams, rng):
    """teams: {abbr: {"vol":..., "itt":, "players":[...]} }. Returns sims per player key (np arrays of DK points)."""
    G = np.exp(rng.normal(0, 0.14, NS))           # shared pace/scoring environment (shootout vs slog)
    out = {}
    for tm, t in teams.items():
        Tm = np.exp(rng.normal(0, 0.11, NS))       # team-specific efficiency
        vol = t["vol"]; ps = [p for p in t["players"] if p["pos"] in ("QB", "RB", "WR", "TE") and p.get("u")]
        A = rng.poisson(np.maximum(1, vol["tgt_proj"] * G ** 0.6 * Tm ** 0.3))
        C = rng.poisson(np.maximum(1, vol["car_proj"] * G ** 0.3 * Tm ** 0.5))
        ts = np.array([max(0, p["u"]["ts"]) for p in ps]); cs = np.array([max(0, p["u"]["cs"]) * (1 if p["pos"] != "QB" else 1) for p in ps])
        if ts.sum() > 0.97: ts = ts * 0.97 / ts.sum()
        if cs.sum() > 0.98: cs = cs * 0.98 / cs.sum()
        tgt = rng.multinomial(A, np.append(ts, 1 - ts.sum())) if len(ps) else np.zeros((NS, 1), int)
        car = rng.multinomial(C, np.append(cs, 1 - cs.sum())) if len(ps) else np.zeros((NS, 1), int)
        # TD environment tied to the implied team total (~0.118 TDs per implied point)
        tdscale = Tm * G ** 0.8
        pass_td_l = t["itt"] * 0.118 * vol["pass_td_share"]; rush_td_l = t["itt"] * 0.118 * (1 - vol["pass_td_share"])
        wr = np.array([0.55 * p["u"].get("rzt", 0) + 0.45 * p["u"]["ts"] for p in ps]) if ps else np.zeros(0)
        wc = np.array([0.6 * p["u"].get("rzr", 0) + 0.4 * p["u"]["cs"] for p in ps]) if ps else np.zeros(0)
        wr = wr / max(1e-6, wr.sum()) * min(1.0, ts.sum() + 0.05); wc = wc / max(1e-6, wc.sum()) * min(1.0, cs.sum() + 0.05)
        team_py = np.zeros(NS); team_ptd = np.zeros(NS)
        res = {}
        lams = []
        for i, p in enumerate(ps):
            lr, lu = pass_td_l * wr[i], rush_td_l * wc[i]
            if p.get("atd"):  # Bet Lab anytime-TD probability -> expected TDs, blended 50/50 with the usage model
                tl = -math.log(max(0.02, 1 - p["atd"])); cur = lr + (lu if p["pos"] != "QB" else 0)
                if cur > 0: f = (0.5 * cur + 0.5 * tl) / cur; lr *= f; lu *= f
                elif p["pos"] == "QB": lu = 0.5 * lu + 0.5 * tl
            lams.append([lr * p.get("tdm", 1.0), lu * p.get("tdm", 1.0)])
        lams = np.array(lams) if lams else np.zeros((0, 2))
        for j, bud in ((0, pass_td_l), (1, rush_td_l)):  # keep the team within ~15% of its Vegas-implied TD budget
            tot = lams[:, j].sum() if len(lams) else 0
            if tot > bud * 1.15: lams[:, j] *= (bud * 1.15) / tot
        for i, p in enumerate(ps):
            e = p["eff"]; mf = p.get("mf", 1.0)
            k = tgt[:, i]; rec = rng.binomial(k, min(0.95, e["cr"]))
            recy = np.maximum(0, rec * e["ypr"] * mf + rng.normal(0, 1, NS) * np.sqrt(rec) * e["ypr"] * 0.85)
            lam_rec, lam_ru = lams[i]
            rectd = rng.poisson(lam_rec * tdscale) if p["pos"] != "QB" else np.zeros(NS)
            c = car[:, i]
            ry = c * e["ypc"] * mf + rng.normal(0, 1, NS) * np.sqrt(np.maximum(c, 0)) * 5.2
            rtd = rng.poisson(lam_ru * tdscale)
            team_py += recy; team_ptd += rectd
            res[p["key"]] = dict(rec=rec, recy=recy, rectd=rectd, ry=ry, rtd=rtd)
        # the uncaptured target share (backups) also produces passing yards/TDs for the QB
        other = tgt[:, -1] if len(ps) else A
        orec = rng.binomial(other, 0.62); team_py += orec * 9.5
        team_ptd += rng.poisson(pass_td_l * max(0, 1 - wr.sum()) * tdscale)
        for p in ps:
            r = res[p["key"]]
            if p["pos"] == "QB":
                py = team_py * p.get("qbshare", 1.0); ptd = team_ptd * p.get("qbshare", 1.0)
                q = p["u"].get("qb") or {}
                if q.get("att"):  # anchor to his own recent passing (yds/TDs), scaled to projected volume & matchup
                    vr = vol["tgt_proj"] / max(1, vol["tgt"])
                    own_py = q["py"] * vr * p.get("mf", 1.0); own_td = q["ptd"] * vr * (t["itt"] / max(14, t.get("itt_avg", t["itt"])))
                    if py.mean() > 0: py = py * (0.4 + 0.6 * own_py / py.mean())
                    if ptd.mean() > 0: ptd = ptd * (0.5 + 0.5 * own_td / ptd.mean())
                it = rng.poisson(A * p["eff"]["intr"] * p.get("qbshare", 1.0))
                pts = DK(py, ptd, it, r["ry"], r["rtd"], 0, 0, 0) - 0.12
                out[p["key"]] = (pts, {"py": py.mean(), "ptd": ptd.mean(), "int": it.mean(), "ry": r["ry"].mean(), "rtd": r["rtd"].mean()})
            else:
                pts = DK(0, 0, 0, r["ry"], r["rtd"], r["rec"], r["recy"], r["rectd"]) - 0.06
                out[p["key"]] = (pts, {"tgt": float((tgt[:, ps.index(p)]).mean()), "rec": r["rec"].mean(), "recy": r["recy"].mean(),
                                       "car": float(car[:, ps.index(p)].mean()), "ry": r["ry"].mean(), "td": (r["rectd"] + r["rtd"]).mean()})
        t["G"], t["Tm"] = G, Tm
    # DST and K: driven by the opponent's simulated scoring environment
    abbrs = list(teams)
    for tm, t in teams.items():
        opp = [a for a in abbrs if a != tm]
        o = teams[opp[0]] if opp else None
        for p in t["players"]:
            if p["pos"] == "DST":
                oitt = o["itt"] if o else 22
                opp_pts = np.maximum(0, rng.normal(oitt, 8.5, NS) * (o["G"] ** 0.8 * o["Tm"] if o else 1))
                tiers = np.select([opp_pts < 0.5, opp_pts < 6.5, opp_pts < 13.5, opp_pts < 20.5, opp_pts < 27.5, opp_pts < 34.5], [10, 7, 4, 1, 0, -1], -4)
                d = p.get("dstrate", {"sk": 2.4, "to": 1.2, "td": 0.12})
                env = 22.5 / max(14, oitt)
                pts = tiers + rng.poisson(d["sk"] * env ** 0.5, NS) + 2 * rng.poisson(d["to"] * env ** 0.5, NS) + 6 * rng.poisson(d["td"] + 0.05, NS)
                out[p["key"]] = (pts.astype(float), {"oitt": oitt, "sk": d["sk"], "to": d["to"]})
            elif p["pos"] == "K":
                base = p.get("kbase", 7.5) * (t["itt"] / 22.5) ** 0.6
                pts = np.maximum(0, base * t["G"] ** 0.5 * t["Tm"] ** 0.5 + rng.normal(0, 3.2, NS))
                out[p["key"]] = (pts, {})
    return out
