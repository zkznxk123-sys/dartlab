"""DART 공시 데이터 활용 라이브러리."""

import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

_IS_PYODIDE = sys.platform == "emscripten"

from dartlab import config, core  # noqa: F401 — 하위호환
from dartlab.company import Company
from dartlab.core.select import ChartResult, SelectResult

if not _IS_PYODIDE:
    from dartlab import ai as llm  # noqa: F401 — 하위호환
    from dartlab.audit import queryAudit, runAudit  # noqa: F401 — 하위호환
    from dartlab.core.env import loadEnv as _loadEnv
    from dartlab.gather.fred import Fred
    from dartlab.gather.listing import codeToName, fuzzySearch, getKindList, nameToCode  # noqa: F401
    from dartlab.listing import listing  # noqa: F401 — 목록 조회 단일 진입점
    from dartlab.providers.dart.company import Company as _DartEngineCompany
    from dartlab.providers.dart.openapi.dart import OpenDart
    from dartlab.providers.edgar.openapi.edgar import OpenEdgar
    from dartlab.review import Review

    # .env 자동 로드 — API 키 등 환경변수
    _loadEnv()


async def prefetch(*stockCodes: str, categories: list[str] | None = None) -> None:
    """HF에서 종목 데이터를 미리 다운로드 (Pyodide/브라우저 전용).

    Company 생성 전에 await로 호출한다.

    Example::

        import dartlab
        await dartlab.prefetch("005930")
        c = dartlab.Company("005930")
    """
    if not _IS_PYODIDE:
        return  # 일반 환경에서는 no-op

    # pyodide 빌트인 패키지 로드 (C 확장 — micropip으로 설치 불가)
    import pyodide_js  # type: ignore[import-not-found]

    await pyodide_js.loadPackage(["pyarrow", "lxml", "polars", "numpy", "pydantic"])

    from dartlab.core.dataConfig import DATA_RELEASES, hfBaseUrl
    from pyodide.http import pyfetch  # type: ignore[import-not-found]

    cats = categories or ["docs", "finance", "report"]
    for code in stockCodes:
        code = code.strip()
        for cat in cats:
            dirPath = DATA_RELEASES[cat]["dir"]
            path = f"/data/{dirPath}/{code}.parquet"

            import os

            if os.path.exists(path):
                continue

            url = f"{hfBaseUrl(cat)}/{code}.parquet"
            try:
                resp = await pyfetch(url)
                if resp.status != 200:
                    print(f"  ⚠ {cat}/{code} 실패 (HTTP {resp.status})")
                    continue
                buf = await resp.bytes()
                os.makedirs(f"/data/{dirPath}", exist_ok=True)
                with open(path, "wb") as f:
                    f.write(buf)
                print(f"  {cat}/{code}: {len(buf) // 1024} KB")
            except Exception as e:
                print(f"  ⚠ {cat}/{code} 실패: {e}")


try:
    __version__ = _pkg_version("dartlab")
except PackageNotFoundError:
    __version__ = "0.0.0"


