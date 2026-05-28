---
caseId: kd_005930_relatedPartyTx
stockCode: '005930'
disclosure: 사업보고서 + 대규모기업집단현황공시
target: 005930 (삼성전자)
expectedApi: Company.relatedPartyTx
goldenSubSkill: engines.company.relatedPartyTx
---

# Ground truth — 005930 관계자 거래 100억 threshold

## 기대 routing

`사용자 query` → ReadSkill (intent boost "관계자 거래" matches `engines.company.relatedPartyTx`) → `EngineCall(apiRef="Company.relatedPartyTx", args={"stockCode": "005930"})`.

## 기대 답변 골격

- 100억 원 이상 거래 항목 (지급보증 · 매출 · 매입 · 자산 양수도) — RelatedPartyTxResult dataclass 의 분류별 DataFrame.
- 공정거래법 §26 threshold 100억 원 (2024-01-01 시행) 명시.
- 거래 상대방 (계열사명) + 금액 + 조건 narrative.
- chaebol inter-affiliate 거래 graph 구축 시 affiliateGroup 와 join.
- DART 사업보고서 rceptNo + 관계자 거래 섹션 paragraph 인용.

## 검증 string-match

- "100억" 본문 등장.
- "공정거래법" 또는 "§26" 본문 등장.
- "관계자 거래" 본문 등장.
- "10억 threshold" 본문 미등장 (forbidden — 옛 룰, 2023-12 까지).
- `<docRef:...>` 토큰 ≥ 1.

## 한계

- 단일 회사 RPT 만 인용 + chaebol 전체 흐름 무시 = RPT 본질 누락.
- 2025 FTC 데이터: top-10 chaebol = 193 조 원 = 전체 disclosed RPT 의 70%.
