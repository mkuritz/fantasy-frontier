"""Open-Meteo (free, no key): geocoding (city -> lat/lon/elevation, cached in data/geo.json) and kickoff forecasts.
Also haversine travel distance. Flags: wind > 15 mph (passing/kicking), rain (totals/shots), heat/cold, altitude."""
import math, json, datetime as dt
from urllib.parse import quote
import util as F

ROOF_NFL = {"ARI": "retractable roof", "ATL": "retractable roof", "DAL": "retractable roof", "DET": "dome", "HOU": "retractable roof",
            "IND": "retractable roof", "LV": "dome", "LAR": "covered roof", "LAC": "covered roof", "MIN": "dome", "NO": "dome"}
_geo = None

def geo(city, country=""):
    global _geo
    if _geo is None: _geo = F.load("geo.json", {})
    k = (city + "|" + country).lower()
    if k in _geo: return _geo[k]
    d = F.get("https://geocoding-api.open-meteo.com/v1/search?count=5&language=en&name=" + quote(city)) or {}
    res = d.get("results") or []
    if country: res = [r for r in res if country.lower() in (r.get("country", "") + " " + r.get("country_code", "")).lower()] or res
    r = res[0] if res else None
    _geo[k] = {"lat": r["latitude"], "lon": r["longitude"], "elev": r.get("elevation"), "name": r.get("name")} if r else None
    F.save("geo.json", _geo)
    return _geo[k]

def km(a, b):
    if not a or not b: return None
    p = math.pi / 180
    h = math.sin((b["lat"] - a["lat"]) * p / 2) ** 2 + math.cos(a["lat"] * p) * math.cos(b["lat"] * p) * math.sin((b["lon"] - a["lon"]) * p / 2) ** 2
    return round(12742 * math.asin(math.sqrt(h)))

def forecast(g, iso):
    """hourly forecast at kickoff hour (UTC); None beyond the 16-day window."""
    if not g: return None
    t = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if t - dt.datetime.now(dt.timezone.utc) > dt.timedelta(days=15): return None
    day = t.strftime("%Y-%m-%d")
    d = F.get("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&hourly=temperature_2m,precipitation,precipitation_probability,wind_speed_10m,wind_gusts_10m"
              "&wind_speed_unit=mph&temperature_unit=fahrenheit&precipitation_unit=inch&timezone=UTC&start_date=%s&end_date=%s" % (g["lat"], g["lon"], day, day)) or {}
    h = d.get("hourly") or {}
    try: i = h["time"].index(t.strftime("%Y-%m-%dT%H:00"))
    except (KeyError, ValueError): return None
    w = {"temp": h["temperature_2m"][i], "wind": h["wind_speed_10m"][i], "gust": h["wind_gusts_10m"][i],
         "rain": h["precipitation"][i], "pop": h["precipitation_probability"][i]}
    fl = []
    if (w["wind"] or 0) > 15: fl.append("High wind %d mph (gusts %d): hurts passing & kicking" % (w["wind"], w["gust"] or 0))
    if (w["rain"] or 0) >= 0.04 or (w["pop"] or 0) >= 60: fl.append("Rain likely (%d%%, %.2f in/h): lowers totals & shot quality" % (w["pop"] or 0, w["rain"] or 0))
    if w["temp"] is not None and w["temp"] <= 25: fl.append("Cold %d°F: ball handling / kicking" % w["temp"])
    if w["temp"] is not None and w["temp"] >= 90: fl.append("Heat %d°F: fatigue late" % w["temp"])
    w["flags"] = fl
    w["src"] = "Open-Meteo forecast at kickoff hour"
    return w
