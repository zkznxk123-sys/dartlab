# 053 dalioDebtCycle

- 실험일: 2026-04-15
- 판정: **통과 (7/8, 88%)**

## 핵심 수치

| 역사 케이스 | 판정 | 기대 |
|---|---|---|
| 1975 스태그플레이션 | reflationary ✓ | reflationary |
| 1982 볼커 | deflationaryDepression ✓ | deflationaryDepression |
| 2000 닷컴 | lateBoom ✓ | lateBoom |
| 2007 하우징 | topBubble ✓ | topBubble |
| 2008-2009 | deflationaryDepression ✓ | deflationaryDepression |
| 2013 beautiful | beautifulDeleveraging ✓ | beautifulDeleveraging |
| **2020 팬데믹** | earlyBoom ✗ | reflationary |
| 2025 현재 | lateBoom ✓ | lateBoom |

## 결론

- Dalio Part 1 템플릿 임계치 기반 규칙이 88% 정확
- 팬데믹 같은 "급락+급완화" 전환기는 단일 enum 한계 — docstring 에 transition 주석 명기
- L0 SSOT `core/finance/crisisDetector.py` 에 `dalioDebtCyclePhase` 로 박음

## 흡수 함수 (L0 SSOT)

- `dalioDebtCyclePhase(totalDebtToGdp, debtServiceYoY, creditGap, realRate, gdpGrowth) -> str`
- `dalioPolicyLeverStatus(policyRate, creditGap, fiscalBalance, fxFlexibility) -> dict`  (별도 턴)
