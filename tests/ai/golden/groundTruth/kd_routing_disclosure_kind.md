---
caseId: kd_routing_disclosure_kind
stockCode: '005930'
target: 한국 공시 종류 routing
expectedApi: ReadSkill (engines.company.koreanDisclosure)
goldenSubSkill: engines.company.koreanDisclosure
---

# Ground truth — 사업보고서 vs 기업지배구조보고서 차이

## 기대 routing

`사용자 query` → ReadSkill (intent boost "공시 종류" + "DART 공시" matches `engines.company.koreanDisclosure`).

## 기대 답변 골격

- 사업보고서 (정기) — 연 1 회 + 분기/반기. K-IFRS 재무제표 + II 항 사업의 내용 + 임원 보수 + 관계자 거래 + 주석.
- 기업지배구조보고서 — KOSPI ≥ 1 조 원 AUM 강제. 15 핵심지표 explain-or-comply.
- 두 공시 양식 차이: 사업보고서 = 종합 / 기업지배구조보고서 = governance 특화.
- 본 sub-skill 의 표 (한국 공시 종류 → apiRef 매핑) 인용.

## 검증 string-match

- "사업보고서" 본문 등장.
- "기업지배구조보고서" 본문 등장.
- "15 핵심지표" 본문 등장 가능.

## 한계

- DART 종류와 EDGAR 8-K/10-K 1:1 매핑 금지.
- KOSPI < 1 조 원 기업은 기업지배구조보고서 미의무.
