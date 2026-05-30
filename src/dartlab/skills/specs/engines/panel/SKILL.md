---
id: engines.panel
title: Panel (공시 수평화 보드)
kind: curated
scope: builtin
status: observed
category: engines
purpose: Panel 은 DART 공시 본문(재무제표·주석·서술)을 항목 × 기간 2D 보드로 수평 정렬하는 엔진 — zip 사전빌드 artifact 를 lazy read 해 콜드 <1s, 태그 무손실 보존, disclosureKey 로 회사내·회사간·세계마켓간 3겹 정규화. 트리거 — '공시 수평화', 'panel', '재무제표 다기간', '공시 항목 회사 비교', 'disclosureKey'.
whenToUse:
  - panel
  - 공시 수평화
  - 재무제표 다기간 정렬
  - 주석 다기간
  - 공시 항목 회사간 비교
  - disclosureKey
  - 항목 × 기간 보드
  - 회사내 수평화
  - 회사간 수평화
inputs:
  - 종목코드 (KR 6자리)
  - disclosureKey (universal, 예 inventoryDisclosure)
  - period 목록 (선택, YYYYQn)
outputs:
  - 항목 × period 수평화 보드 (pl.DataFrame)
  - presence board (contentRaw 제외, <1MB)
  - 회사간/세계마켓간 정렬 보드 (corp × period)
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.company
  - engines.gather
  - engines.data
sourceRefs:
  - dartlab://skills/engines.panel
requiredEvidence:
  - disclosureKey
  - period
  - rceptNo
  - corp
  - sourceRef
expectedOutputs:
  - 한 회사 공시 항목의 다기간 가로 정렬
  - 동일 disclosureKey 의 회사간 비교 보드
  - presence board (어떤 disclosure 가 어느 기간에 있는지)
runtimeCompatibility:
  server:
    status: supported
  localPython:
    status: supported
  mcp:
    status: supported
  webAi:
    status: limited
  pyodide:
    status: limited
    notes: 로컬 panel artifact 필요 — HF fetch 또는 사전 다운로드 후 read.
failureModes:
  - disclosureKey 를 추측 (board 로 가용 키 확인 안 함)
  - board(presence)와 wide(contentRaw 포함)를 혼동 → 대량 본문 로드
  - 연결/별도(scope) 무시하고 BS_C↔BS_S 병합으로 착시
  - contentRaw 를 strip 된 plain text 로 가정 (raw XML 태그 보존이 SSOT)
forbidden:
  - contentRaw 태그 strip 후 사전 저장 금지 — build 무가공, strip 은 runtime on-demand (R4).
  - board(presence)에 contentRaw 노출 금지 — <1MB 콜드 read 회귀.
  - disclosureKey 추측 금지 — board 로 가용 키 확인 후 show.
  - 회사간 대량 정렬 시 전 회사 풀로드 금지 — _index.parquet 로 locator 선별.
examples:
  - 005930 재고자산 주석 다기간 수평화
  - 삼성전자 공시 presence board 확인
  - inventoryDisclosure 를 여러 회사에 걸쳐 가로 비교
  - 한 회사의 사용 가능 기간 목록 조회
procedure:
  - 진입은 `from dartlab.providers.dart.panel import Panel`; `Panel(code).board()` 로 presence 확인.
  - 특정 항목은 `Panel(code).show(disclosureKey)` — disclosureKey 는 board 로 확인.
  - 회사간은 `crossCompany(disclosureKey=..., codes=None)` — _index 자동 발견.
  - 세계마켓간은 `crossMarket({"kr": [...], "us": [...]}, disclosureKey)` (US 는 후속).
  - 빌드는 운영자/CI — `python -m dartlab.gather.dart.panel.build` 또는 `.github/scripts/sync/buildPanel.py`.
linkedSkills:
  - engines.company
  - engines.gather
  - engines.data
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-30'
testUniverse:
  market: KR
  stockCodes:
    - "005930"
---

## 엔진 역할

`panel` 은 DART 공시 본문을 **항목(행) × 기간(열) 2D 보드로 수평 정렬**하는 엔진이다.
양식(era)·회사마다 흔들리는 ACLASS·제목을 기간·회사·시장 간 정렬 가능한 형태로 고정한다.
`docs.parquet`(현역 문서 데이터)과 무관한 **별도 artifact·별도 함수** — zip 에서 직접
사전빌드한다.

핵심 설계:

- **BUILD/READ 물리 분리** — zip→14col 빌드(lxml/zipfile)는 `gather`, read(scan_parquet)는
  `providers`. read 층은 network·lxml 0 (콜드 <1s).
- **태그 무손실** — contentRaw = 원본 XML 그대로, build 에서 태그 strip 0. strip 은 runtime
  on-demand.
- **3겹 정규화** — 회사내(다기간 한 행) · 회사간(동일 disclosureKey) · 세계마켓간(DART↔EDGAR,
  동일 disclosureKey). schema·disclosureKey 는 market-neutral (현재 DART, US 는 후속).

```
DART zip ──build(gather)─→ data/dart/panel/{code}/{period}.parquet (14-col) + _index.parquet
                                          │
                                          ↓
                          Panel / crossCompany / crossMarket (providers read, 콜드 <1s)
```

## 공개 호출 방식

