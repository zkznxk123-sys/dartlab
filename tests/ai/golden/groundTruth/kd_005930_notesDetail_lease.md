---
caseId: kd_005930_notesDetail_lease
stockCode: '005930'
disclosure: 사업보고서 K-IFRS 주석
target: 005930 (삼성전자)
expectedApi: Company.notesDetail
goldenSubSkill: engines.company.notesDetail
---

# Ground truth — 005930 리스 약정 주석

## 기대 routing

`사용자 query` → ReadSkill (intent boost "리스 약정" matches `engines.company.notesDetail`) → `EngineCall(apiRef="Company.notesDetail", args={"stockCode": "005930", "keyword": "리스"})`.

## 기대 답변 골격

- 최근 5 년 historical panel (year 내림차순).
- NotesPeriod (year/kind/items DataFrame/unit).
- 표 line-item 본문 추출 — K-IFRS 1116 리스 양식.
- DART 사업보고서 rceptNo + 주석 섹션 paragraph 인용.

## 검증 string-match

- "리스" 본문 등장.
- "K-IFRS" 또는 "주석" 본문 등장.

## 한계

- NOTES_KEYWORDS 23 종 밖 keyword → None 반환.
- 분기별 양식 변경 (XBRL tag rename) 회귀 가드 강제.
- 주석 본문 narrative = wrapExternalInResult untrusted marker 자동.
