---
id: engines.panel
title: Panel (공시 수평화)
kind: curated
scope: builtin
status: observed
category: engines
purpose: Panel 은 DART 공시 본문(재무제표·주석·서술)을 정부 표준 XBRL 분류(canonicalKey, ACLASS scope-strip) 뼈대 위에서 항목 × 기간 wide pl.DataFrame 으로 수평화하는 엔진. Panel(code)/c.panel 을 잡는 순간 큰 분기별 시계열 DataFrame 이 되고(그 자체가 pl.DataFrame subclass), panel("섹션명") 으로 행 검색. 사전빌드 artifact 를 read (콜드 <1s, 태그 무손실). 트리거 — '공시 수평화', 'panel', '재무제표 다기간', 'canonicalKey', 'disclosureKey'.
whenToUse:
  - panel
  - 공시 수평화
  - 재무제표 다기간 정렬
  - 주석 다기간
  - canonicalKey
  - disclosureKey
  - 항목 × 기간 wide
  - 회사내 수평화
inputs:
  - 종목코드 (KR 6자리)
  - 섹션 검색 key — canonicalKey(NT_D826380/BS) 또는 한글 섹션명 substring(재고) 또는 강한 소스 topic(IS/dividend)
  - period 목록 (선택, YYYYQn)
  - tag (선택, 기본 plain / True 면 원본 XML)
outputs:
  - 항목 × period 수평화 wide (pl.DataFrame, Panel subclass)
  - 섹션 검색 행 (panel(key))
  - 강한 소스(finance/report) 주입 결과 (c.panel("IS") = c.show("IS"))
knowledgeRefs:
  - start.dartlabSkillOs
  - engines.company
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
  - 한 회사 공시 항목의 다기간 가로 정렬 wide
  - 섹션명/canonicalKey 행 검색
  - 강한 소스(재무제표/정형공시)는 finance/report 주입
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
  - canonicalKey/섹션명을 추측 (Panel(code) wide 를 먼저 보고 행 식별 컬럼 확인 안 함)
  - tag=False(기본, plain)를 raw XML 로 가정 (원본 태그는 tag=True)
  - 연결/별도(scope) 무시하고 BS_C↔BS_S 병합으로 착시
  - c.panel("IS") 를 raw 공시로 가정 (강한 소스는 finance 주입 — source="raw" 로 raw 강제)
examples:
  - 005930 잡는 순간 wide (Panel("005930") 또는 c.panel)
  - 재고자산 주석 다기간 행 검색 (c.panel("재고"))
  - 원본 XML 보존 행 (c.panel("재고", tag=True))
  - 재무제표는 finance 주입 (c.panel("IS") = c.show("IS"))
procedure:
  - 진입은 `from dartlab.providers.dart.panel import Panel` 또는 `Company(code).panel`.
  - `Panel(code)` / `c.panel` 자체가 wide pl.DataFrame — shape/filter/columns 등 polars 연산 그대로.
  - 섹션 검색은 `panel("재고")`(한글) 또는 `panel("NT_D826380")`(canonicalKey). 원본 태그는 `tag=True`.
  - 강한 소스(BS/IS/CF/ratios/dividend 등)는 facade `c.panel("IS")` 가 finance/report 주입(c.show 위임). raw 공시 강제는 `source="raw"`.
  - 빌드는 운영자/CI — 로컬 zip `python -m dartlab.providers.dart.panel.build` 또는 online `.github/scripts/sync/onlinePanel.py`.
linkedSkills:
  - engines.company
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

`panel` 은 DART 공시 본문을 **정부 표준 XBRL 분류(canonicalKey) 뼈대 위에서 항목(행) × 기간(열)
wide 로 수평화**하는 엔진이다. 양식(era)·회사마다 흔들리는 ACLASS·제목을 기간 간 정렬 가능한
형태로 고정한다. `Panel(code)` / `c.panel` 을 잡는 순간 그 회사의 큰 분기별 시계열 wide
`pl.DataFrame` 이 된다 (Panel 은 `pl.DataFrame` subclass).

핵심 설계:

