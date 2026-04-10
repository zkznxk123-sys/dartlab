<div align="center">

<br>

<img alt="DartLab" src=".github/assets/logo.png" width="180">

<h3>DartLab</h3>

<p><b>One stock code. The whole story.</b></p>
<p>DART + EDGAR filings, structured and comparable — in one line of Python.</p>

<p>
<a href="https://pypi.org/project/dartlab/"><img src="https://img.shields.io/pypi/v/dartlab?style=for-the-badge&color=ea4647&labelColor=050811&logo=pypi&logoColor=white" alt="PyPI"></a>
<a href="https://pypi.org/project/dartlab/"><img src="https://img.shields.io/pypi/pyversions/dartlab?style=for-the-badge&color=c83232&labelColor=050811&logo=python&logoColor=white" alt="Python"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-94a3b8?style=for-the-badge&labelColor=050811" alt="License"></a>
<a href="https://github.com/eddmpython/dartlab/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/eddmpython/dartlab/ci.yml?branch=master&style=for-the-badge&labelColor=050811&logo=github&logoColor=white&label=CI" alt="CI"></a>
<a href="https://codecov.io/gh/eddmpython/dartlab"><img src="https://img.shields.io/codecov/c/github/eddmpython/dartlab?style=for-the-badge&labelColor=050811&logo=codecov&logoColor=white&label=Coverage" alt="Coverage"></a>
<a href="https://eddmpython.github.io/dartlab/"><img src="https://img.shields.io/badge/Docs-GitHub_Pages-38bdf8?style=for-the-badge&labelColor=050811&logo=github-pages&logoColor=white" alt="Docs"></a>
<a href="https://eddmpython.github.io/dartlab/blog/"><img src="https://img.shields.io/badge/Blog-120%2B_Articles-fbbf24?style=for-the-badge&labelColor=050811&logo=rss&logoColor=white" alt="Blog"></a>
</p>

<p>
<a href="https://eddmpython.github.io/dartlab/">Docs</a> · <a href="https://eddmpython.github.io/dartlab/blog/">Blog</a> · <a href="https://huggingface.co/spaces/eddmpython/dartlab">Live Demo</a> · <a href="https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/01_company.ipynb">Open in Colab</a> · <a href="https://molab.marimo.io/github/eddmpython/dartlab/blob/master/notebooks/marimo/01_company.py">Open in Molab</a> · <a href="README.md">한국어</a> · <a href="https://buymeacoffee.com/eddmpython">Sponsor</a>
</p>

<p>
<a href="https://huggingface.co/datasets/eddmpython/dartlab-data"><img src="https://img.shields.io/badge/Data-HuggingFace-ffd21e?style=for-the-badge&labelColor=050811&logo=huggingface&logoColor=white" alt="HuggingFace Data"></a>
</p>

<a href="https://www.youtube.com/shorts/97lYLWMWzvA"><img src="https://img.youtube.com/vi/97lYLWMWzvA/maxresdefault.jpg" alt="DartLab Demo" width="320"></a>

</div>

## The Problem

Have you ever tried to compare Samsung's "Revenue" across five years?

Open a DART annual report and the same number appears as `ifrs-full_Revenue`, `dart_Revenue`, `매출액`, `영업수익` — four different names. Last year's table of contents doesn't match this year's. Comparing with SK Hynix means starting from scratch.

**The real problem isn't missing data. It's the same data existing under too many names.**

DartLab is built on one premise: **every period must be comparable, and every company must be comparable.** It normalizes disclosure sections into a topic-period grid (~95% mapping rate) and standardizes XBRL accounts into canonical names (~97% mapping rate) — so you compare companies, not filing formats.

## Quick Start

```bash
uv add dartlab

pip install dartlab              # core + AI (openai, gemini included)
pip install dartlab[server]      # + web server (FastAPI, MCP)
pip install dartlab[viz]         # + charts (Plotly)
pip install dartlab[all]         # everything
```

