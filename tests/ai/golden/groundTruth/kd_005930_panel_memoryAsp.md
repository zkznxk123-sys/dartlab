---
caseId: kd_005930_panel_memoryAsp
stockCode: '005930'
disclosure: 사업보고서 II 항
target: 005930 (삼성전자)
expectedApi: Company.panel
goldenSubSkill: engines.panel
---

# Ground truth — 005930 메모리 ASP narrative 분기별

## 기대 routing

`사용자 query` → ReadSkill (intent boost "메모리 ASP" matches `engines.panel`) → `EngineCall(apiRef="Company.panel", args={"stockCode": "005930", "topic": "businessOverview"})` → panel text filter `sectionLeaf` / `topic` contains "메모리".

## 기대 답변 골격

- period × topic narrative grid — 분기별 ASP 추세.
- 005930 panelTextWide 실측: 40 분기 · 60 distinct topics · 3,100 page-equiv.
- period 미명시 호출 시 LazyFrame .collect() 직전 gc.collect() 강제 (Polars OOM 가드).
- DART 사업보고서 rceptNo + section paragraph 인용.

## 검증 string-match

- "사업의 내용" 본문 등장.
- "메모리" 본문 등장.
- "ASP" 본문 등장.
- 한국어 원문 보존 — content_plain 사전 계산 X.

## 한계

- section query 영어 자동 번역 금지 (DART XML 양식 SSOT).
- 분기별 narrative drift 비교 시 양식 변경 회귀 가드.
- 외부 본문 untrusted marker 강제.
