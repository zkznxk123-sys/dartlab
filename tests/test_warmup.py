"""stdio warmup 핸들러 단위 테스트.

P1-2: extension activate 직후 KnowledgeDB init + 모듈 import 비용을
사전 지불하여 첫 ask 의 cold-start 지연을 단축.
"""

from __future__ import annotations

import io
import json

import pytest

pytestmark = pytest.mark.unit


def test_handle_warmup_emits_warmup_done(monkeypatch):
    """_handleWarmup 호출 시 warmup_done 이벤트가 stdout 에 emit 된다."""
    from dartlab.cli import stdio

    # stdout 캡처
    buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", buf)

    stdio._handleWarmup({})

    output = buf.getvalue().strip()
    assert output, "_handleWarmup 이 출력하지 않음"

    msg = json.loads(output)
    assert msg["event"] == "warmup_done"
    assert "data" in msg
    assert "warmed" in msg["data"]
    assert "skipped" in msg["data"]


def test_handle_warmup_imports_core_modules(monkeypatch):
    """warmup 이 핵심 모듈들을 import 한다 (warmed list 에 등장)."""
    from dartlab.cli import stdio

    buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", buf)

    stdio._handleWarmup({})

    msg = json.loads(buf.getvalue().strip())
    warmed = set(msg["data"]["warmed"])
    skipped = set(msg["data"]["skipped"])

    # 핵심 모듈은 import 가능해야 함 — 현재 _handleWarmup 의 prewarm 항목.
    # 회귀: core/providers prewarm 은 cold-start 비용 너무 커서 제외됨 (kernel 기준).
    assert "kernel" in warmed, f"kernel prewarm 실패. skipped={skipped}"
    assert "viz_extract" in warmed, f"viz_extract prewarm 실패. skipped={skipped}"


def test_handle_warmup_is_idempotent(monkeypatch):
    """warmup 을 두 번 호출해도 에러 없이 동작 (knowledge_db 싱글톤)."""
    from dartlab.cli import stdio

    buf1 = io.StringIO()
    monkeypatch.setattr("sys.stdout", buf1)
    stdio._handleWarmup({})

    buf2 = io.StringIO()
    monkeypatch.setattr("sys.stdout", buf2)
    stdio._handleWarmup({})

    msg1 = json.loads(buf1.getvalue().strip())
    msg2 = json.loads(buf2.getvalue().strip())
    assert msg1["event"] == "warmup_done"
    assert msg2["event"] == "warmup_done"


def test_run_dispatches_warmup_message(monkeypatch):
    """run() 메인 루프가 type=warmup 메시지를 _handleWarmup 으로 라우팅한다."""
    from dartlab.cli import stdio

    called = {"warmup": 0}

    def fake_handler(msg):
        called["warmup"] += 1

    monkeypatch.setattr(stdio, "_handleWarmup", fake_handler)

    # stdin 시뮬레이션
    fake_stdin = io.StringIO('{"type":"warmup"}\n{"type":"exit"}\n')
    monkeypatch.setattr("sys.stdin", fake_stdin)

    # stdout 캡처 (ready 이벤트 무시)
    buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", buf)

    stdio.run()

    assert called["warmup"] == 1
