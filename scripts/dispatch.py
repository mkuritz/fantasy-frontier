"""Cheap 30-min dispatcher. Runs the full build only when it matters:
 - new DraftKings salaries posted (a TNF/Sunday-main/MNF draft group we haven't built yet)
 - pre-lock: ~2h and ~45m before each slate's lock (injury/inactive news)
 - overnight ~3 AM ET and an every-4-hours daytime sweep (injuries, odds, Bet Lab props)
Writes mode=full|none to $GITHUB_OUTPUT. Each window fires once (data/refresh_state.json)."""
import os, re, json, datetime as dt, sys
sys.path.insert(0, os.path.dirname(__file__))
import util as U
now = dt.datetime.now(dt.timezone.utc); et = now - dt.timedelta(hours=4)
st = U.load("refresh_state.json", {}); meta = U.load("meta.json", {})
fired, why = st.get("fired", {}), None
def once(key):
    if key in fired: return False
    fired[key] = now.isoformat(timespec="minutes"); return True
if os.environ.get("FORCE_FULL") == "true": why = "manual"
lob = U.get("https://www.draftkings.com/lobby/getcontests?sport=NFL") or {}
known = {str((v or {}).get("dg")) for v in (meta.get("slates") or {}).values()}
from fetch_dfs import pick_groups
for kind, g in pick_groups(lob.get("DraftGroups", [])).items():
    d = dt.datetime.fromisoformat(g["StartDateEst"][:19])
    if str(g["DraftGroupId"]) not in known and not why: why = "new salaries dg %s" % g["DraftGroupId"]
    lock = d.replace(tzinfo=dt.timezone(dt.timedelta(hours=-4)))
    for mins in (120, 45):
        if dt.timedelta(0) <= lock - now <= dt.timedelta(minutes=mins) and once("pre%d-%s" % (mins, g["DraftGroupId"])) and not why:
            why = "pre-lock %dm dg %s" % (mins, g["DraftGroupId"])
if not why and 3 <= et.hour < 6 and once("night-" + et.strftime("%Y-%m-%d")): why = "overnight"
if not why and 9 <= et.hour <= 23 and et.hour % 4 == 1 and once("day-" + et.strftime("%Y-%m-%d-%H")): why = "daytime sweep"
cut = (now - dt.timedelta(days=10)).isoformat()
st["fired"] = {k: v for k, v in fired.items() if v > cut}
U.save("refresh_state.json", st)
mode = "full" if why else "none"
print("mode:", mode, why or "")
with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f: f.write("mode=%s\nwhy=%s\n" % (mode, why or ""))