```python
import dartlab

c = dartlab.Company("005930")       # Samsung Electronics

c.sections                          # every topic, every period, side by side
# shape: (41, 12) — 41 topics across 12 periods
#                     2025Q4  2024Q4  2024Q3  2023Q4  ...
# companyOverview       v       v       v       v
# businessOverview      v       v       v       v
# riskManagement        v       v       v       v

c.show("businessOverview")          # what this company actually does
c.diff("businessOverview")          # what changed since last year
c.show("BS")                        # standardized balance sheet
c.show("ratios")                    # financial ratios, already calculated
#                     2025    2024    2023    ...
# ROE               15.7%   5.4%   -4.3%
# Operating Margin   21.4%   8.6%   -0.9%
# Debt Ratio        37.5%  36.5%   35.6%

# Same interface, different country
us = dartlab.Company("AAPL")
us.show("business")
us.show("ratios")

# Ask in natural language
dartlab.ask("Analyze Samsung Electronics financial health")
# → AI executes code and analyzes: "Operating margin rebounded from 8.6% to 21.4%..."
```

No API key needed. Data auto-downloads from [HuggingFace](https://huggingface.co/datasets/eddmpython/dartlab-data) on first use, then loads instantly from local cache.

## What DartLab Is

One calling convention. Each engine: `dartlab.engine()` for the guide, `dartlab.engine("axis")` to run.

> **New here?** Start with `Company` → `Review` → `Ask`. Load data, generate a report, then ask AI.

| Layer | Engine | What it does | Entry point | Notebook |
|-------|--------|--------------|-------------|:--------:|
| Data | [Data](ops/data.md) | Pre-built HuggingFace datasets, auto-download | `Company("005930")` | — |
| L0/L1 | [Company](ops/company.md) | Filings + financials + structured data unified by ticker | `c.show()`, `c.select()` | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/01_company.ipynb) [![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/01_company.py) |
| L1 | [Gather](ops/gather.md) | External market data (price, flow, macro, news) | `dartlab.gather()` | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/02_gather.ipynb) [![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/02_gather.py) |
| L1 | [Scan](ops/scan.md) | Cross-company comparison (governance, ratios, cashflow, ...) | `dartlab.scan()` | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/03_scan.ipynb) [![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/03_scan.py) |
| L1 | [Quant](ops/quant.md) | Technical & quantitative analysis (momentum/factor/pattern) | `c.quant()` | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/04_quant.ipynb) [![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/04_quant.py) |
| L2 | [Analysis](ops/analysis.md) | Profitability/stability/cashflow causal analysis + valuation + forecast | `c.analysis("financial", "수익성")` | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/05_analysis.ipynb) [![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/05_analysis.py) |
| L2 | [Macro](ops/macro.md) | Market-level macro (cycle/rates/liquidity/sentiment/assets) | `dartlab.macro("사이클")` | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/06_macro.ipynb) [![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/06_macro.py) |
| L2 | [Credit](ops/credit.md) | Independent credit rating (dCR grade, default probability, health) | `c.credit("등급")` | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/07_credit.ipynb) [![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/07_credit.py) |
| L2 | [Review](ops/review.md) | Composes analysis engines into a report (rich/html/markdown/json) | `c.review("수익성")` | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/08_review.ipynb) [![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/08_review.py) |
| L3 | [AI](ops/ai.md) | Active analyst — code execution + interpretation | `dartlab.ask()` | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/09_ai.ipynb) [![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/09_ai.py) |
| L4 | [Channel](ops/channel.md) | External sharing — `dartlab channel` brings PC dartlab to your phone | `dartlab channel` | — |
| core | [Search](ops/search.md) | Semantic filing search *(alpha)* | `dartlab.search()` | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/10_search.ipynb) [![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/10_search.py) |
| facade | [Listing](ops/listing.md) | Catalog API (companies, filings, topics) | `dartlab.listing()` | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/11_listing.ipynb) [![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/11_listing.py) |
| viz | [Viz](ops/viz.md) | Charts and diagrams (`emit_chart`) | `emit_chart({...})` | — |
| guide | [Guide](ops/guide.md) | Concierge — readiness, error handling, education | `dartlab.guide.checkReady()` | — |

> All notebooks: [marimo](notebooks/marimo/) · [colab](notebooks/colab/) · [![Open in marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo)

### Company

> Design: [ops/company.md](ops/company.md)

Three data sources — docs (full-text disclosures), finance (XBRL statements), report (DART API) — merged into one object. Data auto-downloads from [HuggingFace](https://huggingface.co/datasets/eddmpython/dartlab-data), no setup needed.

```python
c = dartlab.Company("005930")

c.index                         # what's available -- topic list + periods
c.show("BS")                    # view data -- DataFrame per topic
c.select("IS", ["매출액"])       # extract data -- finance or docs, same pattern
c.trace("BS")                   # where it came from -- source provenance
c.diff()                        # what changed -- text changes across periods
```

**Notes** — line items behind BS/IS totals. Access via `c.show("topic")`, same pattern as finance topics. Works for both DART (K-IFRS HTML parsing) and EDGAR (US-GAAP XBRL tags).

| `c.show(...)` | What it shows | DART | EDGAR |
|---------------|---------------|:----:|:-----:|
| `"inventory"` | Raw materials / work-in-progress / finished goods | ✅ | ✅ |
| `"borrowings"` | Short-term / long-term debt breakdown | ✅ | ✅ |
| `"tangibleAsset"` | PPE gross / net / depreciation | ✅ | ✅ |
| `"intangibleAsset"` | Goodwill / development costs | ✅ | ✅ |
| `"receivables"` | Trade receivables + allowance | ✅ | ✅ |
| `"provisions"` | Warranty / litigation / restructuring | ✅ | ✅ |
| `"eps"` | Basic / diluted EPS | ✅ | ✅ |
| `"segments"` | Revenue / profit by segment | ✅ | ✅ |
| `"costByNature"` | Raw materials / wages / depreciation | ✅ | ✅ |
| `"lease"` | Right-of-use assets / lease liabilities | ✅ | ✅ |
| `"affiliates"` | Equity method investments | ✅ | ✅ |
| `"investmentProperty"` | Fair value / carrying amount | ✅ | ✅ |

> [![marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/01_company.py) [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/01_company.ipynb)

### Scan — Cross-Company Comparison

> Design: [ops/scan.md](ops/scan.md)

Cross-company analysis across all listed firms. Governance, workforce, capital, debt, cashflow, audit, insider, quality, liquidity, network, account/ratio comparison, and more.

```python
dartlab.scan("governance")            # governance across all firms
dartlab.scan("ratio", "roe")          # ROE across all firms
dartlab.scan("cashflow")              # OCF/ICF/FCF + 8-pattern classification
```

### Gather — External Market Data

> Design: [ops/gather.md](ops/gather.md)

Price, flow, macro, news — all as Polars DataFrames.

```python
dartlab.gather("price", "005930")             # KR OHLCV
dartlab.gather("price", "AAPL", market="US")  # US stock
dartlab.gather("macro", "FEDFUNDS")           # auto-detects US
dartlab.gather("news", "삼성전자")             # Google News RSS
```

### Analysis — 14-Axis Financial Analysis

> Design: [ops/analysis.md](ops/analysis.md)

Revenue structure → profitability → growth → stability → cash flow → capital allocation → valuation → forecast. Turns raw statements into a causal narrative that feeds Review, AI, and direct human reading.

```python
c.analysis("financial", "수익성")       # profitability analysis
c.analysis("financial", "현금흐름")    # cash flow analysis

print(c.credit())                           # available-axes guide DataFrame (self-discovery)
c.credit("등급")                            # dCR-AA, healthScore 93/100
c.credit("등급", detail=True)               # grade + narrative + metrics
```

### Credit — Independent Credit Rating

> Design: [ops/credit.md](ops/credit.md) | Reports: [dartlab.pages.dev/blog/credit-reports](https://dartlab.pages.dev/blog/credit-reports)

Independent credit analysis with 3-Track model (general/financial/holding), Notch Adjustment, CHS market correction, and separate financial statement blending.

**79-company validation: large-cap 87% (26/30), mid-cap 82% (41/50), full sample 70% (55/79, re-measurement pending after v5.0 overvaluation fix). Samsung AA+ exact match.** See [methodology](docs/methodology.md) for validation details.

```python
print(c.credit())           # self-discovery — available axes + grade

cr = c.credit("등급")        # main grade
print(cr["grade"])          # dCR-AA+
print(cr["healthScore"])    # 96 (0-100, higher is better)
print(cr["pdEstimate"])     # 0.01% default probability

cr = c.credit("등급", detail=True)  # grade + narrative + metrics + divergence explanation
print(cr["divergenceExplanation"])  # why it differs from agencies
```

Publish reports (credit narrative + audit are auto-included in review's 5막):

```python
from dartlab.review.publisher import publishReport
publishReport("005930")               # 6막 report including credit narrative + audit
```

### Review — Analysis to Report

> Design: [ops/review.md](ops/review.md)

Assembles analysis into a structured report. 4 output formats: rich (terminal), html, markdown, json.

```python
c.review()              # full report
c.reviewer()            # report + AI interpretation
```

> Samsung report preview: *"Revenue +23.8%, operating margin 8.6%→21.4%. FCF turned positive, ROIC > WACC — reinvestment is creating value."*

**Sample reports:** [Samsung Electronics](docs/samples/005930.md) · [SK Hynix](docs/samples/000660.md) · [Kia](docs/samples/000270.md) · [HD Hyundai Heavy Industries](docs/samples/042660.md) · [SK Telecom](docs/samples/017670.md) · [LG Chem](docs/samples/051910.md) · [NCSoft](docs/samples/036570.md) · [Amorepacific](docs/samples/090430.md)

### Storyteller — Numbers Tell Stories

> Design: [ops/review.md](ops/review.md) · Series: [Company Stories](https://eddmpython.github.io/dartlab/blog/series/company-reports)

Financial analysis isn't ratio tables. DartLab combines 5 engines (analysis, credit, scan, quant, macro) into a **6-act storytelling structure** that auto-generates publishable company stories.

```python
from dartlab.review.publisher import publishReport
publishReport("068270")    # Celltrion — auto-publish 6-act company story
```

**Published stories:**

| Company | Story |
|---------|-------|
| [SK Hynix](https://eddmpython.github.io/dartlab/blog/000660-skhynix) | 30-year Korean semiconductor mystery, 58% operating margin |
| [Samyang Foods](https://eddmpython.github.io/dartlab/blog/003230-samyang-foods) | From last place in Korea's ramen Big 3 to a ₩2.3T global food giant |
| [Doosan Enerbility](https://eddmpython.github.io/dartlab/blog/034020-doosan-enerbility) | Debt ratio from 305% to 129% — the real story of a 9-year diet |
| [Alteogen](https://eddmpython.github.io/dartlab/blog/196170-alteogen) | 9 years of losses, then one license deal turned ₩106.9B operating profit |
| [HMM](https://eddmpython.github.io/dartlab/blog/011200-hmm) | The company where cycles, not markets, decide the stock price |
| [Celltrion](https://eddmpython.github.io/dartlab/blog/068270-celltrion) | Laid off at 41 during IMF crisis, started with $50K — 25 years later, ₩13.78T in intangibles |
| [Hanwha Aerospace](https://eddmpython.github.io/dartlab/blog/012450-hanwha-aerospace) | Samsung dumped it for ₩840B — now it has ₩37T in order backlog |
| [HD Hyundai Electric](https://eddmpython.github.io/dartlab/blog/267260-hd-hyundai-electric) | ₩100.6B loss 7 years ago became ₩1T this year — with one product: transformers |
| [Korea Zinc](https://eddmpython.github.io/dartlab/blog/010130-korea-zinc) | First net loss in 50 years at ₩245.7B, yet operating profit hit all-time high |
| [APR](https://eddmpython.github.io/dartlab/blog/278470-apr) | A cosmetics company sold ₩407B in home appliances — that was just the start |

<a href="https://www.youtube.com/watch?v=d7RUQIlimVM"><img src="https://img.youtube.com/vi/d7RUQIlimVM/hqdefault.jpg" alt="Celltrion Company Story" width="320"></a>

> [Watch Celltrion Story](https://www.youtube.com/watch?v=d7RUQIlimVM) · [DartLab 30s Demo](https://www.youtube.com/shorts/97lYLWMWzvA) · [YouTube Channel](https://www.youtube.com/@eddmpython)

### Search — Find Filings by Meaning *(alpha)*

> Design: [ops/search.md](ops/search.md)

No model, no GPU, no cold start. 95% precision on 4M documents — better than neural embeddings at 1/100th the cost. See [methodology](docs/methodology.md) for benchmark details.

```python
dartlab.search("유상증자 결정")                     # find capital raise filings
dartlab.search("대표이사 변경", corp="005930")       # filter by company
dartlab.search("회사가 돈을 빌렸다")                 # natural language works too
```

### AI — Active Analyst

> Design: [ops/ai.md](ops/ai.md)

The AI writes and executes Python code using dartlab's full API. You see every line of code it runs. 60+ questions validated, 95%+ first-try success. See [methodology](docs/methodology.md) for validation scope and limits.

```python
dartlab.ask("Analyze Samsung Electronics financial health")
dartlab.ask("Samsung analysis", provider="gemini")  # free providers available
```

Providers: `gemini` (free), `groq` (free), `cerebras` (free), `oauth-codex` (ChatGPT subscription), `openai`, `ollama` (local), and more. Auto-fallback across providers when rate-limited.

### Channel — Use your PC dartlab from anywhere

> Design: [ops/channel.md](ops/channel.md)

One command on your PC and dartlab UI works on your phone. Microsoft DevTunnels auto-setup.

```bash
dartlab channel
```

Flow:
1. winget auto-installs the devtunnel CLI (one-time)
2. GitHub OAuth (one-time, browser opens automatically)
3. Permanent URL + QR code (`https://<id>-8400.<region>.devtunnels.ms`)
4. Open the URL/QR on your phone Chrome → dartlab UI just works

Zero domains, zero token tricks. Same infrastructure as VS Code Remote Tunnels — verified mobile compatibility. Optional messaging bots: `--telegram/slack/discord`.

### Architecture

```
L0  core/        Protocols, finance utils, docs utils, registry
L1  providers/   Country-specific data (DART, EDGAR, EDINET)
    gather/      External market data (Naver, Yahoo, FRED)
    scan/        Market-wide analysis — scan("group", "axis")
    quant/       Technical analysis — c.quant()
L2  analysis/    Financial + forecast + valuation — analysis("group", "axis")
    credit/      Independent credit rating — c.credit()
    macro/       Market-level macro — dartlab.macro()
    review/      5-engine composition (analysis + credit + scan + quant + macro)
L3  ai/          Active analyst — dartlab.ask()
L4  vscode/      VSCode extension (dartlab chat --stdio)
    ui/web/      Svelte SPA web interface
```

Import direction enforced by CI. Adding a new country means one provider package — zero core changes.

#### Layer consumption flow

Who consumes whom across the stack:

```mermaid
flowchart TB
    subgraph L4["L4 · User interface"]
        UI["vscode / CLI / web"]
    end
    subgraph L3["L3 · LLM analyst"]
        AI["ai<br/>dartlab.ask()"]
    end
    subgraph L2["L2 · Analysis"]
        ANA["analysis<br/>causal financial + forecast + valuation"]
        CRD["credit<br/>independent rating"]
        MAC["macro<br/>market reading"]
        REV["review<br/>block-composed report"]
    end
    subgraph L1["L1 · Data ingestion"]
        PRV["providers<br/>DART / EDGAR / EDINET"]
        GAT["gather<br/>FRED / ECOS / Naver / Yahoo"]
        SCN["scan<br/>cross-market"]
        QNT["quant<br/>25 technical indicators"]
    end
    subgraph L0["L0 · Infrastructure"]
        CORE["core<br/>protocols + finance + docs + search"]
    end

    UI --> AI
    AI --> REV
    AI --> ANA
    AI --> MAC
    AI --> SCN
    REV --> ANA
    REV --> CRD
    REV --> SCN
    REV --> QNT
    REV --> MAC
    ANA --> PRV
    ANA --> GAT
    CRD --> PRV
    MAC --> GAT
    SCN --> PRV
    QNT --> GAT
    PRV --> CORE
    GAT --> CORE
    SCN --> CORE
    QNT --> CORE

    classDef l0 fill:#f5f5f5,stroke:#999
    classDef l1 fill:#e8f4ff,stroke:#4a90e2
    classDef l2 fill:#fff4e6,stroke:#e67e22
    classDef l3 fill:#f0e6ff,stroke:#8e44ad
    classDef l4 fill:#e6ffe6,stroke:#27ae60
    class CORE l0
    class PRV,GAT,SCN,QNT l1
    class ANA,CRD,MAC,REV l2
    class AI l3
    class UI l4
```

**Core rules**:
- Arrows always flow top → bottom (L4→L3→L2→L1→L0). Reverse imports forbidden (CI-enforced)
- L2 engines never import each other — analysis ↛ credit, macro ↛ analysis. Composition is review's or ai's job
- When adding a feature, pick the right layer first and let data flow in one direction only

## EDGAR (US)

Same interface, different data source. Auto-fetched from SEC API — no pre-download needed.

```python
# Korea (DART)                          # US (EDGAR)
c = dartlab.Company("005930")           c = dartlab.Company("AAPL")
c.sections                              c.sections
c.show("businessOverview")              c.show("business")
c.show("BS")                            c.show("BS")
c.show("ratios")                        c.show("ratios")
c.diff("businessOverview")              c.diff("10-K::item7Mdna")
```

## Macro — Economy Without a Ticker

> Design: [ops/macro.md](ops/macro.md)

No Company needed. Read the economy with `import dartlab`.

```python
dartlab.macro("사이클")          # Business cycle — 4 phases
dartlab.macro("금리")            # Rates + Nelson-Siegel yield curve
dartlab.macro("예측")            # LEI + Cleveland Fed probit + Hamilton RS + GDP Nowcast
dartlab.macro("위기")            # Credit-to-GDP gap + Minsky + Koo + Fisher
dartlab.macro("기업집계")        # Bottom-up: earnings cycle, Ponzi ratio, leverage
dartlab.macro("종합")            # Macro summary + investment strategies + portfolio allocation

# Scenario
dartlab.macro("사이클", overrides={"hy_spread": 600})

# Backtest
dartlab.macro("금리", as_of="2022-01-01")
```

Cycle, rates, assets, sentiment, liquidity, forecast, crisis, inventory, corporate, trade signals — global macro methods (Hamilton EM, Kalman DFM, Nelson-Siegel, Cleveland Fed probit, Sahm Rule, BIS Credit-to-GDP, GHS, Minsky, Koo, Fisher, Cu/Au, FCI) implemented in **numpy only** (zero statsmodels/scipy).

Backtest result (2000-2024, FRED): Cleveland Fed probit detected **3/3 US recessions** with 2-16 month lead time, recall 90% at threshold 0.20.

## MCP — AI Assistant Integration

Built-in [MCP](https://modelcontextprotocol.io/) server for Claude Desktop, Claude Code, Cursor, and any MCP-compatible client.

```bash
# Claude Code — one line setup
claude mcp add dartlab -- uv run dartlab mcp

# Codex CLI
codex mcp add dartlab -- uv run dartlab mcp
```

<details>
<summary>Claude Desktop / Cursor config</summary>

Add to `claude_desktop_config.json` or `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "dartlab": {
      "command": "uv",
      "args": ["run", "dartlab", "mcp"]
    }
  }
}
```

Or auto-generate: `dartlab mcp --config claude-desktop`

</details>

## OpenAPI — Raw Public APIs

```python
from dartlab import OpenDart, OpenEdgar

# Korea (requires free API key from opendart.fss.or.kr)
d = OpenDart()
d.filings("삼성전자", "2024")
d.finstate("삼성전자", 2024)

# US (no API key needed)
e = OpenEdgar()
e.filings("AAPL", forms=["10-K", "10-Q"])
```

## Data

All data is pre-built on [HuggingFace](https://huggingface.co/datasets/eddmpython/dartlab-data) — auto-downloads on first use. EDGAR data comes directly from the SEC API.

| Dataset | Coverage | Size |
|---------|----------|------|
| DART docs | 2,500+ companies | ~8 GB |
| DART finance | 2,700+ companies | ~600 MB |
| DART report | 2,700+ companies | ~320 MB |
| EDGAR | On-demand | SEC API |

Pipeline: local cache (instant) → HuggingFace (auto-download) → DART API (with your key). Most users never leave the first two.

## Try It Now

**[Live Demo](https://huggingface.co/spaces/eddmpython/dartlab)** — no install, no Python

**Notebooks:** [Company](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/01_company.ipynb) · [Scan](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/02_scan.ipynb) · [Review](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/03_review.ipynb) · [Gather](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/04_gather.ipynb) · [Analysis](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/05_analysis.ipynb) · [Ask (AI)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/06_ask.ipynb)

## Documentation

[Docs](https://eddmpython.github.io/dartlab/) · [Quick Start](https://eddmpython.github.io/dartlab/docs/getting-started/quickstart) · [API Overview](https://eddmpython.github.io/dartlab/docs/api/overview)

**Blog (120+ articles):** [All](https://eddmpython.github.io/dartlab/blog/) · [Company Stories](https://eddmpython.github.io/dartlab/blog/series/company-reports) · [Credit Reports](https://eddmpython.github.io/dartlab/blog/credit-reports) · [Macro Reports](https://eddmpython.github.io/dartlab/blog/macro-reports)

## Stability

| Tier | Scope |
|------|-------|
| **Stable** | DART Company (sections, show, trace, diff, BS/IS/CF, CIS, index, filings, profile), EDGAR Company core, valuation, forecast, simulation |
| **Beta** | EDGAR power-user (SCE, notes, freq, coverage), credit, insights, distress, ratios, timeseries, network, governance, workforce, capital, debt, chart/table/text tools, ask/chat, OpenDart, OpenEdgar, Server API, MCP |
| **Experimental** | AI tool calling, export, viz (charts) |

See [docs/stability.md](docs/stability.md).

## Contributing

**Contributors are very welcome.** Whether it's a bug report, a new analysis axis, a mapping fix, or a documentation improvement — every contribution makes dartlab better for everyone.

The one rule: **experiment first, engine second.** Validate your idea in `experiments/` before changing the engine. This keeps the core stable while making it easy to try bold ideas.

- **Experiment folder**: `experiments/XXX_name/` — each file must be independently runnable with actual results in its docstring
- **Data contributions** (e.g. `accountMappings.json`, `sectionMappings.json`): accepted when backed by experiment evidence
- Issues and PRs in Korean or English are both welcome
- Not sure where to start? Open an issue — we'll help you find the right place

## License

MIT