- **정렬키 = native canonicalKey** — `disclosureKey` 는 정부 발행 ACLASS(DART XBRL 표준 Link
  Role)를 scope-strip 한 순수함수 산출(`mapper.canonicalKey`, BS_C→BS / NT_C_D826380→NT_D826380).
  손매핑·학습 0 ([[feedback_xml_native_truth]]).
- **단일 패키지 자급** — schema·mapper·build·read 가 `providers/dart/panel/` 한 곳. 수집(OpenDART
  API)은 이미 `providers/dart/openapi` 라 build 도 providers 가 자급 (gather panel 폐기).
- **BUILD/READ import 격리** — build(`build/`, lxml/zipfile)는 무거운 zip→14col 생산, read 표면
  (`panel.py`·`_read.py`)은 build 를 import 안 함 → `import providers.dart.panel.panel` 시 lxml 0
  (콜드 <1s, R2).
- **태그 무손실** — contentRaw = 원본 XML 그대로 저장. 기본 read 는 plain(태그 strip), `tag=True`
  면 원본 XML (collapse 단계 1회 strip, raw wide 2중 materialize 회피).

```
DART zip / DART API ──build(providers/dart/panel/build)─→ {code}/{period}.parquet (14-col)
                                                              │
                                                              ↓
                          Panel(code) / c.panel  (read, 콜드 <1s, pl.DataFrame subclass)
```

## 공개 호출 방식

```python
from dartlab.providers.dart.panel import Panel

# 1. 잡는 순간 wide — Panel 은 pl.DataFrame subclass
p = Panel("005930")                  # 항목 × period wide (행=공시항목, 열=period)
p.shape                              # (항목수, period수) — polars 연산 그대로
p.columns                           # chapter · sectionLeaf · blockLeaf · disclosureKey · scope · 2025Q4 · ...
p.filter(...)                       # filter/select 등 그대로

# 2. 섹션 행 검색 — callable (board/show verb 없음)
inv = p("재고")                      # 한글 섹션명 substring 매칭 행
invc = p("NT_D826380")              # canonicalKey exact
raw = p("재고", tag=True)           # 원본 XML 보존 (기본은 plain)

# 3. 대형 종목 메모리 핸들 — period 파일 prune
p2 = Panel("005930", periods=["2025Q4", "2026Q1"])
```

```python
import dartlab

c = dartlab.Company("005930")
c.panel                              # 동일 — 잡는 순간 wide pl.DataFrame
c.panel("재고")                      # 섹션 행 (raw 공시)
c.panel("IS")                        # 강한 소스 — finance 주입 (= c.show("IS"), 더 강한 정규화 숫자)
c.panel("dividend")                  # 강한 소스 — report 주입 (정형 공시)
c.panel("IS", source="raw")          # raw 공시 강제 (오리지널)
```

```bash
# 빌드 트랙 A — 로컬 zip 소비 (network 0)
python -X utf8 -m dartlab.providers.dart.panel.build --codes 005930,000660
python .github/scripts/sync/buildPanel.py --changed                       # sync 증분(로컬 zip)

# 빌드 트랙 B — online 1패스 (DART API → 메모리 → parquet, 디스크 zip 0)
python .github/scripts/sync/onlinePanel.py --changed                      # docs.parquet rcept fetch
```

## 호출 동작

`Panel(code, *, marketNs="kr", periods=None, tag=False)` — 한 회사의 panel artifact 를 read 해
wide `pl.DataFrame` 으로 materialize. 상태 없음(누적 0) — multi-company 루프는 매 회사 새 Panel
(Polars Rust heap OOM 가드). `c.panel` 매 접근도 새 인스턴스.

- `Panel(code)` 자체 = wide DataFrame. 행 identity = (chapter, sectionLeaf, blockLeaf,
  disclosureKey, scope), 열 = period, cell = 본문(tag=False plain / tag=True raw XML).
