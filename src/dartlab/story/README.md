# story/ — L3 조합기 (8 막 인과)

> dartlab 의 *분석 엔진 결과 조합기*. L2 분석 5 엔진 (analysis / credit / macro / quant / industry) + L1.5 결과를 8 막 인과로 엮는다.
> 자체 계산 0 — 모든 숫자는 하위 엔진 ref. *조립과 서사* 만 담당.

---

## 공개 API

| 모듈 | 역할 |
|------|------|
| `story/__init__.py` | `Story(code)` facade — 8 막 인과 compose |
| `story/builders.py` | 8 막 block builder (현재 6111줄 monolithic → T9-5 분해 계획) |
| `story/catalog.py` | block / topic 카탈로그 + 메타 |
| `story/composer.py` | 8 막 합성 진입점 |

---

## 8 막 구조 (재무 인과)

| 막 | 의미 | 대표 block |
|----|------|----------|
| 1. profile | 회사 정체성 | profileBlock / segmentCompositionBlock |
| 2. revenue | 매출 성장 | revenueGrowthBlock / concentrationBlock |
| 3. cost | 비용 구조 | (margin blocks) |
| 4. capital | 자본/부채 | capitalOverviewBlock / debtTimelineBlock |
| 5. liquidity | 현금/유동성 | liquidityBlock |
| 6. risk | 위험/거버넌스 | (risk blocks) |
| 7. market | 시장/peer | (technical blocks) |
| 8. close | 종합/forward | (conclusion blocks) |

---

## 진입점

```python
import dartlab
story = dartlab.Story("005930")  # 삼성전자 8 막
print(story.composed)  # 본문 + ref
```

---

## 룰

- **자체 계산 금지** — 모든 숫자는 L2 분석 엔진 ref 인용.
- **ref 추적 가능** — 답변 안 모든 숫자가 원본 데이터 ref 와 연결.
- **분해 진행 중** — `builders.py` 6111줄은 T9-5 트랙으로 8 파일 분해 예정 ([BUILDERS_SPLIT_PLAN.md](BUILDERS_SPLIT_PLAN.md)).

---

## 관련

- [BUILDERS_SPLIT_PLAN.md](BUILDERS_SPLIT_PLAN.md) — T9-5 분해 계획
- [src/dartlab/skills/specs/operation/sixActsAnalysis.md](../skills/specs/operation/sixActsAnalysis.md) — 6 막 인과 spec (8 막 의 base)
- [TODO.md](../../../TODO.md) T9-5 트랙
