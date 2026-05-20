"""recipe momentumFlowDivergence — validateRecipe 호출 + scorecard 출력.

목적: recipes.technical.momentumFlowDivergence 가 5 KR 종목 testUniverse 에서
6 신호 scorecard 어디까지 통과하는지 1 회 측정. drafted → unverified 승격 판단 자료.

결과
----
2026-05-21 1 회 실행 (capture=False · 5 target × 평균 2.36 s).

- executionPassRate    = 1.00 (5/5, 임계 ≥ 0.80)
- evidenceCompleteness = 1.00 (skillRef/tableRef/dateRef/executionRef 모두, 임계 = 1.00)
- crossTargetStability = 0.226 (correlation 표본 std, 임계 ∈ [0.10, 0.50])
- novelty              = True  (expectedNovelty 3 종)
- falsifierEvaluated   = True  (frontmatter 존재)
- meetsThresholds      = True  (5/5 신호 통과)

종목별 correlation (Pearson, 20 거래일 일일수익률 vs 외인+기관 순매수):

| 종목     | corr   | 비고                                  |
|----------|--------|---------------------------------------|
| 005930   | 0.9443 | 삼성전자 — 매우 강한 동조             |
| 000660   | 0.9325 | SK 하이닉스 — 매우 강한 동조          |
| 035420   | 0.9110 | NAVER — 강한 동조                     |
| 051910   | 0.7711 | LG 화학 — 강한 동조                   |
| 207940   | 0.3471 | 삼성바이오로직스 — 약한 동조 (변별점) |

분포 해석:
- 5 종목 중 4 개 corr ≥ 0.77 — 한국 대형주 수급↔가격 동조가 일반적임을 시사.
- 207940 만 corr 0.35 → 외인/기관 순매수가 단기 가격 움직임을 끌어가지 못한 case.
  본 recipe 가 4 동조 vs 1 약동조 식의 변별을 산출 → 단순 모멘텀만으로 못 보는 신호.

다음 액션:
- 운영자 검토 (look-ahead·survivorship 점검) 후 `scripts/dev/recipe_promote.py promote
  recipes.technical.momentumFlowDivergence` 로 drafted → unverified 승격 가능.
- 모든 종목 같은 부호 (전부 +1) 라는 한 가지 우려는 falsifier 본문에 명시 — 다른 윈도우
  (10 일 / 60 일 / 위기 구간) 에서 재실행해 다이버전스 (-1) case 가 실제 잡히는지 확인.
"""

from __future__ import annotations

import json
import os
import sys

# spec 캐시 우회 — 새 .md 파일 즉시 반영
os.environ["DARTLAB_SKILL_NO_CACHE"] = "1"


def main() -> int:
    from dartlab.ai.tools.validateRecipe import validateRecipe

    result = validateRecipe(
        "recipes.technical.momentumFlowDivergence",
        capture=False,  # 디스크 파일 누적 안 함 — 1 회성 측정
    )

    print("=" * 70)
    print(f"ok      : {result.ok}")
    print(f"summary : {result.summary}")
    print(f"error   : {result.error}")
    print("=" * 70)

    if not result.ok or not result.data:
        return 1

    data = result.data
    sc = data.get("scorecard") or {}
    runs = data.get("runs") or []

    print("\n[Scorecard]")
    for k, v in sc.items():
        if isinstance(v, float):
            print(f"  {k:<25} = {v:.4f}")
        elif isinstance(v, list):
            print(f"  {k:<25} = {v}")
        else:
            print(f"  {k:<25} = {v}")

    print(f"\n[Runs] ({len(runs)} targets)")
    for r in runs:
        ok_mark = "OK" if r.get("ok") else "FAIL"
        print(
            f"  {r.get('target'):<8} {ok_mark:<4} "
            f"headline={r.get('headlineMetric')}={r.get('headlineValue')} "
            f"evidence={r.get('evidenceKinds')} "
            f"missing={r.get('missing')} "
            f"err={r.get('errorClass')} "
            f"{r.get('durationMs')}ms"
        )

    if data.get("missingEvidence"):
        print(f"\n[Missing Evidence (overall)] {data['missingEvidence']}")

    print("\n[JSON dump]")
    print(json.dumps({"scorecard": sc, "runs": runs}, ensure_ascii=False, indent=2, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
