"""Phase-2 sources: nflverse schedule (remaining games + lines), Sleeper projections (Rotowire-sourced) and trending adds,
FantasyCalc redraft market values, RotoWire + CBS RSS news. All free/public; used for cross-reference, ROS and news."""
import csv, io, math, re, html, datetime as dt
import util as U

def norm(n):
    n = re.sub(r"[^a-z ]", "", (n or "").lower().replace("-", " "))
    return " ".join(w for w in n.split() if w not in ("jr", "sr", "ii", "iii", "iv", "v"))
FIX = {"LA": "LAR", "WSH": "WAS", "JAC": "JAX"}
T = lambda a: FIX.get(a, a)

def schedule(season):
    b = U.raw("https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv")
    if not b: return []
    return [r for r in csv.DictReader(io.StringIO(b.decode())) if r["season"] == str(season) and r["game_type"] == "REG"]

def week_of(sched, day):
    for r in sched:
        if r["gameday"] == day: return int(r["week"])
    return None

def sleeper(season, week):
    d = U.get("https://api.sleeper.app/projections/nfl/%d/%d?season_type=regular&position[]=QB&position[]=RB&position[]=WR&position[]=TE&position[]=DEF" % (season, week)) or []
    out, ids = {}, {}
    for x in d:
        pl = x.get("player") or {}; s = x.get("stats") or {}
        if not s.get("pts_ppr") and pl.get("position") != "DEF": continue
        nm = (pl.get("first_name", "") + " " + pl.get("last_name", "")).strip()
        tm = T(x.get("team") or pl.get("team") or "")
        ids[x.get("player_id")] = (norm(nm), tm)
        if pl.get("position") == "DEF":
            out[("dst", tm)] = {"pts": None}; continue
        # DK = PPR + yardage bonuses (3 pts at 300 pass / 100 rush / 100 rec), normal approx on projected yards
        def pb(m, thr, cv):
            if not m: return 0.0
            return 0.5 * math.erfc((thr - m) / (cv * m) / math.sqrt(2))
        bonus = 3 * (pb(s.get("pass_yd"), 300, .25) + pb(s.get("rush_yd"), 100, .5) + pb(s.get("rec_yd"), 100, .5))
        out[(norm(nm), tm)] = {"pts": round(s["pts_ppr"] + bonus, 2), "src": x.get("company") or "sleeper"}
    tr = U.get("https://api.sleeper.app/v1/players/nfl/trending/add?lookback_hours=48&limit=60") or []
    trend = {}
    for i, t in enumerate(tr):
        k = ids.get(t.get("player_id"))
        if k: trend[k] = {"rank": i + 1, "adds": t.get("count")}
    return out, trend

def fantasycalc():
    d = U.get("https://api.fantasycalc.com/values/current?isDynasty=false&numQbs=1&numTeams=12&ppr=1") or []
    out = {}
    for x in d:
        p = x.get("player") or {}
        out[(norm(p.get("name")), T(p.get("maybeTeam") or ""))] = {"value": x.get("value"), "rank": x.get("overallRank"), "pos_rank": x.get("positionRank")}
    return out

RSS = [("RotoWire", "https://www.rotowire.com/rss/news.php?sport=NFL"), ("CBS Sports", "https://www.cbssports.com/rss/headlines/nfl/")]
def rss_news():
    items = []
    for src, url in RSS:
        b = U.raw(url)
        if not b: continue
        x = b.decode("utf-8", "ignore")
        for it in re.findall(r"<item>(.*?)</item>", x, re.S):
            g = lambda tag: html.unescape(re.sub(r"<!\[CDATA\[|\]\]>|<[^>]+>", "", (re.search(r"<%s>(.*?)</%s>" % (tag, tag), it, re.S) or [None, ""])[1])).strip()
            items.append({"src": src, "title": g("title"), "desc": g("description")[:300], "date": g("pubDate")[:16]})
    return items

def match_news(items, players):
    """attach RSS items to players whose full name appears in the title/description"""
    by = {}
    names = {p["name"]: p for p in players if p["pos"] != "DST"}
    for it in items:
        txt = it["title"] + " " + it["desc"]
        for n, p in names.items():
            if n in txt or (n.split(" ")[-1] + ":" in it["title"] and n.split(" ")[0] in txt):
                by.setdefault(p["key"], []).append({"t": ("%s: %s %s" % (it["src"], it["title"], it["desc"]))[:240], "d": it["date"]})
    return by
