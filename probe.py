#!/usr/bin/env python3
"""
Probe the weifile channel using Playwright WebKit on macOS runner.
Captures ALL network requests/responses + DOM + JS globals to find the file list.
"""
import asyncio, os, json, sys, re, time

TARGET = os.environ.get("TARGET_URL", "https://v2z8je.u8entertainment.com/channel/O.O.CA/weifile/")
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1"

CAPTURED = []
CONSOLE = []

def log(msg):
    print(msg, flush=True)

async def main():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.webkit.launch(headless=True)
        context = await browser.new_context(
            user_agent=UA,
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale="zh-CN",
            extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9"},
        )

        # Spoof iOS Safari fingerprints
        await context.add_init_script("""
            () => {
                try {
                    Object.defineProperty(navigator, 'platform', {get: () => 'iPhone'});
                    Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 5});
                    Object.defineProperty(navigator, 'vendor', {get: () => 'Apple Computer, Inc.'});
                    Object.defineProperty(navigator, 'userAgent', {get: () => 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1'});
                    window.webkit = window.webkit || {};
                    window.webkit.messageHandlers = window.webkit.messageHandlers || {};
                } catch (e) { console.log('spoof err', e); }
            }
        """)

        page = await context.new_page()

        async def on_response(resp):
            try:
                url = resp.url
                status = resp.status
                ct = resp.headers.get("content-type", "")
                if any(k in url for k in [".js", "res", "list", "api", "json", "weifile", "get", "download", "channel", "rce", "sbx", "pe_"]):
                    try:
                        body = await resp.text()
                    except Exception:
                        body = "<binary/non-text>"
                    entry = {"url": url, "status": status, "ct": ct, "body_head": body[:2000]}
                    CAPTURED.append(entry)
                    log(f"[RESP {status}] {url[:160]} ct={ct} len={len(body)}")
            except Exception as e:
                log(f"[resp err] {e}")

        async def on_request(req):
            log(f"[REQ] {req.method} {req.url[:160]}")

        page.on("response", on_response)
        page.on("request", on_request)
        page.on("console", lambda m: CONSOLE.append(m.text))
        page.on("pageerror", lambda e: log(f"[pageerror] {e}"))

        log(f"[*] goto {TARGET}")
        try:
            await page.goto(TARGET, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            log(f"[goto] {e}")

        # wait and observe dynamic loading
        for i in range(6):
            await asyncio.sleep(10)
            log(f"[wait {i}] url={page.url}")
            try:
                title = await page.title()
                log(f"  title={title}")
            except Exception as e:
                log(f"  title err {e}")

        # Dump any global state / discovered keys
        try:
            state = await page.evaluate("""() => {
                const out = {};
                out.globals = Object.keys(window).filter(k => /enc|session|key|token|hash|list|file|data|download/i.test(k)).slice(0,100);
                out.bodyText = document.body ? document.body.innerText.slice(0, 2000) : '';
                out.htmlLen = document.documentElement ? document.documentElement.outerHTML.length : 0;
                out.cookies = document.cookie;
                return out;
            }""")
            log("[STATE] " + json.dumps(state, ensure_ascii=False)[:3000])
            CAPTURED.append({"kind": "state", "state": state})
        except Exception as e:
            log(f"[state err] {e}")

        await browser.close()

    # Write captured
    out = {
        "target": TARGET,
        "console": CONSOLE,
        "captured": CAPTURED,
    }
    os.makedirs("/tmp/out", exist_ok=True)
    with open("/tmp/out/capture.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    log(f"[*] wrote /tmp/out/capture.json with {len(CAPTURED)} captured responses")

if __name__ == "__main__":
    asyncio.run(main())
