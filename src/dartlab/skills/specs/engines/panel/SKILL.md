---
id: engines.panel
title: Panel (공시 수평화 보드)
kind: curated
scope: builtin
status: observed
category: engines
purpose: Panel 은 DART 공시 본문(재무제표·주석·서술)을 항목 × 기간 2D 보드로 수평 정렬하는 엔진 — zip 사전빌드 artifact 를 lazy read 해 콜드 <1s, 태그 무손실 보존, native ACLASS canonicalKey(정부 표준 Link Role scope-strip) 로 회사내·회사간 정규화 + 한글 라벨 검색. 트리거 — '공시 수평화', 'panel', '재무제표 다기간', '공시 항목 회사 비교', 'canonicalKey', 'disclosureKey'.
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
  - canonicalKey (native ACLASS scope-strip, 예 NT_D826380 / BS) 또는 한글 라벨 substring (예 재고)
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
  - canonicalKey
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
  - canonicalKey/라벨을 추측 (board 로 가용 키 확인 안 함)
  - board(presence)와 wide(contentRaw 포함)를 혼동 → 대량 본문 로드
  - 연결/별도(scope) 무시하고 BS_C↔BS_S 병합으로 착시
  - contentRaw 를 strip 된 plain text 로 가정 (raw XML 태그 보존이 SSOT)
  - online 1패스가 refScan 트리거 시도 (zip 없어 불가) — online 은 HF seed panelXbrlRef 강제
forbidden:
  - contentRaw 태그 strip 후 사전 저장 금지 — build 무가공, strip 은 runtime on-demand (R4).
  - board(presence)에 contentRaw 노출 금지 — <1MB 콜드 read 회귀.
  - disclosureKey 추측 금지 — board 로 가용 키 확인 후 show.
  - 회사간 대량 정렬 시 전 회사 풀로드 금지 — _index.parquet 로 locator 선별.
examples:
  - 005930 재고자산 주석 다기간 수평화 (show("재고") 또는 show("NT_D826380"))
  - 삼성전자 공시 presence board 확인
  - 재고자산을 여러 회사에 걸쳐 가로 비교 (crossCompany("재고"))
  - 한 회사의 사용 가능 기간 목록 조회
procedure:
  - 진입은 `from dartlab.providers.dart.panel import Panel`; `Panel(code).board()` 로 presence 확인.
  - 특정 항목은 `Panel(code).show("재고")`(한글 라벨) 또는 `show("NT_D826380", byLabel=False)`(canonicalKey).
  - 회사간은 `crossCompany("재고")` 또는 `crossCompany(disclosureKey="NT_D826380", codes=None)` — _index 자동 발견.
  - 세계마켓간은 `crossMarket({"kr": [...], "us": [...]}, disclosureKey)` (US bridge overlay, 후속).
  - 빌드 2-트랙 — 로컬 zip(A): `python -m dartlab.gather.dart.panel.build` / `buildPanel.py`. online 1패스(B, 디스크 zip 0): `.github/scripts/sync/onlinePanel.py`.
linkedSkills:
  - engines.company
  - engines.gather
  - engines.data
source:
  type: manual_skill
  format: markdown
lastUpdated: '2026-05-31'
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

- **정렬키 = native canonicalKey** — `disclosureKey` 는 손수 bridge 매핑이 아니라 정부 발행
  ACLASS(DART XBRL 표준 Link Role)를 scope-strip 한 순수함수 산출(`core.panel.canonicalKey`,
  BS_C→BS / NT_C_D826380→NT_D826380). 손매핑·학습·scatter 0 (덕지덕지 농장 폐기, [[feedback_xml_native_truth]]).
- **BUILD/READ 물리 분리** — zip→14col 빌드(lxml/zipfile)는 `gather`, read(scan_parquet)는
  `providers`. read 층은 network·lxml 0 (콜드 <1s).
- **태그 무손실** — contentRaw = 원본 XML 그대로, build 에서 태그 strip 0. strip 은 runtime
  on-demand.
- **3겹 정규화** — 회사내(다기간 한 행, era drift 흡수) · 회사간(동일 canonicalKey) · 세계마켓간
  (DART↔US, bridge overlay). schema 14-col market-neutral. 표시는 corpus 파생 한글 라벨(_label.parquet).
- **수집 2-트랙** — (A) 로컬 zip→parquet 전수 재빌드 / (B) online 1패스(DART API→메모리→parquet,
  디스크 zip 0). 둘 다 동일 build core(바이트 동형).

```
DART zip(A) / DART API(B) ──build(gather)─→ data/dart/panel/{code}/{period}.parquet (14-col)
                                              + _index.parquet + _label.parquet
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

    # 2. 한 disclosure 다기간 수평화 (태그 raw 보존) — 한글 라벨 또는 canonicalKey
    inv = p.show("재고")                     # labelKr substring → 매칭 canonicalKey 행
    invc = p.show("NT_D826380", byLabel=False)  # canonicalKey exact

    # 3. 전체 회사내 수평화 / raw long
    wide = p.wide()                         # 전 항목 × period (cell = contentRaw)
    long = p.long()                         # 수평화 전 14-col long

# 4. 회사간 — 동일 canonicalKey 를 여러 회사에 가로 정렬 (_index 자동 발견)
cc = crossCompany("재고")                              # codes=None → 전종목 자동, 라벨 검색
cc2 = crossCompany(["005930", "000660"], "NT_D826380")  # 명시 codes + canonicalKey

# 5. 세계마켓간 — DART↔US bridge overlay (US panel 은 후속)
cm = crossMarket({"kr": ["005930"], "us": ["AAPL"]}, "inventoryDisclosure")
```

