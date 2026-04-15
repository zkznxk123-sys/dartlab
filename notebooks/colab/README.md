# DartLab Colab 노트북

13개 엔진별 노트북. 각 노트북은 **가이드 호출 + 1 예시** 의 최소 단위.

dartlab 호출 계약은 단순하다 — 무인자 호출로 어떤 축이 있는지 본 후 단일 예시로 실제 데이터를 받는다.

## 노트북 (레이어 순)

| # | 노트북 | 엔진 | ops 문서 | Colab |
|---|---|---|---|---|
| 01 | [01_company.ipynb](01_company.ipynb) | Company facade (L0/L1) | [src/dartlab/README.md](src/dartlab/README.md) | [![Open](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/01_company.ipynb) |
| 02 | [02_gather.ipynb](02_gather.ipynb) | gather (L1) | [src/dartlab/gather/README.md](src/dartlab/gather/README.md) | [![Open](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/02_gather.ipynb) |
| 03 | [03_scan.ipynb](03_scan.ipynb) | scan (L1) | [src/dartlab/scan/README.md](src/dartlab/scan/README.md) | [![Open](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/03_scan.ipynb) |
| 04 | [04_quant.ipynb](04_quant.ipynb) | quant (L1) | [src/dartlab/quant/README.md](src/dartlab/quant/README.md) | [![Open](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/04_quant.ipynb) |
| 05 | [05_analysis.ipynb](05_analysis.ipynb) | analysis (L2) | [src/dartlab/analysis/README.md](src/dartlab/analysis/README.md) | [![Open](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/05_analysis.ipynb) |
| 06 | [06_macro.ipynb](06_macro.ipynb) | macro (L2) | [src/dartlab/macro/README.md](src/dartlab/macro/README.md) | [![Open](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/06_macro.ipynb) |
| 07 | [07_credit.ipynb](07_credit.ipynb) | credit (L2) | [src/dartlab/analysis/CREDIT.md](src/dartlab/analysis/CREDIT.md) | [![Open](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/07_credit.ipynb) |
| 08 | [08_review.ipynb](08_review.ipynb) | review (L2) | [src/dartlab/review/README.md](src/dartlab/review/README.md) | [![Open](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/08_review.ipynb) |
| 09 | [09_ai.ipynb](09_ai.ipynb) | ai (L3) | [src/dartlab/ai/README.md](src/dartlab/ai/README.md) | [![Open](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/09_ai.ipynb) |
| 10 | [10_search.ipynb](10_search.ipynb) | search | [src/dartlab/core/search/README.md](src/dartlab/core/search/README.md) | [![Open](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/10_search.ipynb) |
| 11 | [11_listing.ipynb](11_listing.ipynb) | listing | [src/dartlab/gather/LISTING.md](src/dartlab/gather/LISTING.md) | [![Open](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/11_listing.ipynb) |
| 12 | [12_viz.ipynb](12_viz.ipynb) | viz | [ops/viz.md](../../ops/viz.md) | [![Open](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/12_viz.ipynb) |
| 13 | [13_guide.ipynb](13_guide.ipynb) | guide | [src/dartlab/guide/README.md](src/dartlab/guide/README.md) | [![Open](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/13_guide.ipynb) |

## 호출 계약 — 모든 엔진 동일

```python
import dartlab
dartlab.엔진()        # 가이드 — 어떤 축이 있는지 출력
dartlab.엔진("축")    # 단일 예시
```

각 엔진의 자세한 사용법은 ops 문서 링크 참조.
