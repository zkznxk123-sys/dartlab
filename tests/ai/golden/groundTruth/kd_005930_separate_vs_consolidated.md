---
caseId: kd_005930_separate_vs_consolidated
stockCode: '005930'
disclosure: 재무제표 (별도 + 연결)
target: 005930 (삼성전자)
expectedApi: Company.show
goldenSubSkill: engines.company.koreanDisclosure
---

# Ground truth — 005930 별도 vs 연결 영업이익 차이

## 기대 routing

`사용자 query` → ReadSkill (intent boost "별도 vs 연결" matches `engines.company.koreanDisclosure`) → `EngineCall(apiRef="Company.show", args={"stockCode": "005930", "topic": "IS", "basis": "separate"})` + `Company.show(IS, basis="consolidated")` 2 회 호출.

## 기대 답변 골격

- 별도 영업이익 (parent-only) — 삼성전자 본체.
- 연결 영업이익 (consolidated) — Samsung Display · Harman · 중국 자회사 포함.
- 두 basis 의 차이 narrative — 자회사 기여 영업이익 분해.
- K-IFRS 한국 dual reporting 양식 명시.

## 검증 string-match

- "별도" 본문 등장.
- "연결" 본문 등장.
- "basis" 또는 "K-IFRS" 본문 등장.
- "parent only" 본문 미등장 (forbidden — 한글 명시 필요).

## 한계

- basis 인자 명시 없이 NI/EBIT 비교 금지 (혼동 위험).
- 별도 = 본체 만 · 연결 = 자회사 포함.
