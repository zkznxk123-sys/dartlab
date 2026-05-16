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
    """credit.evaluate 결과 → 등급 이력 JSON 누적 + 전이 매트릭스 자동 업데이트.

    Capabilities:
        ``data/credit/history/{stockCode}.json`` 에 등급/점수/outlook 시계열
        JSON 축적. 이전 등급 대비 변경이 있으면 transition matrix
        (data/credit/transition.json) 의 (from, to) 카운트 자동 증가. credit
        모니터링 파이프라인의 핵심 함수.

    Args:
        stockCode: 종목코드 (예 ``"005930"``).
        result: ``credit.evaluate`` 결과 dict. 필수 키: ``grade``,
            ``gradeRaw``, ``score``, ``eCR``, ``outlook``,
            ``methodologyVersion``, ``latestPeriod``.

    Returns:
        Path: 저장된 이력 파일 (``data/credit/history/{stockCode}.json``).

    Raises:
        없음 — 디렉토리 자동 생성, write 실패 시도 silently log.

    Example:
        >>> from dartlab.credit import credit
        >>> result = credit("005930")
        >>> path = recordGrade("005930", result)
        >>> path.name
        '005930.json'

    Guide:
        매 분기 (또는 매주) 호출 권장 — 등급 변화 자동 추적. transition
        matrix 는 KR 평균 누적되므로 분기별 운영자 검증 필요.

    SeeAlso:
        - ``loadHistory``: 본 함수 저장 결과 로드
        - ``gradeChanged``: 변화 여부 판정
        - ``buildTransitionMatrix``: 누적 카운트 → 확률 matrix

    When:
        분기 / 주 단위 운영자 cron 트리거. AI 응답 흐름에서 직접 호출 금지 (mutation).

    How:
        history JSON 로드 → previousGrade 비교 → 새 entry append → 파일 저장 → 변화 시
        transition.json 카운트 갱신.

    Requires:
        ``data/credit/history/`` 디렉토리 + write 권한.

    AIContext:
        본 함수는 mutation (파일 IO + transition.json 업데이트). 회귀 테스트
        에서 자동 호출 금지 (data 폴더 오염). 사용자/cron 트리거 권장.

    LLM Specifications:
        AntiPatterns:
            - 동일 분기 동일 종목 반복 호출 → 중복 entry. ``latestPeriod``
              체크 + 호출자 dedupe 필요.
            - transition.json 의 stockCode 단위 추적 부재 — 전체 KR 평균만.
              개별 종목 transition 은 history JSON 에서 별도 계산.
        OutputSchema:
            Path 객체.
        Prerequisites:
            ``data/credit/history/`` write 권한.
        Freshness:
            entry 마다 ``auditDate`` 추가 (오늘 날짜).
        Dataflow:
            stockCode → loadHistory → previousGrade 비교 → JSON entry 추가
            → 저장 → transition matrix 업데이트.
        TargetMarkets: KR (DART). US 미적용.
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

    Capabilities:
        ``data/credit/history/{stockCode}.json`` 을 로드해 시계열 entry 리스트 반환. 파일/JSON
        손상 시 빈 리스트 폴백.

    AIContext:
        AI 답변에서 "등급 변경 이력" / "현재 outlook" 인용 시 본 함수 결과 직접 사용. 빈 리스트
        면 "이력 없음" 단서 명시.

    When:
        ``gradeChanged`` / ``recordGrade`` 가 본 함수 호출. AI 가 시계열 답변 시 직접 호출.

    How:
        파일 경로 결정 → read_text → json.loads → 리스트 반환.

    Guide:
        반환 entry 의 ``date`` 컬럼은 운영자 호출 시점. 분기 보고서 기준 기간은 ``period``.

    See Also:
        - ``dartlab.credit.monitoring.history.recordGrade`` : 본 함수 저장 측
        - ``dartlab.credit.monitoring.history.gradeChanged`` : 변경 여부

    Requires:
        - ``data/credit/history/{stockCode}.json`` (없어도 빈 리스트 폴백).

    Raises:
        없음 — 파일 부재 / JSON 손상 모두 빈 리스트.

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
    """이전 등급 대비 변경 여부.

    Capabilities:
        ``loadHistory`` 결과 마지막 entry 의 grade 와 ``newGrade`` 비교. 이력 없으면 True (첫
        발행도 변경으로 간주).

    Args:
        stockCode: 종목코드.
        newGrade: 비교 대상 신규 등급 (예: "dCR-AA+").

    Returns:
        bool: 변경되었거나 첫 발행이면 True.

    Raises:
        없음.

    Example:
        >>> gradeChanged("005930", "dCR-AA+")
        False

    Guide:
        Alert / Slack 발송 트리거에 사용. 첫 발행 케이스도 True 처리 — 호출자가 별도 처리 필요.

    When:
        ``recordGrade`` 호출 전 변경 여부 사전 체크, 또는 모니터링 알람 트리거.

    How:
        ``loadHistory`` → 마지막 entry grade vs newGrade.

    Requires:
        - ``data/credit/history/`` 접근 가능

    See Also:
        - ``dartlab.credit.monitoring.history.loadHistory`` : 본 함수 사용
        - ``dartlab.credit.monitoring.history.recordGrade`` : 변경 저장

    AIContext:
        AI 가 "등급 변경됐는가" 답변 시 본 함수 직접 호출. True 면 ``loadHistory`` 로 직전 등급
        확인 + 답변 첨부.
    """
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

    Capabilities:
        ``data/credit/history/`` 내 모든 종목 이력 파일을 순회해 (이전 등급 → 현재 등급) 전이를
        집계, ``data/credit/transition.json`` 에 dict 저장 + 반환. 분기별 운영자 재계산용.

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

    Raises:
        OSError: 디스크 쓰기 실패 시. 개별 파일 읽기 실패는 silent skip.

    Example:
        >>> from dartlab.credit.monitoring.history import updateTransitionMatrix
        >>> matrix = updateTransitionMatrix()
        >>> matrix.get("dCR-AA+", {})

    Guide:
        본 함수는 누적 카운트만 — 확률 matrix 가 필요하면 호출자가 row 정규화. KR 평균 추적.

    When:
        분기 1 회 운영자 실행 (cron). AI 가 직접 호출하지 않는다 (전 종목 IO 비용).

    How:
        history 폴더 glob → 종목별 이력 로드 → 인접 entry grade 비교 → 변경 시 (from, to)
        카운트 증가 → transition.json 직렬화.

    Requires:
        - ``data/credit/history/*.json`` 다수 + transition.json write 권한

    See Also:
        - ``dartlab.credit.monitoring.history.recordGrade`` : 신규 entry 추가 + 점진 갱신
        - ``dartlab.credit.monitoring.history.loadHistory`` : 개별 종목 이력 로드

    AIContext:
        AI 직접 호출 없음. 답변 시 "전이 확률" 통계 인용 가능 — KR 평균이므로 단일 종목 단정 금지.
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
