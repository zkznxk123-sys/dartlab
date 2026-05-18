"""휴리스틱 ask() 의 출력을 baseline.json 에 캡처.

P1 5 패스 LLM path 와 비교용. 실 dartlab 데이터 로드를 피하는 안전 question 만 사용 — OOM 방지.

사용:
    uv run python -X utf8 tests/ai/runners/captureGoldenBaseline.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# 안전 셋 — dartlab 데이터 로드 안 함 (Company/scan 호출 안 함). 휴리스틱 fail path 위주.
_SAFE_QUESTIONS: list[str] = [
    "hi",
    "DartLab 의 분석 범위는?",
    "재무제표 분석 절차 알려줘",
    "회사 비교는 어떻게 하나",
    "거시 경제 지표는 무엇이 있나",
]


def _captureOne(question: str) -> dict:
    from dartlab.ai import ask

    try:
        text = ask(question, stream=False)
    except Exception as exc:  # noqa: BLE001
        text = f"[capture failed: {type(exc).__name__}: {exc}]"

    # 같은 질문을 events 모드로 다시 — refs 추출
    refs: list[str] = []
    try:
        for ev in ask(question, events=True):
            if ev.kind == "reference":
                for r in ev.data.get("refs") or []:
                    rid = r.get("id") if isinstance(r, dict) else None
                    if rid:
                        refs.append(rid)
            elif ev.kind == "done":
                for r in ev.data.get("refs") or []:
                    rid = r.get("id") if isinstance(r, dict) else None
                    if rid and rid not in refs:
                        refs.append(rid)
    except Exception:  # noqa: BLE001
        pass

    return {
        "question": question,
        "expected": {
            "textPreview": (text or "")[:300],
            "textLength": len(text or ""),
            "refs": refs,
            "refCount": len(refs),
        },
    }


def main() -> int:
    out_path = Path(__file__).resolve().parents[2] / "tests" / "ai" / "golden" / "baseline.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    scenarios = [_captureOne(q) for q in _SAFE_QUESTIONS]

    try:
        from dartlab import __version__ as version
    except Exception:  # noqa: BLE001
        version = None

    payload = {
        "_comment": "휴리스틱 ask() 캡처. P1 LLM 5 패스 회귀 비교용. 안전 question 셋만 — dartlab 데이터 로드 안 함.",
        "_capturedAt": datetime.now(timezone.utc).isoformat(),
        "_dartlabVersion": version,
        "scenarios": scenarios,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"baseline 작성: {out_path}")
    print(f"scenarios: {len(scenarios)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
