---
caseId: kd_005930_executivePay
stockCode: '005930'
disclosure: 사업보고서
target: 005930 (삼성전자)
expectedApi: Company.executivePay
goldenSubSkill: engines.company.executivePay
---

# Ground truth — 005930 임원 보수 5억 이상

## 기대 routing

`사용자 query` → ReadSkill (intent boost +11.0 "임원 보수" matches `engines.company.executivePay`) → `EngineCall(apiRef="Company.executivePay", args={"stockCode": "005930"})`.

## 기대 답변 골격

- 5억 이상 보수 임원 명단 (성명/직위/총액) — 상위 5~10 명만 인용 (전체 dump 금지).
- 산정기준 narrative (스톡옵션 행사 timing · 상여 산정 룰) 동반.
- 등기 vs 미등기 분리 명시 — 한국 unique disclosure 양식 (US NEO-5 와 다름).
- DART 사업보고서 rceptNo (14 자리) + 임원 보수 섹션 paragraph 인용 (docRef).

## 검증 string-match

- "5억 이상" 또는 "임원 보수" 본문 등장.
- "산정기준" 본문 등장.
- "NEO-5" 본문 미등장 (forbidden — 한국을 US proxy 와 1:1 매핑 금지).
- `<docRef:...>` 토큰 ≥ 1.

## 한계

- 5억 미만 회사 (KOSDAQ 소형주) 는 None 반환 — 답변 본문 "데이터 없음" 명시.
- 추정 금지.
