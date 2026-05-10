"""골든 trace runner — 15 케이스를 실 LLM (OAuth Codex) 1 회 호출 → outcome_log 기록 + baseline freeze.

OAuth Codex 토큰 (~/.dartlab/oauth_token.json 또는 DARTLAB_OAUTH_TOKEN 환경변수) 필수.
비용 발생 — 수동 트리거 (CI 자동 실행 X).

산출:
- ~/.dartlab/decisions/{market}/{stockCode}.md — outcome_log entry (per stockCode)
- tests/ai/golden/baseline_v{N}.json — taxonomy 분류 결과 freeze (P1 후 비교 기준선)

사용:
    uv run python -X utf8 scripts/dev/runGoldenTrace.py [--version v1]
    uv run python -X utf8 scripts/dev/runGoldenTrace.py --case c1_samsung_health  # 단일 케이스만
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = ROOT / "tests" / "ai" / "golden"
CASES_PATH = GOLDEN_DIR / "cases.yaml"


def _hasOAuthToken() -> bool:
    token_env = os.environ.get("DARTLAB_OAUTH_TOKEN")
    token_file = Path.home() / ".dartlab" / "oauth_token.json"
    return bool(token_env) or token_file.exists()


def _loadCases() -> dict[str, Any]:
    import yaml

    text = CASES_PATH.read_text(encoding="utf-8")
    return yaml.safe_load(text) or {}


def _runCase(case: dict[str, Any]) -> dict[str, Any]:
    """단일 케이스 실행 — provider 호출 + trace 결과 dict 반환."""
    from dartlab.ai import ask
    from dartlab.ai.providers import createProvider, getConfig

    config = getConfig(provider="oauth-codex")
    provider = createProvider(config)

    case_id = case["id"]
    question = case["question"]
    print(f"\n[{case_id}] {question}")
    print("─" * 60)

    text = ask(question, stream=False, provider=provider)
    answer = text or ""
    print(answer[:300] + ("..." if len(answer) > 300 else ""))

    return {
        "id": case_id,
        "stockCode": case.get("stockCode"),
        "market": case.get("market"),
        "industryHint": case.get("industryHint"),
        "questionType": case.get("questionType"),
        "question": question,
        "answerText": answer,
        "answerLength": len(answer),
    }


def _runAll(cases: list[dict[str, Any]], filter_id: str | None = None) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for case in cases:
        if filter_id and case.get("id") != filter_id:
            continue
        try:
            result = _runCase(case)
        except Exception as exc:  # noqa: BLE001
            print(f"[{case.get('id')}] FAILED — {type(exc).__name__}: {exc}")
            result = {
                "id": case.get("id"),
                "error": f"{type(exc).__name__}: {exc}",
            }
        results.append(result)
    return results


def _classifyTaxonomy(case: dict[str, Any], result: dict[str, Any]) -> dict[str, bool]:
    """5 범주 taxonomy 분류 — 단순 키워드 매칭 (LLM 분류기 없이 결정적).

    반환: {category: bool} — True 면 해당 실패 패턴 발견.
    """
    from tests.ai.test_failure_taxonomy import classify  # type: ignore[import-not-found]

    return classify(case, result)


def _writeBaseline(version: str, results: list[dict[str, Any]], cases: list[dict[str, Any]]) -> Path:
    captured = datetime.now(timezone.utc).isoformat()
    try:
        dlb_version = pkg_version("dartlab")
    except PackageNotFoundError:
        dlb_version = "0.0.0"

    cases_by_id = {c["id"]: c for c in cases}
    enriched = []
    for r in results:
        case = cases_by_id.get(r["id"], {})
        try:
            taxonomy = _classifyTaxonomy(case, r)
        except Exception as exc:  # noqa: BLE001
            taxonomy = {"_classifier_error": f"{type(exc).__name__}: {exc}"}
        enriched.append({**r, "taxonomy": taxonomy})

    payload = {
        "_capturedAt": captured,
        "_dartlabVersion": dlb_version,
        "_version": version,
        "results": enriched,
    }
    out = GOLDEN_DIR / f"baseline_{version}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n→ Baseline freeze: {out.relative_to(ROOT)}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="골든 trace runner")
    parser.add_argument("--version", default="v1", help="baseline 버전 태그 (기본 v1)")
    parser.add_argument("--case", default=None, help="단일 케이스 id 만 실행 (디버그용)")
    args = parser.parse_args()

    if not _hasOAuthToken():
        print(
            "OAuth Codex 토큰 없음. ~/.dartlab/oauth_token.json 또는 DARTLAB_OAUTH_TOKEN 환경변수 필요.\n"
            "발급: dartlab.setup('chatgpt')",
            file=sys.stderr,
        )
        return 2

    if not CASES_PATH.exists():
        print(f"케이스 명세 없음: {CASES_PATH}", file=sys.stderr)
        return 2

    spec = _loadCases()
    cases = spec.get("cases") or []
    if not cases:
        print("케이스 0 개", file=sys.stderr)
        return 2

    print(f"골든 trace 시작 — {len(cases)} 케이스 (version={args.version})")
    results = _runAll(cases, filter_id=args.case)

    if args.case:
        # 단일 케이스 모드는 baseline freeze 생략.
        return 0

    _writeBaseline(args.version, results, cases)
    return 0


if __name__ == "__main__":
    sys.exit(main())
