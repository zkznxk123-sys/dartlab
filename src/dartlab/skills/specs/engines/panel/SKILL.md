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
- **행 순서·계층 = 정부 서식 뼈대(spine)** — `blockOrder` 는 보고서마다 0 리셋이라 read 가
  재발견 못 하고 `canonicalKey` 는 정렬 가능 번호가 아니다 → 정부 문서 표시순서·트리를 빌드 시 1회
  명시 spine 으로 굽는다. `build.buildSpine` 이 **기준 종목 한 회사**(정부 표준 서식이라 reference
  하나로 충분) 최신 사업보고서(Q4)를 raw 파싱 → `rowIdentity`(keyed=disclosureKey /
  narrative=NARR::chapter␟section)별 문서순서·parentKey → `spine/spineData.py`(생성 .py, git-diff
  추적) 생성. `read.readWide` 가 `SPINE` dict 로 `(chapterRank 우선, spineOrder 차선)` 정렬 →
  표지→I→II→III→재무→주석 정부순서(챕터 단위 그룹핑, '(첨부)' 본문 중간 삽입도 자기 챕터로 모음).
  회사간 비교는 `disclosureKey`(같은 항목 같은 키)로 — 회사간 순서 표준화/합의는 panel 책임 밖(scan
  엔진의 cross-market 일). `parentKey` 트리는 Phase 2 셀 세분화 토대.
- **단일 패키지 자급** — schema·mapper·spine·build·read 가 `providers/dart/panel/` 한 곳. 수집
  (OpenDART API)은 이미 `providers/dart/openapi` 라 build 도 providers 가 자급 (gather panel 폐기).
- **BUILD/READ import 격리** — build(`build/`, lxml/zipfile)는 무거운 zip→14col·spine 생산, read 표면
  (`panel.py`·`read.py`·`spine/`)은 build 를 import 안 함 → read 표면 lxml 0 (콜드 <1s, R2).
  KR 정규화는 native canonicalKey 단독(bridge lookup 농장 0) — US cross-market 정규화는 후속(별도
  설계, `scan.sectionsNew` bridge 재사용).
- **태그 무손실** — contentRaw = 원본 XML 그대로 저장. 기본 read 는 plain(태그 strip), `tag=True`
  면 원본 XML (collapse 단계 1회 strip, raw wide 2중 materialize 회피).

### parquet 저장 기준 — "불변 원본 + 순수 규칙 산물"만 굽는다 (SSOT)

panel artifact(`{code}/{period}.parquet`)에 **굽는 것**과 **read 가 매번 계산하는 것**을 가르는 단일
기준: **그 값이 "언제 어떻게 바뀔지 모르는가"**. 바뀔 수 있으면 굽지 않는다.

| 무엇 | 굽나 | 왜 |
|---|---|---|
| `contentRaw` (원본 XML) | ✅ build | **불변 원본** — etree.tostring 그대로(R4). 원본이라 영원히 안 변함 |
| `disclosureKey`(=canonicalKey)·`xbrlClass`·`blockOrder`·`atocId` 등 | ✅ build | walker 가 뽑은 원본 속성 + `canonicalKey` **순수함수 규칙** (read fallback 보유 → 규칙 변경 시 재빌드 전에도 동작) |
| `scope` (연결/별도) | ❌ read 파생 | `scopeExpr(xbrlClass)` 판정 — **규칙이 바뀔 수 있음** → 안 구움, read 가 계산 |
| 행 순서·계층 (spine) | ❌ read 정렬 | 전역 spine `(chapterRank, spineOrder)` — corpus 확대·정부 양식 변경 시 재산정 → artifact 불변, spineData.py 만 재생성 |
| plain (태그 strip) | ❌ read strip | raw 의 파생 표현 — strip 규칙 변경 가능 + 같은 정보 이중저장([[feedback_no_content_plain_precompute]]) → 안 구움 |

