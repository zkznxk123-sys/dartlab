# DartLab Marimo 노트북

13개 엔진별 노트북. 각 노트북은 **가이드 호출 + 1 예시** 의 최소 단위.

dartlab 호출 계약은 단순하다 — 무인자 호출로 어떤 축이 있는지 본 후 단일 예시로 실제 데이터를 받는다. 나머지는 사용자가 추론한다.

## 노트북 (레이어 순)

| # | 노트북 | 엔진 | ops 문서 |
|---|---|---|---|
| 01 | [01_company.py](01_company.py) | Company facade (L0/L1) | [src/dartlab/README.md](src/dartlab/README.md) |
| 02 | [02_gather.py](02_gather.py) | gather — 외부 시장 데이터 (L1) | [src/dartlab/gather/README.md](src/dartlab/gather/README.md) |
| 03 | [03_scan.py](03_scan.py) | scan — 전종목 횡단 (L1) | [src/dartlab/scan/README.md](src/dartlab/scan/README.md) |
| 04 | [04_quant.py](04_quant.py) | quant — 정량 (L1) | [src/dartlab/quant/README.md](src/dartlab/quant/README.md) |
| 05 | [05_analysis.py](05_analysis.py) | analysis — 14축 재무분석 (L2) | [src/dartlab/analysis/README.md](src/dartlab/analysis/README.md) |
| 06 | [06_macro.py](06_macro.py) | macro — 매크로 (L2) | [src/dartlab/macro/README.md](src/dartlab/macro/README.md) |
| 07 | [07_credit.py](07_credit.py) | credit — 신용분석 (L2) | [src/dartlab/analysis/CREDIT.md](src/dartlab/analysis/CREDIT.md) |
| 08 | [08_review.py](08_review.py) | review — 4엔진 조합 (L2) | [src/dartlab/review/README.md](src/dartlab/review/README.md) |
| 09 | [09_ai.py](09_ai.py) | ai — ask/chat (L3) | [src/dartlab/ai/README.md](src/dartlab/ai/README.md) |
| 10 | [10_search.py](10_search.py) | search — 공시 원문 검색 | [src/dartlab/core/search/README.md](src/dartlab/core/search/README.md) |
| 11 | [11_listing.py](11_listing.py) | listing — 카탈로그 | [src/dartlab/gather/LISTING.md](src/dartlab/gather/LISTING.md) |
| 12 | [12_viz.py](12_viz.py) | viz — 차트/다이어그램 | [ops/viz.md](../../ops/viz.md) |
| 13 | [13_guide.py](13_guide.py) | guide — 안내 데스크 | [src/dartlab/guide/README.md](src/dartlab/guide/README.md) |

## 실행

```bash
pip install marimo dartlab
marimo edit notebooks/marimo/05_analysis.py
```

또는 marimo.app 에서 바로 열기:

[![Open in marimo](https://marimo.io/shield.svg)](https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo)

## 호출 계약 — 모든 엔진 동일

```python
import dartlab
dartlab.엔진()        # 가이드 — 어떤 축이 있는지 출력
dartlab.엔진("축")    # 단일 예시
```

각 엔진의 자세한 사용법은 ops 문서 링크 참조.
