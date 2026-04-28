"""서버 경유 /api/ask AI audit runner.

PowerShell here-string 인코딩에 기대지 않도록 질문 세트와 HTTP 호출을 UTF-8
Python 파일에 고정한다. 결과는 data/audit/ai/YYYY-MM-DD/{run-id}/ 에 저장한다.

사용법:
    uv run python -X utf8 scripts/audit/serverAskAudit.py --run oauth-contract-rerun1
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

QUESTIONS: list[tuple[str, str | None, str, bool]] = [
    ("q01_samsung_profit", "005930", "삼성전자 수익성 분석해줘", False),
    ("q02_daewoo_stability", "047040", "대우건설 안정성 분석해줘", False),
    ("q03_samyang_cashflow", "003230", "삼양식품 현금흐름 분석해줘", False),
    ("q04_intel", "INTC", "인텔 분석해줘", False),
    ("q05_macro", None, "최근 한국 금리와 환율 상황 어때?", False),
    ("q06_semiconductor_compare", None, "삼성전자와 SK하이닉스 반도체 업종 경쟁력을 비교해줘", False),
    ("q07_samsung_filings", "005930", "삼성전자 최근 공시에서 중요한 내용 찾아줘", False),
    ("q08_hynix_story", "000660", "SK하이닉스 기업이야기 만들어줘", False),
    ("q09_meta", None, "dartlab 뭐 할 수 있어?", False),
    ("q10_help", None, "show 함수 어떻게 써?", False),
    ("q11_krx_movers", None, "최근 주가가 많이 오른 종목을 찾아줘", False),
    ("q12_krx_movers_stream", None, "최근 주가가 많이 오른 종목을 찾아줘", True),
]


def _runStream(client: httpx.Client, url: str, payload: dict[str, Any]) -> tuple[int, str, list[dict[str, Any]]]:
    chunks: list[str] = []
    events: list[dict[str, Any]] = []
    with client.stream("POST", url, json=payload, timeout=240.0) as response:
        status = response.status_code
        event = "message"
        for line in response.iter_lines():
            if not line:
                continue
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
                continue
            if not line.startswith("data:"):
                continue
            raw = line.split(":", 1)[1].strip()
            try:
                data: Any = json.loads(raw)
            except json.JSONDecodeError:
                data = raw
            events.append({"event": event, "data": data})
            if event == "chunk" and isinstance(data, dict):
                chunks.append(str(data.get("text", "")))
    return status, "".join(chunks), events


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8400/api/ask")
    parser.add_argument("--provider", default="oauth-codex")
    parser.add_argument("--run", default=f"server-ask-{datetime.now().strftime('%H%M%S')}")
    parser.add_argument("--day", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--timeout", type=float, default=240.0)
    parser.add_argument("--id", action="append", dest="ids", help="특정 질문 id만 실행")
    args = parser.parse_args()

    out = Path("data") / "audit" / "ai" / args.day / args.run
    out.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, Any]] = []
    questions = [q for q in QUESTIONS if not args.ids or q[0] in set(args.ids)]

    with httpx.Client(timeout=args.timeout) as client:
        for qid, company, question, stream in questions:
            started = time.time()
            payload: dict[str, Any] = {"question": question, "provider": args.provider, "stream": stream}
            if company:
                payload["company"] = company
            status: int | None = None
            answer = ""
            events: list[dict[str, Any]] = []
            error: str | None = None
            try:
                if stream:
                    status, answer, events = _runStream(client, args.url, payload)
                else:
                    response = client.post(args.url, json=payload, timeout=args.timeout)
                    status = response.status_code
                    body = response.json()
                    answer = str(body.get("answer") or body)
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}"

            elapsed = round(time.time() - started, 1)
            meta = {
                "id": qid,
                "question": question,
                "company": company,
                "stream": stream,
                "status": status,
                "ok": status == 200 and error is None,
                "elapsedSec": elapsed,
                "answerLen": len(answer),
                "error": error,
                "events": events[-30:] if stream else [],
            }
            (out / f"{qid}.txt").write_text(answer, encoding="utf-8")
            (out / f"{qid}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            row = {k: meta[k] for k in ("id", "ok", "status", "elapsedSec", "answerLen", "error")}
            summary.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)

    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OUT {out}")
    return 0 if all(row["ok"] for row in summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
