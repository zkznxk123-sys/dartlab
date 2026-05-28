---
caseId: kd_005930_flow_foreignNet
stockCode: '005930'
target: 005930 (삼성전자)
expectedApi: Company.flow
goldenSubSkill: engines.company.flow
---

# Ground truth — 005930 외국인 net-buy 최근 30 일 추세

## 기대 routing

`사용자 query` → ReadSkill (intent boost "외국인 net-buy" matches `engines.company.flow`) → `EngineCall(apiRef="Company.flow", args={"stockCode": "005930"})` → head 30.

## 기대 답변 골격

- 일별 외국인/기관/개인 net-buy DataFrame (date · foreignNet · institutionNet · individualNet).
- 최근 5~30 일 인용 + 누적 cumsum 또는 비중.
- 외국인 매수 + 기관 동조/역행 context 동반 — 단독 신호 해석 금지.
- KR 한정 — US/JP target 빈 DataFrame.

## 검증 string-match

- "외국인" 본문 등장.
- "기관" 본문 등장.
- "net-buy" 또는 "순매수" 본문 등장.

## 한계

- 일별 raw flow 전체 dump 금지 — 답변 본문 최근 5~30 일만.
- 외국인 net-buy 단독 신호 해석 금지 — 기관 동조/역행 context 동반.
- 펀더멘털 (실적 · 공시) context 없이 수급만으로 매매 결론 금지.
