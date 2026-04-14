"""AI audit — 표준 질문 세트로 AI 응답 품질 점검.

사용법::

    uv run python -X utf8 scripts/audit/aiAudit.py              # 9개 전체
    uv run python -X utf8 scripts/audit/aiAudit.py --quick      # 3개만
    uv run python -X utf8 scripts/audit/aiAudit.py --stock 005930
    uv run python -X utf8 scripts/audit/aiAudit.py --provider gemini

규격: ops/ai.md "AI Audit 체계"
결과: data/audit/ai/{YYYY-MM-DD}/results.json + report.md
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logging.getLogger().setLevel(logging.ERROR)

# 표준 질문 세트 (ops/ai.md 규격)
_STANDARD_SET = [
    ("005930", "삼성전자", "수익성"),
    ("005930", "삼성전자", "현금흐름"),
    ("005930", "삼성전자", "안정성"),
    ("047040", "대우건설", "수익성"),
    ("047040", "대우건설", "현금흐름"),
    ("047040", "대우건설", "안정성"),
    ("003230", "삼양식품", "수익성"),
    ("003230", "삼양식품", "현금흐름"),
    ("003230", "삼양식품", "안정성"),
]


def _count_code_rounds(response: str) -> int:
    """응답에서 python 코드블록 수 카운트."""
    return len(re.findall(r"```python", response))


def _has_error_indicators(response: str) -> bool:
    """에러/면피 패턴 검출."""
    patterns = [
        "해석 불가",
        "출력 없음",
        "수치가 없습니다",
        "NameError",
        "AttributeError",
        "ValueError",
        "TypeError",
    ]
    return any(p in response for p in patterns)


def _has_playbook_mention(response: str) -> bool:
    """SuperMaster/playbook 활용 흔적."""
    return any(kw in response for kw in ["playbook", "수퍼마스터", "과거 사례", "과거 성공"])


def _has_table_structure(response: str) -> bool:
    """마크다운 테이블 존재."""
    return bool(re.search(r"\|\s*기간\s*\|", response)) or bool(re.search(r"\|\s*---\s*\|", response))


def _count_dash_cells(response: str) -> int:
    """테이블에서 '-' 셀 수 (dict 키 추측 실패 징후)."""
    return len(re.findall(r"\|\s*-\s*\|", response))


def _grade(response: str) -> tuple[str, list[str]]:
    """등급 판정 + 이슈 목록.

    P/T/C/V 규격은 ops/ai.md 참조.
    """
    issues: list[str] = []
    length = len(response)
    rounds = _count_code_rounds(response)
    has_error = _has_error_indicators(response)
    has_table = _has_table_structure(response)
    dash_count = _count_dash_cells(response)

    # V (Violation)
    if rounds == 0 and length < 200:
        issues.append("V: 코드도 없고 응답도 너무 짧음")
        return "V", issues

    # C (Critical)
    if has_error:
        issues.append("C: 에러/면피 문구 감지")
        return "C", issues
    if dash_count >= 5:
        issues.append(f"C: 테이블에 '-' 셀 {dash_count}개 (dict 키 추측 실패 징후)")
        return "C", issues
    if not has_table and length < 500:
        issues.append("C: 테이블 없고 짧은 응답")
        return "C", issues

    # T (Tolerable)
    if rounds >= 3:
        issues.append(f"T: 코드 블록 {rounds}회 (비효율)")
    if length > 6000:
        issues.append(f"T: 응답 길이 {length}자 (과도)")
    if dash_count >= 3:
        issues.append(f"T: '-' 셀 {dash_count}개")

    if issues:
        return "T", issues

    # P (Pass)
    return "P", []


def runOne(stockCode: str, corpName: str, axis: str, *, provider: str = "oauth-codex") -> dict[str, Any]:
    """단일 질문 실행 + 등급 판정."""
    import dartlab

    dartlab.verbose = False
    question = f"{corpName} {axis} 분석해줘"

    start = time.monotonic()
    response = ""
    error: str | None = None
    try:
        for chunk in dartlab.ask(question, provider=provider, stream=True):
            response += chunk
    except Exception as e:
        error = f"{type(e).__name__}: {str(e)[:300]}"

    duration = round(time.monotonic() - start, 2)

    if error:
        return {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "provider": provider,
            "question": question,
            "stockCode": stockCode,
            "axis": axis,
            "grade": "V",
            "error": error,
            "duration_sec": duration,
            "response": "",
        }

    grade, issues = _grade(response)

    # P등급이면 성공 패턴을 playbook recipe로 저장 → HF 공유 대상
    if grade == "P":
        _save_recipe(question, axis, response)

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "provider": provider,
        "question": question,
        "stockCode": stockCode,
        "axis": axis,
        "grade": grade,
        "metrics": {
            "responseLength": len(response),
            "codeRounds": _count_code_rounds(response),
            "hasError": _has_error_indicators(response),
            "mentionsPlaybook": _has_playbook_mention(response),
            "hasTableStructure": _has_table_structure(response),
            "dashCells": _count_dash_cells(response),
        },
        "issues": issues,
        "duration_sec": duration,
        "response": response,
    }


def _save_recipe(question: str, axis: str, response: str) -> None:
    """P등급 응답에서 코드 패턴을 추출해 playbook recipe로 저장."""
    try:
        from dartlab.ai.context.intent import classifyIntent
        from dartlab.ai.persistence.knowledge_db import KnowledgeDB

        # intent 분류
        intent_result = classifyIntent(question, hasCompany=True)
        intent = intent_result.intent.value

        # 응답에서 코드 블록 추출
        code_blocks = re.findall(r"```python\n(.*?)```", response, re.DOTALL)
        if not code_blocks:
            return

        # 마지막 성공 코드 (보통 최종 실행 코드)
        code = code_blocks[-1].strip()
        if len(code) < 20:
            return

        # recipe bullet 형식: "질문유형 → 코드패턴"
        bullet = f"{question[:80]} → {code[:500]}"

        db = KnowledgeDB.get()
        db.upsert_bullet(
            intent=intent,
            sector="",
            bullet=bullet,
            outcome="success",
            source="recipe",
        )
    except (ImportError, OSError, ValueError):
        pass


def writeReport(outDir: Path, results: list[dict]) -> None:
    outDir.mkdir(parents=True, exist_ok=True)
    # JSON
    (outDir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # 요약 md
    grade_counts = {g: sum(1 for r in results if r["grade"] == g) for g in "PTCV"}
    lines = [
        f"# AI Audit Report\n",
        f"**실행 시각**: {datetime.now().isoformat(timespec='seconds')}\n",
        f"**총 질문**: {len(results)}개\n",
        "",
        "## 등급 집계",
        "",
        f"- **P (Pass)**: {grade_counts['P']}",
        f"- **T (Tolerable)**: {grade_counts['T']}",
        f"- **C (Critical)**: {grade_counts['C']}",
        f"- **V (Violation)**: {grade_counts['V']}",
        "",
        "## 개별 결과",
        "",
        "| 종목 | 축 | 등급 | 길이 | 코드 | 이슈 |",
        "|---|---|:---:|---:|:---:|---|",
    ]
    for r in results:
        m = r.get("metrics", {})
        issues = "; ".join(r.get("issues", [])) or "-"
        lines.append(
            f"| {r['stockCode']} | {r['axis']} | **{r['grade']}** | "
            f"{m.get('responseLength', '-')} | {m.get('codeRounds', '-')} | {issues} |"
        )

    lines.append("\n## 비-P 상세\n")
    for r in results:
        if r["grade"] != "P":
            lines.append(f"### {r['stockCode']} {r['axis']} — {r['grade']}\n")
            for issue in r.get("issues", []):
                lines.append(f"- {issue}")
            if r.get("response"):
                lines.append(f"\n응답 첫 300자:\n```\n{r['response'][:300]}\n```\n")
            lines.append("")

    (outDir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="dartlab AI audit")
    parser.add_argument("--stock", help="단일 종목만 (3축 모두)")
    parser.add_argument("--axis", help="단일 축만")
    parser.add_argument("--provider", default="oauth-codex", help="LLM provider")
    parser.add_argument("--quick", action="store_true", help="삼성전자 3축만")
    args = parser.parse_args()

    # 세트 결정
    if args.quick:
        questions = [q for q in _STANDARD_SET if q[0] == "005930"]
    elif args.stock:
        questions = [q for q in _STANDARD_SET if q[0] == args.stock]
        if args.axis:
            questions = [q for q in questions if q[2] == args.axis]
        if not questions:
            # 표준 세트에 없으면 임의 생성
            questions = [(args.stock, args.stock, args.axis or "수익성")]
    else:
        questions = _STANDARD_SET

    print(f"AI audit 시작: {len(questions)}개 질문, provider={args.provider}\n")

    results: list[dict] = []
    for code, name, axis in questions:
        print(f"--- {name}({code}) {axis} ---")
        r = runOne(code, name, axis, provider=args.provider)
        results.append(r)
        m = r.get("metrics", {})
        print(
            f"  {r['grade']} — length={m.get('responseLength', 0)}, "
            f"rounds={m.get('codeRounds', 0)}, {r['duration_sec']}s"
        )
        if r.get("issues"):
            for issue in r["issues"]:
                print(f"  ! {issue}")

    # 저장
    date = datetime.now().strftime("%Y-%m-%d")
    outDir = Path("data/audit/ai") / date
    writeReport(outDir, results)
    print(f"\n리포트: {outDir / 'report.md'}")

    # exit code: C/V 있으면 1
    has_critical = any(r["grade"] in ("C", "V") for r in results)
    return 1 if has_critical else 0


if __name__ == "__main__":
    sys.exit(main())