```python
from dartlab.providers.dart.panel import Panel, crossCompany, crossMarket

# 1. presence board — 어떤 disclosure 가 어느 기간에 있는지 (contentRaw 제외, 콜드 <1s)
with Panel("005930") as p:
    board = p.board()                       # 항목 × period presence
    periods = p.periods()                   # ['2015Q4', ..., '2026Q1']

    # 2. 한 disclosure 다기간 수평화 (태그 raw 보존)
    inv = p.show("inventoryDisclosure")     # disclosureKey 행만, period 가로 정렬

    # 3. 전체 회사내 수평화 / raw long
    wide = p.wide()                         # 전 항목 × period (cell = contentRaw)
    long = p.long()                         # 수평화 전 14-col long

# 4. 회사간 — 동일 disclosureKey 를 여러 회사에 가로 정렬 (_index 자동 발견)
cc = crossCompany(disclosureKey="inventoryDisclosure")          # codes=None → 전종목 자동
cc2 = crossCompany(["005930", "000660"], "inventoryDisclosure")  # 명시 codes

# 5. 세계마켓간 — DART↔EDGAR 동일 disclosureKey (US panel 은 후속)
cm = crossMarket({"kr": ["005930"], "us": ["AAPL"]}, "inventoryDisclosure")
```

```bash
# 운영자/CI 빌드 (network 0 — 로컬 zip 소비)
python -X utf8 -m dartlab.gather.dart.panel.build --codes 005930,000660   # baseline
python -X utf8 -m dartlab.gather.dart.panel.build --all                    # 전종목 (~2.6h)
python .github/scripts/sync/buildPanel.py --changed                        # sync 증분
```

## 호출 동작

`Panel(code, marketNs="kr")` — 한 회사의 panel artifact 를 lazy read 하는 facade. 상태
없음(누적 0) — multi-company 루프는 `with Panel(code) as p:` 권장(Polars Rust heap OOM 가드).

- `board(periods=None)` — presence board (cell = blockOrder). contentRaw 제외 → <1MB, 콜드 <1s.
- `show(disclosureKey, periods=None)` — 해당 disclosureKey 행만 period 가로 정렬. 없으면 None.
- `wide(periods=None, valueColumn="contentRaw")` — 전 항목 회사내 수평화.
- `long(periods=None)` — 수평화 전 14-col long (+ disclosureKey).
- `periods()` — 가용 period 목록 (정렬). artifact 없으면 빈 list.

`crossCompany(codes=None, disclosureKey, marketNs="kr", periods=None)` — 같은 disclosureKey 를
회사간 가로 정렬. `codes=None` 이면 slim `_index.parquet` 로 보유 종목 자동 발견(본문 미read).
disclosureKey 빈 값이면 None.

`crossMarket(codesByMarket, disclosureKey, periods=None)` — 시장별 crossCompany 후 결합.
schema·disclosureKey 가 market-neutral 이라 DART↔EDGAR 한 보드 (US panel 빌드는 후속).

artifact 부재·빈 결과는 모두 None (예외 없음). disclosureKey 는 build 가 부착하며, 옛 artifact
(전부 null)만 read 시점 bridge fallback resolve.

## 대표 반환 형태

```text
Panel("005930").board()
→ pl.DataFrame
   chapter · sectionLeaf · blockLeaf · disclosureKey · scope · 2025Q4 · 2025Q3 · ...
   (cell = blockOrder presence, contentRaw 제외)
```

```text
Panel("005930").show("inventoryDisclosure")
→ pl.DataFrame
   chapter · sectionLeaf · blockLeaf · disclosureKey · scope · 2025Q4 · ...
   (cell = contentRaw 원본 XML, 태그 무손실)
```

```text
crossCompany(disclosureKey="inventoryDisclosure")
→ pl.DataFrame
   corp · marketNs · scope · disclosureKey · 2025Q4 · 2025Q3 · ...   (diagonal concat)
```

14-col artifact schema (PANEL_SCHEMA): chapter · sectionLeaf · blockLeaf · xbrlClass ·
xbrlMatched · xbrlMatchScore · atocId · aassocnote · blockOrder · contentRaw · period · corp ·
rceptNo · disclosureKey. `scope`(연결/별도)는 read 파생 (저장 안 함).

## evidence 기준

panel 답변은 `disclosureKey` · `period` · `rceptNo` · `corp` 를 남긴다. 공시 본문(contentRaw)은
외부 untrusted 데이터 — ai 층이 `[EXTERNAL CONTENT START]` 마커로 감싼다. disclosureKey 는
board 로 확인한 실재 키만 인용(추측 금지).

## 기본 실행 순서

1. `Panel(code).board()` 로 presence + 가용 disclosureKey/period 확인.
2. 항목 분석은 `show(disclosureKey)`, 전체는 `wide()`.
3. 회사간은 `crossCompany(disclosureKey=...)` (대량은 _index 자동 발견).
4. 빌드는 운영자/CI — read 는 사전빌드 artifact 만 소비.

## 기본 검증

PANEL_SCHEMA(14-col, `core/panel/schema.py`)·disclosureKey 어휘(bridge)·period(`core/panel/
period.py`)가 바뀌면 본 skill 갱신. build 무손실(태그·char 합 보존)은
`tests/panel/test_build_lossless.py`, 회사내 수평화·콜드 read 는 `tests/panel/test_panel_intra.py`,
계층/물리분리(R1·R2)는 `tests/architecture/test_panel_layer.py` ·
`tests/architecture/test_panel_no_network_lxml.py` 가 강제. 실패는 None / 빈 DataFrame 으로
표현 (예외 없음).
