---
caseId: kd_035420_executivePay_unregistered
stockCode: '035420'
disclosure: 사업보고서
target: 035420 (NAVER)
expectedApi: Company.executivePay
goldenSubSkill: engines.company.executivePay
---

# Ground truth — NAVER 미등기 임원 보수 분포

## 기대 routing

`사용자 query` → ReadSkill (intent boost "미등기 임원 보수" matches `engines.company.executivePay`) → `EngineCall(apiRef="Company.executivePay", args={"stockCode": "035420"})` → `topPay` filter `직위 == "미등기임원"`.

## 기대 답변 골격

- 미등기 임원 명단 + 보수 분포 (등기 임원과 분리 인용).
- 한국 unique: 등기/미등기/퇴직 임원 5억 이상 disclosure — US 와 다름.
- 산정기준 narrative 동반.

## 검증 string-match

- "미등기" 본문 등장.
- "임원 보수" 본문 등장.
- 직책 정규화 없이 회사 간 비교 금지.

## 한계

- 직위 필드 정규화 (대표이사/사외이사/등) 미흡 시 회사 간 비교 노이즈.