def search(
    query: str,
    *,
    corp: str | None = None,
    start: str | None = None,
    end: str | None = None,
    topK: int = 10,
    scope: str = "auto",
):
    """공시 검색. *(alpha)*

    제목형 쿼리와 본문형 쿼리를 자동 판별하여 검색.
    DART 공시 뷰어 링크(dartUrl) 포함.

    Capabilities:
        - 제목 검색: 공시 유형명/섹션 제목에서 매칭 ("유상증자", "대표이사 변경")
        - 본문 검색: 사업보고서 등 본문에서 개념 매칭 ("반도체 HBM 투자", "환율 리스크")
        - 종목/기간 필터 지원
        - DART 공시 뷰어 링크 포함 (dartUrl 컬럼)

    Requires:
        데이터: stemIndex (scope=title) + contentIndex (scope=content)

    AIContext:
        공시를 찾을 때 사용. 공시 유형명으로 찾으면 제목 검색, 내용으로 찾으면 본문 검색.
        scope 지정 없이 자동 판별.

    Guide:
        - "유상증자 한 회사?" -> search("유상증자")
        - "반도체 투자 트렌드?" -> search("반도체 HBM 투자")

    SeeAlso:
        - Company: 종목코드/회사명으로 Company 생성
        - listing: 전체 상장법인 목록

    Args:
        query: 검색어 (한국어). "유상증자", "반도체 HBM 투자" 등.
        corp: 종목 필터 (종목코드 "005930" 또는 회사명 "삼성전자").
        start: 시작일 (YYYYMMDD).
        end: 종료일 (YYYYMMDD).
        topK: 반환 건수 (기본 10).
        scope: ``"auto"`` (기본), ``"title"``, ``"content"``, ``"both"``.

    Returns
    -------
    pl.DataFrame
        score : float — 매칭 점수
        rcept_no : str — 접수번호 (DART 고유 ID)
        corp_name : str — 회사명
        report_nm : str — 공시 유형명
        scope : str — 검색 소스 ("title" 또는 "content", auto/both 모드)
        dartUrl : str — DART 공시 뷰어 URL

    Example::

        import dartlab
        dartlab.search("유상증자")                                # 제목 매칭
        dartlab.search("반도체 HBM 투자")                          # 본문 자동 매칭
        dartlab.search("환율 리스크", scope="content")              # 본문 강제
        dartlab.search("대표이사 변경", corp="005930")              # 종목 필터
    """
    # R33-1: 빈 query 거부
    if not query or not query.strip():
        raise ValueError(
            "search 의 query 가 비어 있습니다. 검색어를 1자 이상 전달하세요. 예: dartlab.search('유상증자')"
        )
    from dartlab.core.search import search as _search

    return _search(query, corp=corp, start=start, end=end, topK=topK, scope=scope)


def searchName(keyword: str):
    """종목명/코드로 종목 찾기 (KR + US).

    Args:
        keyword: 종목명, 종목코드, 또는 ticker.

    Returns:
        pl.DataFrame — 종목 검색 결과.

    Example::

        dartlab.searchName("삼성전자")
        dartlab.searchName("AAPL")
    """
    # R33-2: 빈 keyword 거부
    if not keyword or not keyword.strip():
        raise ValueError(
            "searchName 의 keyword 가 비어 있습니다. 종목명/코드를 1자 이상 전달하세요. "
            "예: dartlab.searchName('삼성전자') 또는 dartlab.searchName('AAPL')"
        )
    if any("\uac00" <= ch <= "\ud7a3" for ch in keyword):
        kr_result = _DartEngineCompany.search(keyword)
        # Phase 11 A3: 한글 alias → EDGAR 재검색 (예: "인텔" → "Intel")
        try:
            from dartlab.core.finance.nameAliases import resolveEnglishAlias
            from dartlab.providers.edgar.company import Company as _US

            en = resolveEnglishAlias(keyword)
            if en:
                us_result = _US.search(en)
                if us_result.height > 0:
                    # KR + US 합치기
                    if kr_result.height > 0:
                        import polars as _pl

                        return _pl.concat([kr_result, us_result], how="diagonal_relaxed")
                    return us_result
        except (ImportError, AttributeError, NotImplementedError):
            pass
        return kr_result
    if keyword.isascii() and keyword.isalpha():
        try:
            from dartlab.providers.edgar.company import Company as _US

            us_result = _US.search(keyword)
            if us_result.height > 0:
                return us_result
        except (ImportError, AttributeError, NotImplementedError):
            pass
    return _DartEngineCompany.search(keyword)


