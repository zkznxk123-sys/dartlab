"""증권사 리서치 메타 로컬 parquet I/O — pub_date 월별 파티션 + report_id dedup.

수집 메타를 ``data/research/brokerage/{YYYYMM}.parquet`` 로 병합 기록(report_id 중복 제거)하고,
변경된 월 파일의 상대경로를 돌려준다 — sync 가 그걸 changed manifest 로 써서 증분 HF 업로드.
별도빌드 금지: 파티션/병합 로직은 본 source 가 소유(sync 는 호출만).
"""

from __future__ import annotations

import os
from pathlib import Path

import polars as pl

from dartlab.core.dataConfig import DATA_RELEASES

from .schema import _COLUMNS

_CATEGORY = "brokerageReports"


def _dataDir() -> Path:
    """``{DARTLAB_DATA_DIR|data}/research/brokerage`` 디렉터리(없으면 생성). hfUpload 와 동일 base."""
    base = Path(os.environ.get("DARTLAB_DATA_DIR") or "data")
    d = base / DATA_RELEASES[_CATEGORY]["dir"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def writeMonthly(df: pl.DataFrame) -> list[str]:
    """리포트 메타 DataFrame 을 pub_date 월별 parquet 로 병합 기록하고 변경 상대경로 반환.

    Capabilities:
        - pub_date(YYYY-MM-DD) → YYYYMM 버킷별로 분할.
        - 기존 월 파일이 있으면 concat 후 report_id 기준 중복 제거(재수집 idempotent).
        - 발간일 내림차순 정렬 후 ``{YYYYMM}.parquet`` 기록.

    AIContext:
        - 본문 0 — 메타만 적재(제목·URL·날짜·구분·종목). 링크아웃 대상.
        - 반환 상대경로는 changed manifest 입력(증분 HF 업로드 SSOT).

    Guide:
        sync 스크립트가 gather 수집 결과(g.brokerageReports())를 그대로 넘겨 호출.

    When:
        일별/증분 sync 시 또는 과거 백필 시.

    How:
        pub_date≥7자만 채택 → ``group_by(YYYYMM)`` → 월 파일 merge(unique report_id) → write.

    Args:
        df: report_id·broker·title·pub_date 등 PRD 스키마 DataFrame.

    Returns:
        list[str] — 변경된 월 파일 상대경로(예: ``["202606.parquet"]``). 빈 입력은 ``[]``.

    Requires:
        polars + 쓰기 가능한 ``data/research/brokerage`` 경로.

    Raises:
        없음 — 빈/이상 날짜 행은 skip.

    Example::

        from dartlab.gather.sources.brokerage.io import writeMonthly
        changed = writeMonthly(df)   # ["202606.parquet"]

    See Also:
        loadLocal : 기록된 월 parquet 을 다시 읽는다.
        dartlab.pipeline.changed.writeChanged : 반환값을 manifest 로 기록.
    """
    if df.is_empty():
        return []
    base = _dataDir()
    work = df.filter(pl.col("pub_date").str.len_chars() >= 7).with_columns(
        pl.col("pub_date").str.replace_all("-", "").str.slice(0, 6).alias("_ym")
    )
    changed: list[str] = []
    for (ym,), grp in work.group_by("_ym", maintain_order=True):
        if not ym or len(str(ym)) < 6:
            continue
        part = grp.drop("_ym").select(_COLUMNS)
        fp = base / f"{ym}.parquet"
        if fp.exists():
            merged = pl.concat([pl.read_parquet(fp), part]).unique(subset="report_id", keep="last")
        else:
            merged = part
        merged.sort("pub_date", descending=True).write_parquet(fp)
        changed.append(f"{ym}.parquet")
    return changed


def loadLocal() -> pl.DataFrame:
    """로컬에 기록된 모든 월 parquet 을 합쳐 반환(발간일 내림차순). 없으면 빈 DataFrame.

    Capabilities:
        - ``data/research/brokerage/*.parquet`` 전부 read + concat + 발간일 정렬.

    AIContext:
        - 오프라인/로컬 검증용 read 경로. 공개 HF 직독은 bulkData 경유(별도).

    Guide:
        sync 직후 적재 결과 확인, 테스트 검증에 사용.

    When:
        로컬 빌드 검증 / 디버깅 시.

    How:
        glob ``*.parquet`` → ``pl.read_parquet`` 각각 → concat → sort.

    Args:
        없음.

    Returns:
        pl.DataFrame — 전 월 합본(발간일 내림차순). 파일 없으면 빈 DataFrame(스키마 0열).

    Requires:
        polars + ``data/research/brokerage`` (없으면 빈 결과).

    Raises:
        없음.

    Example::

        from dartlab.gather.sources.brokerage.io import loadLocal
        df = loadLocal()

    See Also:
        writeMonthly : 본 함수가 읽는 월 parquet 생산자.
    """
    base = _dataDir()
    files = sorted(base.glob("*.parquet"))
    if not files:
        return pl.DataFrame()
    frames = [pl.read_parquet(f) for f in files]
    return pl.concat(frames).sort("pub_date", descending=True)
