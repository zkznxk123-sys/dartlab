"""HuggingFace 데이터셋 README 업로드."""

from huggingface_hub import HfApi

token = None
for line in open(".env", encoding="utf-8"):
    line = line.strip()
    if line.startswith("HF_TOKEN="):
        token = line.split("=", 1)[1].strip()
        break

README = r"""---
license: apache-2.0
task_categories:
  - table-question-answering
  - text-classification
language:
  - ko
  - en
tags:
  - finance
  - disclosure
  - dart
  - edgar
  - sec
  - xbrl
  - korea
  - financial-statements
  - corporate-filings
  - 전자공시
  - 재무제표
  - 사업보고서
  - 한국
pretty_name: DartLab 전자공시 데이터
size_categories:
  - 1K<n<10K
---

<div align="center">

<br>

<img alt="DartLab" src="https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main/assets/logo.png" width="160">

<h3>DartLab Data</h3>

<p><b>Structured company data from DART & EDGAR disclosure filings</b></p>
<p>DART 전자공시 + EDGAR 공시 데이터 — 한국 2,700사 / 미국 970사</p>

<p>
<a href="https://github.com/eddmpython/dartlab"><img src="https://img.shields.io/badge/GitHub-dartlab-ea4647?style=for-the-badge&labelColor=050811&logo=github&logoColor=white" alt="GitHub"></a>
<a href="https://pypi.org/project/dartlab/"><img src="https://img.shields.io/pypi/v/dartlab?style=for-the-badge&color=ea4647&labelColor=050811&logo=pypi&logoColor=white" alt="PyPI"></a>
<a href="https://eddmpython.github.io/dartlab/"><img src="https://img.shields.io/badge/Docs-GitHub_Pages-38bdf8?style=for-the-badge&labelColor=050811&logo=github-pages&logoColor=white" alt="Docs"></a>
<a href="https://buymeacoffee.com/eddmpython"><img src="https://img.shields.io/badge/Sponsor-Buy_Me_A_Coffee-ffdd00?style=for-the-badge&labelColor=050811&logo=buy-me-a-coffee&logoColor=white" alt="Sponsor"></a>
</p>

</div>

## What is this?

<img align="right" src="https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main/assets/avatar-study.png" width="120">

Pre-collected [Parquet](https://parquet.apache.org/) files from [DartLab](https://github.com/eddmpython/dartlab) — a Python library that turns DART (Korea) and EDGAR (US) disclosure filings into one structured company map.

한국 DART 전자공시 시스템과 미국 SEC EDGAR에서 수집한 기업 공시 데이터입니다.

This dataset is the **data layer** behind DartLab. When you run `dartlab.Company("005930")`, the library automatically downloads the relevant parquet from this repo.

## Dataset Structure

```
dart/
├── panel/         DART disclosure panel (horizontalized filings)
├── finance/       financial statements (BS, IS, CF, XBRL)
└── report/        structured disclosure APIs (28 types)
```

Each file is one company: `{stockCode}.parquet`

### panel — Disclosure Panel

DART periodic reports horizontalized into a company-level panel. Narrative text and XBRL-linked tables share one artifact so the viewer, search, and comparison tools use the same source.

| Column | Description |
|--------|------------|
| `corp` | Stock code |
| `period` | Period key (`YYYYQn`) |
| `rceptNo` | DART filing ID |
| `chapter` | Top-level report chapter |
| `sectionLeaf` | Native section title |
| `sectionPath` | Full native section path |
| `leafType` | `text` / `table` |
| `blockLeaf` | Block or table title |
| `xbrlClass` | Native DART XBRL class |
| `disclosureKey` | Canonical horizontalization key |
| `contentRaw` | Source-preserving XML/text payload |

### finance — Financial Statements

XBRL-based financial data from DART OpenAPI (`fnlttSinglAcntAll`).

| Column | Description |
|--------|------------|
| `bsns_year` | Business year |
| `reprt_code` | Report quarter code |
| `stock_code` | Stock code |
| `corp_name` | Company name |
| `fs_div` | `CFS` (consolidated) / `OFS` (separate) |
| `sj_div` | Statement type (BS/IS/CF/SCE) |
| `account_id` | XBRL account ID |
| `account_nm` | Account name (Korean) |
| `thstrm_amount` | Current period amount |
| `frmtrm_amount` | Prior period amount |
| `bfefrmtrm_amount` | Two periods prior amount |

### report — Structured Disclosure APIs

28 DART API categories covering governance, compensation, shareholding, and more.

| Column | Description |
|--------|------------|
| `apiType` | API category (e.g., `dividend`, `employee`, `executive`) |
| `year` | Year |
| `quarter` | Quarter |
| `stockCode` | Stock code |
| `corpCode` | DART corp code |
| *(varies)* | Category-specific columns |

**28 API types:** dividend, employee, executive, majorHolder, treasuryStock, capitalChange, auditOpinion, stockTotal, outsideDirector, corporateBond, and more.

## Learn More

<img align="right" src="https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main/assets/avatar-analyze.png" width="120">

DartLab auto-downloads from this dataset — one stock code gives you the full company map. Start with the intro below.

<div align="center">

<a href="https://www.youtube.com/shorts/97lYLWMWzvA"><img src="https://img.youtube.com/vi/97lYLWMWzvA/maxresdefault.jpg" alt="DartLab 30s Demo" width="320"></a>

<sub>▶ <a href="https://www.youtube.com/shorts/97lYLWMWzvA">DartLab 30s Demo</a></sub>

</div>

- **GitHub** — [github.com/eddmpython/dartlab](https://github.com/eddmpython/dartlab)
- **Intro blog** — [DartLab 시작하기 / Getting started](https://eddmpython.github.io/dartlab/blog/dartlab-easy-start)
- **Docs** — [eddmpython.github.io/dartlab](https://eddmpython.github.io/dartlab/)
- **YouTube** — [@eddmpython](https://www.youtube.com/@eddmpython)

<img align="right" src="https://huggingface.co/datasets/eddmpython/dartlab-data/resolve/main/assets/avatar-discover.png" width="120">

## Data Source

- **DART** (Korea): [dart.fss.or.kr](https://dart.fss.or.kr) — Korea's electronic disclosure system operated by the Financial Supervisory Service
- **EDGAR** (US): [sec.gov/edgar](https://www.sec.gov/edgar) — SEC's Electronic Data Gathering, Analysis, and Retrieval system

All data is sourced from public government disclosure systems. Financial figures are preserved as-is from the original filings — no rounding, no estimation, no interpolation.

## Update Schedule

This dataset is updated automatically via GitHub Actions (daily). Recent filings (last 7 days) are checked and collected incrementally.

## License

Apache 2.0 — same as [DartLab](https://github.com/eddmpython/dartlab).

## Support

If DartLab is useful for your work, consider supporting the project:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy_Me_A_Coffee-Support-ffdd00?style=for-the-badge&labelColor=050811&logo=buy-me-a-coffee&logoColor=white)](https://buymeacoffee.com/eddmpython)

- [GitHub Issues](https://github.com/eddmpython/dartlab/issues) — bug reports, feature requests
- [Blog](https://eddmpython.github.io/dartlab/blog/) — 120+ articles on Korean disclosure analysis
"""

api = HfApi(token=token)
api.upload_file(
    repo_id="eddmpython/dartlab-data",
    repo_type="dataset",
    path_or_fileobj=README.encode("utf-8"),
    path_in_repo="README.md",
    commit_message="update sponsor link to buymeacoffee.com/eddmpython",
)
print("README.md 업로드 완료")
