# Credit (dCR)

> 상위 사상: [philosophy.md](philosophy.md) · 자가개선 루프: [coreloop.md](coreloop.md)

**주체**: credit 엔진 (`dartlab.credit(stockCode?, axis?)` · `c.credit(axis?)`).
**현재**: 7 축 정량 스코어링 (dCR-AAA ~ dCR-D) · 업종별 차등 + 시계열 안정화 · DART·EDGAR 재무제표만으로 재현 — API 키 없이 돌아간다.
**방향**: override 키 자동 노출 · eCR (현금흐름등급) 고도화 · 신용 이력 narrative 블록화.

공시 재무제표만으로 재현 가능한 독립 신용등급 산출. 외부 신평사 등급에 의존하지 않는다. 각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 1. 호출 — `dartlab.credit` · `c.credit` 두 진입점으로 쓴다

```python
import dartlab

# 모듈 진입점
dartlab.credit()                        # 7축 + 종합 가이드 DataFrame
dartlab.credit("005930")                # 삼성전자 종합 등급
dartlab.credit("005930", "채무상환")     # 채무상환 축만

# Company-bound
c = dartlab.Company("005930")
c.credit()                              # Company-bound 가이드
c.credit("등급")                        # dCR 종합 등급
c.credit("채무상환")                     # 축별 결과
c.credit("등급", detail=True)           # 7축 상세 + 지표 시계열 + 서사
```

---

## 2. 7 축 — 이 구조로 평가한다

| 영문 axis | 한글 라벨 | 설명 |
|---|---|---|
| `grade` | 등급 | 7 축 가중평균 종합 등급 (default) |
| `repayment` | 채무상환능력 | 이자보상배율 · 부채상환능력 |
| `leverage` | 자본구조 | 부채비율 · 자본 안정성 |
| `liquidity` | 유동성 | 유동비율 · 단기 상환 여력 |
| `cashflow` | 현금흐름 | OCF · FCF 안정성 |
| `business` | 사업안정성 | 매출 변동성 · 사업 지속성 |
| `reliability` | 재무신뢰성 | 감사의견 · 회계 일관성 |
| `disclosure` | 공시리스크 | 공시 변경 · 정정 빈도 |

한글·영문 alias 양방향 (`_ALIASES`) — `"repayment" ↔ "채무상환"`, `"leverage" ↔ "자본구조"` 등.

---

## 3. 결과 구조 — 종합·축별·detail 3 형태로 반환한다

### 종합 등급 (axis 미지정)

```
dict
    grade : str — dCR 등급 (예: "dCR-AA+")
    score : float — 위험 점수 (0=최우량, 100=최위험) (점)
    healthScore : float — 건전성 점수 (100-score) (점)
    axes : list[dict] — 7 축 상세 (name · score · weight · metrics)
    eCR : str | None — 현금흐름등급
    outlook : str — 전망 ("안정적"·"긍정적"·"부정적")
    assumptions : dict — overrides 적용 시 시나리오 가정 투명화
```

### 축 단일 (axis 지정)

```
dict
    axis : str — 축 풀네임 (예: "채무상환능력")
    score : float — 해당 축 위험 점수 (점)
    weight : int — 가중치 (%)
    metrics : list[dict] — 개별 지표 (name · value · score)
    grade : str — 전체 등급 (참조용)
    overallScore : float — 전체 점수 (참조용)
```

### `detail=True`
- 7 축 `metrics` 에 시계열 (YoY · 5 년 평균) 부착.
- `narrative` 키 추가 — 한국어 인과 문장 (review 블록 재료).

---

## 4. override 키 — AI 자율 개입으로 시나리오 재계산한다

`c.credit("등급", overrides={...})` 로 시나리오 재계산. 상세 키: `core/overrides.py::CREDIT_KEYS`.

- `debtRatio` — 부채비율 (%)
- `interestCoverage` — 이자보상배율 (배)
- `currentRatio` — 유동비율 (%)
- `quickRatio` — 당좌비율 (%)
- `ocfToDebt` — OCF/부채 (%)
- `fcfToDebt` — FCF/부채 (%)
- `scenarioStress` — 스트레스 시나리오 (0=기본 · 1=mild · 2=severe)

결과 dict 의 `assumptions` 키에 시나리오와 원본 값 병기 (투명성).

---

## 5. 안정성 — 이 상태로 간다

| 항목 | 상태 |
|---|---|
| 데이터 소스 | DART·EDGAR 재무제표 (API 키 없이 동작) |
| 업종 차등 | 업종별 threshold 매트릭스 내장 (`thresholds.py`) |
| EDGAR 커버리지 | 일부 축 (예: 공시리스크) 은 DART 전용 · EDGAR 는 부분 지원 |
| 시계열 | `basePeriod` 로 특정 시점 재현 가능 |
| review 통합 | `c.review("신용분석")` 으로 블록식 보고서 |

---

## 6. 실패 대응

| 증상 | 원인 | 해결 |
|---|---|---|
| `None` 반환 | 재무 parquet 부재 | `dartlab.gather('finance', stockCode)` 로 수집 |
| 신흥 업종 등급 신뢰도 낮음 | `thresholds.py` 에 업종 미정의 | fallback 업종 적용 — `detail=True` 로 raw score 확인 |
| 알 수 없는 축 에러 | 축 typo | `c.credit()` 가이드 확인 |

**반복 실패** — 업종이 `thresholds.py` 에 정의되지 않은 신흥 업종은 fallback 으로 빠지는 것만으로는 판정 정확도가 낮다. 해당 업종 기준 매트릭스를 추가해야 근본 해결.

---

## 관련 코드

- `src/dartlab/credit/__init__.py` — 공개 API (`credit` · `creditCompany` · `axes` · `guide`).
- `src/dartlab/credit/engine.py` — `evaluate` · `evaluateCompany` 7 축 dispatch.
- `src/dartlab/credit/scorecard.py` — 축별 스코어링 + 등급 매핑.
- `src/dartlab/credit/thresholds.py` — 업종별 threshold 매트릭스.
- `src/dartlab/credit/calcs.py` — 지표 계산.
- `src/dartlab/credit/history.py` — 시계열 이력.
- `src/dartlab/credit/narrative.py` — 한국어 서사 생성.
- `src/dartlab/credit/metrics.py` — 지표 메타데이터.
- `src/dartlab/credit/audit.py` — 검증 유틸.
- `src/dartlab/core/overrides.py::CREDIT_KEYS` — override 키 SSOT.

---

## 요약 — 명제 6 줄

1. `dartlab.credit` · `c.credit` 두 진입점 · 축 없으면 종합 등급 · 축 있으면 축 단일.
2. 7 축 (repayment · leverage · liquidity · cashflow · business · reliability · disclosure) 가중평균으로 dCR 등급 산출.
3. 결과는 종합(`grade`·`score`·`healthScore`·`axes`·`eCR`·`outlook`) · 축 단일 · `detail=True` 시계열+서사 3 형태.
4. `overrides` 로 AI 자율 개입 — `debtRatio`·`interestCoverage`·`currentRatio`·`ocfToDebt`·`scenarioStress` 등 재계산.
5. DART·EDGAR 재무제표만으로 동작 (API 키 불필요), 업종별 차등 + 시계열 안정화.
6. `c.review("신용분석")` 으로 블록식 보고서에 통합, `narrative` 는 review 블록 재료.