**원칙**: 파생물·정렬·표현·판정은 **굽지(build) 도, 즉시 다 계산(eager)도 강제하지 않는다.** 굽으면
규칙 변경 시 전 종목 재빌드 폭탄 + 이중저장 회귀. → scope·spine·plain 이 전부 read 시점인 이유.
[[feedback_panel_wide_identity]] (wide 정체성 불가침) 와 한 사상.

### 콜드스타트 — strip 위치(채택) + lazy(후속), build 굽기·wide 교체 금지

read plain 콜드 비용의 90%가 173MB raw→plain 정규식 strip (정규식 chain 자체는 floor — per-row·
대체정규식 전부 더 느리거나 틀림, 측정 확인). I/O 72ms·anchor·pivot·orderBySpine 는 ≤10ms.
strip 을 **빠르게**가 아니라 **언제·어디서 하나**로 푼다 — 세 제약 충족: (1) wide 형태·내용 불가침
([[feedback_panel_wide_identity]]), (2) build 굽기 금지(위 저장 기준, R4), (3) plain 결과 불변.

- **채택(strip 위치 이동)**: strip 을 collapse(long fragment) 단계가 아니라 **pivot·spine 정렬 후
  wide period 셀**에 1회. 큰 셀 1회 정규식이 작은 조각 수천개보다 빠름 → **콜드 ~1s→0.35s (2.8x)**,
  byte-identical(10481 셀 불일치 0)·plain 기본·tag 옵션·wide 정체성 0 변경. `read._stripExpr` 재사용
  Expr. 이미 적용.
- **후속(lazy, 미착수)**: strip 을 "잡는 순간"이 아니라 "표시/특정 셀 접근" 시점으로 더 미루면 콜드
  ~0.16s 가능 — 단 잡는 순간 셀이 raw(태그 포함)가 되어 plain 직관성과 충돌. `Panel(pl.DataFrame)`
  eager subclass 와 lazy 경계 정합도 미해결. 기본 plain 직관성 > 0.16s 라 보류, 별도 검토.
- **금지**: build plain 사전계산(R4 위반) · wide 를 metadata-only/long 으로 교체(정체성 파괴).

```
DART zip / DART API ──build(providers/dart/panel/build)─→ {code}/{period}.parquet (14-col)
                                                              │
                                                              ↓
                          Panel(code) / c.panel  (read, plain 콜드 ~0.35s, pl.DataFrame subclass)
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

# 정부 서식 뼈대(spine) 생성 — 기준 종목 최신 사업보고서 문서순서·트리 → spine/spineData.py (git 추적)
python -X utf8 -m dartlab.providers.dart.panel.build --spine --codes 005930,000660
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
rceptNo · disclosureKey(=canonicalKey). `scope`(연결/별도)는 read 파생 (저장 안 함). 행 순서·계층은
artifact 가 아니라 정부 서식 spine(`spine/spineData.py`, 기준 종목 reference)이 결정 — schema 불변.

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

PANEL_SCHEMA(14-col, `providers/dart/panel/schema.py`)·canonicalKey/rowIdentity 규칙(`mapper.py`)·
period(`period.py`)·전역 뼈대(`spine/`, `build/spineBuilder.py`)가 바뀌면 본 skill 갱신.
canonicalKey scope-strip·rowIdentity 는 `tests/providers/dart/panel/test_mapper.py`, spine 정렬·
무결성은 `test_read.py`(orderBySpine)·`test_spine.py`·`build/test_spineBuilder.py`, build 무손실은
`tests/panel/test_build_lossless.py`, Panel subclass·callable·tag 는 `test_panel.py` +
`tests/panel/test_panel_intra.py`(requires_data), 자급 격리·import 분리(R1·R2)는
`tests/architecture/test_panel_layer.py` · `test_panel_no_network_lxml.py` 가 강제. 실패는 None /
빈 DataFrame (예외 없음).

> Skill OS JSON index(`src/dartlab/skills/*.json`)는 **운영자 수동 동기화** — 본 spec 변경 시
> 자동 생성 금지(CLAUDE.md "자동 빌드 도구 금지").
