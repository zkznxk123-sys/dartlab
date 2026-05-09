<div align="center">

<br>

<img alt="DartLab" src=".github/assets/logo.png" width="180">

<h3>DartLab</h3>

<p><b>종목코드 하나. 기업의 전체 이야기.</b></p>
<p>Korean DART + US SEC EDGAR 공시를 한 줄의 Python 으로 읽고 비교한다.</p>

<p>
<a href="https://pypi.org/project/dartlab/"><img src="https://img.shields.io/pypi/v/dartlab?style=for-the-badge&color=ea4647&labelColor=050811&logo=pypi&logoColor=white" alt="PyPI"></a>
<a href="https://pypi.org/project/dartlab/"><img src="https://img.shields.io/pypi/pyversions/dartlab?style=for-the-badge&color=c83232&labelColor=050811&logo=python&logoColor=white" alt="Python"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-94a3b8?style=for-the-badge&labelColor=050811" alt="License"></a>
<a href="https://github.com/eddmpython/dartlab/actions/workflows/ci-fast.yml"><img src="https://img.shields.io/github/actions/workflow/status/eddmpython/dartlab/ci-fast.yml?branch=master&style=for-the-badge&labelColor=050811&logo=github&logoColor=white&label=CI" alt="CI"></a>
<a href="https://codecov.io/gh/eddmpython/dartlab"><img src="https://img.shields.io/codecov/c/github/eddmpython/dartlab?style=for-the-badge&labelColor=050811&logo=codecov&logoColor=white&label=Coverage" alt="Coverage"></a>
<a href="https://eddmpython.github.io/dartlab/"><img src="https://img.shields.io/badge/Docs-GitHub_Pages-38bdf8?style=for-the-badge&labelColor=050811&logo=github-pages&logoColor=white" alt="Docs"></a>
<a href="https://eddmpython.github.io/dartlab/blog/"><img src="https://img.shields.io/badge/Blog-fbbf24?style=for-the-badge&labelColor=050811&logo=rss&logoColor=white" alt="Blog"></a>
</p>

<p>
<a href="https://eddmpython.github.io/dartlab/">문서</a> · <a href="https://eddmpython.github.io/dartlab/blog/">블로그</a> · <a href="https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/01_company.ipynb">Colab에서 열기</a> · <a href="https://molab.marimo.io/github/eddmpython/dartlab/blob/master/notebooks/marimo/01_company.py">Molab에서 열기</a> · <a href="README_EN.md">English</a> · <a href="https://buymeacoffee.com/dartlab">후원</a>
</p>

<p>
<a href="https://huggingface.co/datasets/eddmpython/dartlab-data"><img src="https://img.shields.io/badge/Data-HuggingFace-ffd21e?style=for-the-badge&labelColor=050811&logo=huggingface&logoColor=white" alt="HuggingFace Data"></a>
<a href="https://github.com/eddmpython/dartlab-desktop/releases/latest/download/DartLab.exe"><img src="https://img.shields.io/badge/Desktop-Windows-38bdf8?style=for-the-badge&labelColor=050811&logo=windows&logoColor=white" alt="Desktop Download"></a>
</p>

<a href="https://www.youtube.com/shorts/97lYLWMWzvA"><img src="https://img.youtube.com/vi/97lYLWMWzvA/maxresdefault.jpg" alt="DartLab Demo" width="320"></a>

</div>

## 회사에는 이야기가 있다

숫자를 나열하면 대시보드가 되지만, 숫자의 인과를 연결하면 스토리가 된다.
DartLab은 그 스토리를 읽는 두 가지 방법을 제공한다.

**사람이 직접 읽는다** — 종목코드 하나로 재무제표, 공시, 비율을 꺼내고, 6막 인과 구조로 "왜 이 회사의 마진이 이 수준인가"를 추적한다. 코드 한 줄이면 데이터가 나오고, 그 데이터가 이야기를 만든다.

**AI가 읽어준다** — 같은 도구를 AI가 조합해서 질문에 맞는 분석 흐름을 스스로 설계하고, 코드와 결과를 투명하게 보여준다. 사용자는 답만 얻는 게 아니라 분석 방법을 배운다.

두 경로 모두 같은 엔진 위에서 동작한다. **엔진이 다리다** — 사람이 만든 엔진·블로그가 자동으로 AI 의 skill 이 되고, AI 가 실행 중 발견한 개선이 엔진 docstring·블로그로 사람 자산에 환류한다 (`operation.philosophy`).

투톱 진입점:

- `dartlab.ask("...")` — AI 의 입구. 자연어 한 줄.
- `dartlab.Company(code)` — 사람의 입구. 종목 파사드 하나로 `c.story()` · `c.analysis(...)` · `c.credit()` · `c.quant()` 등 전 엔진 접근.

## AI agent — engines + skills 위의 chat-native 루프

dartlab 은 *데이터 라이브러리 + AI 부속* 이 아니라 **engine ↔ AI ↔ skill 순환 루프** 자체. AI 는 외부 API 가 아니라 dartlab 의 데이터 엔진 (`Company` · `scan` · `macro`) + 분석 엔진 (`analysis` · `credit` · `quant` · `story`) 을 *RunPython 안에서 직접 호출* 한다. 같은 도구 표면을 **MCP** 로 외부 LLM (Claude Desktop · Cursor · Codex) 도 그대로 사용.

<img src=".github/assets/architecture.svg" alt="dartlab 아키텍처 — 사용자 / 입구 / chat-native 루프 / 도구 표면 11 / 메타 계층 (Skill OS · Capability) / 엔진 계층 (분석 7 + 데이터 7) / core / 외부 소스 / 진화 루프" width="1100">

> ① 사용자·외부 LLM → ② chat-native 루프 (`dartlab.ask`) 또는 사람 파사드 (`dartlab.Company`) → ③ 도구 표면 11 개 → ④ 메타 계층 (Skill OS · Capability) 읽기 + ⑤ 엔진 계층 (분석 7 / 데이터 7) 호출 → ⑥ core (mappers·data·providers) → ⑦ 외부 소스. ⑧ 진화 루프 — 답변 → 시장 N 일 후 reflection → 사람 검토 → Skill OS · Capability 갱신.