def collect(
    *codes: str,
    categories: list[str] | None = None,
    incremental: bool = True,
) -> dict[str, dict[str, int]]:
    """지정 종목 DART 데이터 수집 (OpenAPI).

    Capabilities:
        - 종목별 DART 공시 데이터 직접 수집 (finance, docs, report)
        - 멀티키 병렬 수집 (DART_API_KEYS 쉼표 구분)
        - 증분 수집 — 이미 있는 데이터는 건너뜀
        - 카테고리별 선택 수집

    Requires:
        API 키: DART_API_KEY

    AIContext:
        사용자가 특정 종목의 최신 데이터를 직접 수집할 때 사용.

    Guide:
        - "데이터 수집해줘" -> DART_API_KEY 필요. dartlab.setup("dart-key", "YOUR_KEY")로 설정 안내
        - "삼성전자 재무 데이터 수집" -> collect("005930", categories=["finance"])
        - 보안: 키는 로컬 .env에만 저장, 외부 전송 절대 없음

    SeeAlso:
        - Company: 수집된 데이터로 Company 생성하여 분석
        - search: 종목코드 모를 때 먼저 검색

    Args:
        *codes: 종목코드 1개 이상 ("005930", "000660").
        categories: 수집 카테고리 ["finance", "docs", "report"]. None이면 전체.
        incremental: True면 증분 수집 (기본). False면 전체 재수집.

    Returns:
        dict — 종목코드별 카테고리별 수집 건수.

    Example::

        import dartlab
        dartlab.collect("005930")                              # 삼성전자 전체
        dartlab.collect("005930", "000660", categories=["finance"])  # 재무만
    """
    from dartlab.providers.dart.openapi.batch import batchCollect

    return batchCollect(list(codes), categories=categories, incremental=incremental)


def collectAll(
    *,
    categories: list[str] | None = None,
    mode: str = "new",
    maxWorkers: int | None = None,
    incremental: bool = True,
) -> dict[str, dict[str, int]]:
    """전체 상장종목 DART 데이터 일괄 수집.

    Capabilities:
        - 전체 상장종목 DART 공시 데이터 일괄 수집
        - 미수집 종목만 선별 수집 (mode="new") 또는 전체 재수집 (mode="all")
        - 멀티키 병렬 수집 (DART_API_KEYS 쉼표 구분)
        - 카테고리별 선택 (finance, docs, report)

    Requires:
        API 키: DART_API_KEY

    Guide:
        - "전종목 데이터 수집" -> collectAll() 안내. DART_API_KEY 필요
        - "재무 데이터만 수집" -> collectAll(categories=["finance"])
        - 보안: 키는 로컬 .env에만 저장, 외부 전송 절대 없음

    SeeAlso:
        - collect: 특정 종목만 수집
        - downloadAll: HuggingFace 사전구축 데이터 (API 키 불필요, 더 빠름)

    Args:
        categories: 수집 카테고리 ["finance", "docs", "report"]. None이면 전체.
        mode: "new" (미수집만, 기본) 또는 "all" (전체 재수집).
        maxWorkers: 병렬 워커 수. None이면 키 수에 따라 자동.
        incremental: True면 증분 수집. False면 전체 재수집.

    Returns:
        dict — 종목코드별 카테고리별 수집 건수.

    Example::

        import dartlab
        dartlab.collectAll()                          # 전체 미수집 종목
        dartlab.collectAll(categories=["finance"])    # 재무만
        dartlab.collectAll(mode="all")                # 기수집 포함 전체
    """
    from dartlab.providers.dart.openapi.batch import batchCollectAll

    return batchCollectAll(
        categories=categories,
        mode=mode,
        maxWorkers=maxWorkers,
        incremental=incremental,
    )


def downloadAll(category: str = "finance", *, forceUpdate: bool = False) -> None:
    """HuggingFace에서 전체 시장 데이터 다운로드.

    Capabilities:
        - HuggingFace 사전 구축 데이터 일괄 다운로드
        - finance (~600MB, 2700+종목), docs (~8GB, 2500+종목), report (~320MB, 2700+종목)
        - 이어받기/병렬 다운로드 지원 (huggingface_hub)
        - 전사 분석(scanAccount, governance, digest 등)에 필요한 데이터 사전 준비

    Requires:
        없음 (HuggingFace 공개 데이터셋)

    Guide:
        - "데이터 어떻게 받아?" -> downloadAll("finance") 안내. API 키 불필요
        - "scan 쓰려면?" -> downloadAll("finance") + downloadAll("report") 필요
        - finance 먼저 (600MB), report 다음 (320MB), docs는 대용량 주의 (8GB)

    SeeAlso:
        - scan: 다운로드된 데이터로 전종목 비교
        - collect: DART API로 직접 수집 (최신 데이터, API 키 필요)

    Args:
        category: "finance" (재무 ~600MB), "docs" (공시 ~8GB), "report" (보고서 ~320MB).
        forceUpdate: True면 이미 있는 파일도 최신으로 갱신.

    Returns:
        None.

    Example::

        import dartlab
        dartlab.downloadAll("finance")   # 재무 전체 — scanAccount/scanRatio 등에 필요
        dartlab.downloadAll("report")    # 보고서 전체 — governance/workforce/capital/debt에 필요
        dartlab.downloadAll("docs")      # 공시 전체 — digest에 필요 (대용량 ~8GB)
    """
    from dartlab.core.dataLoader import downloadAll as _downloadAll

    _downloadAll(category, forceUpdate=forceUpdate)