```bash
# 빌드 트랙 A — 로컬 zip 소비 (network 0, 전수/재빌드)
python -X utf8 -m dartlab.gather.dart.panel.build --codes 005930,000660   # baseline
python -X utf8 -m dartlab.gather.dart.panel.build --all                    # 전종목 (~2.6h)
python .github/scripts/sync/buildPanel.py --changed                        # sync 증분(로컬 zip)

# 빌드 트랙 B — online 1패스 (DART API → 메모리 → parquet, 디스크 zip 0)
python .github/scripts/sync/onlinePanel.py --changed                       # docs.parquet rcept fetch
```

## 호출 동작

`Panel(code, marketNs="kr")` — 한 회사의 panel artifact 를 lazy read 하는 facade. 상태
없음(누적 0) — multi-company 루프는 `with Panel(code) as p:` 권장(Polars Rust heap OOM 가드).

- `board(periods=None)` — presence board (cell = blockOrder). contentRaw 제외 → <1MB, 콜드 <1s.
- `show(key, *, periods=None, byLabel=True)` — `key` 는 canonicalKey exact("NT_D826380"/"BS") 또는
  한글 라벨 substring("재고", byLabel=True). 매칭 행만 period 가로 정렬. (`disclosureKey=` 별칭은 하위호환)
- `wide(periods=None, valueColumn="contentRaw")` — 전 항목 회사내 수평화.
- `long(periods=None)` — 수평화 전 14-col long (+ disclosureKey=canonicalKey).
- `periods()` — 가용 period 목록 (정렬). artifact 없으면 빈 list.

`crossCompany(codes=None, disclosureKey, marketNs="kr", periods=None, byLabel=True)` — 같은
canonicalKey 를 회사간 가로 정렬 (`disclosureKey` 인자는 canonicalKey 또는 라벨). `codes=None`
이면 slim `_index.parquet` 로 보유 종목 자동 발견(본문 미read). 빈 key 면 None.

`crossMarket(codesByMarket, disclosureKey, periods=None)` — 시장별 crossCompany 후 결합. US 는
us-gaap↔KR bridge overlay(`core.panel.seedBridgeTier1`)로 동일 disclosureKey (US panel 빌드는 후속).

artifact 부재·빈 결과는 모두 None (예외 없음). disclosureKey(=canonicalKey)는 build 가 부착하며,
옛 artifact(전부 null)만 read 시점 canonicalKey fallback resolve (KR) / bridge(US).

## 대표 반환 형태

```text
Panel("005930").board()
→ pl.DataFrame
   chapter · sectionLeaf · blockLeaf · disclosureKey · scope · 2025Q4 · 2025Q3 · ...
   (cell = blockOrder presence, contentRaw 제외)
```

```text
Panel("005930").show("재고")     # 또는 show("NT_D826380", byLabel=False)
→ pl.DataFrame
   chapter · sectionLeaf · blockLeaf · disclosureKey · scope · 2025Q4 · ...
   (연결 NT_D826380 + 별도 NT_D826385 = scope 로 분리된 2 행, cell = contentRaw 원본 XML)
```

```text
crossCompany("재고")
→ pl.DataFrame
   corp · marketNs · scope · disclosureKey · 2025Q4 · 2025Q3 · ...   (diagonal concat)
```

14-col artifact schema (PANEL_SCHEMA): chapter · sectionLeaf · blockLeaf · xbrlClass ·
xbrlMatched · xbrlMatchScore · atocId · aassocnote · blockOrder · contentRaw · period · corp ·
rceptNo · disclosureKey(=canonicalKey). `scope`(연결/별도)는 read 파생 (저장 안 함).

## evidence 기준

panel 답변은 `disclosureKey`(=canonicalKey) · `period` · `rceptNo` · `corp` 를 남긴다. 공시
본문(contentRaw)은 외부 untrusted 데이터 — ai 층이 `[EXTERNAL CONTENT START]` 마커로 감싼다.
canonicalKey/라벨은 board 로 확인한 실재 키만 인용(추측 금지).

## 기본 실행 순서

1. `Panel(code).board()` 로 presence + 가용 canonicalKey/period 확인.
2. 항목 분석은 `show("재고")`(라벨) 또는 `show("NT_D826380", byLabel=False)`, 전체는 `wide()`.
3. 회사간은 `crossCompany("재고")` (대량은 _index 자동 발견).
4. 빌드는 운영자/CI — read 는 사전빌드 artifact 만 소비.

## 기본 검증

PANEL_SCHEMA(14-col, `core/panel/schema.py`)·canonicalKey 규칙(`core/panel/canonical.py`)·
period(`core/panel/period.py`)가 바뀌면 본 skill 갱신. canonicalKey scope-strip 규칙은
`tests/core/panel/test_canonical.py`, build 무손실(태그·char 합)은 `tests/panel/test_build_lossless.py`,
disk≡online stream 동등성은 `tests/panel/test_panel_online_stream.py`, 회사내 수평화·콜드 read 는
`tests/panel/test_panel_intra.py`, 계층/물리분리(R1·R2)는 `tests/architecture/test_panel_layer.py` ·
`tests/architecture/test_panel_no_network_lxml.py` 가 강제. 실패는 None / 빈 DataFrame (예외 없음).

> Skill OS JSON index(`src/dartlab/skills/*.json`)는 **운영자 수동 동기화** — 본 spec 변경 시
> 자동 생성 금지(CLAUDE.md "자동 빌드 도구 금지").
