---
caseId: kd_005930_governance_outsideDirectors
stockCode: '005930'
disclosure: 기업지배구조보고서
target: 005930 (삼성전자)
expectedApi: Company.governance
goldenSubSkill: engines.company.governance
---

# Ground truth — 005930 사외이사 비율 + 감사위원회 독립성

## 기대 routing

`사용자 query` → ReadSkill (intent boost "사외이사" matches `engines.company.governance`) → `EngineCall(apiRef="Company.governance", args={"stockCode": "005930"})`.

## 기대 답변 골격

- 이사회 구성 board (totalDirectors/outsideDirectors/outsideRatio/ceoChairSeparated).
- 감사위원회 auditCommittee (totalMembers/outsideMembers/independenceScore).
- 15 핵심지표 disclosure dict (compliant boolean + 미준수 narrative).
- KOSPI ≥ 1 조 원 AUM 강제 — 기업지배구조보고서 의무.
- DART 기업지배구조보고서 rceptNo + section paragraph 인용.

## 검증 string-match

- "사외이사" 본문 등장.
- "감사위원회" 본문 등장.
- "기업지배구조보고서" 본문 등장.
- 15 핵심지표 yes/no 만 답변 본문에 박지 말고 미준수 narrative 도 같이 인용.
- `<docRef:...>` 토큰 ≥ 1.

## 한계

- KOSPI < 1 조 원 기업은 governance 보고서 미의무 → fallback = Company.disclosure(category="기업지배구조") · 결과 None.
- 사외이사 비율을 NEO-5 만으로 산출 금지 (한국은 전체 등기/미등기 임원 disclosure).
