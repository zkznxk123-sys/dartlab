"""filings.build — BUILD-time sections artifact 빌더 (메모리 무관, runtime import 금지).

zip / docs.parquet → walker (ACLASS 추출, 손실0/중복0) → canonical 키 부착 →
period-sharded parquet write (``data/dart/sections/{code}/{period}.parquet``).

구성:
    - ``walker`` — container/emit 규칙 walker (raw XML 무손실).
    - ``builder`` — 종목별 zip → period split 빌더 entry.
    - ``canonical`` — xbrlClass → disclosureKey (bridge lookup).
    - ``bridge`` — bridge SSOT loader + tier1 seed (~60).
    - ``refScan`` — ACLASS ref table scanner (옛 양식 fuzzy match 지원).

⚠️ 이 패키지는 lxml/zip 을 import 한다 — runtime (``filings.sections``) 에서 import 금지.
사용자/CI 빌드 단계에서만 실행.
"""

from __future__ import annotations

__all__: list[str] = []
