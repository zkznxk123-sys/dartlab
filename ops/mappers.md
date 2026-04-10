# Mappers

dartlab 전체 매핑 데이터의 통합 엔진. 계정·topic·alias·flow·notes 5개 매퍼를 단일 인터페이스로 관리.

## 한눈에 보기

| 항목 | 내용 |
|------|------|
| 레이어 | L0 (core/mappers/) |
| 진입점 | `from dartlab.core.mappers import getEngine` |
| 원칙 | 기존 코드 수정 0줄 — 읽기 전용 래퍼, 검증 후 순차 교체 |
| 매퍼 | account(34K), topic(33), alias(61), flow(14), notes(46+) |
| 학습 | Scanner → notesStructure.json 갱신 → 분기별 스냅샷 |

## 사용법

```python
from dartlab.core.mappers import getEngine

engine = getEngine()
engine.summary()                          # 전체 매퍼 통계

engine.get("account").lookup("매출액")     # 계정 매핑
engine.get("topic").lookup("dividend")     # topic 키워드
engine.get("alias").resolve("revenue")     # snakeId 정규화
engine.get("flow").isEvent("dividends_paid")  # 이벤트 계정 판별
engine.get("notes").isAmount("완제품")     # notes 항목 유형 판별
```

## 아키텍처

```
core/mappers/
├── __init__.py          # getEngine() 싱글턴 (5개 매퍼 자동 등록)
├── engine.py            # MapperEngine + BaseMapper ABC + snapshot/diff
├── accountMapper.py     # accountMappings.json 래핑 (34,000+ 매핑)
├── topicMapper.py       # TOPIC_KEYWORDS 래핑 (33 topics)
├── aliasMapper.py       # SNAKEID_ALIASES 래핑 (61 alias)
├── flowMapper.py        # _EVENT_ACCOUNTS 래핑 (14 이벤트 계정)
├── notesMapper.py       # notesStructure.json 기반 (46+ 항목)
├── scanner.py           # 전종목 notes 구조 스캔 → notesStructure.json 갱신
└── masterParser.py      # notesMapper 기반 파서 + legacy 비교 compare()
```

## 5개 매퍼

### account — 계정 매핑 (34,000+)

K-IFRS 한국어 계정명 ↔ snakeId 매핑. `core/data/accountMappings.json`을 읽기 전용 래핑.

```python
m = engine.get("account")
m.lookup("매출액")           # → {"snakeId": "sales", "korName": "매출액", ...}
m.korToSnakeId("영업이익")   # → "operating_profit"
m.snakeIdToKor("sales")     # → "매출액"
```

**원본**: `core/finance/labels.py::_load_account_mappings()` (수정 0줄)

### topic — 주제 키워드 (33)

공시 sections의 topic → 한국어 키워드 매핑. `core/docs/topicGraph.py::TOPIC_KEYWORDS` 참조.

```python
m = engine.get("topic")
m.lookup("dividend")              # → {"topic": "dividend", "keywords": ["배당", ...]}
m.topicForKeyword("사업의 개요")  # → "businessOverview"
```

**원본**: `core/docs/topicGraph.py::TOPIC_KEYWORDS` (수정 0줄)

### alias — snakeId 정규화 (61)

DART ↔ EDGAR snakeId variant → canonical 매핑. `core/finance/labels.py::SNAKEID_ALIASES` 참조.

```python
m = engine.get("alias")
m.resolve("revenue")         # → "sales"
m.resolve("operating_income")  # → "operating_profit"
m.variantsOf("sales")        # → ["revenue"]
```

**원본**: `core/finance/labels.py::SNAKEID_ALIASES` (수정 0줄)

### flow — 이벤트 계정 분류 (14)

매 분기 발생하지 않는 이벤트성 계정 판별. `core/finance/flow.py::_EVENT_ACCOUNTS` 참조.

```python
m = engine.get("flow")
m.isEvent("dividends_paid")   # → True (비정기 → 부분 합산 허용)
m.isEvent("sales")            # → False (정기 → 4분기 strict 합산)
```

**원본**: `core/finance/flow.py::_EVENT_ACCOUNTS` (수정 0줄)

### notes — 주석 항목 구조 (46+)

notes 파서의 항목별 유형(amount/rate/text), 외화 혼합 여부, 카테고리.
`core/data/notesStructure.json`을 읽고, Scanner가 갱신.

```python
m = engine.get("notes")
m.isAmount("완제품")              # → True
m.isSkip("연이자율")              # → True (rate → 파싱 제외)
m.hasForeignCurrency("외화대출")  # → True
m.byCategory("inventory")        # → ["완제품", "반제품", "원재료", ...]
```

## 공통 인터페이스 (BaseMapper)

모든 매퍼가 구현하는 인터페이스:

