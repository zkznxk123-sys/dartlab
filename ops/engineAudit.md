# Engine Audit — 엔진 기능 점검 규격

> AI audit(AI가 엔진을 제대로 쓰는지) 과 달리, engine audit은 **엔진 자체가 제대로 작동하는지** 점검한다.
> 단위 테스트는 로직을 보고, engine audit은 **실제 데이터로 end-to-end 결과**를 본다.

## 목적

- Company 생성 → show/select/analysis/credit/scan/review/macro/gather/quant 전체 통로 작동 확인
- 주요 종목 (KR + US) 에서 반환값이 기대 형식인지
- 새 기능 추가 / 데이터 갱신 / 리팩토링 후 회귀 감지
- AI audit 전에 선행 점검 (엔진 깨진 채 AI 돌리면 무의미)

## 점검 범위 (체크리스트)

### Company facade
- [ ] `Company("005930")` — 한국 종목코드 → DartCompany
- [ ] `Company("삼성전자")` — 한글 회사명 → DartCompany
- [ ] `Company("AAPL")` — 영문 ticker → EdgarCompany
- [ ] `c.market`, `c.currency` 반환
- [ ] `c.topics`, `c.index` 반환
- [ ] `c.filings()` DataFrame 반환

### show / select
- [ ] `c.show("IS")` — 손익계산서 DataFrame (분기 컬럼)
- [ ] `c.show("BS")`, `c.show("CF")`, `c.show("CIS")`, `c.show("SCE")`
- [ ] `c.show("IS", freq="Y")` — 연간 합산
- [ ] `c.select("IS", ["매출액"])` — 행 필터
- [ ] `c.show("inventory")` — 주석 상세 (notes 12항목 중 대표)
- [ ] `c.show("dividend")` — report topic

### analysis (L2)
- [ ] `c.analysis()` — 가이드 DataFrame
- [ ] `c.analysis("수익성")` — dict with marginTrend, returnTrend, roicTree, profitabilityFlags
- [ ] `c.analysis("성장성")`, `c.analysis("안정성")`, `c.analysis("현금흐름")`
- [ ] `c.analysis("비용구조")`, `c.analysis("효율성")`, `c.analysis("자산구조")`
- [ ] `c.analysis("수익구조")`, `c.analysis("자금조달")`, `c.analysis("이익품질")`
- [ ] `c.analysis("자본배분")`, `c.analysis("투자효율")`, `c.analysis("재무정합성")`
- [ ] `c.analysis("종합평가")`
- [ ] `c.analysis("forecast", "매출전망")` — 그룹 호출
- [ ] `c.analysis("valuation", "가치평가")`

### credit
- [ ] `c.credit()` — 가이드 DataFrame
- [ ] `c.credit("등급")` — dict with grade, healthScore, pdEstimate
- [ ] `c.credit("등급", detail=True)` — + narratives

### scan (L1)
- [ ] `dartlab.scan()` — 가이드 DataFrame
- [ ] `dartlab.scan("profitability")` — 전종목 수익성
- [ ] `dartlab.scan("account", "매출액")` — 전종목 계정 시계열
- [ ] `dartlab.scan("ratio", "roe")` — 전종목 비율 시계열
- [ ] `dartlab.scan("governance")` — 지배구조 5축

### macro (L2, Company 불필요)
- [ ] `dartlab.macro()` — 가이드
- [ ] `dartlab.macro("사이클")`, `dartlab.macro("금리")`, `dartlab.macro("종합")`
- [ ] market="US"와 "KR" 모두 동작

### gather (L1)
- [ ] `c.gather("price")` — 주가 OHLCV
- [ ] `c.gather("flow")` — 수급 (KR only)
- [ ] `c.gather("news")` — 뉴스
- [ ] EDGAR에서 `c.gather("flow")`는 None 반환 확인

### quant (L1)
- [ ] `c.quant()` — 가이드
- [ ] `c.quant("종합")` — dict with verdict

### review (L3)
- [ ] `c.review("수익성")` — 단일 섹션 ~5초
- [ ] Review 객체 반환, `.toMarkdown()` / `.toHtml()` / `.toJson()`

### search
- [ ] `dartlab.search("유상증자")` — 공시 검색 DataFrame
- [ ] `dartlab.search("대표이사 변경", corp="005930")` — 종목 필터

### SuperMaster (신규)
- [ ] `CapabilityIndex.search("수익성")` — top-5 API
- [ ] `ExperienceIndex.search("수익성", stockCode="005930")` — 과거 사례
- [ ] `SuperMaster.gather(...)` — api_text + example_text

## 종목 커버리지

| 종목 | market | 이유 |
|------|--------|------|
| 삼성전자 (005930) | KR | 제조, 현금 풍부, 대형주 |
| 대우건설 (047040) | KR | 건설 (사이클), 부채 비중 |
| 삼양식품 (003230) | KR | 식품 (프랜차이즈), 해외 성장 |
| Apple (AAPL) | US | EDGAR 기본 |
| Microsoft (MSFT) | US | EDGAR 대형 |

## 등급 판정

| 등급 | 기준 |
|------|------|
| **Pass** | 모든 체크 통과. 예외 없음 |
| **Warning** | 1~3개 실패. 재실행 시 재현되는지 확인 |
| **Fail** | 4개 이상 실패 또는 Company 생성 자체 실패 |

## 자동화 출력

```json
{
  "timestamp": "2026-04-12T13:45:00",
  "stockCode": "005930",
  "market": "KR",
  "results": {
    "Company.create": "Pass",
    "Company.topics": "Pass",
    "show.IS": "Pass",
    "show.inventory": "Warning (empty DataFrame)",
    "analysis.수익성": "Pass",
    "analysis.현금흐름": "Fail (KeyError: ocf)",
    ...
  },
  "duration_sec": 45.2,
  "overall": "Fail"
}
```

## 실행

```bash
uv run python -X utf8 scripts/audit/engineAudit.py              # 전체 5종목
uv run python -X utf8 scripts/audit/engineAudit.py --stock 005930  # 단일
uv run python -X utf8 scripts/audit/engineAudit.py --quick      # 핵심 체크만
```

결과: `data/audit/engine/{YYYY-MM-DD}/{stockCode}.json` + `report.md`

## 발견 시 처리

- **Fail 발견 시 즉시 중단** + 원인 분석
- 엔진 버그 → 해당 파일 근본 수정 (feedback_code_quality.md)
- 데이터 이슈 → `_reference/LEARNING_WORKFLOW.md` 6단계
- Warning은 별도 등록. Fail 잡은 후 해결.

## AI audit 와의 관계

```
engineAudit (선행) → Pass 확인 → aiAudit 진행
                  ↓
                Fail 발견 시 aiAudit 의미 없음 (엔진이 깨졌으니 AI도 깨짐)
```

engineAudit이 엔진 품질을, aiAudit이 AI 활용 품질을 본다. 둘 다 필수.

## 관련 코드

- `scripts/audit/engineAudit.py` — 실행 스크립트
- `scripts/audit/aiAudit.py` — AI audit 실행
- `ops/ai.md` "AI Audit 체계" — AI audit 규격
