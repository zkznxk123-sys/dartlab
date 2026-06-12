"""뉴스 소스 레지스트리 — rss·gdelt·naver 메타데이터 SSOT.

`core/providers/dataCredentials.py` 의 `DataProviderSpec` 레지스트리 톤을 그대로
따른다. sync/load/upload 가 소스별 if-분기 대신 본 레지스트리를 순회해 *대칭* 처리.

설계 원칙 (의도적 경계):
    - 레지스트리는 **메타데이터만** 담는다. fetch 함수를 `Callable` 로 박는 dispatch
      테이블은 만들지 않는다 — query 팬아웃(rss/naver) vs 시간슬롯(gdelt)을 1개
      시그니처로 강제하면 caller 가 어차피 분기해 추상화 가치가 없다. caller 는
      `fetchKind` 로 분기하고 구체 함수를 직접 호출한다.
    - `dir` 은 데이터 물리 경로 SSOT. `core/dataConfig.py` 의 동명 카테고리 `dir` 과
      일치해야 한다 (L0 dataConfig 를 L1 본 모듈에서 파생하면 import 역방향 위반 →
      문자열 일치 + `test_newsSources` 회귀로 drift 차단).

See Also:
    core/providers/dataCredentials.py — 자격증명 레지스트리(동일 패턴).
    sources/newsSchema.py — 소스 출력 canonical 스키마.
    sources/newsIo.py — 레지스트리 dir 로 write/load 하는 공유 IO.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class NewsSourceSpec:
    """단일 뉴스 소스의 메타 — 레지스트리 항목.

    Attributes:
        id: 정식 소스 id (예 ``"rss"``).
        label: 사람용 표시명.
        visibility: ``"public"`` (재배포 가능) | ``"private"`` (저작권 — 비공개 캐시 전용).
        hfCategory: `dataConfig.DATA_RELEASES` 카테고리 키 (예 ``"newsHeadlines"``).
        dir: 데이터 물리 경로 (예 ``"news/public/rss"``). dataConfig dir 과 일치.
        fetchKind: ``"query"`` (검색어 팬아웃) | ``"slot"`` (시간슬롯 루프).
        enrichable: Phase B sentiment/topic enrich 대상 여부.
        credentialProvider: 필요 자격증명 공급자 id (`dataCredentials`). None=불필요.
        markets: 이 소스가 다루는 시장 코드.
    """

    id: str
    label: str
    visibility: Literal["public", "private"]
    hfCategory: str
    dir: str
    fetchKind: Literal["query", "slot"]
    enrichable: bool = True
    credentialProvider: str | None = None
    markets: tuple[str, ...] = ("KR", "US")


# 뉴스 소스 레지스트리 (SSOT). 새 소스 추가 시 여기 1엔트리 + dataConfig 카테고리.
_NEWS_SOURCES: dict[str, NewsSourceSpec] = {
    "rss": NewsSourceSpec(
        id="rss",
        label="Google News RSS",
        visibility="public",
        hfCategory="newsHeadlines",
        dir="news/public/rss",
        fetchKind="query",
        enrichable=True,
        credentialProvider=None,
        markets=("KR", "US"),
    ),
    "gdelt": NewsSourceSpec(
        id="gdelt",
        label="GDELT 2.0 GKG",
        visibility="public",
        hfCategory="newsGdelt",
        dir="news/public/gdelt",
        fetchKind="slot",
        enrichable=False,  # V2Tone/V2Themes built-in
        credentialProvider=None,
        markets=("KR", "US", "JP", "CN", "GLOBAL"),
    ),
    "naver": NewsSourceSpec(
        id="naver",
        label="Naver 검색 API",
        visibility="private",  # 언론사 저작권 — 비공개 캐시 전용 (KRX 선례)
        hfCategory="newsNaver",
        dir="news/private/naver",
        fetchKind="query",
        enrichable=True,
        credentialProvider="naver",  # + naverSecret (쌍)
        markets=("KR",),
    ),
}


def getNewsSource(sourceId: str) -> NewsSourceSpec:
    """소스 spec 조회.

    Sig: ``getNewsSource(sourceId) -> NewsSourceSpec``

    Capabilities:
        - 소스 id → NewsSourceSpec 1:1 조회
        - 미등록 id 는 등록 목록 안내와 함께 명시 에러

    AIContext:
        newsIo·sync 계열이 소스별 if-분기 없이 메타(dir·visibility·hfCategory)에
        접근하는 단일 관문.

    Guide:
        등록 id = rss·gdelt·naver. 새 소스는 _NEWS_SOURCES 1엔트리 +
        dataConfig 카테고리 쌍으로 추가 (둘의 dir 문자열 일치 필수).

    When:
        loadSourceDay 등 소스 메타가 필요한 모든 지점.

    How:
        레지스트리 dict get — 미스 시 KeyError (등록 목록 포함).

    Requires:
        없음.

    Args:
        sourceId: 정식 소스 id (예 ``"rss"``).

    Returns:
        NewsSourceSpec — 레지스트리 항목.

    Raises:
        KeyError: 미등록 소스 id (등록 목록 안내).

    Example:
        >>> getNewsSource("naver").visibility
        'private'

    See Also:
        ``allNewsSources``: 전체 순회.
        ``publicNewsSources``: 재배포 가능 소스만.
    """
    spec = _NEWS_SOURCES.get(sourceId)
    if spec is None:
        known = ", ".join(sorted(_NEWS_SOURCES))
        raise KeyError(f"미등록 뉴스 소스: {sourceId!r} (등록됨: {known})")
    return spec


def allNewsSources() -> list[NewsSourceSpec]:
    """등록된 모든 뉴스 소스 spec (id 정렬).

    Sig: ``allNewsSources() -> list[NewsSourceSpec]``

    Requires:
        없음.

    Returns:
        list[NewsSourceSpec] — 레지스트리 전체. 읽기(loadNewsArchive)가 순회.

    Raises:
        없음.

    Example:
        >>> sorted(s.id for s in allNewsSources())
        ['gdelt', 'naver', 'rss']
    """
    return [_NEWS_SOURCES[k] for k in sorted(_NEWS_SOURCES)]


def publicNewsSources() -> list[NewsSourceSpec]:
    """public(재배포 가능) 소스만 (id 정렬).

    Sig: ``publicNewsSources() -> list[NewsSourceSpec]``

    Requires:
        없음.

    Returns:
        list[NewsSourceSpec] — visibility=="public". bulkUploadHf 공개 카테고리 파생용.

    Raises:
        없음.

    Example:
        >>> [s.id for s in publicNewsSources()]
        ['gdelt', 'rss']
    """
    return [s for s in allNewsSources() if s.visibility == "public"]


__all__ = [
    "NewsSourceSpec",
    "allNewsSources",
    "getNewsSource",
    "publicNewsSources",
]
