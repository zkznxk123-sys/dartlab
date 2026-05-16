"""폰트 실 로드 + computed style 검증 — 거짓말 안 하기 위한 진짜 게이트."""

from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5400"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()

        font_responses: dict[str, int] = {}
        page.on(
            "response",
            lambda r: font_responses.setdefault(r.url, r.status)
            if ("pretendard" in r.url.lower() or "geist" in r.url.lower() or r.url.endswith((".woff", ".woff2")))
            else None,
        )

        page.goto(BASE + "/", wait_until="networkidle", timeout=20000)
        page.wait_for_timeout(1500)

        body_font = page.evaluate("() => getComputedStyle(document.body).fontFamily")
        h_font = page.evaluate(
            "() => { const el = document.querySelector('h4, [data-slot=card-title]') || document.querySelector('span'); return el ? getComputedStyle(el).fontFamily : null }"
        )
        body_font_actual = page.evaluate(
            """async () => {
                const ranges = await document.fonts.ready;
                const list = [];
                document.fonts.forEach(f => list.push(f.family + ' ' + f.weight + ' ' + f.status));
                return list;
            }"""
        )

        print("body computed font-family:")
        print(" ", body_font)
        print("\nh/span computed font-family:")
        print(" ", h_font)
        print("\nfont network responses (Pretendard / Geist):")
        if not font_responses:
            print("  (none — CDN 미로드)")
        else:
            for url, status in font_responses.items():
                short = url[-90:] if len(url) > 90 else url
                marker = "OK " if status == 200 else f"!! {status}"
                print(f"  {marker} {short}")
        print("\ndocument.fonts (loaded):")
        for f in body_font_actual[:15]:
            print(f"  {f}")

        browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
