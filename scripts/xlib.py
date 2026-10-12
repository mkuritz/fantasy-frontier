"""Shared helpers for the free-source cross-check (data/xcheck.json). Every source is optional."""
import csv, gzip, io, json, os, time, datetime as dt
from urllib.request import Request, urlopen
UA = {"User-Agent": "Mozilla/5.0 (SportsLabs data refresh; +https://mkuritz.github.io/sports-labs/)"}
class Src:
    def __init__(s): s.list = []
    def get(s, name, url, what, fn, link=None, new=True):
        t = time.time()
        try:
            v = fn(); n = len(v) if hasattr(v, "__len__") else None
            s.list.append(dict(name=name, url=link or url, status="ok" if n else "empty", rows=n, what=what, new=new)); return v
        except Exception as e:
            s.list.append(dict(name=name, url=link or url, status="failed", err=str(e)[:90], what=what, new=new)); return None
        finally: time.sleep(0.5)
def fetch(url, timeout=60, hdr=None):
    with urlopen(Request(url, headers=hdr or UA), timeout=timeout) as r: b = r.read()
    if url.endswith(".gz") or b[:2] == b"\x1f\x8b": b = gzip.decompress(b)
    return b
def js(url, **k): return json.loads(fetch(url, **k))
def rows(url, **k): return list(csv.DictReader(io.StringIO(fetch(url, **k).decode("utf-8-sig"))))
def f(x, d=None):
    try: return float(x)
    except Exception: return d
def norm(n):
    import re, unicodedata
    n = unicodedata.normalize("NFKD", n or "").encode("ascii", "ignore").decode().lower()
    n = re.sub(r"[.'’,-]", " ", n); n = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", " ", n)
    return " ".join(n.split())
def verdict(rel, tol=0.15, hard=0.30):
    a = abs(rel); return "agree" if a <= tol else ("watch" if a <= hard else "disagree")
def write(path, title, src, tables, summary):
    old = {}
    if os.path.exists(path):
        try: old = json.load(open(path))
        except Exception: pass
    # degrade gracefully: if a table came back empty because its source failed, keep the previous one
    names = {t["title"] for t in tables if t["rows"]}
    for t in old.get("tables", []):
        if t["title"] not in names and not any(x["title"] == t["title"] and x["rows"] for x in tables):
            t["note"] = (t.get("note") or "").split(" (kept from previous")[0] + " (kept from previous refresh: source unavailable this run)"
            tables = [x for x in tables if x["title"] != t["title"]] + [t]
    json.dump(dict(title=title, generated=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                   sources=src.list, tables=tables, summary=summary), open(path, "w"), separators=(",", ":"))
