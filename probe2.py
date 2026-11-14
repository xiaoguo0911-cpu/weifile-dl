#!/usr/bin/env python3
"""Determine whether the 403 is geo-IP based or path/exploit based.
Tests multiple paths from the runner, and reports the runner's public IP + geo."""
import urllib.request, json, sys, os

BASE = "https://v2z8je.u8entertainment.com"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        r = urllib.request.urlopen(req, timeout=25)
        return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return "ERR", {}, str(e).encode()

out = {}

# runner public IP + geo
try:
    req = urllib.request.Request("https://api.ipify.org?format=json", headers={"User-Agent": "curl/8"})
    ip = json.loads(urllib.request.urlopen(req, timeout=15).read()).get("ip")
    out["runner_ip"] = ip
    try:
        req2 = urllib.request.Request(f"https://ipapi.co/{ip}/json/", headers={"User-Agent": "curl/8"})
        geo = json.loads(urllib.request.urlopen(req2, timeout=15).read())
        out["geo"] = {k: geo.get(k) for k in ["country", "region", "city", "org", "asn"]}
    except Exception as e:
        out["geo"] = "err " + str(e)
except Exception as e:
    out["runner_ip"] = "err " + str(e)

paths = [
    "/",
    "/channel/",
    "/channel/O.O.CA/",
    "/channel/O.O.CA/weifile/",
    "/channel/O.O.CA/weifile/weifile.html",
    "/channel/O.O.CA/weifile/index.js",
    "/channel/O.O.CA/weifile/weifile.js",
    "/next-chain/frame.html",
    "/next-chain/rce_loader.js",
]

out["paths"] = {}
for p in paths:
    st, hd, b = get(BASE + p)
    out["paths"][p] = {"status": st, "len": len(b), "server": hd.get("Server")}
    print(f"{p} -> {st} len={len(b)}")

os.makedirs("/tmp/out", exist_ok=True)
with open("/tmp/out/probe2.json", "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print(json.dumps(out, indent=2, ensure_ascii=False))
