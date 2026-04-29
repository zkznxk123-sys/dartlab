---
title: Quick Start
---

# Quick Start

DartLab does three things: **Company**, **Scan**, **Ask**.

## Install

```bash
uv add dartlab
```

## 1. Company -- read any company

```python
import dartlab

c = dartlab.Company("005930")  # Samsung Electronics
```

Data is downloaded automatically on first use. No setup needed.

### Data freshness

- **첫 사용**: HuggingFace에서 자동 다운로드 (종목당 수 MB)
- **이후**: 24시간마다 HF 업데이트 자동 확인 (HTTP HEAD, 비용 거의 0)
- **대량 다운로드**: `dartlab.downloadAll("finance")` — 전체 종목 일괄 (`pip install dartlab[hf]`)
- **오프라인**: `dartlab.loadData("005930", refresh="local_only")` — 네트워크 체크 생략

## 2. See the whole company

```python
c.sections   # topic x period company map
c.topics     # what topics are available
```

## 3. Open any topic

```python
c.show("businessOverview")   # narrative text
c.show("companyOverview")    # company overview
```

## 4. Financial statements

```python
c.show("IS")       # Income Statement
c.show("BS")       # Balance Sheet
c.show("CF")       # Cash Flow
c.show("ratios")   # 47 financial ratios
```

## 5. Detect what changed

```python
c.diff()                    # which topics changed most
c.diff("businessOverview")  # drill into one topic
```

## 6. US companies -- same API

```python
apple = dartlab.Company("AAPL")
apple.show("IS")
apple.show("10-K::item1ARiskFactors")
```

## 7. Scan the market

```python
dartlab.search("삼성전자")              # find companies
dartlab.scan("ratio", "roe")           # ROE across all listed companies
dartlab.scan("account", "매출액")       # revenue across all companies
```

## 8. Ask AI

```bash
uv add "dartlab[llm]"
```

```python
dartlab.ask("Analyze Samsung Electronics financial health")
```

Requires a provider. Run `dartlab setup` for options (OpenAI, Ollama, ChatGPT OAuth).

## 실습

실습은 **[노트북 섹션](../tutorials/)** 에서. Colab / Molab / 로컬 마리모 — 같은 코드를 세 경로로 돌려볼 수 있다.

- [Notebooks →](../tutorials/)
- [Installation details](./installation)
