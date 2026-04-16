"""실험 ID: 053
실험명: Dalio 부채사이클 단계 분류 규칙 검증

목적:
- Ray Dalio "Principles for Navigating Big Debt Crises" Part 1 의 템플릿을 규칙으로 코드화.
- 역사 스냅샷 (1970s / 1982 / 2000 / 2008 / 2013 / 2020 / 2025) 에 규칙 적용 → 기대 단계와 대조.
- L0 SSOT `core/finance/crisisDetector.py` 에 박기 전 임계치 타당성 확인.

가설:
1. 임계치 기반 규칙이 8개 역사 케이스 중 최소 6개 (75%) 에서 기대 단계와 일치.
2. 모든 케이스에서 enum 반환 (빈 문자열/예외 없음).

방법:
1. 단순 규칙 함수 구현:
   phase = dalioDebtCyclePhase(totalDebtToGdp, debtServiceYoY, creditGap, realRate, gdpGrowth)
2. 8개 역사 스냅샷 투입 → 비교.
3. 정확도 계산 + 판정.

분류 체계 (Dalio Part 1):
- earlyBoom: 부채 증가 정상, 성장 건강
- lateBoom: 신용 확대 과열 시작, 부채서비스 악화 초기
- topBubble: 신용 갭 과열 + realRate 마이너스/저금리 + 성장 양호
- deflationaryDepression: 성장 -, 신용 수축, realRate 상승
- beautifulDeleveraging: 부채/GDP 하락 + 성장 +, 디레버리징 성공
- reflationary: realRate 깊은 마이너스, 성장 회복 중, 신용 확대 재개

실험일: 2026-04-15
"""

from __future__ import annotations

import sys


def dalioDebtCyclePhase(
    totalDebtToGdp: float,
    debtServiceYoY: float,
    creditGap: float,
    realRate: float,
    gdpGrowth: float,
) -> str:
    """Dalio 부채사이클 단계 판정.

    Args:
        totalDebtToGdp: 총부채/GDP (%). 일반 선진국 100~300.
        debtServiceYoY: 부채서비스(이자/소득) 전년대비 변화 (%p).
        creditGap: BIS Credit-to-GDP gap (%p). >10 과열.
        realRate: 실질금리 (%).
        gdpGrowth: 실질 GDP 성장률 (%, 전년대비).

    Returns:
        단계 문자열. earlyBoom | lateBoom | topBubble |
        deflationaryDepression | beautifulDeleveraging | reflationary.
    """
    # 1. 디플레이션 공황: 성장 음수 + 신용 갭 음전환
    if gdpGrowth < -1.0 and creditGap < 0:
        return "deflationaryDepression"

    # 2. Reflationary: 실질금리 깊은 마이너스 + 성장 회복 중 (신용 갭 상승)
    if realRate < -2.0 and gdpGrowth >= -2.0:
        return "reflationary"

    # 3. Top Bubble: 신용 갭 과열 + 성장 양호 + 실질금리 낮음
    if creditGap >= 8.0 and gdpGrowth > 0 and realRate < 2.0:
        return "topBubble"

    # 4. Late Boom: 신용 갭 상승 중 + 부채서비스 악화
    if creditGap >= 2.0 and debtServiceYoY > 0 and gdpGrowth > 0:
        return "lateBoom"

    # 5. Beautiful Deleveraging: 부채서비스 개선 + 성장 양호
    if debtServiceYoY < 0 and gdpGrowth > 0:
        return "beautifulDeleveraging"

    # 6. Early Boom: 기본값 — 신용 완만, 성장 건강
    return "earlyBoom"


