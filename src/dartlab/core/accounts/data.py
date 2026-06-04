"""account SSOT 로더 — ``reference/data/accountMappings.json`` 단일 파일.

전 계정 매핑 지식의 단일 진실의 원천(SSOT). 한 파일에:

- ``standardAccounts`` — snakeId 정의 (korName/category/type/topic)
- ``mappings`` — 한글/영문 → snakeId 평면 사전
- ``layers`` — stage 별 정규화 dict (idSynonym/nameSynonym/snakeAlias/labelEn/korSynonym)
- ``edgar`` — EDGAR tag 매핑 소스 (accounts/learnedTags/stmtOverrides)

본 모듈은 *로드와 캐시 무효화만* 책임진다. 12 단계 정규화·라벨 cascade·EDGAR
tag 매핑 알고리즘은 각각 ``normalize``/``labels``/``edgar`` 형제 모듈이 본
로더 위에서 구현한다.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent.parent / "reference" / "data"
_SSOT_PATH = _DATA_DIR / "accountMappings.json"
_SUPPLEMENTS_PATH = _DATA_DIR / "labelSupplements.json"


def _required(path: Path) -> dict:
    """번들 필수 리소스 로드 — 누락 시 loud-fail (2026-04-19 wheel 사고 class).

    Args:
        path: 번들 JSON 경로.

    Returns:
        파싱된 dict.

    Raises:
        FileNotFoundError: 파일 부재 시 (패키징 사고 — silent 빈 dict 금지).
    """
    if not path.exists():
        raise FileNotFoundError(
            f"필수 번들 리소스 누락: {path}\n"
            f"  → pip install -U --force-reinstall dartlab\n"
            f"  (wheel 패키징 사고 시 이 파일이 빠질 수 있음)"
        )
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def loadAccounts() -> dict:
    """account SSOT 전체 dict 반환 (process 당 1 회 parse, lru_cache).

    Args:
        없음.

    Returns:
        ``{_metadata, standardAccounts, mappings, layers, edgar}`` dict.

    Raises:
        FileNotFoundError: accountMappings.json 부재 시.

    Example:
        >>> from dartlab.core.accounts.data import loadAccounts
        >>> "layers" in loadAccounts()
        True
    """
    return _required(_SSOT_PATH)


@lru_cache(maxsize=1)
def loadSupplements() -> dict[str, str]:
    """labelSupplements.json — standardAccounts 외 보충 라벨 SSOT.

    Args:
        없음.

    Returns:
        ``{snakeId: 한글 라벨}`` 보충 dict.

    Raises:
        FileNotFoundError: labelSupplements.json 부재 시.

    Example:
        >>> from dartlab.core.accounts.data import loadSupplements
        >>> isinstance(loadSupplements(), dict)
        True
    """
    return _required(_SUPPLEMENTS_PATH).get("supplements", {})


def release() -> None:
    """전 account 캐시 무효화 — SSOT JSON 직접 편집 후 호출.

    로더 lru_cache + 형제 모듈(normalize/edgar/labels/aliases)의 파생 캐시
    모두 리셋. ``mappingPromote.py`` apply 후 동일 프로세스 캐시 정합용.

    Args:
        없음.

    Returns:
        None.

    Raises:
        없음.

    Example:
        >>> from dartlab.core.accounts import data
        >>> data.release()
    """
    loadAccounts.cache_clear()
    loadSupplements.cache_clear()
    # 형제 파생 캐시 — 지연 import 로 순환 회피
    from dartlab.core.accounts import aliases, edgar, labels, normalize

    aliases.reset()
    normalize.AccountNormalizer.release()
    edgar.EdgarTagMapper.release()
    labels.reset()
