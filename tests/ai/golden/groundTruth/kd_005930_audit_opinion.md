---
caseId: kd_005930_audit_opinion
stockCode: '005930'
disclosure: 감사보고서
target: 005930 (삼성전자)
expectedApi: Company.audit
goldenSubSkill: engines.company.audit
---

# Ground truth — 005930 감사 의견 + KAM

## 기대 routing

`사용자 query` → ReadSkill (intent boost "감사보고서" matches `engines.company.audit`) → `EngineCall(apiRef="Company.audit", args={"stockCode": "005930"})`.

## 기대 답변 골격

- opinion (적정 / 한정 / 부적정 / 의견거절 4 분류 — 한국공인회계사회 표준).
- auditor (외부감사인) — 삼일/삼정/안진/한영 등.
- keyAuditMatters (KAM) list — K-IFRS 1701 도입 (2018-) 후 의무.
- goingConcernFlag boolean.
- DART 감사보고서 rceptNo + KAM section paragraph 인용.

## 검증 string-match

- "감사보고서" 본문 등장.
- "적정" 또는 "한정" 또는 "부적정" 또는 "의견거절" 본문 등장.
- "KAM" 또는 "핵심감사사항" 본문 등장.
- "PCAOB ICFR" 본문 미등장 (forbidden — 한국 K-IFRS audit 을 US PCAOB 양식과 1:1 매핑 금지).

## 한계

- KAM 본문은 자유 narrative — 표준 카테고리 자동 분류 X.
- goingConcernFlag=True 만으로 부도 예측 결론 X — Company.credit 의 Altman Z-score 추가 호출.
- 외부감사인 변경 (직전 5 년 내 2 회+) = audit shopping 신호.