- `panel(key, *, source="auto", tag=None, periods=None)` — callable 섹션 검색.
  - `source="auto"`(기본): 강한 소스(BS/IS/CF/ratios/inventory/dividend…)는 facade 주입 `c.show`
    위임(finance/report 가 raw 공시보다 강함). canonicalKey/한글 섹션명은 raw 공시 행 검색.
  - `source="raw"`: 강제 raw 공시 행. `source="finance"/"report"`: 강제 주입.
  - `tag`: None 면 인스턴스 tag 상속, 명시 시 그 tag 로 재read (raw 검색만).
  - finance/report 주입은 **facade(`c.panel`) 전용** — standalone `Panel(code)` 는 주입 없어 항상
    raw 검색 (panel 패키지는 finance 를 import 안 함, cycle 0).

artifact 부재·빈 결과는 빈 DataFrame / None (예외 없음). disclosureKey(=canonicalKey)는 build 가
부착하며, 옛 artifact(전부 null)만 read 시점 canonicalKey fallback resolve.

## 대표 반환 형태

```text
Panel("005930")     # 그 자체가 wide pl.DataFrame
→ chapter · sectionLeaf · blockLeaf · disclosureKey · scope · 2025Q4 · 2025Q3 · ...
  (행 = 공시 항목, cell = 본문 plain — tag=True 면 원본 XML)
```

```text
Panel("005930")("재고")     # 또는 ("NT_D826380")
→ pl.DataFrame  (매칭 행만, 연결 NT_D826380 + 별도 NT_D826385 = scope 로 분리된 2 행)
```

```text
c.panel("IS")     # 강한 소스 — finance 주입 (c.show("IS") 와 동일)
→ pl.DataFrame  (snakeId · 항목 · 2026Q1 · 2025Q4 · ... — XBRL 정규화 숫자)
```

14-col artifact schema (PANEL_SCHEMA): chapter · sectionLeaf · blockLeaf · xbrlClass ·
xbrlMatched · xbrlMatchScore · atocId · aassocnote · blockOrder · contentRaw · period · corp ·
rceptNo · disclosureKey(=canonicalKey). `scope`(연결/별도)는 read 파생 (저장 안 함).

## evidence 기준

panel 답변은 `disclosureKey`(=canonicalKey) · `period` · `rceptNo` · `corp` 를 남긴다. 공시
본문(contentRaw)은 외부 untrusted 데이터 — ai 층이 `[EXTERNAL CONTENT START]` 마커로 감싼다.
canonicalKey/섹션명은 `Panel(code)` wide 의 행 식별 컬럼으로 확인한 실재 값만 인용(추측 금지).

## 기본 실행 순서

1. `Panel(code)` / `c.panel` 으로 wide 확보 — 그 자체가 DataFrame (shape/columns 확인).
2. 항목 분석은 `panel("재고")`(섹션명) 또는 `panel("NT_D826380")`(canonicalKey). 원본 태그는 `tag=True`.
3. 재무제표·정형 공시는 facade `c.panel("IS")` (finance/report 주입) — raw 강제는 `source="raw"`.
4. 빌드는 운영자/CI — read 는 사전빌드 artifact 만 소비.

## 기본 검증

PANEL_SCHEMA(14-col, `providers/dart/panel/schema.py`)·canonicalKey 규칙(`mapper.py`)·period
(`_period.py`)가 바뀌면 본 skill 갱신. canonicalKey scope-strip 은 `tests/providers/dart/panel/
test_mapper.py`, build 무손실은 `tests/panel/test_build_lossless.py`, disk≡online 동등성은
`tests/providers/dart/panel/build/test_online_stream.py`, Panel subclass·callable·tag 는
`tests/providers/dart/panel/test_panel.py` + `tests/panel/test_panel_intra.py`(requires_data),
자급 격리·import 분리(R1·R2)는 `tests/architecture/test_panel_layer.py` ·
`test_panel_no_network_lxml.py` 가 강제. 실패는 None / 빈 DataFrame (예외 없음).

> Skill OS JSON index(`src/dartlab/skills/*.json`)는 **운영자 수동 동기화** — 본 spec 변경 시
> 자동 생성 금지(CLAUDE.md "자동 빌드 도구 금지").
