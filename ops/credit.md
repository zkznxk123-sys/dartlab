# Credit (dCR)

**주체**: credit 엔진 (`dartlab.credit(stockCode?, axis?)` · `c.credit(axis?)`).
**현재**: 7축 정량 스코어링 (dCR-AAA ~ dCR-D) · 업종별 차등 + 시계열 안정화 · DART/EDGAR 재무제표만으로 재현 — API 키 불필요.
**방향**: override 키 자동 노출 · eCR (현금흐름등급) 고도화 · 신용 이력 narrative 블록화.

공시 재무제표만으로 재현 가능한 독립 신용등급 산출. 외부 신평사 등급에 의존하지 않는다.

## 호출 계약

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

## 7축 구조

| 영문 axis | 한글 라벨 | 설명 |
|---|---|---|
| `grade` | 등급 | 7축 가중평균 종합 등급 (default) |
| `repayment` | 채무상환능력 | 이자보상배율, 부채상환능력 |
| `leverage` | 자본구조 | 부채비율, 자본 안정성 |
| `liquidity` | 유동성 | 유동비율, 단기 상환 여력 |
| `cashflow` | 현금흐름 | OCF, FCF 안정성 |
| `business` | 사업안정성 | 매출 변동성, 사업 지속성 |
| `reliability` | 재무신뢰성 | 감사의견, 회계 일관성 |
| `disclosure` | 공시리스크 | 공시 변경, 정정 빈도 |

한글/영문 alias 양방향 (`_ALIASES`) — `"repayment" ↔ "채무상환"`, `"leverage" ↔ "자본구조"` 등.

## 결과 구조

### 종합 등급 (axis 미지정)
```
dict
    grade : str — dCR 등급 (예: "dCR-AA+")
    score : float — 위험 점수 (0=최우량, 100=최위험) (점)
    healthScore : float — 건전성 점수 (100-score) (점)
    axes : list[dict] — 7축 상세 (name, score, weight, metrics)
    eCR : str | None — 현금흐름등급
    outlook : str — 전망 ("안정적"/"긍정적"/"부정적")
    assumptions : dict — overrides 적용 시 시나리오 가정 투명화
```

### 축 단일 (axis 지정)
```
dict
    axis : str — 축 풀네임 (예: "채무상환능력")
    score : float — 해당 축 위험 점수 (점)
    weight : int — 가중치 (%)
    metrics : list[dict] — 개별 지표 (name, value, score)
    grade : str — 전체 등급 (참조용)
    overallScore : float — 전체 점수 (참조용)
```

### `detail=True`
- 7축 metrics 에 시계열 (YoY, 5년 평균) 부착.
- `narrative` 키 추가 — 한국어 인과 문장 (review 블록 재료).

## override 키 (AI 자율 개입)

`c.credit("등급", overrides={...})` 로 시나리오 재계산. 상세: `core/overrides.py::CREDIT_KEYS`.

- `debtRatio` — 부채비율 (%)
- `interestCoverage` — 이자보상배율 (배)
- `currentRatio` — 유동비율 (%)
- `quickRatio` — 당좌비율 (%)
- `ocfToDebt` — OCF/부채 (%)
- `fcfToDebt` — FCF/부채 (%)
- `scenarioStress` — 스트레스 시나리오 (0=기본, 1=mild, 2=severe)

결과 dict 의 `assumptions` 키에 시나리오와 원본 값 병기 (투명성).

## 안정성

| 항목 | 상태 |
|---|---|
| 데이터 소스 | DART/EDGAR 재무제표 (API 키 불필요) |
| 업종 차등 | 업종별 threshold 매트릭스 내장 (`thresholds.py`) |
| EDGAR 커버리지 | 일부 축 (e.g. 공시리스크) 는 DART 전용 · EDGAR 는 부분 지원 |
| 시계열 | basePeriod 로 특정 시점 재현 가능 |
| review 통합 | `c.review("신용분석")` 으로 블록식 보고서 |

## 실패 시나리오

| 증상 | 원인 | 해결 |
|---|---|---|
| `None` 반환 | 재무 parquet 부재 | `dartlab.gather('finance', stockCode)` 로 수집 |
| 신흥 업종 등급 신뢰도 낮음 | thresholds.py 에 업종 미정의 | fallback 업종 적용 — detail=True 로 raw score 확인 |
| 알 수 없는 축 에러 | 축 typo | `c.credit()` 가이드 확인 |

## 관련 코드

- `src/dartlab/credit/__init__.py` — 공개 API (`credit` · `creditCompany` · `axes` · `guide`)
- `src/dartlab/credit/engine.py` — `evaluate` / `evaluateCompany` 7축 dispatch
- `src/dartlab/credit/scorecard.py` — 축별 스코어링 + 등급 매핑
- `src/dartlab/credit/thresholds.py` — 업종별 threshold 매트릭스
- `src/dartlab/credit/calcs.py` — 지표 계산
- `src/dartlab/credit/history.py` — 시계열 이력
- `src/dartlab/credit/narrative.py` — 한국어 서사 생성
- `src/dartlab/credit/metrics.py` — 지표 메타데이터
- `src/dartlab/credit/audit.py` — 검증 유틸
- `src/dartlab/core/overrides.py::CREDIT_KEYS` — override 키 SSOT
