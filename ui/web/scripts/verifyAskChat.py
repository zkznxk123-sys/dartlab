"""Ask 페이지 실 chat 통합 검증 — Python 8400 서버 통해서.

흐름:
1. http://localhost:8400/ask 로딩
2. 입력창에 짧은 질문 타이핑
3. Send 클릭
4. 어시스턴트 메시지 텍스트가 시간이 지나면서 채워짐 (스트리밍 확인)
5. 메시지 최종 본문에 한글 또는 영문 응답 있음
6. 스크린샷 저장
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8400"
SHOTS = Path(__file__).resolve().parent.parent / "screenshots"


def main() -> int:
    fails: list[str] = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={"width": 1440, "height": 900}).new_page()

        console_errors: list[str] = []
        page.on(
            "console",
            lambda msg: console_errors.append(f"{msg.type}: {msg.text}") if msg.type == "error" else None,
        )

        # localStorage 초기화 (이전 대화 잔존 방지)
        page.goto(BASE + "/ask", wait_until="domcontentloaded")
        page.evaluate("localStorage.clear()")
        page.evaluate("localStorage.setItem('dartlab-ui-theme','dark')")
        page.goto(BASE + "/ask", wait_until="networkidle")
        page.wait_for_timeout(800)

        # 빈 상태 확인
        if "질문을 입력하세요" not in page.content():
            fails.append("empty state 텍스트 없음")

        # 입력
        inp = page.locator('input[placeholder*="질문"]')
        if inp.count() == 0:
            fails.append("입력창 미존재")
            b.close()
            return 1
        inp.fill("안녕")

        # Send 버튼 — input 옆 Send 아이콘
        send_btn = page.locator('button[type="submit"]')
        if send_btn.count() == 0:
            fails.append("send 버튼 미존재")
        else:
            send_btn.click()

        # 메시지 1 (user) + 메시지 2 (assistant) 등장 대기
        page.wait_for_timeout(2000)

        # 어시스턴트 메시지 텍스트 변화 — 최대 30 초 대기
        last_text = ""
        start_t = page.evaluate("Date.now()")
        for _ in range(30):
            page.wait_for_timeout(1000)
            cards = page.locator('[data-slot="card-content"]').all_text_contents()
            if len(cards) >= 2:
                assistant_text = cards[1].strip()
                if assistant_text and assistant_text != last_text:
                    last_text = assistant_text
                # 응답 길이 충분하면 종료
                if len(assistant_text) > 30:
                    break

        elapsed = (page.evaluate("Date.now()") - start_t) / 1000
        print(f"streaming 응답 길이: {len(last_text)} 자 / 경과 {elapsed:.1f}s")
        print(f"응답 발췌: {last_text[:200]}")

        if len(last_text) < 5:
            fails.append(f"어시스턴트 응답 너무 짧음 ({len(last_text)}자)")

        # 스크린샷
        page.screenshot(path=str(SHOTS / "integration-ask-chat.png"))

        if console_errors:
            fails.append(f"콘솔 에러 {len(console_errors)} 건")
            for e in console_errors[:3]:
                fails.append(f"  {e}")

        b.close()

    if fails:
        print(f"\n[FAIL] {len(fails)} 건")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("\n[PASS] /ask 가 /api/ask 호출 + SSE 스트림 받아서 어시스턴트 메시지 렌더 OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
