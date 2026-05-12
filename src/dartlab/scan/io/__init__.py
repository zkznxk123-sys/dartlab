"""scan 데이터 로더 + 엔진 선택 — io 격리 폴더.

`parquet.py` (former `parquetLoad.py`) 와 `cross.py` (former `crossScanEngine.py`)
를 SSOT 폴더로 묶는다. scan 의 모든 prebuild parquet 적재 경로는 본 폴더 경유.
"""

from __future__ import annotations
