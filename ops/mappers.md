# Mappers

dartlab 전체 매핑 데이터의 통합 엔진. 6개 매퍼를 단일 인터페이스로 관리.
모든 매핑 데이터는 JSON이 단일 진실의 원천. 코드에 매핑 데이터 0줄.
AI 학습을 전제로 설계 — 매퍼 데이터는 AI가 소비하고 학습한다.

## 한눈에 보기

| 항목 | 내용 |
|------|------|
| 레이어 | L0 (core/mappers/) |
| 진입점 | `from dartlab.core.mappers import getEngine` |
| 매퍼 | account(34K), topic(33), alias(61), flow(14), notes(2,640), parser(160+) |
| 데이터 | `core/data/` JSON 파일이 단일 진실의 원천 |
| 학습 | Scanner 2,877종목 학습 완료 → 분기별 갱신 |
| AI | 모든 매퍼 데이터는 AI 학습 대상 |

## 절대 규칙

1. **코드에 매핑 데이터 0줄** — 모든 매핑은 JSON 파일에. 코드는 JSON 로드만.
2. **단일 정의** — 같은 함수/데이터의 중복 정의 금지. common.py가 공통 유틸.
3. **파서 로직은 매퍼 패키지에 두지 않는다** — 매퍼는 데이터만, 파서는 providers/.
4. **private 함수 외부 import 금지** — 공개 API만 노출 (loadAffiliate, loadCostByNature 등).
5. **매퍼 추가 시 반드시 테스트** — test_mappers.py에 lookup/stats/allKeys 3개 이상.
6. **JSON 수정 시 기존 키 삭제 금지** — 신규 추가만. 삭제는 scanner 검증 후.
7. **AI 학습 전제** — 모든 매핑 데이터는 구조화되어 AI가 읽을 수 있어야 한다.

## 아키텍처

```
core/mappers/                          # 매퍼 엔진 (L0)
├── __init__.py                        # getEngine() 싱글턴 (6개 매퍼)
├── engine.py                          # MapperEngine + BaseMapper ABC
├── common.py                          # 공통 유틸 (normalizeName, isCurrentPeriod, pickValue)
├── accountMapper.py                   # accountMappings.json 래핑
├── topicMapper.py                     # TOPIC_KEYWORDS 래핑
├── aliasMapper.py                     # SNAKEID_ALIASES 래핑
├── flowMapper.py                      # _EVENT_ACCOUNTS 래핑
├── notesMapper.py                     # notesStructure.json + NOTES_KEYWORDS
├── parserMapper.py                    # parserMappings/*.json 통합
└── scanner.py                         # 전종목 notes 구조 스캔

core/data/                             # 매핑 데이터 (JSON)
├── accountMappings.json               # 계정 매핑 (34K)
├── notesStructure.json                # notes 항목 구조 + keywords
└── parserMappings/                    # 파서 매핑
    ├── affiliate.json                 # 관계기업 (91항목)
    ├── costByNature.json              # 비용 분류 (46항목)
    └── sections.json                  # sections topic (24항목)

providers/dart/docs/finance/notesDetail/  # 파서 (L1)
├── pipeline.py                        # 데이터 로드 + 섹션 추출
└── tableBuilder.py                    # notesMapper 기반 테이블 빌드
```

## 6개 매퍼

| 매퍼 | 데이터 소스 | 항목 수 | 역할 |
|------|-----------|:---:|------|
| account | accountMappings.json | 34K | 한국어 계정명 ↔ snakeId |
| topic | topicGraph.py TOPIC_KEYWORDS | 33 | 공시 topic → 한국어 키워드 |
| alias | labels.py SNAKEID_ALIASES | 61 | DART↔EDGAR snakeId 정규화 |
| flow | flow.py _EVENT_ACCOUNTS | 14 | 이벤트성 계정 분류 |
| notes | notesStructure.json | 2,640 | notes 항목 유형/외화/카테고리 (2,877종목 학습) |
| parser | parserMappings/*.json | 160+ | 파서 매핑 (affiliate/cost/sections) |

## 공통 유틸 (common.py)

모든 파서/매퍼가 공유하는 함수. 단일 정의.

```python
from dartlab.core.mappers.common import normalizeName, isCurrentPeriod, pickValue

normalizeName("기 초")      # → "기초" (한글 사이 공백 제거)
isCurrentPeriod("당기말")    # → True (전기/전반기는 False)
pickValue(["USD 1K", "1,234"])  # → "1,234" (원화 우선)
```

## AI 학습 설계

### 데이터 구조

모든 매핑 JSON은 AI가 읽고 학습할 수 있는 구조:

```json
{
  "_metadata": {"description": "...", "source": "..."},
  "movement": {"기초": "opening", ...},
  "profile": {"지분율": "ownership", ...}
}
```

- `_metadata.description`: AI가 이 매핑의 목적을 이해
- key → value: 한국어 → 영문 canonical (일관된 패턴)
- category/type 분류: AI가 새 항목을 자동 분류하는 학습 데이터

### Scanner → AI 학습 파이프라인

```
1. Scanner: 전종목 스캔 → 항목 구조 패턴 추출
2. notesStructure.json: 항목별 type/category/frequency 갱신
3. AI: JSON 데이터를 학습하여 새 항목 자동 분류
4. Curator: AI 분류 결과를 JSON에 반영 (수동 검증 후)
```

### AI가 소비하는 매퍼 데이터

| 매퍼 | AI 학습 용도 |
|------|------------|
| account | 계정명 ↔ snakeId 번역 학습 |
| notes | 항목 유형 분류 (amount/rate/text) 학습 |
| parser | 파서 매핑 패턴 학습 (열 이름 정규화) |
| alias | snakeId 정규화 규칙 학습 |

## 매퍼 추가 절차

1. `core/data/` 에 JSON 생성 (기존 코드에서 인라인 데이터 추출)
2. `core/mappers/` 에 매퍼 클래스 생성 (BaseMapper 구현)
3. `__init__.py` getEngine()에 등록
4. 기존 코드에서 인라인 데이터 삭제 → JSON 로드로 교체
5. `tests/test_mappers.py` 에 테스트 추가
6. ops/mappers.md 갱신

## 관련 코드

| 경로 | 역할 |
|------|------|
| `src/dartlab/core/mappers/` | 매퍼 엔진 (11파일) |
| `src/dartlab/core/data/` | 매핑 데이터 JSON |
| `src/dartlab/core/docs/topicGraph.py` | TOPIC_KEYWORDS 원본 |
| `src/dartlab/core/finance/labels.py` | SNAKEID_ALIASES, accountMappings 원본 |
| `src/dartlab/core/finance/flow.py` | _EVENT_ACCOUNTS 원본 |
| `tests/test_mappers.py` | 45개 unit 테스트 |

## 학습 현황

| 항목 | 값 |
|------|------|
| 스캔 종목 | 2,877 |
| 학습 항목 | 2,640 (frequency ≥ 0.5% 정제) |
| 범용 항목 (>50%) | 8 |
| 업종 특화 (10-50%) | 218 |
| 업종 공통 (0.5-10%) | 2,410 |
| aliases | 12 (수동 시드 + Scanner 자동 탐지) |
| 전수조사 | 208호출, FAIL 0 |
