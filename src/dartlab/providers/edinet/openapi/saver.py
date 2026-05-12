"""EDINET ZIP → parquet 변환 + 저장.

EDINET API에서 다운로드한 ZIP 파일을 파싱하여:
- docs parquet: 서술형 텍스트 블록 (sections 수평화용)
- finance parquet: XBRL 재무 숫자
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import polars as pl


def extractCsvFromZip(zipPath: str | Path) -> dict[str, str]:
    """ZIP 내 CSV 파일을 추출하여 {파일명: 내용} dict 반환.

    Args:
        zipPath: 인자.

    Raises:
        없음.

    Example:
        >>> extractCsvFromZip(...)

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    Guide:
        - <TODO: 사용 시나리오>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>

    Returns:
        <TODO: return desc> (dict[str, str])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - csv
        - io
        - polars
        - zipfile
    """
    result: dict[str, str] = {}
    zipPath = Path(zipPath)

    with zipfile.ZipFile(zipPath, "r") as zf:
        for name in zf.namelist():
            if name.endswith(".csv"):
                with zf.open(name) as f:
                    content = f.read()
                    # EDINET CSV는 Shift_JIS 또는 UTF-8
                    for enc in ("utf-8", "shift_jis", "cp932"):
                        try:
                            result[name] = content.decode(enc)
                            break
                        except UnicodeDecodeError:
                            continue
    return result


def buildFinanceParquet(csvContent: str, *, edinetCode: str = "") -> pl.DataFrame:
    """EDINET CSV(재무) → Polars DataFrame.

    EDINET CSV 재무 데이터 컬럼:
    - 요素ID (element_id)
    - 項目名 (account_name, 일본어)
    - コンテキストID (context_id: 기간+연결/개별)
    - 値 (value: 숫자)
    - 単位 (unit: JPY 등)

    Args:
        csvContent: 인자.
        edinetCode: 인자.

    Raises:
        없음.

    Example:
        >>> buildFinanceParquet(...)

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    Guide:
        - <TODO: 사용 시나리오>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>

    Returns:
        <TODO: return desc> (pl.DataFrame)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - csv
        - io
        - polars
        - zipfile
    """
    reader = csv.DictReader(io.StringIO(csvContent))
    rows: list[dict] = []

    for row in reader:
        elementId = row.get("要素ID", row.get("element_id", ""))
        accountName = row.get("項目名", row.get("account_name", ""))
        contextId = row.get("コンテキストID", row.get("context_id", ""))
        value = row.get("値", row.get("value", ""))
        unit = row.get("単位", row.get("unit", ""))

        if not elementId or not value:
            continue

        # 숫자 파싱 시도
        try:
            numericValue = float(value.replace(",", ""))
        except ValueError:
            continue

        rows.append(
            {
                "edinet_code": edinetCode,
                "element_id": elementId,
                "account_name": accountName,
                "context_id": contextId,
                "value": numericValue,
                "unit": unit,
            }
        )

    if not rows:
        return pl.DataFrame(
            schema={
                "edinet_code": pl.Utf8,
                "element_id": pl.Utf8,
                "account_name": pl.Utf8,
                "context_id": pl.Utf8,
                "value": pl.Float64,
                "unit": pl.Utf8,
            }
        )

    return pl.DataFrame(rows)


def buildDocsParquet(csvContent: str, *, edinetCode: str = "") -> pl.DataFrame:
    """EDINET CSV(서술형) → Polars DataFrame.

    서술형 블록: 요소ID가 텍스트 타입인 행들.

    Args:
        csvContent: 인자.
        edinetCode: 인자.

    Raises:
        없음.

    Example:
        >>> buildDocsParquet(...)

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    Guide:
        - <TODO: 사용 시나리오>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>

    Returns:
        <TODO: return desc> (pl.DataFrame)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - csv
        - io
        - polars
        - zipfile
    """
    reader = csv.DictReader(io.StringIO(csvContent))
    rows: list[dict] = []

    for row in reader:
        elementId = row.get("要素ID", row.get("element_id", ""))
        label = row.get("項目名", row.get("account_name", ""))
        contextId = row.get("コンテキストID", row.get("context_id", ""))
        value = row.get("値", row.get("value", ""))

        if not elementId or not value:
            continue

        # 숫자가 아닌 텍스트 블록만
        try:
            float(value.replace(",", ""))
            continue
        except ValueError:
            pass

        rows.append(
            {
                "edinet_code": edinetCode,
                "element_id": elementId,
                "label": label,
                "context_id": contextId,
                "text": value,
            }
        )

    if not rows:
        return pl.DataFrame(
            schema={
                "edinet_code": pl.Utf8,
                "element_id": pl.Utf8,
                "label": pl.Utf8,
                "context_id": pl.Utf8,
                "text": pl.Utf8,
            }
        )

    return pl.DataFrame(rows)


def saveParquet(df: pl.DataFrame, outputPath: str | Path) -> Path:
    """DataFrame을 parquet 파일로 저장.

    Args:
        df: 인자.
        outputPath: 인자.

    Raises:
        없음.

    Example:
        >>> saveParquet(...)

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    Guide:
        - <TODO: 사용 시나리오>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>

    Returns:
        <TODO: return desc> (Path)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - csv
        - io
        - polars
        - zipfile
    """
    outputPath = Path(outputPath)
    outputPath.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(outputPath)
    return outputPath