**한 줄 사용** — Python 또는 MCP:

```python
import dartlab
dartlab.ask("삼성전자 재무건전성 분석해줘")
# → AI 가 RunPython 으로 c.analysis("수익성") · c.credit("등급") 등 직접 호출
#   답변 안의 모든 숫자는 executionRef / tableRef 로 검산 가능
```

```bash
claude mcp add dartlab -- dartlab mcp        # Claude Code
codex  mcp add dartlab -- dartlab mcp        # Codex CLI
```

> Claude Desktop · 원격 SSE · 절대 경로 옵션은 [아래 MCP 섹션](#mcp--ai-어시스턴트-연동) 참조.

**핵심 디자인 4 가지**:

- **chat-native** — 고정 단계 (BRIEF / WORK / GATE 같은 graph 노드) 없음. LLM 이 매 iteration 도구 10 종 중 *언제·무엇을* 자율 결정. Cursor / Aider / dexter 와 같은 패턴.
- **Ref 검산** — 모든 숫자·날짜·랭킹 답이 `executionRef` · `tableRef` · `valueRef` · `webRef` 같은 ref 에 닿는다. GATE 가 ref 없는 답을 차단.
- **외부 본문 untrusted** — WebSearch / 외부 URL 본문은 `[EXTERNAL CONTENT START — untrusted]` 마커로 감싸 prompt injection 차단. 마커 안의 "이전 지시 무시" 문구는 *데이터* 로만 다룬다.
- **컨텍스트 관리** — 50KB+ 도구 결과는 자동 디스크 persist (`~/.dartlab/tool-results/`) + 2KB preview 만 inject (Read 도구로 전체 회수 가능). 옛 reasoning microcompact 로 prompt cache 보존.

**3 자 진화 (AI 자율 진화 아님)** — AI 가 skill 을 자율로 만들지 않는다 ([propose_skill 폐기, 2026-05-07](https://github.com/eddmpython/dartlab/commit/4ad36db1b) — `kind=generated` 사다리는 0 promoted skill 로 dormant 였고 *AI 자기 평가* 보다 *시장 평가* 가 더 강한 신호). 대신:

1. AI 분석 결정 → `~/.dartlab/decisions/{market}/{stockCode}.md` 에 *pending* outcome 기록
2. 다음 같은 종목 호출 시 → 가격 fetch + 벤치마크 비교 → reflection (*"방향 옳았나? thesis 어디 유지? lesson 1 개"*) → resolved 로 atomic 갱신
3. 사람이 reflection 보고 skill / engine docstring / 블로그 갱신
4. 다음 AI 호출이 *갱신된 skill* + *과거 reflection 비대칭 주입* (같은 종목 5 + 다른 종목 3) 으로 더 잘함

**AI + 시장 + 사람 공동 진화**. 상세는 [`ai/SSOT.md` §6 Outcome ground truth 선순환](src/dartlab/ai/SSOT.md).

## 문제

삼성전자의 "매출액"을 5년간 비교하려고 한 적 있는가?

DART에서 사업보고서를 열면 같은 숫자가 `ifrs-full_Revenue`, `dart_Revenue`, `매출액`, `영업수익` 네 가지 이름으로 나온다. 작년과 올해의 목차 구조가 다르다. SK하이닉스와 비교하려면 같은 작업을 처음부터 다시 해야 한다.

**진짜 문제는 데이터가 없는 게 아니다. 같은 데이터가 너무 많은 이름으로 존재하는 것이다.**

DartLab은 하나의 전제 위에 서 있다: **모든 기간은 비교 가능해야 하고, 모든 회사는 비교 가능해야 한다.** 공시 섹션을 토픽-기간 그리드로 정규화하고(~95% 매핑율), XBRL 계정을 표준 이름으로 통일한다(~97% 매핑율) — 양식이 아니라 기업을 비교한다.

## 빠른 시작

```bash
uv add dartlab
```

```python
import dartlab

c = dartlab.Company("005930")       # 삼성전자

c.sections                          # 모든 topic, 모든 기간, 나란히
# shape: (41, 12) — 41개 토픽 × 12개 기간
#                     2025Q4  2024Q4  2024Q3  2023Q4  ...
# companyOverview       v       v       v       v
# businessOverview      v       v       v       v
# riskManagement        v       v       v       v
```

> 텍스트와 숫자의 시계열 수평화 — 전 기간 비교 가능성의 핵심
>
> <img src=".github/assets/sections-example.webp" alt="c.sections 출력 예시 — 삼성전자 41개 토픽 × 12개 기간" width="720">

```python

c.show("IS")                        # 손익계산서 — 분기가 기본
```

> 분기별 재무제표가 기본 — snakeId + 한글 항목명 동시 제공
>
> <img src=".github/assets/show-is-quarterly.webp" alt="c.show('IS') — 삼성전자 분기 손익계산서" width="720">

```python
c.show("IS", freq="Y")             # freq="Y"로 연간 합산
```

> 같은 데이터, 연간으로 — 4분기 합산 자동 처리
>
> <img src=".github/assets/show-is-annual.webp" alt="c.show('IS', freq='Y') — 삼성전자 연간 손익계산서" width="720">

```python
c.show("businessOverview")          # 이 회사가 실제로 뭘 하는지
c.diff("businessOverview")          # 작년 대비 뭐가 바뀌었는지
c.show("ratios")                    # 재무비율, 이미 계산됨

c.filings()                         # 모든 보고서 — DART 뷰어로 바로 연결
```

> 사업보고서부터 분기보고서까지, dartUrl로 원문 즉시 확인
>
> <img src=".github/assets/show-filings.webp" alt="c.filings() — 삼성전자 보고서 목록 + DART 뷰어 링크" width="720">

```python
# 같은 인터페이스, 다른 나라
us = dartlab.Company("AAPL")
us.show("business")
us.show("ratios")

# 자연어로 질문
dartlab.ask("삼성전자 재무건전성 분석해줘")
# → AI가 코드를 실행하며 분석: "영업이익률이 8.6%→21.4%로 반등..."
```

API 키 불필요. [HuggingFace](https://huggingface.co/datasets/eddmpython/dartlab-data)에서 자동 다운로드, 로컬 캐시로 즉시 로드.

## 세 겹의 분석

Company가 종목코드 하나로 데이터를 준비하면, 세 겹이 분석한다.

1. **분석 엔진** — 숫자를 만든다. 마진 추이, 현금흐름 패턴, 부도 확률, 업종 비교, 매크로 사이클. 해석하지 않는다. 숫자와 근거만 제공한다.
2. **story** — 엔진 데이터를 블록 단위로 조합하여 보고서를 만든다. 11가지 보고서 타입 × 7가지 기업유형 템플릿. 해석은 제공하지 않는다. 다양한 관점의 근거를 체계적으로 배치한다.
3. **AI** — 엔진을 직접 쓰고 판단한다. 결과를 의심하고, 원본으로 검증하고, 이상하면 가정을 바꿔서 재계산한다. dartlab을 대표하는 적극적 분석가.

## DartLab은 무엇인가

하나의 호출 계약. `dartlab.엔진()` 으로 가이드 보고 `dartlab.엔진("축")` 으로 실행.

> **처음이라면?** `Company` → `Story` → `Ask` 순서로. 종목코드로 데이터를 보고, 보고서를 만들고, AI에게 물어본다.

| 레이어 | 엔진 | 하는 일 | 진입점 | 노트북 |
|--------|------|---------|--------|--------|
| Data | [Data](/skills) | HuggingFace 사전 구축, 자동 다운로드 | `Company("005930")` | — |
| L0/L1 | [Company](/skills) | 공시 + 재무제표 + 정형 데이터를 종목코드 하나로 통합 | `c.show()`, `c.select()` | [Colab](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/01_company.ipynb) · [marimo](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/01_company.py) |
| L1 | [Gather](/skills) | 외부 시장 데이터 (주가/수급/매크로/뉴스) | `dartlab.gather()` | [Colab](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/02_gather.ipynb) · [marimo](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/02_gather.py) |
| L1.5 | [Scan](/skills) | 전 종목 사전 빌드 (거버넌스/비율/현금흐름 등 parquet) | `dartlab.scan()` | [Colab](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/03_scan.ipynb) · [marimo](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/03_scan.py) |
| L2 | [Analysis](/skills) | 재무 심층 분석 (수익성/안정성/현금흐름) + 가치평가 + 전망 | `c.analysis("financial", "수익성")` | [Colab](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/05_analysis.ipynb) · [marimo](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/05_analysis.py) |
| L2 | [Quant](/skills) | 가격 기반 정량 신호 (기술/리스크/팩터/백테스트) | `c.quant()` | [Colab](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/04_quant.ipynb) · [marimo](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/04_quant.py) |
| L2 | [Credit](/skills) | 독립 신용평가 (dCR 등급, 부도확률, 건전도) | `c.credit("등급")` | [Colab](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/07_credit.ipynb) · [marimo](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/07_credit.py) |
| L2 | [Macro](/skills) | 시장 레벨 매크로 (사이클/금리/유동성/심리/자산 + 시나리오 110) | `dartlab.macro("사이클")` | [Colab](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/06_macro.ipynb) · [marimo](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/06_macro.py) |
| L2 | [Industry](/skills) | 산업 매퍼 — 전 상장사 × 공정·역할·스트림 + 공급망 엣지 (산업지도 `/map`) | `c.industry()`, `dartlab.industry("semiconductor")` | — |
| L3 | [Story](/skills) | 보고서 빌더 — 6엔진 블록 조합 (analysis/quant/credit/macro/scan/**industry**), 11 타입 × 7 템플릿 (해석 안 함) | `c.story("수익성")` | [Colab](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/08_story.ipynb) · [marimo](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/08_story.py) |
| L4 | [AI/Skills](/skills) | skills 검색 + DartLab 실행 + ref 검산을 쓰는 분석 작업대 (사람도 L4) | `dartlab.ask()` | [Colab](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/09_ai.ipynb) · [marimo](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/09_ai.py) |
| L4 | [Channel](/skills) | 외부 공유 — `dartlab channel` 한 줄로 폰에서 PC dartlab 사용 | `dartlab channel` | — |
| core | [Search](/skills) | 공시 시맨틱 검색 *(beta — 인덱스 신선도 부족)* | `dartlab.search()` | [Colab](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/10_search.ipynb) · [marimo](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/10_search.py) |
| facade | [Listing](/skills) | 종목/공시/topic 카탈로그 API | `dartlab.listing()` | [Colab](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/11_listing.ipynb) · [marimo](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/11_listing.py) |
| viz | [Viz](/skills) | 차트/다이어그램 (`emit_chart`) | `emit_chart({...})` | — |

> 모든 노트북: [marimo](notebooks/marimo/) · [colab](notebooks/colab/) · [![Open in marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo)

### Company

> 설계: [engines.company](/skills)

세 가지 데이터 소스 — docs(전문 공시), finance(XBRL 재무제표), report(DART API 정형 데이터) — 를 하나의 객체로 통합. [HuggingFace](https://huggingface.co/datasets/eddmpython/dartlab-data)에서 자동 다운로드, 설정 불필요.

```python
c = dartlab.Company("005930")

c.index                         # 뭐가 있는지 -- topic 목록 + 가용 기간
c.show("BS")                    # 데이터를 보려면 -- topic별 DataFrame
c.select("IS", ["매출액"])       # 데이터를 뽑으려면 -- finance든 docs든 같은 패턴
c.trace("BS")                   # 어디서 왔는지 -- source provenance
c.diff()                        # 뭐가 바뀌었는지 -- 기간 간 텍스트 변화
```

**주석(Notes)** — BS/IS 총액 이면의 항목별 분해. `c.show("topic")`으로 재무제표와 같은 패턴으로 접근. DART(K-IFRS HTML 파싱)와 EDGAR(US-GAAP XBRL 태그) 동일 인터페이스.

| `c.show(...)` | 내용 | DART | EDGAR |
|---------------|------|:----:|:-----:|
| `"inventory"` | 원재료/재공품/제품 분해 | ✅ | ✅ |
| `"borrowings"` | 단기/장기 차입금 분해 | ✅ | ✅ |
| `"tangibleAsset"` | 유형자산 취득원가/감가상각/장부가 | ✅ | ✅ |
| `"intangibleAsset"` | 영업권/개발비 등 | ✅ | ✅ |
| `"receivables"` | 매출채권 + 대손충당금 | ✅ | ✅ |
| `"provisions"` | 보증/소송/구조조정 충당부채 | ✅ | ✅ |
| `"eps"` | 기본/희석 주당이익 | ✅ | ✅ |
| `"segments"` | 부문별 매출/이익 | ✅ | ✅ |
| `"costByNature"` | 원재료/급여/감가상각 성격별 비용 | ✅ | ✅ |
| `"lease"` | 사용권자산/리스부채 | ✅ | ✅ |
| `"affiliates"` | 관계기업 지분법 투자 | ✅ | ✅ |
| `"investmentProperty"` | 투자부동산 공정가치/장부가 | ✅ | ✅ |

> [![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/01_company.py) [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/01_company.ipynb)

### Scan — 전 종목 횡단 비교

> 설계: [engines.scan](/skills)

전 종목 대상 횡단 분석. 거버넌스, 인력, 주주환원, 부채, 현금흐름, 감사, 내부자, 이익의 질, 유동성, 네트워크, 계정/비율 비교 등.

```python
dartlab.scan("governance")            # 전종목 지배구조
dartlab.scan("ratio", "roe")          # 전종목 ROE
dartlab.scan("account", "매출액")      # 전종목 매출액 시계열
```

> 2,500+ 종목의 매출액을 한 번에 — 분기별 시계열로 즉시 비교
>
> <img src=".github/assets/scan-account.webp" alt="dartlab.scan('account', '매출액') — 전종목 매출액 횡단 비교" width="720">

### Gather — 외부 시장 데이터

> 설계: [engines.gather](/skills)

주가, 수급, 거시지표, 뉴스 — Polars DataFrame으로.

```python
dartlab.gather("price", "005930")             # KR OHLCV
dartlab.gather("price", "AAPL", market="US")  # US 주가
dartlab.gather("macro", "FEDFUNDS")           # 자동 US 감지
dartlab.gather("news", "삼성전자")             # Google News RSS
```

### Analysis — 재무 인과 분석

> 설계: [engines.analysis](/skills)

수익구조 → 수익성 → 성장성 → 안정성 → 현금흐름 → 자본배분 → 가치평가 → 전망. 원본 재무제표를 인과 서사로 가공한다.

```python
c.analysis("financial", "수익성")       # 수익성 분석
c.analysis("수익성")                     # 단축형 (financial 자동)

print(c.credit())                            # 사용 가능한 축 가이드 DataFrame (self-discovery)
c.credit("등급")                             # dCR-AA, 건전도 93/100
c.credit("등급", detail=True)                # 등급 + 서사 + 지표 시계열
```

### Credit — 독립 신용분석

> 설계: [engines.credit](/skills) | 보고서: [dartlab.pages.dev/blog/credit-reports](https://dartlab.pages.dev/blog/credit-reports)

3-Track 모델(일반/금융/지주) + Notch Adjustment + CHS 시장 보정 + 별도재무 블렌딩.

**79개사 검증: 대기업 87% (26/30), 중대형 82% (41/50), 전체 70% (55/79, v5.0 과대평가 수정 후 재측정 예정). 삼성전자 AA+ 정확 일치.** 검증 방법론은 [methodology](https://eddmpython.github.io/dartlab/skills/operation.methodology) 참조.

```python
print(c.credit())            # self-discovery — 사용 가능한 축 + 종합 등급

cr = c.credit("등급")        # 종합 등급
print(cr["grade"])          # dCR-AA+
print(cr["healthScore"])    # 96 (0-100, 높을수록 건전)
print(cr["pdEstimate"])     # 0.01% 부도확률

cr = c.credit("등급", detail=True)  # 등급 + 서사 + 지표 + 괴리 설명
print(cr["divergenceExplanation"])  # 신평사와 왜 다른지
```

신용분석 보고서 발간 (credit 서사 + 신평사 대조가 story 5막에 자동 통합):

```python
from dartlab.story.publisher import publishReport
publishReport("005930")               # 6막 보고서 (credit narrative + audit 포함)
```

### Macro — 종목코드 없이 경제를 읽다

> 설계: [engines.macro](/skills)

Company 없이 경제 환경을 분석한다. `import dartlab` 하나로.

```python
dartlab.macro("사이클")          # 경기 4국면 판별
dartlab.macro("금리")            # 금리 + Nelson-Siegel 수익률곡선
dartlab.macro("예측")            # LEI + 침체확률 + Hamilton RS + GDP Nowcast
dartlab.macro("종합")            # 매크로 종합 + 투자전략 + 포트폴리오 매핑
```

시장 사이클·금리·유동성·심리·자산 신호와 글로벌 거시 분석 방법론(Hamilton EM, Kalman DFM, Nelson-Siegel, Cleveland Fed 프로빗, Sahm Rule, BIS Credit-to-GDP)을 **numpy만으로 직접 구현**.

백테스트 실증 (2000-2024, FRED): Cleveland Fed 프로빗이 **미국 3/3 침체를 2-16개월 전에 사전 감지**, recall 90%.

### Story — 분석을 보고서로

> 설계: [engines.story](/skills)

analysis를 구조화 보고서로 조립. 4개 출력 형식: rich(터미널), html, markdown, json.

```python
c.story()              # 전체 보고서
dartlab.ask()            # 보고서 + AI 종합의견
```

> 삼성전자 보고서 미리보기: *"매출 +23.8% 성장, 영업이익률 8.6%→21.4% 반등. FCF 양수 전환, ROIC > WACC — 재투자가 가치를 창출하는 구간."*

### 이야기꾼 — 숫자가 아니라 이야기다

> 설계: [engines.story](/skills) · 시리즈: [기업이야기](https://eddmpython.github.io/dartlab/blog/series/company-reports)

기업분석은 비율 나열이 아니다. DartLab은 5개 엔진(analysis, credit, scan, quant, macro)의 결과를 **6막 스토리텔링 구조**로 조합해 블로그에 발간 가능한 기업이야기를 자동 생성한다.

```python
from dartlab.story.publisher import publishReport
publishReport("068270")    # 셀트리온 — 6막 기업이야기 자동 발간
```

**발간된 기업이야기:**

| 기업 | 이야기 |
|------|--------|
| [SK하이닉스](https://eddmpython.github.io/dartlab/blog/000660-skhynix) | 한국 반도체 30년의 미스터리, 영업이익률 58% |
| [삼양식품](https://eddmpython.github.io/dartlab/blog/003230-samyang-foods) | 라면 빅3 꼴등이 매출 2.3조 글로벌 식품 거인이 되기까지 |
| [두산에너빌리티](https://eddmpython.github.io/dartlab/blog/034020-doosan-enerbility) | 부채비율 305%에서 129%까지, 9년 다이어트의 진짜 모습 |
| [알테오젠](https://eddmpython.github.io/dartlab/blog/196170-alteogen) | 9년 적자 바이오텍이 한 건의 라이선스로 영업이익 +1,069억 |
| [HMM](https://eddmpython.github.io/dartlab/blog/011200-hmm) | 시장이 아니라 사이클이 주가를 결정하는 회사 |
| [셀트리온](https://eddmpython.github.io/dartlab/blog/068270-celltrion) | IMF로 직장 잃은 41세, 5천만원으로 시작해 25년 후 무형자산 13.78조 |
| [한화에어로스페이스](https://eddmpython.github.io/dartlab/blog/012450-hanwha-aerospace) | 삼성이 8,400억에 버린 무기가 수주잔고 37조가 됐다 |
| [HD현대일렉트릭](https://eddmpython.github.io/dartlab/blog/267260-hd-hyundai-electric) | 7년 전 적자 1,006억이 올해 1조가 됐다, 변압기 하나로 |
| [고려아연](https://eddmpython.github.io/dartlab/blog/010130-korea-zinc) | 50년 만에 첫 순손실 2,457억, 그런데 영업이익은 사상 최대 |
| [에이피알](https://eddmpython.github.io/dartlab/blog/278470-apr) | 화장품 회사가 가전을 4,070억 팔았다, 그게 시작이었다 |

<div align="center">
<a href="https://www.youtube.com/watch?v=d7RUQIlimVM"><img src="https://img.youtube.com/vi/d7RUQIlimVM/maxresdefault.jpg" alt="셀트리온 기업이야기" width="100%"></a>

[셀트리온 이야기 보기](https://www.youtube.com/watch?v=d7RUQIlimVM) · [DartLab 30초 데모](https://www.youtube.com/shorts/97lYLWMWzvA) · [유튜브 채널](https://www.youtube.com/@eddmpython)
</div>

### Search — 공시를 의미로 검색 *(beta — 인덱스 신선도 한계)*

> 설계: [engines.search](/skills)

> ⚠ 현재 인덱스가 일정 시점까지만 빌드됨 (매일 증분 자동화 미완성). 단일 종목 공시 조회는 `Company.disclosure` / `Company.liveFilings` 권장. 인프라(CI cron + HF push) 구축 후 stable 승격 예정.

모델 없음, GPU 없음, cold start 없음. 400만 문서 95% 정밀도 — 임베딩보다 정확, 1/100 비용. 벤치마크 상세는 [methodology](https://eddmpython.github.io/dartlab/skills/operation.methodology) 참조.

```python
dartlab.search("유상증자 결정")                     # 유상증자 공시 찾기
dartlab.search("대표이사 변경", corp="005930")       # 종목 필터
dartlab.search("회사가 돈을 빌렸다")                 # 자연어도 동작
```

### AI — skills 기반 분석 작업대

> 설계: [operation.opsAsSkills](/skills) · 루프 개요: [상단 AI agent 섹션](#ai-agent--engines--skills-위의-chat-native-루프)

```python
dartlab.ask("삼성전자 재무건전성 분석해줘")
dartlab.ask("삼성전자 분석", provider="gemini")  # 무료 provider 사용 가능
```

Provider: `gemini`(무료), `groq`(무료), `cerebras`(무료), `oauth-codex`(ChatGPT 구독), `openai`, `ollama`(로컬) 등. Rate limit 시 자동 대체.

### Channel — 외부에서 내 PC dartlab 접근

> 설계: [runtime.channel](/skills)

PC에서 한 줄이면 폰에서 dartlab UI 그대로 사용. Microsoft DevTunnels 자동 셋업.

```bash
dartlab channel
```

흐름:
1. winget으로 devtunnel CLI 자동 설치 (최초 1회)
2. GitHub OAuth 1회 인증 (브라우저 자동 오픈)
3. 영구 URL + QR 발급 (`https://<id>-8400.<region>.devtunnels.ms`)
4. 폰 Chrome에 URL/QR 입력 → dartlab UI 그대로 동작

도메인 0개, 토큰 트릭 0개. VS Code Remote Tunnels와 동일 인프라라 모바일 호환성 검증됨. 메시징 봇 옵션 (`--telegram/slack/discord`) 도 지원.

### 아키텍처

**"엔진 = 도구 (숫자만), story = 이야기꾼, AI/사람 = 소비자"** — 1.0.0 전 근본 구조.

```
L0     core/         SSOT 인프라 (protocols, finance, memory, docs, search)
                     공용 헬퍼: toDictBySnakeId, memoized_calc, parseNumStr, safeDiv, fmtBig
L1     providers/    국가별 공시 데이터 (DART, EDGAR, EDINET)
       gather/       외부 시장 데이터 (Naver, Yahoo, FRED, ECOS)
L1.5   scan/         전종목 사전 빌드 (parquet) — 데이터 빌더, 분석 아님
L2     analysis/     재무 심층 (14축 + forecast + valuation)
       quant/        가격 기반 정량 신호 (기술/리스크/팩터/백테스트)
       credit/       독립 신용등급 (dCR 20단계, 7축)
       macro/        거시 지표 (11축 + scenarios 110 + historicalContext)
                     — 4개 엔진 동등, 상호 import 금지. dict/숫자만 반환.
L3     story/        이야기꾼 — L2 4엔진 + scan 소비, 보고서 조립
                     narrate (문장) + builders (블록) + templates (관점/성격)
L4     ai/ + 사람    소비자 — story 보고서를 해석하고 판단
       vscode/       VSCode 확장 (dartlab chat --stdio)
       ui/web/       Svelte SPA 웹 인터페이스
```

**import 방향**: `L0 ← L1 ← L1.5 ← L2 ← L3 ← L4` (CI 강제, 역방향 0건).

#### 레이어 간 소비 흐름

```mermaid
flowchart TB
    subgraph L4["L4 · 소비자 (해석과 판단)"]
        direction LR
        HUMAN["🧑 사람<br/>투자자/분석가"]
        AI["ai<br/>dartlab.ask()"]
        UI["vscode / CLI / web"]
    end
    subgraph L3["L3 · 이야기꾼"]
        REV["story<br/>narrate + builders + templates<br/>보고서 조립 (6막 서사)"]
    end
    subgraph L2["L2 · 분석 엔진 (dict만 반환, 상호 독립)"]
        ANA["analysis<br/>재무 14축 + forecast + valuation"]
        QNT["quant<br/>기술/리스크/팩터/백테스트"]
        CRD["credit<br/>dCR 20단계 · 7축"]
        MAC["macro<br/>11축 + scenarios 110"]
    end
    subgraph L15["L1.5 · 데이터 빌더"]
        SCN["scan<br/>전종목 parquet 사전 빌드"]
    end
    subgraph L1["L1 · 데이터 수집"]
        PRV["providers<br/>DART / EDGAR / EDINET"]
        GAT["gather<br/>FRED / ECOS / Naver / Yahoo"]
    end
    subgraph L0["L0 · 인프라 (SSOT)"]
        CORE["core<br/>finance.helpers · memory · docs · search"]
    end

    HUMAN --> UI
    UI --> AI
    UI --> REV
    AI --> REV
    AI --> ANA
    AI --> QNT
    AI --> MAC
    REV --> ANA
    REV --> QNT
    REV --> CRD
    REV --> MAC
    REV --> SCN
    ANA --> SCN
    ANA --> PRV
    ANA --> GAT
    QNT --> SCN
    QNT --> GAT
    CRD --> SCN
    CRD --> PRV
    MAC --> GAT
    SCN --> PRV
    SCN --> CORE
    PRV --> CORE
    GAT --> CORE
    ANA --> CORE
    QNT --> CORE
    CRD --> CORE
    MAC --> CORE

    classDef l0 fill:#f5f5f5,stroke:#999
    classDef l1 fill:#e8f4ff,stroke:#4a90e2
    classDef l15 fill:#dbeafe,stroke:#3b82f6
    classDef l2 fill:#fff4e6,stroke:#e67e22
    classDef l3 fill:#f0e6ff,stroke:#8e44ad
    classDef l4 fill:#e6ffe6,stroke:#27ae60
    class CORE l0
    class PRV,GAT l1
    class SCN l15
    class ANA,QNT,CRD,MAC l2
    class REV l3
    class AI,UI,HUMAN l4
```

**핵심 규칙**:
- **L2 엔진 상호 import 금지** — analysis↛quant, macro↛credit 등 (0건 유지, CI 검증)
- **L2 → L3 역방향 금지** — 엔진은 dict만, 해석/블록/보고서 생성은 story의 책임 (0건 유지)
- **L2 → L1.5(scan) 하향 참조 허용** — scan은 순수 데이터 빌더
- **새 국가 추가** = providers/ 패키지 하나, core 수정 0줄

## EDGAR (미국)

같은 인터페이스, 다른 데이터 소스. SEC API에서 자동 수집, 사전 다운로드 불필요.

```python
# Korea (DART)                          # US (EDGAR)
c = dartlab.Company("005930")           c = dartlab.Company("AAPL")
c.sections                              c.sections
c.show("businessOverview")              c.show("business")
c.show("BS")                            c.show("BS")
c.show("ratios")                        c.show("ratios")
c.diff("businessOverview")              c.diff("10-K::item7Mdna")
```

## MCP — AI 어시스턴트 연동

> 루프·도구 표면 개요: [상단 AI agent 섹션](#ai-agent--engines--skills-위의-chat-native-루프)

[MCP](https://modelcontextprotocol.io/) 서버 내장. **canonical 6 도구 + ask** 메타로 외부 LLM 이 dartlab 라이브러리를 RunPython 안에서 직접 호출하는 패턴 (도구 표면을 좁혀 토큰 비용 ↓, 도구 선택 정확도 ↑).

### Claude Desktop / Claude Code / Cursor (stdio, 권장)

`uvx dartlab mcp` 의 cold start 가 Claude Desktop attach timeout 안에 들어가지 못하므로 **사전 설치 + entry point 직접 호출** 이 정본입니다. `command: "python"` 은 Microsoft Store Python 환경에서 spawn ENOENT 로 실패할 수 있어 (이슈 [#28](https://github.com/eddmpython/dartlab/issues/28)), `command: "dartlab"` 으로 entry point 를 직접 호출하는 게 가장 견고합니다.

```bash
# 1. 사전 설치 (한 번만) — .local/bin/dartlab(.exe) entry point 생성
uv tool install dartlab        # 또는: pipx install dartlab
```

```jsonc
// 2-A. Claude Desktop — %APPDATA%\Claude\claude_desktop_config.json
{
  "mcpServers": {
    "dartlab": {
      "command": "dartlab",
      "args": ["mcp"],
      "env": { "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1" }
    }
  }
}
```

```bash
# 2-B. Claude Code 한 줄 설정
claude mcp add dartlab -- dartlab mcp

# 2-C. Codex CLI
codex mcp add dartlab -- dartlab mcp
```

`dartlab` 명령이 PATH 에 잡히지 않는 환경 (한정적) 이라면 절대 경로로 적어주세요:

```jsonc
{
  "mcpServers": {
    "dartlab": {
      "command": "C:\\Users\\<user>\\.local\\bin\\dartlab.exe",   // Windows
      // "command": "/Users/<user>/.local/bin/dartlab",              // macOS / Linux
      "args": ["mcp"],
      "env": { "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1" }
    }
  }
}
```

> 같은 출력은 `dartlab mcp --config claude-desktop` / `dartlab mcp --config claude-code` 로도 받을 수 있습니다. 프로젝트 `.mcp.json` 자동 생성: `dartlab mcp --install`.

### 원격 MCP (Claude Code · Cursor 등 SSE 지원 클라이언트만)

```jsonc
{
  "mcpServers": {
    "dartlab": {
      "url": "https://eddmpython-dartlab.hf.space/mcp/sse"
    }
  }
}
```

HuggingFace Spaces 호스팅. DART API 키 불필요. **Claude Desktop 데스크톱 앱은 stdio 만 받으므로 이 URL 방식을 reject 합니다** — 위 stdio 경로를 사용하세요.

### 도구 표면

| 도구 | 역할 |
|------|------|
| **ask** | dartlab chat-native 루프 — LLM 자율 도구 호출 + Ref 검산 일괄 |
| **ReadSkill** · **GetSkillBody** | Skill OS 검색 + frontmatter + 본문 |
| **ReadCapability** | dartlab 공개 API/docstring 검색 |
| **EngineCall** | 단일 capability 1 회 호출 (가벼운 단발 조회용) |
| **RunPython** | dartlab + Polars 코드 실행 → executionRef/valueRef/tableRef |
| **Read** | 디스크 파일 직접 인용 (큰 결과 persist 후 회수) |
| **WebSearch** | 외부 최신 정보 → webRef (untrusted 마커 자동 적용) |
| **SaveArtifact** | 큰 표·차트 별도 저장 → artifactRef |
| **CompileVisual** | 차트 spec codegen → visualRef |
| **RunWorkbench** | 명시적 deep analysis sub-agent (옵션 — 사용자 `/analyze` 또는 LLM 자율 elevate) |

> 옛 33 generated 도구 (`companyAnalysis`/`companyStory`/`marketScan` 등) 는 0.10 부터 폐기 — 모두 `RunPython` 안에서 `dartlab.Company / dartlab.scan / dartlab.macro` 직접 호출. 마이그레이션은 [CHANGELOG](https://github.com/eddmpython/dartlab/releases) 참조.

## dartlab-lite — 브라우저·엑셀에서 설치 없이 (Pyodide)

> 상세: [블로그 — 엑셀·브라우저·노트북에서 설치 없이 dartlab 쓰기 (Pyodide)](https://eddmpython.github.io/dartlab/blog/pyodide-dartlab-lite)

[Pyodide](https://pyodide.org/)가 CPython을 WebAssembly로 포팅한 덕에 **파이썬이 설치되지 않은 환경**에서도 dartlab이 그대로 돈다. 같은 API, 같은 데이터.

**지원 환경**: [xlwings Lite](https://lite.xlwings.org/) (Excel) · [Anaconda Code](https://www.anaconda.com/products/code-for-excel) (Excel) · [JupyterLite](https://jupyterlite.readthedocs.io/) · Google Colab WASM 런타임 · marimo (pyodide) · 순수 HTML 임베드.

**[👉 웹 엑셀에서 바로 열어보기 — OneDrive 공유 워크북](https://1drv.ms/x/c/4e17617bfea66347/IQB9zW91TaD4TJvHM8LRQTh4ARj0gHMapx4LVhCCSbBz92Q?e=HQ4E7d)** — xlwings Lite + dartlab 세팅 완료. 버튼만 누르면 시트에 재무제표가 찍힌다.

### 두 가지 사용 방식 — script형 vs func형

xlwings Lite는 두 데코레이터를 제공한다. **`@script`는 버튼형(명령형)**, **`@func`는 수식형(선언형)**. dartlab은 둘 다 지원하며, **함수형이 dartlab을 엑셀답게 쓰는 방법**이다.

**1. `@script` — 사이드바 버튼 → 시트에 채우기**

```python
import dartlab
import xlwings as xw
from xlwings import arg, func, script

@script(name="isTest")
def finance(book: xw.Book):
    c = dartlab.Company('000020')
    df = c.show('IS')
    data = [list(df.columns)] + [list(r) for r in df.iter_rows()]
    sheet = book.sheets.active
    sheet["A3"].value = data
```

<img src=".github/assets/xlwings-lite-script.webp" alt="xlwings Lite — @script 모드, 버튼 누르면 시트에 IS가 채워진다" width="720">

**2. `@func` — 엑셀 셀에 수식처럼 `=GETFINANCE("005930")`**

```python
@func
def getFinance(code: str):
    c = dartlab.Company(code)
    df = c.show('IS')
    data = [list(df.columns)] + [list(r) for r in df.iter_rows()]
    return data
```

<img src=".github/assets/xlwings-lite-func.webp" alt="xlwings Lite — @func 모드, 셀에 =GETFINANCE(\"005930\")만 쳐도 5분기 IS가 자동 스필" width="720">

VLOOKUP과 나란히 **`=GETFINANCE`가 엑셀 네이티브 함수**로 동작한다. 종목코드를 바꾸면 셀 재계산으로 전부 갱신된다.

### 설치 (xlwings Lite · 한 줄)

```python
import micropip
await micropip.install(["diff-match-patch", "openpyxl"])
await micropip.install(
    "https://huggingface.co/eddmpython/dartlab-data/resolve/main/pyodide/dartlab-latest-py3-none-any.whl",
    deps=False,
)

import dartlab
c = dartlab.Company("005930")
c.show("IS")
```

또는 xlwings Lite 사이드바의 `requirements.txt`에 `dartlab` 한 줄 — 그것만으로 끝. **로컬 파이썬 0줄, uv 0줄, venv 0줄.**

### 제약 (브라우저 런타임의 한계)

| 기능 | Pyodide | 비고 |
|---|:---:|---|
| `Company()` · `c.show()` · `analysis` · `story` · `credit` | ✅ | HF parquet 자동 다운로드 |
| `dartlab.ask()` | ✅ | API 키 설정 필요 (gemini·openai CORS OK) |
| `dartlab.scan()` | ❌ | 사전 빌드 parquet 271MB (브라우저 비현실적) |
| `dartlab.gather()` | ❌ | Naver·Yahoo·Google News CORS 차단 |

스레드 없음 · MEMFS 휘발 · CORS 미허용 API 불가 — 이 세 제약이 근본이다. 상세와 빌드 파이프라인은 [pyodide/README.md](pyodide/README.md), 설치 5단계 스크린샷은 [블로그 글](https://eddmpython.github.io/dartlab/blog/pyodide-dartlab-lite)을 본다.

## REST API — 키 없이 공시 조회

HuggingFace Spaces에서 DART API 프록시 제공. API 키 없이 실시간 공시 데이터 접근:

```bash
# 공시 목록
curl "https://eddmpython-dartlab.hf.space/api/dart/filings?corp=005930&start=20260101"

# 기업 정보
curl "https://eddmpython-dartlab.hf.space/api/dart/company/005930"

# 재무제표
curl "https://eddmpython-dartlab.hf.space/api/dart/finance/005930?year=2024"

# 보고서 (배당, 직원, 임원 등 56개 카테고리)
curl "https://eddmpython-dartlab.hf.space/api/dart/report/005930/배당?year=2023"
```

## OpenAPI — 원본 공공 API

```python
from dartlab import OpenDart, OpenEdgar

# 한국 (opendart.fss.or.kr 무료 API 키 필요)
d = OpenDart()
d.filings("삼성전자", "2024")
d.finstate("삼성전자", 2024)

# 미국 (API 키 불필요)
e = OpenEdgar()
e.filings("AAPL", forms=["10-K", "10-Q"])
```

## 데이터

모든 데이터는 [HuggingFace](https://huggingface.co/datasets/eddmpython/dartlab-data)에 사전 구축 — 자동 다운로드. EDGAR는 SEC API 직접 수집.

| 데이터셋 | 용량 |
|----------|------|
| DART docs | ~8 GB |
| DART finance | ~600 MB |
| DART report | ~320 MB |
| EDGAR | SEC API (주문형) |

파이프라인: 로컬 캐시(즉시) → HuggingFace(자동 다운로드) → DART API(키 필요). 대부분 처음 두 단계로 충분.

## 바로 시작하기

**노트북 (Colab):** [Company](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/01_company.ipynb) · [Gather](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/02_gather.ipynb) · [Scan](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/03_scan.ipynb) · [Quant](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/04_quant.ipynb) · [Analysis](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/05_analysis.ipynb) · [Macro](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/06_macro.ipynb) · [Credit](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/07_credit.ipynb) · [Story](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/08_story.ipynb) · [AI](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/09_ai.ipynb)

**노트북 (marimo):** [전체 목록](notebooks/marimo/README.md) — `import` 반복 없는 단일 진입, 셀마다 주석 설명, 마크다운 셀 미사용

## 문서

[문서](https://eddmpython.github.io/dartlab/) · [빠른 시작](https://eddmpython.github.io/dartlab/skills/start.quickStart) · [Skills](https://eddmpython.github.io/dartlab/skills)

**블로그 (120+ 글):** [전체](https://eddmpython.github.io/dartlab/blog/) · [기업이야기](https://eddmpython.github.io/dartlab/blog/series/company-reports) · [신용평가 보고서](https://eddmpython.github.io/dartlab/blog/credit-reports) · [매크로 보고서](https://eddmpython.github.io/dartlab/blog/macro-reports)

## 안정성

| Tier | 범위 |
|------|------|
| **Stable** | DART Company (sections, show, trace, diff, BS/IS/CF, CIS, index, filings, profile), EDGAR Company core, valuation, forecast, simulation |
| **Beta** | EDGAR 파워유저 (SCE, notes, freq, coverage), credit, insights, distress, ratios, timeseries, network, governance, workforce, capital, debt, chart/table/text 도구, ask/chat, OpenDart, OpenEdgar, Server API, MCP |
| **Experimental** | AI 도구 호출, export, viz (차트) |

자세한 기준은 [operation.stability](https://eddmpython.github.io/dartlab/skills/operation.stability) 를 본다.

## 기여

기여는 무엇이든 환영합니다. 버그 리포트, 기능 제안, 문서 개선, 예제 추가, 데이터 매핑 수정처럼 작은 변경도 dartlab을 더 좋게 만듭니다.

한국어와 영어 이슈·PR 모두 편하게 열어주세요. 어디서 시작할지 모르겠다면 이슈로 먼저 이야기해도 좋습니다.

## 라이선스

[Apache License 2.0](LICENSE) — 자유롭게 사용하되, [NOTICE](NOTICE) 파일의 출처 표기를 포함해주세요.
