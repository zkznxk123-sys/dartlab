# Review Audit

종목별 `c.review()` 실측 audit으로 발견된 버그와 fix 기록. 같은 함정 반복 방지용.

## 진행 절차

1. `c.review()` 단일 섹션씩 호출(메모리 안전), 표/숫자 line by line 읽기
2. 의심점 → raw `c.IS/BS/CF/notes` 직접 호출로 교차검증
3. 진짜 버그면 아래 표에 등록 → 보수적 fix → 재검증
4. 종목 1개 끝나면 다음 종목으로 커버리지 확장

## 단위 함정 (반복 금지)

- `c.notes.*` (costByNature, borrowings, tangibleAsset, intangibleAsset, receivables, provisions, inventory, lease, investmentProperty, affiliates) → **백만원**
- `c.IS / c.BS / c.CF` → **원**
- review/analysis가 두 소스를 섞어 표시·산술할 때 ×1e6 또는 ÷1e6 명시 필수
- 비화폐성 notes(eps, segments, count) 는 절대 스케일 금지
- 새 화폐성 notes 키 추가 시 `review/builders.py::_NOTES_MONETARY_KEYS` 에도 등록

## Q4 컬럼 함정 (반복 금지)

- DART finance의 IS/CF 컬럼은 **분기 단독값**. `2025Q4` 컬럼 = 4분기 한 분기만.
- 연간 비교가 필요하면 반드시 Q1+Q2+Q3+Q4 합산. calc 함수는 `_helpers.py::ttmSum`, narrative detector는 `narrative.py::_annualizeFlow` 사용.
- BS는 stock이라 Q4=연말 그대로 OK.
- 새 detector/calc 추가 시 IS/CF row를 row.get("2025Q4") 직접 호출하지 말 것.

## 종목별 발견 버그

### 2026-04-07 — SK하이닉스(000660)

| # | 위치 | 증상 | 원인 | Fix | 상태 |
|---|---|---|---|---|---|
| 1 | `review/builders.py::_notesDetailBlocks` | 비용성격별 "원재료사용 1,210만" (실제 12.1조) | `c.notes.*` 는 백만원 단위, `_fmtAmtShort` 는 원 단위 가정 → 6자리 축소 표시 | 화폐성 키 10개(`_NOTES_MONETARY_KEYS`)에 `_scaleNotesRowsToWon()` ×1e6 적용 | ✅ |
| 2 | 영업레버리지(DOL) | 2024Q4/2023Q4/2018Q4 None | 부호 전환(음→양) 시 직관적 해석 불가로 의도적 None 가능성 큼. 우선 보류 | — | ⏸ |
| 3 | 수익성 — 매출총이익률 표 | 본문 60.4% vs 표 57.3%→68.8% | 재현 불가(현재 표 60.4% 정상). 이전 세션 오인 | — | ❌ |
| 4 | `review/narrative.py::_detectGrowthProfitability` 외 6개 detector | "매출 +66.1% / 영업이익률 40.9%→58.4%" — 표(46.8%/35.5%→48.6%)와 불일치 | `_annualCols`가 Q4 컬럼을 연간값으로 오인. DART IS/CF Q4는 분기 단독값. 7개 detector 모두 영향 | `_annualizeFlow()` 헬퍼 추가 + 7개 detector에서 IS/CF dict annualize 적용 | ✅ |