def checkFreshness(stockCode: str, *, forceCheck: bool = False):
    """종목의 로컬 데이터가 최신인지 DART API로 확인.

    Capabilities:
        - 로컬 데이터와 DART 서버의 최신 공시 비교
        - 누락 공시 수 + 최신 여부 판정
        - 캐시된 결과 재사용 (forceCheck=False)

    Requires:
        API 키: DART_API_KEY

    AIContext:
        - 분석 전 데이터 최신성 확인에 사용
        - isFresh=False이면 collect()로 갱신 권장
        - missingCount로 누락 규모 파악 후 수집 우선순위 판단

    Guide:
        - "내 데이터 최신이야?" -> checkFreshness("005930")
        - "공시 누락 있어?" -> checkFreshness로 missingCount 확인
        - "데이터 업데이트 필요해?" -> checkFreshness 후 collect 안내

    SeeAlso:
        - collect: 누락 공시 실제 수집 (checkFreshness에서 발견한 gap 채우기)
        - Company: 종목 데이터 접근 (최신 데이터 기반 분석)

    Args:
        stockCode: 종목코드 ("005930").
        forceCheck: True면 캐시 무시, DART API 강제 조회.

    Returns:
        FreshnessResult — isFresh (bool), missingCount (int), lastLocalDate, lastRemoteDate.

    Example::

        import dartlab
        result = dartlab.checkFreshness("005930")
        result.isFresh       # True/False
        result.missingCount  # 누락 공시 수
    """
    from dartlab.providers.dart.openapi.freshness import (
        checkFreshness as _check,
    )

    return _check(stockCode, forceCheck=forceCheck)


def setup(provider: str | None = None):
    """AI provider 설정 안내 + 인터랙티브 설정.

    Capabilities:
        - 전체 AI provider 설정 현황 테이블 표시
        - provider별 대화형 설정 (키 입력 → .env 저장)
        - ChatGPT OAuth 브라우저 로그인
        - OpenAI/Gemini/Groq/Cerebras/Mistral API 키 설정
        - Ollama 로컬 LLM 설치 안내

    Requires:
        없음

    AIContext:
        - AI 분석 기능 사용 전 provider 설정 상태 확인
        - 미설정 provider 감지 시 setup() 안내로 연결
        - 설정 완료 여부를 프로그래밍 방식으로 체크 가능

    Guide:
        - "AI 설정 어떻게 해?" -> setup()으로 전체 현황 확인
        - "ChatGPT 연결하고 싶어" -> setup("chatgpt")
        - "OpenAI 키 등록" -> setup("openai")
        - "Ollama 어떻게 써?" -> setup("ollama")

    SeeAlso:
        - ask: AI 질문 (setup 완료 후 사용)
        - chat: AI 대화 (setup 완료 후 사용)
        - llm.configure: 프로그래밍 방식 provider 설정

    Args:
        provider: provider명 또는 alias. None이면 전체 현황 표시.
            지원: "chatgpt", "openai", "gemini", "groq", "cerebras",
            "mistral", "ollama", "codex", "custom".

    Returns:
        None (터미널/노트북에 안내 출력).

    Example::

        import dartlab
        dartlab.setup()              # 전체 provider 현황
        dartlab.setup("chatgpt")     # ChatGPT OAuth 브라우저 로그인
        dartlab.setup("openai")      # OpenAI API 키 설정
        dartlab.setup("ollama")      # Ollama 설치 안내
    """
    from dartlab.core.ai.guide import (
        providers_status,
        resolve_alias,
    )

    if provider is None:
        print(providers_status())
        return

    provider = resolve_alias(provider)

    if provider == "oauth-codex":
        _setup_oauth_interactive()
    else:
        _setup_apikey_interactive(provider)


