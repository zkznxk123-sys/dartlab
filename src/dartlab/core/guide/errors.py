"""에러 복구 안내 템플릿.

편의성 원칙(사용자 배려 최우선)을 구현하는 SSOT. 모든 "데이터 없음"
계열 에러 메시지는 해결책(gather 명령·show 경로·수집 절차)을 포함해야
한다. 파일 곳곳에 흩어진 안내 문구를 이 템플릿으로 통일.

편의성 원칙 (memory + CLAUDE.md):
- 기술적 정당성보다 사용자 편의가 먼저
- `"데이터 없음"` ❌ → `"데이터 없음 → dartlab.gather('price', '005930')으로 먼저 수집하세요"` ✓
"""

from __future__ import annotations


def missingDataHint(
    resource: str,
    *,
    recoverCmd: str | None = None,
    detail: str | None = None,
) -> str:
    """ "데이터 없음" 에러에 복구 명령을 포함한 친절한 안내 문자열 생성.

    파일 곳곳에 흩어진 `"XX 데이터 없음"` 문구를 이 템플릿으로 통일해
    편의성 원칙을 지킨다. 복구 명령이 있으면 함께 안내하고, 세부 사유가
    필요하면 detail 로 덧붙인다.

    Parameters
    ----------
    resource : str
        데이터 리소스 이름 (예: "재고자산", "컨센서스", "감사의견").
    recoverCmd : str, optional
        사용자가 실행할 복구 명령 문자열
        (예: `"dartlab.gather('price', '005930')"`). 없으면 해결책 생략.
    detail : str, optional
        부가 설명 (예: "최소 2기 필요", "금융업 미지원").

    Returns
    -------
    str
        한국어 안내 문자열. 포맷:
        - 복구명령·detail 모두 있음: `"{resource} 데이터 없음 → {recoverCmd}으로 먼저 수집하세요 ({detail})"`
        - 복구명령만: `"{resource} 데이터 없음 → {recoverCmd}으로 먼저 수집하세요"`
        - detail만: `"{resource} 데이터 없음 ({detail})"`
        - 둘 다 없음: `"{resource} 데이터 없음"`

    Raises
    ------
    없음.

    Examples
    --------
    >>> missingDataHint("컨센서스", recoverCmd="dartlab.gather('consensus', '005930')")
    '컨센서스 데이터 없음 → dartlab.gather(\\'consensus\\', \\'005930\\')으로 먼저 수집하세요'
    >>> missingDataHint("비교", detail="최소 2기 필요")
    '비교 데이터 없음 (최소 2기 필요)'
    >>> missingDataHint("시계열")
    '시계열 데이터 없음'

    Notes
    -----
    - 복구 명령을 **가능한 한 붙여라** — "데이터 없음"만 던지는 메시지는
      편의성 원칙 위반이다.
    - 파서 내부 계산 중간값 같은 특수 컨텍스트 메시지(사용자에게 직접
      노출되지 않는)는 굳이 템플릿으로 교체하지 않아도 된다.

    Guide
    -----
    L2 calc 함수가 데이터 누락 시 반환 None 대신 이 문자열을 로그로
    남기거나, 에러 경로에서 raise 메시지로 쓸 때 사용한다.

    See Also
    --------
    apiKeyMissingHint : API 키 누락 시 provider 별 안내.
    """
    base = f"{resource} 데이터 없음"
    if recoverCmd:
        base += f" → {recoverCmd}으로 먼저 수집하세요"
    if detail:
        base += f" ({detail})"
    return base


def apiKeyMissingHint(provider: str) -> str:
    """provider 별 API 키 발급·설정 안내 문자열.

    core/ai/aiSetup.py 의 `provider_guide` 에 delegate (중복 구현 방지).
    8개 provider (Gemini/Groq/Cerebras/Mistral/ChatGPT/OpenAI/Ollama/Codex)
    의 발급 URL + `.env` 설정법 SSOT 가 거기 있다.

    Parameters
    ----------
    provider : str
        provider 이름 (예: "gemini", "openai", "ollama").

    Returns
    -------
    str
        API 키 발급 URL + `.env` 설정 절차 안내 문자열.

    Raises
    ------
    없음 — 알 수 없는 provider 는 기본 안내를 반환한다 (aiSetup 구현에 의존).

    Examples
    --------
    >>> text = apiKeyMissingHint("gemini")
    >>> "GEMINI_API_KEY" in text or "gemini" in text.lower()
    True

    Notes
    -----
    이 함수는 단순 delegate 이다. provider 별 안내 원문을 고치려면
    `core/ai/aiSetup.py::provider_guide` 를 수정한다 — SSOT 위치.

    Guide
    -----
    AI provider 설정 전 진입점에서 호출. `c.ask()` 같은 AI 경로가 키
    누락을 감지하면 이 함수를 통해 사용자에게 안내한다.

    See Also
    --------
    missingDataHint : 데이터 누락 시 복구 안내.
    """
    from dartlab.core.ai.aiSetup import provider_guide

    return provider_guide(provider)
