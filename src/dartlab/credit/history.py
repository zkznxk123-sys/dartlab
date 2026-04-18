"""등급 이력 관리 + 전이 매트릭스.

보고서 발행마다 등급을 JSON으로 축적하고,
등급 전이 매트릭스를 자동 업데이트한다.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_CREDIT_DATA_DIR = Path("data/credit")
_HISTORY_DIR = _CREDIT_DATA_DIR / "history"
_TRANSITION_PATH = _CREDIT_DATA_DIR / "transition.json"


def _ensureDir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def recordGrade(stockCode: str, result: dict) -> Path:
    """등급 이력에 현재 결과 추가.

    ``data/credit/history/{stockCode}.json``에 등급·점수·outlook 등을
    JSON 배열로 축적한다. 이전 등급 대비 변경이 있으면
    전이 매트릭스도 자동 업데이트한다.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: ``"005930"``).
    result : dict
        신용분석 결과. 주요 키: ``grade`` (str), ``gradeRaw`` (str),
        ``score`` (점), ``eCR`` (str), ``outlook`` (str),
        ``methodologyVersion`` (str), ``latestPeriod`` (str).

    Returns
    -------
    Path
        저장된 이력 파일의 경로 (``data/credit/history/{stockCode}.json``).
    """
    _ensureDir(_HISTORY_DIR)
    path = _HISTORY_DIR / f"{stockCode}.json"

    history = loadHistory(stockCode)

    previousGrade = history[-1]["grade"] if history else None
    changed = previousGrade != result.get("grade") if previousGrade else False

    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "grade": result.get("grade"),
        "gradeRaw": result.get("gradeRaw"),
        "score": result.get("score"),
        "eCR": result.get("eCR"),
        "outlook": result.get("outlook"),
        "methodologyVersion": result.get("methodologyVersion"),
        "period": result.get("latestPeriod"),
        "previousGrade": previousGrade,
        "changed": changed,
    }

    history.append(entry)
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    # 전이 매트릭스 업데이트
    if previousGrade and changed:
        _updateTransition(previousGrade, result.get("grade", ""))

    return path


def loadHistory(stockCode: str) -> list[dict]:
    """종목의 등급 이력 전체를 로드.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: ``"005930"``).

    Returns
    -------
    list[dict]
        등급 이력 리스트. 각 항목의 키:

        - ``date`` : str — 기록일 (``"YYYY-MM-DD"``)
        - ``grade`` : str — 최종 등급 (예: ``"A+"``)
        - ``gradeRaw`` : str — 보정 전 원시 등급
        - ``score`` : float — 종합 점수 (점)
        - ``eCR`` : str — 추정 신용등급
        - ``outlook`` : str — 등급 전망 (``"안정적"`` / ``"부정적"`` 등)
        - ``methodologyVersion`` : str — 평가 방법론 버전
        - ``period`` : str — 평가 기준 기간
        - ``previousGrade`` : str | None — 이전 등급
        - ``changed`` : bool — 등급 변경 여부

        파일이 없거나 파싱 실패 시 빈 리스트를 반환한다.
    """
    path = _HISTORY_DIR / f"{stockCode}.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def gradeChanged(stockCode: str, newGrade: str) -> bool:
    """이전 등급 대비 변경 여부."""
    history = loadHistory(stockCode)
    if not history:
        return True  # 첫 발행
    return history[-1].get("grade") != newGrade


def _updateTransition(fromGrade: str, toGrade: str) -> None:
    """전이 매트릭스 업데이트."""
    _ensureDir(_CREDIT_DATA_DIR)
    matrix = _loadTransition()

    if fromGrade not in matrix:
        matrix[fromGrade] = {}
    matrix[fromGrade][toGrade] = matrix[fromGrade].get(toGrade, 0) + 1

    _TRANSITION_PATH.write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")


def _loadTransition() -> dict:
    """전이 매트릭스 로드."""
    if not _TRANSITION_PATH.exists():
        return {}
    try:
        return json.loads(_TRANSITION_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def updateTransitionMatrix() -> dict:
    """전체 히스토리에서 전이 매트릭스 재계산.

    ``data/credit/history/`` 내 모든 종목 이력 파일을 순회하여
    등급 변경 건수를 집계하고, 전이 매트릭스를
    ``data/credit/transition.json``에 저장한다.

    Returns
    -------
    dict
        전이 매트릭스. 구조: ``{from_grade: {to_grade: count}}``
        예: ``{"A+": {"A": 3, "AA-": 1}}``.
        ``from_grade`` — 변경 전 등급, ``to_grade`` — 변경 후 등급,
        ``count`` : int — 해당 전이 발생 횟수 (건).
    """
    _ensureDir(_HISTORY_DIR)
    matrix: dict = {}

    for path in _HISTORY_DIR.glob("*.json"):
        try:
            history = json.loads(path.read_text(encoding="utf-8"))
            for i in range(1, len(history)):
                prev = history[i - 1].get("grade", "")
                curr = history[i].get("grade", "")
                if prev and curr and prev != curr:
                    if prev not in matrix:
                        matrix[prev] = {}
                    matrix[prev][curr] = matrix[prev].get(curr, 0) + 1
        except (json.JSONDecodeError, OSError):
            continue

    _ensureDir(_CREDIT_DATA_DIR)
    _TRANSITION_PATH.write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    return matrix
