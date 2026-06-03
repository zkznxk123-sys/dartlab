"""변경 매니페스트 I/O — ``dist/changed_{category}.txt`` 통일.

증분 HF 업로드의 단일 계약: stage 가 변경된 상대경로(예: ``{code}/{period}.parquet``)
목록을 ``dist/changed_{category}.txt`` 로 쓰고, 업로드 단계가 읽어 그 파일만 commit.
빈 매니페스트 = 변경 0 → 업로드 skip(전체 폴더 fallback 아님). 옛 syncRecent/buildPanel/
onlinePanel 의 흩어진 ``changed_*.txt`` writer 를 한 함수로 모은다.
"""

from __future__ import annotations

from pathlib import Path


def _distDir() -> Path:
    d = Path("dist")
    d.mkdir(parents=True, exist_ok=True)
    return d


def changedPath(category: str) -> Path:
    """category 의 변경 매니페스트 경로(``dist/changed_{category}.txt``).

    Args:
        category: DATA_RELEASES 카테고리명(docs/finance/panel 등).

    Returns:
        매니페스트 ``Path``.

    Raises:
        없음.

    Example:
        >>> changedPath("panel").name
        'changed_panel.txt'
    """
    return _distDir() / f"changed_{category}.txt"


def writeChanged(category: str, paths: list[str]) -> Path:
    """변경된 상대경로 목록을 매니페스트로 기록한다.

    Args:
        category: 카테고리명.
        paths: 카테고리 dir 기준 상대경로 목록(중복 제거·정렬해 기록).

    Returns:
        기록한 매니페스트 ``Path``.

    Raises:
        OSError: 쓰기 실패.

    Example:
        >>> writeChanged("panel", ["005930/2024Q1.parquet"]).exists()
        True
    """
    target = changedPath(category)
    uniq = sorted({p.strip().replace("\\", "/") for p in paths if p and p.strip()})
    target.write_text("\n".join(uniq) + ("\n" if uniq else ""), encoding="utf-8")
    return target


def readChanged(category: str) -> list[str]:
    """매니페스트에서 변경 상대경로 목록을 읽는다(없으면 빈 list).

    Args:
        category: 카테고리명.

    Returns:
        상대경로 목록. 매니페스트 부재 시 ``[]``.

    Raises:
        없음.

    Example:
        >>> readChanged("__none__")
        []
    """
    target = changedPath(category)
    if not target.exists():
        return []
    return [ln.strip() for ln in target.read_text(encoding="utf-8").splitlines() if ln.strip()]
