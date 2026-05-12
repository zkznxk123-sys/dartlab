"""scan 프리빌드 빌더 — KR (DART) · EDGAR (US) 대칭 폴더.

`kr/` 는 기존 `scan/builder/` 본체 (DART finance/report/docs 합산 + scan parquet
생성), `edgar/` 는 EDGAR XBRL 기반 axis 구현. 두 시장 빌드 진입을 동일 계층에
노출 (P-S3 대칭화).
"""

from __future__ import annotations