CASES = [
    # (label, totalDebt/GDP, 부채서비스YoY(%p), creditGap(%p), realRate(%), gdpGrowth(%), 기대)
    ("1975 스태그플레이션",   130, +2.0, +5.0,  -3.0, -0.5, "reflationary"),
    ("1982 볼커",             150, +4.0, -3.0,  +6.0, -2.0, "deflationaryDepression"),
    ("2000 닷컴 버블",        180, +3.0, +12.0, +3.0, +4.0, "lateBoom"),
    ("2007 하우징",           240, +5.0, +10.0, +0.5, +2.0, "topBubble"),
    ("2008-2009 위기",        250, +6.0, -5.0,  -1.0, -3.0, "deflationaryDepression"),
    ("2013 beautiful",        240, -2.0, +2.0,  -1.0, +2.0, "beautifulDeleveraging"),
    ("2020 팬데믹 완화",       270, +3.0, +8.0,  -5.0, -3.0, "reflationary"),
    ("2025 현재 (가정)",       250, +2.0, +3.0,  +1.0, +2.0, "lateBoom"),
]


def main() -> int:
    print("=" * 72)
    print("실험 053: Dalio debtCyclePhase 분류 규칙 검증")
    print("=" * 72)
    correct = 0
    for label, debt, ds, cg, rr, g, expected in CASES:
        phase = dalioDebtCyclePhase(debt, ds, cg, rr, g)
        ok = phase == expected
        correct += int(ok)
        mark = "OK" if ok else "XX"
        print(f"  [{mark}] {label:<20s}  phase={phase:<25s}  expected={expected}")
    total = len(CASES)
    print("-" * 72)
    print(f"정확도: {correct}/{total} ({correct / total:.0%})")
    verdict = "통과" if correct >= 6 else "기각"
    print(f"판정: {verdict}")
    return 0 if correct >= 6 else 1


if __name__ == "__main__":
    sys.exit(main())


"""결과 (2026-04-15 실행):

  [OK] 1975 스태그플레이션          phase=reflationary               expected=reflationary
  [OK] 1982 볼커                    phase=deflationaryDepression     expected=deflationaryDepression
  [OK] 2000 닷컴 버블               phase=lateBoom                   expected=lateBoom
  [OK] 2007 하우징                  phase=topBubble                  expected=topBubble
  [OK] 2008-2009 위기               phase=deflationaryDepression     expected=deflationaryDepression
  [OK] 2013 beautiful               phase=beautifulDeleveraging      expected=beautifulDeleveraging
  [XX] 2020 팬데믹 완화             phase=earlyBoom                  expected=reflationary
  [OK] 2025 현재 (가정)             phase=lateBoom                   expected=lateBoom

정확도: 7/8 (88%)
판정: 통과 (기준 75%)

엣지 분석 — 2020 팬데믹:
- 입력: debt/GDP=270, debtService=+3, creditGap=+8, realRate=-5, gdpGrowth=-3
- 규칙 #2 (reflationary) 조건 `realRate < -2 and gdpGrowth >= -2` — gdpGrowth=-3 으로 탈락
- 규칙 #1 (deflationaryDepression) 조건 `gdpGrowth < -1 and creditGap < 0` — creditGap=+8 으로 탈락
- → earlyBoom 기본값 폴백
- 해석: "급락(실물) + 급완화(신용)" 동시진행은 두 단계 경계. Dalio 본인도 이런 순간은
  "transition" 으로 명시적 별도 처리. 규칙만으로 단일 enum 강제는 무리.

결론:
1. 역사 8 케이스 중 7개 정확 (88%) — Dalio Part 1 템플릿 규칙이 sanity check 통과.
2. 엣지 (팬데믹 같은 급전환) 는 규칙 기반 단일 분류의 한계. 흡수 시 docstring 에
   "전환기 케이스는 debtCyclePhase + policyLeverStatus 조합으로 해석" 주석 명기.
3. L0 SSOT `core/finance/crisisDetector.py` 에 아래 임계치 그대로 박음:
   - deflationaryDepression: gdpGrowth < -1 AND creditGap < 0
   - reflationary: realRate < -2 AND gdpGrowth >= -2
   - topBubble: creditGap >= 8 AND gdpGrowth > 0 AND realRate < 2
   - lateBoom: creditGap >= 2 AND debtServiceYoY > 0 AND gdpGrowth > 0
   - beautifulDeleveraging: debtServiceYoY < 0 AND gdpGrowth > 0
   - earlyBoom: 기본값
4. policyLeverStatus (4 레버) 규칙은 별도 턴에서 확장.
"""
