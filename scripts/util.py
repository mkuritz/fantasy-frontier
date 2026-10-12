import json, os, time, urllib.request
DATA = os.path.join(os.path.dirname(__file__), "..", "data")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
def raw(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=40) as r: return r.read()
        except Exception as e:
            print("GET fail", url[:100], e); time.sleep(2 + 3 * i)
    return None
def get(url, tries=3):
    b = raw(url, tries)
    try: return json.loads(b) if b else None
    except Exception: return None
def load(name, default):
    try:
        with open(os.path.join(DATA, name)) as f: return json.load(f)
    except Exception: return default
def save(name, obj):
    with open(os.path.join(DATA, name), "w") as f: json.dump(obj, f, separators=(",", ":"), sort_keys=True)