def _setup_oauth_interactive():
    """노트북/CLI에서 ChatGPT OAuth 브라우저 로그인."""
    try:
        from dartlab.ai.providers.support.oauth_token import is_authenticated

        if is_authenticated():
            print("\n  ✓ ChatGPT OAuth 이미 인증되어 있습니다.")
            print('  재인증: dartlab.setup("chatgpt")  # 재실행하면 갱신\n')
            return
    except ImportError:
        pass

    try:
        from dartlab.cli.commands.setup import _do_oauth_login

        _do_oauth_login()
    except ImportError:
        print("\n  ChatGPT OAuth 브라우저 로그인:")
        print("  CLI에서 실행: dartlab setup oauth-codex\n")


def _setup_apikey_interactive(provider: str):
    """API 키 기반 provider 인터랙티브 설정."""
    from dartlab.core.ai.providers import _PROVIDERS

    spec = _PROVIDERS.get(provider)
    if spec is None or not spec.env_key:
        from dartlab.core.ai.guide import provider_guide

        print(provider_guide(provider))
        return

    from dartlab.core.env import promptAndSave

    promptAndSave(
        spec.env_key,
        label=spec.label,
        guide=spec.signupUrl or spec.description,
    )


def _auto_stream(gen) -> str:
    """Generator를 소비하면서 stdout에 스트리밍 출력, 전체 텍스트 반환."""
    import sys

    chunks: list[str] = []
    for chunk in gen:
        chunks.append(chunk)
        sys.stdout.write(chunk)
        sys.stdout.flush()
    sys.stdout.write("\n")
    sys.stdout.flush()
    return "".join(chunks)


def ask(
    question: str,
    *,
    stockCode: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    stream: bool = True,
    raw: bool = False,
    reflect: bool = False,
    pattern: str | None = None,
    template: str | None = None,
    modules: list[str] | None = None,
    **kwargs,
):
    """AI 에게 질문. AI 가 모든 엔진(analysis/scan/macro/credit/gather/search)을 tool 로 다룬다.

    Capabilities:
        - 자연어로 기업/시장 분석 (종목은 질문 텍스트에서 AI 가 자동 감지)
        - 스트리밍 출력 (기본) / 배치 반환 / Generator 직접 제어
        - 원본 검증 · 가정 조정 · 업종 비교 전부 AI 자율

    Requires:
        AI: provider 설정 (dartlab.setup() 참조)

    Guide:
        - "삼성전자 수익성 분석" -> dartlab.ask("삼성전자 수익성 분석해줘")
        - "삼성 vs SK하이닉스" -> dartlab.ask("삼성전자와 SK하이닉스 비교")
        - "반도체 업황" -> dartlab.ask("반도체 업황 어때")  (종목 불필요)

    SeeAlso:
        - Company: 원본 데이터 조회 (show/select)
        - scan: 전종목 비교 (프로그래밍)

    Args:
        question: 자연어 질문.
        stockCode: UI/서버가 현재 화면 종목코드를 힌트로 전달 (선택).
        provider: LLM provider.
        stream: True 면 실시간 스트리밍 출력 (기본). False 면 조용히 전체 텍스트 반환.
        raw: True 면 Generator 를 직접 반환 (커스텀 UI 용).

    Returns:
        str | None: 전체 답변 텍스트. 설정 오류 시 None. (raw=True 일 때만 Generator[str])

    Example::

        import dartlab
        dartlab.ask("삼성전자 수익성 분석해줘")
        dartlab.ask("삼성전자 분석", stream=False)  # 조용히 전체 텍스트
    """
    from dartlab.ai.runtime.standalone import ask as _ask

    if not question or not question.strip():
        print("\n  질문을 입력해 주세요.")
        print("  예: dartlab.ask('삼성전자 재무건전성 분석해줘')\n")
        return None

    if provider is None:
        from dartlab.core.ai.detect import auto_detect_provider

        detected = auto_detect_provider()
        if detected is None:
            from dartlab.core.ai.guide import no_provider_message

            print(no_provider_message())
            return None
        provider = detected

    _call_kwargs = dict(
        stockCode=stockCode,
        provider=provider,
        model=model,
        reflect=reflect,
        pattern=pattern,
        template=template,
        modules=modules,
        **kwargs,
    )

    if raw:
        return _ask(question, stream=stream, **_call_kwargs)

    if not stream:
        return _ask(question, stream=False, **_call_kwargs)

    gen = _ask(question, stream=True, **_call_kwargs)
    return _auto_stream(gen)


