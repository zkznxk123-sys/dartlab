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


def _artifactsFromEvents(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for event in events:
        data = event.get("data")
        if not isinstance(data, dict):
            continue
        if event.get("event") != "tool_result":
            continue
        for artifact in data.get("artifacts") or []:
            if isinstance(artifact, dict):
                artifacts.append(artifact)
    return _dedupeArtifacts(artifacts)


def _countEvents(events: list[dict[str, Any]], event_name: str) -> int:
    count = 0
    for event in events:
        if event.get("event") != event_name:
            continue
        data = event.get("data")
        if event_name == "chart" and isinstance(data, dict):
            count += len([v for v in data.get("visuals") or data.get("charts") or [] if isinstance(v, dict)])
        else:
            count += 1
    return count


def _doneMeta(events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(events):
        if event.get("event") != "done":
            continue
        data = event.get("data")
        if isinstance(data, dict) and isinstance(data.get("responseMeta"), dict):
            return data["responseMeta"]
    return {}


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.95)))
    return round(float(ordered[idx]), 1)


def _dedupeArtifacts(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for artifact in artifacts:
        key = str(artifact.get("url") or artifact.get("id") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(artifact)
    return out


def _latestAuditEntry(day: str, question: str) -> dict[str, Any] | None:
    path = Path("data") / "audit" / "ai-ask" / f"{day}.jsonl"
    if not path.exists():
        return None
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("question") == question:
            return row
    return None


def _requiresCsvArtifact(qid: str, question: str) -> bool:
    q = question.lower()
    if qid in {"q11_krx_movers", "q12_krx_movers_stream"}:
        return True
    return any(word in q for word in ("찾아줘", "랭킹", "순위", "많이 오른", "top", "rank"))


def _compactEvents(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for event in events:
        name = str(event.get("event") or "")
        data = event.get("data")
        if name == "system_prompt":
            continue
        if not isinstance(data, dict):
            compact.append(event)
            continue
        if name == "tool_result":
            artifacts = [a for a in data.get("artifacts") or [] if isinstance(a, dict)]
            compact.append(
                {
                    "event": name,
                    "data": {
                        "id": data.get("id"),
                        "name": data.get("name"),
                        "label": data.get("label"),
                        "summary": data.get("summary"),
                        "status": data.get("status"),
                        "round": data.get("round"),
                        "durationMs": data.get("durationMs"),
                        "resultSizeBytes": data.get("resultSizeBytes"),
                        "resultChars": len(str(data.get("result") or "")),
                        "artifacts": artifacts,
                    },
                }
            )
            continue
        compact.append({"event": name, "data": data})
    return compact


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
            artifacts: list[dict[str, Any]] = []
            body: dict[str, Any] = {}
            error: str | None = None
            try:
                if stream:
                    status, answer, events = _runStream(client, args.url, payload)
                    artifacts = _artifactsFromEvents(events)
                else:
                    response = client.post(args.url, json=payload, timeout=args.timeout)
                    status = response.status_code
                    parsed = response.json()
                    body = parsed if isinstance(parsed, dict) else {}
                    answer = str(body.get("answer") or parsed)
                    artifacts = _dedupeArtifacts([a for a in body.get("artifacts", []) if isinstance(a, dict)])
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}"

            elapsed = round(time.time() - started, 1)
            audit = _latestAuditEntry(args.day, question) or {}
            failed_tools = [t for t in audit.get("tool_calls", []) if t.get("error") or t.get("ok") is False]
            csv_artifacts = [a for a in artifacts if a.get("format") == "csv"]
            primary_csv_artifacts = [a for a in csv_artifacts if a.get("primary")]
            response_evidence = body.get("evidence", []) if not stream and isinstance(body, dict) else []
            response_claims = body.get("claims", []) if not stream and isinstance(body, dict) else []
            response_visuals = body.get("visuals", []) if not stream and isinstance(body, dict) else []
            response_meta = (body.get("responseMeta") if not stream and isinstance(body, dict) else None) or _doneMeta(
                events
            )
            response_graph = response_meta.get("graph") if isinstance(response_meta, dict) else {}
            if not isinstance(response_graph, dict):
                response_graph = {}
            evidence_count = max(
                int(audit.get("evidence_count") or 0), len(response_evidence), _countEvents(events, "evidence")
            )
            claim_count = max(int(audit.get("claim_count") or 0), len(response_claims), _countEvents(events, "claim"))
            visual_count = max(
                int(audit.get("visual_count") or 0), len(response_visuals), _countEvents(events, "chart")
            )
            requires_artifact = _requiresCsvArtifact(qid, question)
            artifact_violation = bool(requires_artifact and not csv_artifacts)
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
                "requestId": audit.get("request_id"),
                "qualityIssues": audit.get("quality_issues") or [],
                "toolFailed": len(failed_tools),
                "artifacts": artifacts,
                "csvArtifactCount": len(csv_artifacts),
                "primaryCsvArtifactCount": len(primary_csv_artifacts),
                "evidenceCount": evidence_count,
                "claimCount": claim_count,
                "visualCount": visual_count,
                "missingVisualExplanation": "missing_visual_explanation" in (audit.get("quality_issues") or []),
                "llmRoundMs": max(int(audit.get("llm_round_ms") or 0), int(response_meta.get("llmRoundMs") or 0)),
                "toolTotalMs": max(int(audit.get("tool_total_ms") or 0), int(response_meta.get("toolTotalMs") or 0)),
                "rewriteCount": max(int(audit.get("rewrite_count") or 0), int(response_meta.get("rewriteCount") or 0)),
                "maxRoundsReached": bool(audit.get("max_rounds_reached") or response_meta.get("maxRoundsReached")),
                "slowReason": audit.get("slow_reason") or response_meta.get("slowReason") or [],
                "routeHit": bool(audit.get("route_hit") or response_graph.get("routeHit")),
                "contractHit": bool(audit.get("contract_hit") or response_graph.get("contractHit")),
                "processMapUsed": bool(audit.get("process_map_used") or response_graph.get("processMapUsed")),
                "processMapSatisfied": bool(
                    audit.get("process_map_satisfied")
                    or response_graph.get("processMapSatisfied")
                    or response_meta.get("processMapSatisfied")
                ),
                "claimSupportRate": max(
                    float(audit.get("claim_support_rate") or 0),
                    float(response_meta.get("claimSupportRate") or 0),
                ),
                "toolArgValidRate": max(
                    float(audit.get("tool_arg_valid_rate") or 0),
                    float(response_meta.get("toolArgValidRate") or 0),
                ),
                "freshnessSatisfied": bool(
                    audit.get("freshness_satisfied", True) and response_meta.get("freshnessSatisfied", True)
                ),
                "processMapIds": audit.get("process_map_ids") or response_graph.get("processMapIds") or [],
                "selectedTools": audit.get("selected_tools") or [],
                "skippedCandidateTools": audit.get("skipped_candidate_tools") or [],
                "requiredEvidenceSatisfied": bool(
                    audit.get("required_evidence_satisfied") or response_graph.get("requiredEvidenceSatisfied")
                ),
                "artifactSatisfied": bool(audit.get("artifact_satisfied") or response_graph.get("artifactSatisfied")),
                "visualSatisfied": bool(audit.get("visual_satisfied") or response_graph.get("visualSatisfied")),
                "requiresArtifact": requires_artifact,
                "artifactViolation": artifact_violation,
                "events": _compactEvents(events[-30:]) if stream else [],
            }
            (out / f"{qid}.txt").write_text(answer, encoding="utf-8")
            (out / f"{qid}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            row = {
                k: meta[k]
                for k in (
                    "id",
                    "ok",
                    "status",
                    "elapsedSec",
                    "answerLen",
                    "error",
                    "qualityIssues",
                    "toolFailed",
                    "csvArtifactCount",
                    "primaryCsvArtifactCount",
                    "evidenceCount",
                    "claimCount",
                    "visualCount",
                    "missingVisualExplanation",
                    "llmRoundMs",
                    "toolTotalMs",
                    "rewriteCount",
                    "maxRoundsReached",
                    "slowReason",
                    "routeHit",
                    "contractHit",
                    "processMapUsed",
                    "processMapSatisfied",
                    "claimSupportRate",
                    "toolArgValidRate",
                    "freshnessSatisfied",
                    "requiredEvidenceSatisfied",
                    "artifactSatisfied",
                    "visualSatisfied",
                    "artifactViolation",
                )
            }
            summary.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)

    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    latency_p95 = _p95([float(row.get("elapsedSec") or 0) for row in summary])
    (out / "summary_meta.json").write_text(
        json.dumps({"latencyP95": latency_p95, "count": len(summary)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"OUT {out}")
    return 0 if all(row["ok"] and not row["artifactViolation"] for row in summary) else 1


if __name__ == "__main__":
    raise SystemExit(main())
