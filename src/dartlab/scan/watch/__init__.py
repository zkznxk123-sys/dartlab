"""공시 변화 감지 엔진 — sections diff 기반 자동 스캔 + 중요도 스코어링.

sections 수평화 위에 구축된 변화 감지 시스템.
Bloomberg에 없는 기능: 서술형 공시 텍스트의 자동 변화 추적.

사용법::

    import dartlab

    # 단일 기업
    c = dartlab.Company("005930")
    c.watch()                       # 전체 topic 변화 요약 (중요도 순)
    c.watch("riskManagement")       # 특정 topic 상세

    # 시장 다이제스트
    dartlab.digest()                # 전체 시장 TOP 변화
    dartlab.digest(sector="반도체")  # 섹터별
"""

from dartlab.scan.watch.digest import buildDigest
from dartlab.scan.watch.scanner import scanCompany, scanMarket
from dartlab.scan.watch.scorer import scoreChanges


def scanDigest(*, format: str = "dataframe", topN: int = 30, **kwargs) -> object:
    """시장 전체 공시 변화 다이제스트 (scan_market + build_digest 래핑).

    Parameters
    ----------
    format : str, default "dataframe"
        출력 형식. "dataframe" | "markdown" | "json".
    topN : int, default 30
        포함할 최대 항목 수.
    **kwargs
        ``scanMarket`` 에 전달할 추가 인자.

    Returns
    -------
    pl.DataFrame | str | dict
        format 에 따라 반환 타입이 달라진다.

    Raises
    ------
    polars.PolarsError
        scanMarket / buildDigest 가 발생시키는 예외 전파.

    Examples
    --------
    >>> import dartlab
    >>> df = dartlab.scan("digest", format="dataframe", topN=10)

    Capabilities:
        - 시장 전체 공시 변화 (`scanMarket`) → 중요도 스코어 (`scoreChanges`) → 다이제스트
          형식 변환 (`buildDigest`). format = dataframe/markdown/json 3 종.
        - Bloomberg / 기존 데이터 서비스가 다루지 않는 서술형 공시 변화 자동 추적.

    AIContext:
        Agent 가 ``dartlab.scan("digest")`` 또는 ``dartlab.digest()`` 호출 시 본 함수 dispatch.
        "오늘 시장에 무슨 일이 있었지?" 류 시장 전체 변화 요약 source.

    Guide:
        - topN 보통 30 정도. 너무 크면 noise, 너무 작으면 중요 신호 누락.
        - format="markdown" 은 사람이 읽기 좋고, "dataframe" 은 추가 분석에, "json" 은 API
          페이로드에 적합.

    When:
        시장 전체 공시 변화 빌드 시. 일일 시장 요약 / 디지털 트레이딩 노트.

    How:
        scanMarket(topN, **kwargs) → 중요도 score 가 포함된 df → buildDigest 가 format 별 변환.

    Requires:
        - 로컬 ``data/dart/scan/changes.parquet`` (``buildChanges`` 산출)
        - ``scanMarket`` · ``scoreChanges`` · ``buildDigest``

    SeeAlso:
        - :func:`dartlab.scan.watch.scanner.scanCompany` — 단일 기업 변화 요약 (보완)
        - :func:`dartlab.scan.watch.scorer.scoreChanges` — 중요도 스코어링 SSOT
        - :func:`dartlab.scan.builders.kr.core.buildChanges` — 본 함수의 raw source
    """
    df = scanMarket(topN=topN, **kwargs)
    return buildDigest(df, format=format, topN=topN)


__all__ = ["scan_company", "scan_market", "score_changes", "build_digest", "scanDigest"]