def templates(name: str | None = None):
    """분석 템플릿 목록 또는 특정 템플릿 내용.

    Example::

        dartlab.templates()          # 전체 목록
        dartlab.templates("가치투자") # 특정 템플릿 내용
    """
    from dartlab.ai import templates as _templates

    return _templates(name)


def saveTemplate(name: str, *, content: str | None = None, file: str | None = None):
    """사용자 분석 템플릿 저장. ~/.dartlab/templates/{name}.md

    Example::

        dartlab.saveTemplate("my_style", content="## 내 기준\\n- ROE > 15%")
    """
    from dartlab.ai import saveTemplate as _save

    return _save(name, content=content, file=file)


def plugins():
    """로드된 플러그인 목록 반환.

    Capabilities:
        - 설치된 dartlab 플러그인 자동 탐색
        - 플러그인 메타데이터 (이름, 버전, 제공 topic) 조회

    Requires:
        없음

    AIContext:
        - 확장 기능 탐색 시 설치된 플러그인 목록 확인
        - 플러그인이 제공하는 topic을 show()에서 사용 가능
        - 플러그인 유무에 따라 분석 범위 동적 결정

    Guide:
        - "플러그인 뭐 있어?" -> plugins()
        - "확장 기능 목록" -> plugins()로 설치된 플러그인 확인
        - "ESG 플러그인 있어?" -> plugins()에서 검색

    SeeAlso:
        - reload_plugins: 새 플러그인 설치 후 재스캔
        - Company.show: 플러그인 topic 조회 (plugins가 제공한 topic 사용)

    Args:
        없음.

    Returns:
        list[PluginMeta] — 로드된 플러그인 목록.

    Example::

        import dartlab
        dartlab.plugins()  # [PluginMeta(name="esg-scores", ...)]
    """
    from dartlab.core.plugins import discover, get_loaded_plugins

    discover()
    return get_loaded_plugins()


def reload_plugins():
    """플러그인 재스캔 — pip install 후 재시작 없이 즉시 인식.

    Capabilities:
        - 새로 설치한 플러그인 즉시 인식 (세션 재시작 불필요)
        - entry_points 재스캔

    Requires:
        없음

    AIContext:
        - pip install 후 세션 재시작 없이 플러그인 즉시 활성화
        - 새로 인식된 topic이 Company.show()에서 바로 사용 가능

    Guide:
        - "새 플러그인 설치했는데 안 보여" -> reload_plugins()
        - "플러그인 재스캔" -> reload_plugins()

    SeeAlso:
        - plugins: 현재 로드된 플러그인 확인 (reload 전후 비교)
        - Company.show: 플러그인 topic 조회

    Args:
        없음.

    Returns:
        list[PluginMeta] — 재스캔 후 플러그인 목록.

    Example::

        # 1. 새 플러그인 설치
        # !uv pip install dartlab-plugin-esg

        # 2. 재스캔
        dartlab.reload_plugins()

        # 3. 즉시 사용
        dartlab.Company("005930").show("esgScore")
    """
    from dartlab.core.plugins import rediscover

    return rediscover()