```python
class BaseMapper(ABC):
    name: str                        # 매퍼 이름
    lookup(key) → dict | None        # 키로 매핑 조회
    contains(key) → bool             # 키 존재 여부
    allKeys() → list[str]            # 등록된 모든 키
    missing(candidates) → list[str]  # 미매핑 항목 탐지
    stats() → MapperStats            # 통계 (이름, 총수, 매핑수, 커버리지)
```

## 학습 메커니즘

### 학습 사이클

```
1. 스캔 (Scanner)
   - 전종목 docs parquet에서 notes 항목 구조 패턴 추출
   - 항목명, 유형(amount/rate/text), 외화 여부, 출현 빈도 자동 분류
   - 결과: notesStructure.json 갱신 (기존 수동 보정 보존, 신규만 추가)

2. 검증 (compare)
   - masterParser.compare(stockCode) — legacy vs master 결과 비교
   - 항목별 일치율, 값 차이, legacy-only/master-only 항목 리포트
   - 일치율 95%+ 항목만 master로 전환

3. 이력 (snapshot)
   - engine.snapshot("2026Q2") → history/ 분기 스냅샷
   - engine.diff("2026Q1", "2026Q2") → 매퍼 변경 diff
   - 롤백 가능
```

### Scanner 사용법

```python
from dartlab.core.mappers.scanner import scanNotes, scanAll

# 단일 종목 스캔
items = scanNotes("005930")
# → {"완제품": {"type": "amount", "category": "inventory", ...}, ...}

# 전체 종목 스캔 → notesStructure.json 갱신
stats = scanAll(limit=100)   # 테스트용 100종목
stats = scanAll()            # 전체 (~2,700종목)
# → {"scanned": 2700, "newItems": 150, "updatedItems": 300, "totalItems": 500}
```

### 분기별 학습 사이클

```
매 분기 DART 데이터 갱신 후:
  → scanAll()                    # 신규 종목/연도 포함 재스캔
  → compare() × 6종목            # legacy vs master 비교
  → engine.snapshot("2026Q2")   # history/ 스냅샷
  → 일치율 95%+ 항목 master 전환
```

### 하드코딩 → 매퍼 전환 매핑

| 기존 하드코딩 | 위치 | → 매퍼 |
|---|---|---|
| `_isNonAmountRow` regex | pipeline.py | `notesMapper.isSkip(name)` |
| `_hasForeignCurrency` regex | pipeline.py | `notesMapper.hasForeignCurrency(name)` + 값 수준 감지 |
| `_EVENT_ACCOUNTS` frozenset | flow.py | `flowMapper.isEvent(name)` |
| `_NON_AMOUNT_PATTERNS` | pipeline.py | `notesMapper.lookup(name).type != "amount"` |

## Master Parser

notesMapper 기반 파서. 기존 pipeline.py(legacy)와 동일 인터페이스, 나란히 존재.

```python
from dartlab.core.mappers.masterParser import buildTableDf, compare

# legacy vs master 비교
result = compare("005930", "재고자산")
# → {"match": True, "legacy_rows": 8, "master_rows": 8, ...}
```

### 교체 순서

1. masterParser 만들고 동일 인터페이스 ✅
2. 6종목에서 legacy vs master 결과 비교
3. 일치율 95%+ → 해당 notes 항목 master로 전환
4. 항목별로 순차 전환
5. 전 항목 전환 완료 → legacy 제거

## 설계 원칙

1. **레거시 먼저 안 건드린다** — master를 별도로 만들고 검증 후 교체
2. **매퍼 데이터는 절대 날리지 않는다** — history/ 분기 스냅샷
3. **하나씩 테스트해서 순차 교체** — 전체 교체 금지
4. **기존 코드 수정 0줄** — 모든 매퍼가 원본 데이터를 lazy import로 읽기만

## 장기 로드맵

```
Phase 1 (완료): 매퍼 엔진 + 5개 래퍼 + Scanner + Master Parser
Phase 2 (다음): 6종목 compare 검증 → 항목별 순차 전환
Phase 3 (분기): 학습 사이클 자동화 + history 스냅샷
Phase 4 (장기): AI가 notes 원문에서 패턴 추출 → 매퍼 자동 갱신 제안
```

## 관련 코드

| 경로 | 역할 |
|------|------|
| `src/dartlab/core/mappers/` | 매퍼 엔진 전체 (8파일) |
| `src/dartlab/core/data/accountMappings.json` | 계정 매핑 원본 (34K) |
| `src/dartlab/core/data/notesStructure.json` | notes 항목 구조 (Scanner 갱신) |
| `src/dartlab/core/docs/topicGraph.py` | TOPIC_KEYWORDS 원본 (33) |
| `src/dartlab/core/finance/labels.py` | SNAKEID_ALIASES 원본 (61) |
| `src/dartlab/core/finance/flow.py` | _EVENT_ACCOUNTS 원본 (14) |
| `src/dartlab/providers/dart/docs/finance/notesDetail/pipeline.py` | legacy 파서 |
| `tests/test_mappers.py` | 37개 unit 테스트 |
