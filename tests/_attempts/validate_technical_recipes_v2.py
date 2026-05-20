"""기술적 트랙 4 신규 recipe sweep — disclosureAdjacent · breakoutNews · macroRegime · momentumFlowSplit.

목적: 1 호 (`momentumFlowDivergence`) 형판으로 폭 3 + 깊이 1 동시 검증. 각 recipe 5 KR
대형주 testUniverse 직렬 실행 → 6 신호 scorecard 출력. drafted → 운영자 검토용 자료.

메모리 안전: 4 recipe × 5 target = 20 회 validateRecipe 호출. capture=False (디스크 누적 안 함).
recipe 사이 gc.collect() 호출 — polars rust heap 회수는 불가하지만 python obj 라도 해제.

결과
----
2026-05-21 1 회 실행 (capture=False · 4 recipe × 5 KR target = 20 회 sweep, 합계 ~70 s).

| recipe                          | passRate | completeness | stability | meets |
|---------------------------------|----------|--------------|-----------|-------|
| disclosureAdjacentVolatility    | 1.00     | 1.00         | 0.273     | ✓ 통과 |
| macroRegimeSectorBreakout       | 1.00     | 1.00         | 0.417     | ✓ 통과 |
| breakoutNewsConfirmation        | 1.00     | 1.00         | **0.066** | ✗ stab < 0.10 |
| momentumFlowSplit               | 1.00     | 1.00         | **0.526** | ✗ stab > 0.50 |

**통과 2 종 — 신호 변별 확인:**

- disclosureAdjacentVolatility: atrRatio 분포 0.83/1.10/1.19/1.47/1.60. 207940 만 평탄
  (0.83), 나머지 4 종 모두 ATR jump. 30 일 horizon 안 공시 임박 종목 변동성 확장 가시화.
- macroRegimeSectorBreakout: ret60 분포 0.83/0.43/-0.00/-0.22/-0.25. SK 하이닉스+삼성전자
  강한 상승, 나머지 3 종 약세~정체. 매크로 정합 alignment 신호 동행 → 종목 변별력 명확.

**실패 2 종 — falsifier 가 예측한 모드:**

- breakoutNewsConfirmation (stab 0.066): breakoutRatio = 1.00/1.00/0.84/1.00/0.89. 5 종
  중 3 종이 60 일 신고가 → "all_high" 패턴. falsifier 본문이 미리 예측 — 현 강세장 KR 대형주
  변별 불가. 수정 방향: testUniverse 약세주 추가 또는 윈도우 20/120 확장.
- momentumFlowSplit (stab 0.526): spread20d = 0.12/0.17/0.19/1.35/1.09. 3 종 (0.12~0.19)
  외인/기관 거의 동일 corr, 2 종 (1.09/1.35) 정반대 corr — 분포 매우 bimodal. std 임계
  0.50 미세 초과. 수정 방향: headline 을 spread 대신 |corrForeign + corrInst|/2 (평균)
  같은 안정적 metric 으로 변경, 또는 spread 를 cap 1.0 처리.

**해석:**

인프라 (gather raw → runPython 인라인 → scorecard) 4/4 모두 정상. passRate · completeness
· novelty · falsifier 4 신호 4/4 만점. **유일하게 깨진 건 crossTargetStability** — 그것도
falsifier 가 예측한 모드 그대로. → 형판 검증은 4/4 완료. 신호 깊이 (universe 다양성·metric
선택) 가 2/4 의 다음 일이며 본 인프라와는 독립.

**기술적 트랙 통과 누계:** 4 (momentumFlowDivergence + disclosureAdjacentVolatility +
macroRegimeSectorBreakout, 다 status=drafted). 1 호 sweep 합치면 3 통과.

다음 액션:
- 4 종 모두 status=drafted. 운영자 검토 후 `recipePromote.py promote` 가 정상 경로.
- breakoutNews / momentumFlowSplit 의 stability 깨짐 두 모드는 v2 변형으로 분리 추진 가능
  (별 id, 본 4 종은 그대로 evidence 보존).
"""

from __future__ import annotations

import gc
import json
import os
import sys

os.environ["DARTLAB_SKILL_NO_CACHE"] = "1"

RECIPE_IDS = [
    "recipes.technical.disclosureAdjacentVolatility",
    "recipes.technical.breakoutNewsConfirmation",
    "recipes.technical.macroRegimeSectorBreakout",
    "recipes.technical.momentumFlowSplit",
]


def main() -> int:
    from dartlab.ai.tools.validateRecipe import validateRecipe

    summary_rows: list[dict] = []
    all_runs: dict[str, list] = {}

    for skill_id in RECIPE_IDS:
        print("=" * 72)
        print(f"validateRecipe: {skill_id}")
        print("=" * 72)
        result = validateRecipe(skill_id, capture=False)
        print(f"ok      : {result.ok}")
        print(f"summary : {result.summary}")
        if result.error:
            print(f"error   : {result.error}")

        if not result.ok or not result.data:
            summary_rows.append({"skill": skill_id, "meets": False, "error": result.error or "no_data"})
            gc.collect()
            continue

        data = result.data
        sc = data.get("scorecard") or {}
        runs = data.get("runs") or []
        all_runs[skill_id] = runs

        print(f"\n  passRate     = {sc.get('executionPassRate', 0):.2f}")
        print(f"  completeness = {sc.get('evidenceCompleteness', 0):.2f}")
        print(f"  stability    = {sc.get('crossTargetStability', 0):.4f}")
        print(f"  novelty      = {sc.get('novelty')}")
        print(f"  falsifier    = {sc.get('falsifierEvaluated')}")
        print(f"  meets        = {sc.get('meetsThresholds')}")
        if sc.get("notes"):
            print(f"  notes        = {sc.get('notes')}")

        print(f"\n  Runs ({len(runs)}):")
        for r in runs:
            mark = "OK  " if r.get("ok") else "FAIL"
            print(
                f"    {r.get('target'):<8} {mark} "
                f"head={r.get('headlineMetric')}={r.get('headlineValue')} "
                f"err={r.get('errorClass')} "
                f"{r.get('durationMs')}ms"
            )

        summary_rows.append(
            {
                "skill": skill_id,
                "passRate": sc.get("executionPassRate", 0),
                "completeness": sc.get("evidenceCompleteness", 0),
                "stability": sc.get("crossTargetStability", 0),
                "novelty": sc.get("novelty"),
                "falsifier": sc.get("falsifierEvaluated"),
                "meets": sc.get("meetsThresholds"),
                "headlines": [r.get("headlineValue") for r in runs],
            }
        )

        gc.collect()
        print()

    # 최종 요약 표
    print("=" * 72)
    print("FINAL SUMMARY (4 recipes × 5 targets)")
    print("=" * 72)
    print(f"{'skill':<60} {'meets':<6} {'pass':<6} {'stab':<8}")
    for row in summary_rows:
        short = row["skill"].split(".")[-1]
        print(f"{short:<60} {str(row.get('meets')):<6} {row.get('passRate', 0):<6.2f} {row.get('stability', 0):<8.4f}")

    print("\n[JSON dump]")
    print(json.dumps(summary_rows, ensure_ascii=False, indent=2, default=str))

    meets_count = sum(1 for r in summary_rows if r.get("meets"))
    print(f"\nmeetsThresholds: {meets_count}/{len(summary_rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