class _Module(sys.modules[__name__].__class__):
    """dartlab.verbose / dartlab.dataDir / dartlab.chart|table|text 프록시."""

    @property
    def verbose(self):
        """전역 verbose 설정 조회."""
        return config.verbose

    @verbose.setter
    def verbose(self, value):
        config.verbose = value

    @property
    def askLog(self):
        """ask/chat 로그 활성화 조회."""
        return config.askLog

    @askLog.setter
    def askLog(self, value):
        config.askLog = bool(value)

    @property
    def dataDir(self):
        """데이터 저장 디렉토리 경로 조회."""
        return config.dataDir

    @dataDir.setter
    def dataDir(self, value):
        config.dataDir = str(value)

    def __getattr__(self, name):
        if name == "scan":
            from dartlab.scan import Scan

            instance = Scan()
            setattr(self, name, instance)
            return instance
        if name == "analysis":
            from dartlab.analysis.financial import Analysis

            instance = Analysis()
            setattr(self, name, instance)
            return instance
        if name == "credit":
            from dartlab.credit import credit

            setattr(self, name, credit)
            return credit
        if name == "quant":
            from dartlab.quant import Quant

            instance = Quant()
            setattr(self, name, instance)
            return instance
        if name == "macro":
            from dartlab.macro import Macro

            instance = Macro()
            setattr(self, name, instance)
            return instance
        if name == "industry":
            from dartlab.industry import Industry

            instance = Industry()
            setattr(self, name, instance)
            return instance
        if name == "topdown":
            from dartlab.topdown import _TopdownEntry

            instance = _TopdownEntry()
            setattr(self, name, instance)
            return instance
        if name == "viz":
            import dartlab.viz as _viz

            setattr(self, name, _viz)
            return _viz
        if name == "chart":
            # 하위호환: dartlab.chart → dartlab.viz
            import dartlab.viz as _viz

            setattr(self, name, _viz)
            return _viz
        if name == "table":
            from dartlab.table import Table

            instance = Table()
            setattr(self, name, instance)
            return instance
        if name == "text":
            import importlib

            mod = importlib.import_module("dartlab.tools.text")
            setattr(self, name, mod)
            return mod
        raise AttributeError(f"module 'dartlab' has no attribute {name!r}")


sys.modules[__name__].__class__ = _Module

# ── 모듈 callable 패치 (Pyodide 제외 — 서버/CLI/네트워크 의존) ──

if not _IS_PYODIDE:
    # gather 모듈을 GatherEntry callable로 덮어쓰기
    # (gather 서브모듈이 top-level import로 이미 로드되므로 __getattr__ lazy 불가)
    from dartlab.gather.entry import GatherEntry as _GatherEntry

    sys.modules[__name__].gather = _GatherEntry()

    # topdown도 같은 문제 — 모듈 import가 __getattr__보다 우선이라 callable로 덮어쓴다
    from dartlab.topdown import _TopdownEntry as _TopdownEntry

    sys.modules[__name__].topdown = _TopdownEntry()

    # scan/analysis/credit/quant — 어떤 import 체인이 모듈을 먼저 로드하면
    # 모듈 클래스의 __getattr__이 동작 안 함 (CI에서 발견된 회귀).
    # 해결: 모듈 자체를 callable로 패치 — 모듈 객체에 __call__을 직접 부여.
    import types as _types

    def _makeCallableModule(modName: str, instanceFactory):
        """이미 로드된 서브모듈에 __call__을 부여하여 callable하게 만든다.

        서브모듈(rank, _helpers 등)도 그대로 import 가능. instance 메소드는 lazy 호출.
        """
        mod = sys.modules.get(modName)
        if mod is None:
            return

        class _CallableModule(_types.ModuleType):
            _instance = None

            def __call__(self, *args, **kwargs):
                if self._instance is None:
                    self._instance = instanceFactory()
                return self._instance(*args, **kwargs)

            def __getattr__(self, name):
                if self._instance is None:
                    self._instance = instanceFactory()
                try:
                    return getattr(self._instance, name)
                except AttributeError:
                    raise AttributeError(f"module '{modName}' has no attribute '{name}'") from None

        mod.__class__ = _CallableModule

    def _scanFactory():
        from dartlab.scan import Scan

        return Scan()

    def _analysisFactory():
        from dartlab.analysis.financial import Analysis

        return Analysis()

    def _quantFactory():
        from dartlab.quant import Quant

        return Quant()

    def _macroFactory():
        from dartlab.macro import Macro

        return Macro()

    # scan/analysis/quant/macro — 모듈 자체를 callable로 변환
    import dartlab.analysis.financial as _analysis_mod  # noqa: F401
    import dartlab.macro as _macro_mod  # noqa: F401
    import dartlab.quant as _quant_mod  # noqa: F401
    import dartlab.scan as _scan_mod  # noqa: F401

    _makeCallableModule("dartlab.scan", _scanFactory)
    _makeCallableModule("dartlab.analysis.financial", _analysisFactory)
    _makeCallableModule("dartlab.quant", _quantFactory)
    _makeCallableModule("dartlab.macro", _macroFactory)

    # credit은 함수형 (이미 callable)
    from dartlab.credit import credit as _credit_callable

    sys.modules[__name__].credit = _credit_callable


