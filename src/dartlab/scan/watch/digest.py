"""시장 변화 다이제스트 생성.

scan_market 결과를 마크다운/JSON/DataFrame 형태의 요약 다이제스트로 변환한다.

사용법::

    from dartlab.scan.watch.digest import build_digest

    df = scan_market(top_n=30)
    md = build_digest(df, format="markdown")
    _log.info(md)
"""

from __future__ import annotations

from datetime import date

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


import polars as pl


def buildDigest(
    scanDf: pl.DataFrame,
    *,
    title: str | None = None,
    format: str = "markdown",
    topN: int = 20,
) -> str | pl.DataFrame | dict:
    """스캔 결과에서 다이제스트를 생성한다.

    score 내림차순으로 정렬한 뒤 top_n개를 선택하여
    지정 format으로 변환한다.

    Parameters
    ----------
    scan_df : pl.DataFrame
        scan_market() 결과 DataFrame. 필수 컬럼: score.
        선택 컬럼: stockCode, corpName, topic, changeRate,
        latestPeriod, reason, deltaBytes.
    title : str | None
        다이제스트 제목. None이면 날짜 기반 자동 생성.
    format : str
        출력 형식. "markdown" | "json" | "dataframe".
    top_n : int
        다이제스트에 포함할 최대 항목 수.

    Returns
    -------
    str | dict | pl.DataFrame
        format에 따라 반환 타입이 달라진다.

        - ``"markdown"`` → str — 마크다운 문자열 (기업별 그룹핑, 배지 포함)
        - ``"json"`` → dict:
            - title : str — 다이제스트 제목
            - date : str — 생성일 (ISO 8601)
            - count : int — 항목 수
            - items : list[dict] — 각 항목 (stockCode, corpName, topic,
              score(점), changeRate(비율), deltaBytes(바이트),
              latestPeriod, reason)
        - ``"dataframe"`` → pl.DataFrame — score 내림차순 상위 top_n행
    """
    if scanDf.height == 0:
        if format == "dataframe":
            return scanDf
        if format == "json":
            return {"title": title or "변화 없음", "date": str(date.today()), "items": []}
        return f"# {title or '시장 변화 다이제스트'}\n\n변화가 감지되지 않았습니다.\n"

    df = scanDf.sort("score", descending=True).head(topN)

    if format == "dataframe":
        return df

    if format == "json":
        return _toJson(df, title)

    return _toMarkdown(df, title)


def _toMarkdown(df: pl.DataFrame, title: str | None) -> str:
    """DataFrame을 마크다운 형식 다이제스트 문자열로 변환한다.

    기업별로 그룹핑하여 score 배지, 변화율, 기간, 근거를 포함한
    계층형 마크다운을 생성한다.

    Parameters
    ----------
    df : pl.DataFrame
        score 내림차순 정렬된 스캔 결과.
    title : str | None
        다이제스트 제목. None이면 날짜 기반 자동 생성.

    Returns
    -------
    str
        마크다운 형식 다이제스트 문자열.
    """
    today = date.today().isoformat()
    header = title or f"시장 변화 다이제스트 ({today})"

    lines = [f"# {header}\n"]

    # 기업별 그룹핑
    if "stockCode" in df.columns and "corpName" in df.columns:
        grouped = df.group_by(["stockCode", "corpName"], maintain_order=True)
        for (stockCode, corpName), group_df in grouped:
            name_label = corpName if corpName else stockCode
            lines.append(f"\n## {name_label} ({stockCode})\n")
            for row in group_df.iter_rows(named=True):
                score = row.get("score", 0)
                topic = row.get("topic", "")
                reason = row.get("reason", "")
                change_rate = row.get("changeRate", 0)
                period = row.get("latestPeriod", "")

                badge = _scoreBadge(score)
                lines.append(f"- {badge} **{topic}** (score: {score:.1f}, 변화율: {change_rate:.1%})")
                if period:
                    lines.append(f"  - 기간: {period}")
                if reason:
                    lines.append(f"  - 근거: {reason}")
    else:
        for row in df.iter_rows(named=True):
            score = row.get("score", 0)
            topic = row.get("topic", "")
            reason = row.get("reason", "")
            badge = _scoreBadge(score)
            lines.append(f"- {badge} **{topic}** (score: {score:.1f}) — {reason}")

    lines.append(f"\n---\n생성일: {today}\n")
    return "\n".join(lines)


def _toJson(df: pl.DataFrame, title: str | None) -> dict:
    """DataFrame을 JSON-직렬화 가능한 dict로 변환한다.

    Parameters
    ----------
    df : pl.DataFrame
        score 내림차순 정렬된 스캔 결과.
    title : str | None
        다이제스트 제목. None이면 날짜 기반 자동 생성.

    Returns
    -------
    dict
        - title : str — 다이제스트 제목
        - date : str — 생성일 (ISO 8601)
        - count : int — 항목 수
        - items : list[dict] — 각 항목별 stockCode, corpName,
          topic, score(점), changeRate(비율), deltaBytes(바이트),
          latestPeriod, reason
    """
    today = date.today().isoformat()
    items = []
    for row in df.iter_rows(named=True):
        items.append(
            {
                "stockCode": row.get("stockCode", ""),
                "corpName": row.get("corpName", ""),
                "topic": row.get("topic", ""),
                "score": round(row.get("score", 0), 1),
                "changeRate": round(row.get("changeRate", 0), 4),
                "deltaBytes": row.get("deltaBytes", 0),
                "latestPeriod": row.get("latestPeriod", ""),
                "reason": row.get("reason", ""),
            }
        )
    return {
        "title": title or f"시장 변화 다이제스트 ({today})",
        "date": today,
        "count": len(items),
        "items": items,
    }


def _scoreBadge(score: float) -> str:
    """점수 구간에 따른 텍스트 배지를 반환한다.

    Parameters
    ----------
    score : float
        중요도 점수 (0~100).

    Returns
    -------
    str
        배지 문자열. 80+ → ``"[!!!]"``, 50+ → ``"[!!]"``,
        25+ → ``"[!]"``, 그 외 → ``"[~]"``.
    """
    if score >= 80:
        return "[!!!]"
    if score >= 50:
        return "[!!]"
    if score >= 25:
        return "[!]"
    return "[~]"