from dartlab.ai.insights import pastInsight, sectorInsights  # noqa: E402

__all__ = [
    "Company",
    "Fred",
    "OpenDart",
    "OpenEdgar",
    "config",
    "ask",
    "setup",
    "search",
    "listing",
    "collect",
    "collectAll",
    "downloadAll",
    "scan",
    "analysis",
    "gather",
    "quant",
    "credit",
    "macro",
    "industry",
    "topdown",
    "verbose",
    "dataDir",
    "codeToName",
    "nameToCode",
    "searchName",
    "pastInsight",
    "sectorInsights",
    "Review",
    "SelectResult",
    "ChartResult",
    "capabilities",
]


def capabilities(key: str | None = None, *, search: str | None = None) -> dict | list[str]:
    """dartlab 전체 기능 카탈로그 조회.

    Capabilities:
        CAPABILITIES dict에서 부분 조회 가능.
        key 없이 호출 시 전체 키 목록(summary 포함) 반환.
        key 지정 시 해당 항목의 상세(guide, capabilities, seeAlso 등) 반환.
        search 지정 시 자연어 질문 기반 관련 API 검색 (상위 10개).

    Requires:
        없음

    AIContext:
        AI가 "dartlab에 뭐가 있는지" 모를 때 탐색용.
        capabilities() → 목차 확인 → capabilities("analysis") → 상세 확인 → execute_code.
        capabilities(search="재무건전성") → 질문 관련 API 검색 → 코드 생성.

    Guide:
        - "dartlab 뭐 할 수 있어?" -> capabilities()
        - "분석 기능 뭐 있어?" -> capabilities("analysis")
        - "scan 어떻게 써?" -> capabilities("scan")
        - "재무건전성 관련 API?" -> capabilities(search="재무건전성")

    SeeAlso:
        - ask: AI 질문 (capabilities로 기능 파악 후 ask로 분석)
        - setup: AI provider 설정 (capabilities 확인 후 설정)

    Args:
        key: 조회할 기능 키. None이면 전체 목차.
        search: 자연어 질문 기반 검색. key와 동시 사용 불가.

    Returns:
        dict | list[str] — key 있으면 해당 항목 dict, 없으면 키+summary 목록.

    Example::

        dartlab.capabilities()                       # 전체 목차
        dartlab.capabilities("analysis")             # analysis 상세 (guide, capabilities)
        dartlab.capabilities("Company.analysis")     # Company.analysis 상세
        dartlab.capabilities("scan")                 # scan 상세
        dartlab.capabilities(search="재무건전성")     # 질문 기반 검색 → 상위 10개
    """
    if search is not None:
        from dartlab.core._capabilitySearch import searchCapabilities

        results = searchCapabilities(search)
        return {key: entry for key, entry, _score in results}

    from dartlab.core._generatedCapabilities import CAPABILITIES

    if key is None:
        return {k: v.get("summary", "") for k, v in CAPABILITIES.items()}
    if key in CAPABILITIES:
        return CAPABILITIES[key]
    # 부분 매칭: "analysis" → "Company.analysis" 등도 포함
    matched = {k: v for k, v in CAPABILITIES.items() if key.lower() in k.lower()}
    if matched:
        return matched
    return {}
