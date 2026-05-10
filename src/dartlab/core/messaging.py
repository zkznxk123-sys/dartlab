"""사용자 안내 메시지 단일 출처.

모든 user-facing ``[dartlab]`` 메시지(진행, 힌트, 에러 안내)가 이 모듈을 경유한다.

Public API::

    from dartlab.core.messaging import emit, progress, format as fmt

    emit("download:start", stockCode="005930", label="DART 공시 문서 데이터")
    emit("error:no_data", stockCode="005930", raise_as=ValueError)
    progress("KRX KIND 상장법인 목록 다운로드 중...")
    msg = fmt("hint:stale", stockCode="005930", ageStr="120일")
"""

from __future__ import annotations

from typing import Any

from dartlab.core.logger import getLogger

_PREFIX = "[dartlab]"
_log = getLogger(__name__)

# ── Simple Messages (template 문자열) ────────────────────────────

_SIMPLE: dict[str, str] = {
    # download (loadData / _ensureData / download)
    "download:start": "{stockCode} ({label}) \u2192 첫 사용: 자동 다운로드 중...",
    "download:done": "\u2713 {label} 다운로드 완료 ({sizeStr})",
    "download:done_short": "\u2713 다운로드 완료 ({sizeStr})",
    "download:exists": "\u2713 {stockCode} ({label}) 이미 존재",
    "download:progress": "{stockCode} ({label}) 다운로드 중...",
    "download:failed_single": "\u2717 {stockCode} ({label}) 다운로드 실패: {error}",
    "download:failed_item": "\u2717 {name} 실패: {error}",
    "download:refreshed": "\u2713 {stockCode} 데이터 갱신 완료",
    # downloadAll (HuggingFace snapshot_download)
    "download_all:hf_start": "{label} \u2014 HuggingFace ({repo}/{dir}) 전체 다운로드 시작...",
    "download_all:hf_retry": "\u26a0 다운로드 재시도 ({attempt}/{maxRetries})... {error}",
    "download_all:hf_done": "\u2713 {label} 전체 다운로드 완료 \u2014 {count} \u2192 {dataDir}",
    # collect (투채널 자동 수집)
    "collect:start": "{stockCode} ({label}) \u2192 로컬에 없음. DART API로 수집 중... ({keyCount}키 {mode})",
    "collect:done": "\u2713 {label} 수집 완료 ({sizeStr})",
    "collect:skip": "\u2713 {stockCode} ({label}) 이미 수집됨",
    "collect:no_key": "DART API 키가 있으면 자동 수집 가능합니다: dartlab setup dart-key",
    "collect:batch_start": "{stockCode} \u2192 로컬에 없음. {categories} {keyCount}키 병렬 수집 시작...",
    "collect:batch_done": "\u2713 {stockCode} 수집 완료 ({summary})",
    "collect:exhausted": "\u26a0 DART API 일일 한도 도달. 내일 다시 시도하거나 추가 키를 등록하세요.",
    # EDGAR
    "edgar:fallback": "사전 수집 데이터에 없음 \u2192 SEC EDGAR API에서 직접 수집 중... (최초 1회, 수 분 소요)",
    "edgar:sec_download": "{cik} (SEC EDGAR 재무 데이터) 로컬에 없음 \u2192 SEC API에서 다운로드 중...",
    # ── EDGAR 벌크 (primary 경로) ──
    # dartlab 은 SEC companyfacts.zip 을 사용자 PC 에 자동 다운로드 \u2192 {cik}.parquet 으로 변환.
    # HF 미러링 없음 (SEC 벌크가 원본).
    "edgar:bulk_download_start": "[dartlab] SEC EDGAR 재무 데이터 전체 다운로드 중 (~1.37GB, 최초 1회 5~15분) \u2014 companyfacts.zip",
    "edgar:bulk_download_done": "\u2713 companyfacts.zip 다운로드 완료 ({sizeMB:.0f}MB, {elapsedSec:.0f}s)",
    "edgar:bulk_convert_start": "[dartlab] companyfacts.zip \u2192 종목별 parquet 변환 중 (수 분 소요) \u2014 {totalCiks}개 기업",
    "edgar:bulk_convert_done": "\u2713 EDGAR 재무 parquet 변환 완료 (converted={converted} / skipped={skipped} / failed={failed}, {elapsedSec:.0f}s)",
    "edgar:bulk_fresh": "\u2713 companyfacts.zip 최신 (TTL {ttlHours}h)",
    "edgar:bulk_quarterly_start": "[dartlab] SEC 분기 메타 벌크 다운로드 중 ({year}Q{quarter}, {sizeMB:.0f}MB)",
    "edgar:bulk_quarterly_done": "\u2713 {year}Q{quarter} sub/pre/tag parquet 생성 완료",
    "edgar:empty": "{cik} SEC API 응답이 비어있음 (데이터 없음)",
    "edgar:save_done": "저장 완료: {path}",
    "edgar:download_failed": "{cik} SEC API 다운로드 실패: {error}",
    "edgar:filing_limit": "{ticker} filing 수가 많아 최근 {maxFilings}건만 수집",
    "edgar:docs_start": "{ticker} EDGAR docs 원문 수집 시작 ({count} filings, since {sinceYear})",
    "edgar:docs_skip": "{ticker} filing {count}건 skip",
    "edgar:docs_save": "저장 완료: {path}",
    "edgar:batch_start": "EDGAR docs 배치 수집 시작 ({total} tickers, since {sinceYear})",
    "edgar:batch_progress": "{idx}건 처리 완료 \u2192 {cooldown:.1f}초 휴지",
    "edgar:batch_done": "\u2713 EDGAR 배치 수집 완료 (성공 {success} / 실패 {failed} / 총 {total})",
    "edgar:incremental_start": "{ticker} EDGAR docs 증분 업데이트 ({newCount}건 신규 filing)",
    "edgar:incremental_done": "\u2713 {ticker} EDGAR docs 증분 완료 ({newRows}행 추가)",
    "edgar:no_new": "\u2713 {ticker} EDGAR docs 최신 상태",
    # freshness (L3: DART API 직접 조회)
    "freshness:checking": "{stockCode} 최신 공시 확인 중...",
    "freshness:fresh": "\u2713 {stockCode} 최신 상태",
    "freshness:stale": "\u26a0 {stockCode} 새 공시 {count}건 발견 ({latestReport})",
    "freshness:noKey": "DART API 키 없음 \u2192 사전 수집 데이터 기준으로만 확인",
    "freshness:scanDone": "\u2713 {total}종목 스캔: {staleCount}종목에 새 공시",
    # listing
    "listing:download": "KRX KIND 상장법인 목록 다운로드 중...",
    "listing:done": "{count}개 종목 로드 완료",
    "listing:krx:download": "KRX 상장법인 목록 다운로드 중...",
    "listing:krx:done": "{count}개 종목 로드 완료",
    "listing:dartlist:download": "DART 전체 법인 목록 다운로드 중 (HuggingFace)...",
    "listing:dartlist:done": "{count}개 법인 로드 완료",
    # scan
    "scan:signal_start": "서술형 시그널 스캔: {count}사",
    "scan:network_health": "그룹 건전성 분석 중...",
    "scan:prebuild_check": "scan 프리빌드 데이터 확인 중... ({dir})",
    "scan:prebuild_missing": "scan 프리빌드 데이터 없음 \u2192 HuggingFace에서 다운로드 (약 271MB, 시간이 걸릴 수 있습니다)",
    "scan:prebuild_ready": "\u2713 scan 프리빌드 준비 완료 ({fileCount}개 파일)",
    "scan:prebuild_failed": "\u26a0 scan 프리빌드 다운로드 실패: {error} \u2014 종목별 fallback 사용 (느림)",
    "scan:prebuild_incomplete": (
        "⚠ scan 프리빌드 다운로드 불완전 — 누락 파일: {missing}. "
        "네트워크 확인 후 dartlab.downloadAll('scan', forceUpdate=True) 로 재시도하세요."
    ),
    "scan:fallback_insufficient": (
        "⚠ scan/finance.parquet 프리빌드가 없어 종목별 파일 {count}개만으로 fallback. "
        "전종목(~2700)이 아닌 부분 결과입니다. dartlab.downloadAll('scan') 으로 프리빌드를 받으세요."
    ),
    # EDGAR bulk batch (finance/docs 공통)
    "edgar:bulk_start": "EDGAR {kind} 배치 수집 시작 \u2014 {total}종목 (시간이 걸릴 수 있습니다)",
    "edgar:bulk_done": "\u2713 EDGAR {kind} 배치 완료 (성공 {success} / 실패 {failed} / {elapsedSec:.0f}초)",
    "edgar:bulk_partial": "\u26a0 EDGAR {kind} 배치 부분 완료 ({done}/{total}, 오류 {errors})",
    "edgar:bulk_empty": "EDGAR 배치: 수집할 ticker가 없습니다",
    "edgar:bulk_target": "EDGAR 배치 대상: {count}종목 ({tier}, mode={mode})",
    # search 인덱스 (stemIndex)
    "stemindex:hf_start": "검색 인덱스 다운로드 중... HuggingFace ({repo})",
    "stemindex:hf_done": "\u2713 검색 인덱스 준비 완료 ({sizeStr})",
    "stemindex:hf_fail": "\u26a0 검색 인덱스 다운로드 실패: {error}",
    "stemindex:local": "\u2713 검색 인덱스 로컬 사용 ({path})",
    # data stale 경고
    "data:stale_warning": "\u26a0 로컬 데이터가 {ageDays}일째 갱신되지 않았습니다. 네트워크 또는 HuggingFace 접근을 확인하세요.",
    # 전사 분석 데이터 필요 안내
    "hint:market_data_needed": (
        "\u26a0 {category} 데이터가 로컬에 없습니다. {fn}은 전체 시장 데이터가 필요합니다.\n"
        "  dartlab.downloadAll('{category}')"
    ),
    # edgar universe
    "edgar:universe_update": "SEC listed universe 갱신 중...",
    "edgar:universe_save": "저장 완료: {path}",
    # silent failure 안내 — property/메서드가 None 반환할 때
    "hint:no_docs": "{stockCode} docs 데이터 없음 \u2192 {prop} 사용 불가. dartlab.Company('{stockCode}')로 자동 다운로드 또는 dartlab.collect('{stockCode}')",
    "hint:no_finance": "{stockCode} finance 데이터 없음 \u2192 {prop} 사용 불가. dartlab.downloadAll('finance') 또는 dartlab.collect('{stockCode}')",
    "hint:no_report": "{stockCode} report 데이터 없음 \u2192 {prop} 사용 불가. dartlab.downloadAll('report')",
    "hint:no_ai": "AI provider 미설정 \u2192 {fn} 사용 불가. dartlab.setup()으로 설정하세요.",
}


# ── Structured Messages (actions + hasDartApiKey 분기) ───────────


class _StructuredMsg:
    """structured 메시지 정의. actions_with_key / actions_without_key로 분기."""

    __slots__ = ("template", "actions", "actions_with_key", "actions_without_key")

    def __init__(
        self,
        template: str,
        actions: list[str] | None = None,
        actions_with_key: list[str] | None = None,
        actions_without_key: list[str] | None = None,
    ):
        self.template = template
        self.actions = actions or []
        self.actions_with_key = actions_with_key or []
        self.actions_without_key = actions_without_key or []


_STRUCTURED: dict[str, _StructuredMsg] = {
    "hint:missing_docs": _StructuredMsg(
        template="{stockCode} ({label}) \u2192 사전 수집 데이터에 없습니다.",
        actions_with_key=[
            "DART API 키가 설정되어 있으므로 직접 수집이 가능합니다:\n    dartlab collect {stockCode}",
        ],
        actions_without_key=[
            "DART API 키를 설정하면 직접 수집할 수 있습니다:\n    dartlab setup dart-key\n    dartlab collect {stockCode}",
        ],
    ),
    "hint:missing_other": _StructuredMsg(
        template="{stockCode} ({label}) \u2192 사전 수집 데이터에 없습니다.",
        actions=["해당 종목이 dartlab 데이터셋에 포함되어 있는지 확인하세요."],
        actions_with_key=[
            "DART API 키가 설정되어 있으므로 직접 수집이 가능합니다:\n    dartlab collect {stockCode}\n    dartlab collect --batch {stockCode}  (전 카테고리 병렬)",
        ],
        actions_without_key=[
            "DART API 키를 설정하면 직접 수집할 수 있습니다:\n    dartlab setup dart-key",
        ],
    ),
    "hint:newFilingsAvailable": _StructuredMsg(
        template="{stockCode} \u2014 새 공시 {count}건 발견 ({latestReport})",
        actions_with_key=[
            "증분 수집: dartlab collect --incremental {stockCode}",
            "또는 Python: c.update()",
        ],
        actions_without_key=[
            "DART API 키를 설정하면 자동 수집 가능:\n    dartlab setup dart-key",
        ],
    ),
    "hint:stale": _StructuredMsg(
        template="{stockCode} docs 데이터가 {ageStr} 전 기준입니다.",
        actions_with_key=["최신 공시 반영: dartlab collect {stockCode}"],
        actions_without_key=[
            "갱신하려면 DART API 키 설정이 필요합니다:\n    dartlab setup dart-key",
        ],
    ),
    "error:download_failed": _StructuredMsg(
        template="데이터 다운로드 실패 ({stockCode}, {label}): {error}",
        actions=[
            "인터넷 연결을 확인하세요",
            "해당 종목이 dartlab 데이터셋에 포함되어 있는지 확인하세요\n  \u2192 DART: 한국 상장기업 ~2,700개 / EDGAR: 미국 상장기업 ~970개",
        ],
        actions_with_key=[
            "DART 공시 문서는 직접 수집 가능합니다:\n  dartlab collect {stockCode}",
        ],
        actions_without_key=[
            "DART API 키를 설정하면 직접 수집할 수 있습니다:\n  dartlab setup dart-key\n  dartlab collect {stockCode}",
        ],
    ),
    "error:no_data": _StructuredMsg(
        template="'{stockCode}' 데이터를 찾을 수 없습니다.",
        actions=[
            "종목코드가 올바른지 확인하세요 (6자리, 예: '005930')",
            "비상장 또는 dartlab 데이터셋에 미포함 종목일 수 있습니다",
            "인터넷 연결을 확인하세요 (첫 사용 시 자동 다운로드 필요)",
        ],
        actions_with_key=[
            "DART API 키가 설정되어 있으므로 직접 수집이 가능합니다:\n  dartlab collect {stockCode}",
            "종목 검색: dartlab.searchName('\uc0bc\uc131') 또는 dartlab.listing()",
        ],
        actions_without_key=[
            "DART API 키를 설정하면 직접 수집할 수 있습니다:\n  dartlab setup dart-key\n  dartlab collect {stockCode}",
            "종목 검색: dartlab.searchName('\uc0bc\uc131') 또는 dartlab.listing()",
        ],
    ),
}


# ── Lazy Context ─────────────────────────────────────────────────


class _Context:
    """hasDartApiKey, verbose 캐시 — lazy import으로 circular dependency 방지."""

    def __init__(self) -> None:
        self._dart_key: bool | None = None
        self._verbose: bool | None = None

    @property
    def has_dart_key(self) -> bool:
        if self._dart_key is None:
            try:
                from dartlab.providers.dart.openapi.client import hasDartApiKey

                self._dart_key = hasDartApiKey()
            except ImportError:
                self._dart_key = False
        return self._dart_key

    @property
    def verbose(self) -> bool:
        if self._verbose is None:
            from dartlab import config

            self._verbose = config.verbose
        return self._verbose

    def reset(self) -> None:
        """테스트나 config 변경 후 캐시 초기화."""
        self._dart_key = None
        self._verbose = None


_ctx = _Context()


# ── Internal Formatting ──────────────────────────────────────────


def _format_simple(key: str, **kwargs: Any) -> str:
    return _SIMPLE[key].format(**kwargs)


def _format_structured(msg: _StructuredMsg, **kwargs: Any) -> str:
    lines = [msg.template.format(**kwargs)]

    actions: list[str] = list(msg.actions)
    if msg.actions_with_key or msg.actions_without_key:
        if _ctx.has_dart_key:
            actions.extend(msg.actions_with_key)
        else:
            actions.extend(msg.actions_without_key)

    if actions:
        lines.append("")
        for action in actions:
            lines.append(f"  \u2022 {action.format(**kwargs)}")

    return "\n".join(lines)


# ── Public API ───────────────────────────────────────────────────


def emit(key: str, *, raise_as: type | None = None, **kwargs: Any) -> str:
    """메시지 조립 + 출력 (또는 예외).

    Parameters
    ----------
    key : str
        메시지 키. ``_SIMPLE`` 또는 ``_STRUCTURED``에 정의.
    raise_as : type | None
        ``ValueError`` / ``RuntimeError`` 등을 넘기면 print 대신 raise.
    **kwargs
        template 변수 (stockCode, label, sizeStr 등).

    Returns
    -------
    str
        조립된 메시지 문자열.
    """
    text = format(key, **kwargs)

    if raise_as is not None:
        raise raise_as(text)

    # structured 메시지(hint/error) + collect/download 안내는 항상 출력
    _ALWAYS_SHOW = (
        "hint:",
        "error:",
        "collect:",
        "download:",
        "download_all:",
        "edgar:",
        "scan:prebuild",
        "stemindex:",
        "data:",
    )
    if key in _STRUCTURED or any(key.startswith(p) for p in _ALWAYS_SHOW):
        _log.info("%s %s", _PREFIX, text)
    else:
        # 그 외 simple 메시지는 verbose일 때만 출력
        if _ctx.verbose:
            _log.info("%s %s", _PREFIX, text)

    return text


def format(key: str, **kwargs: Any) -> str:
    """메시지만 조립하고 출력하지 않음. Server SSE, RuntimeError 등에서 사용."""
    if key in _STRUCTURED:
        return _format_structured(_STRUCTURED[key], **kwargs)
    return _format_simple(key, **kwargs)


def progress(text: str) -> None:
    """verbose-aware 한 줄 진행 메시지. ``config.verbose=False``이면 무시."""
    if _ctx.verbose:
        _log.info("%s %s", _PREFIX, text)


# ── suggest() — CAPABILITIES 기반 함수 안내 ──────────────────────


def suggest(funcName: str) -> str | None:
    """함수/메서드의 Capabilities를 안내 문자열로 반환.

    _generated.py의 CAPABILITIES dict를 소비하여,
    "이 함수로 뭘 할 수 있는지 + 뭐가 필요한지"를 안내한다.

    Args:
        funcName: "valuation", "Company.BS", "scan.governance" 등.

    Returns:
        안내 문자열 또는 매칭 없으면 None.
    """
    try:
        from dartlab.core.capability._generated import CAPABILITIES
    except ImportError:
        return None

    entry = CAPABILITIES.get(funcName)
    if entry is None:
        entry = CAPABILITIES.get(f"Company.{funcName}")
    if entry is None:
        for prefix in ("scan.", "gather."):
            entry = CAPABILITIES.get(f"{prefix}{funcName}")
            if entry:
                break
    if entry is None:
        return None

    lines = [f"[{funcName}] {entry.get('summary', '')}"]

    capText = entry.get("capabilities")
    if capText:
        lines.append("")
        for item in capText.split("\n"):
            item = item.strip()
            if item:
                lines.append(f"  - {item}")

    reqText = entry.get("requires")
    if reqText:
        lines.append(f"\n  필요: {reqText}")

    return "\n".join(lines)


# ── 에러 복구 안내 템플릿 ───────────────────────────────────────────
#
# "데이터 없음" 계열 에러 메시지는 해결책 (gather 명령·show 경로·수집 절차)
# 을 포함해야 한다. 편의성 원칙(사용자 배려 최우선) 의 SSOT.


def missingDataHint(
    resource: str,
    *,
    recoverCmd: str | None = None,
    detail: str | None = None,
) -> str:
    """\"데이터 없음\" 에러에 복구 명령을 포함한 친절한 안내 문자열 생성.

    Parameters
    ----------
    resource : str
        데이터 리소스 이름 (예: "재고자산", "컨센서스").
    recoverCmd : str, optional
        사용자가 실행할 복구 명령 문자열.
    detail : str, optional
        부가 설명 (예: "최소 2기 필요").

    Returns
    -------
    str — 한국어 안내 문자열.
    """
    base = f"{resource} 데이터 없음"
    if recoverCmd:
        base += f" → {recoverCmd}으로 먼저 수집하세요"
    if detail:
        base += f" ({detail})"
    return base


def apiKeyMissingHint(provider: str) -> str:
    """provider 별 API 키 발급·설정 안내. ``ai/settings/aiSetup.provider_guide`` 위임."""
    from dartlab.ai.settings.aiSetup import provider_guide

    return provider_guide(provider)


# ── 맥락 인식 힌트 ──────────────────────────────────────────────────
#
# 상황별 (Company 생성, 분석/스캔 요청, 키 누락, 외부 공유 등) 사용자 안내.


def onCompanyCreated(company: Any) -> list[str]:
    """Company 생성 후 표시할 힌트 목록."""
    hints: list[str] = []

    hasDocs = getattr(company, "_hasDocs", False)
    hasFinance = getattr(company, "_hasFinanceParquet", False)
    hasReport = getattr(company, "_hasReport", False)
    stockCode = getattr(company, "stockCode", "")

    if hasDocs and not hasFinance:
        hints.append(f"finance 데이터를 추가하면 재무비율/분석을 사용할 수 있습니다: dartlab.collect('{stockCode}')")
    if hasDocs and not hasReport:
        hints.append("report 데이터를 추가하면 배당/임원/지배구조 상세를 볼 수 있습니다")

    freshnessResult = getattr(company, "_freshnessResult", None)
    if freshnessResult and hasattr(freshnessResult, "ageInDays"):
        age = freshnessResult.ageInDays
        if age is not None and age > 90:
            hints.append(f"데이터가 {age}일 전 기준입니다. 갱신: c.update() 또는 dartlab collect {stockCode}")

    return hints


def nextSteps(company: Any) -> list[str]:
    """Company 생성 후 '다음에 뭘 할 수 있는지' 안내."""
    hasFinance = getattr(company, "_hasFinanceParquet", False)
    hasDocs = getattr(company, "_hasDocs", False)
    steps: list[str] = []

    if hasFinance:
        steps.append("c.show('IS' / 'BS' / 'CF')   재무제표")
        steps.append("c.show('ratios')             재무비율")
    if hasDocs:
        steps.append("c.show(topic)                공시 원문 조회")
        steps.append("c.sections                   전체 topic × period 지도")
    steps.append("c.analysis('수익성')             14축 분석")
    steps.append("c.story('수익성')               6막 보고서")

    return steps


def onScanRequested(axis: str) -> str | None:
    """스캔 호출 시 안내. (현재는 데이터 준비 상태 점검 미구현 — None.)"""
    return None


def onAnalysisRequested(axis: str | None = None) -> str | None:
    """분석 축 선택 시 안내. axis=None이면 축 선택 가이드."""
    if axis is not None:
        return None

    return (
        "분석 축을 선택하세요:\n"
        "  구조: 수익구조, 자금조달, 자산구조, 현금흐름\n"
        "  성과: 수익성, 성장성, 안정성, 효율성\n"
        "  종합: 종합평가, 이익품질, 비용구조\n"
        "  투자: 자본배분, 투자효율\n"
        "  외부: 지배구조, 공시변화, 비교분석\n"
        "  전망: 매출전망, 예측신호\n"
        '  예시: c.analysis("financial", "수익구조")'
    )


# ── 키 관리 통합 안내 ──────────────────────────────────────────────

# 키가 필요한 기능 → (환경변수, 서비스명, 발급URL, 안내) 매핑
_KEY_REQUIREMENTS: dict[str, dict[str, str]] = {
    "dart": {
        "envKey": "DART_API_KEY",
        "label": "DART OpenAPI",
        "signupUrl": "https://opendart.fss.or.kr",
        "guide": "전자공시 API 키 — 한국 상장기업 공시 직접 수집에 필요",
        "setupCmd": 'dartlab.setup("dart-key")',
    },
    "fred": {
        "envKey": "FRED_API_KEY",
        "label": "FRED (미국 연방준비제도)",
        "signupUrl": "https://fred.stlouisfed.org/docs/api/api_key.html",
        "guide": "미국 거시경제 데이터 (금리, 실업률, GDP 등) 수집에 필요",
        "setupCmd": "FRED_API_KEY=... (.env에 직접 입력)",
    },
    "ecos": {
        "envKey": "ECOS_API_KEY",
        "label": "ECOS (한국은행 경제통계)",
        "signupUrl": "https://ecos.bok.or.kr/api/",
        "guide": "한국 거시경제 데이터 (기준금리, 환율, 물가 등) 수집에 필요",
        "setupCmd": "ECOS_API_KEY=... (.env에 직접 입력)",
    },
}


def onKeyRequired(service: str) -> str:
    """키가 필요한 기능 호출 시 안내 메시지 생성.

    Parameters
    ----------
    service : str
        "dart", "fred", "ecos", 또는 provider id ("gemini", "groq" 등).
    """
    req = _KEY_REQUIREMENTS.get(service)
    if req:
        return (
            f"\n  {req['label']} API 키가 필요합니다.\n"
            f"  {req['guide']}\n\n"
            f"  1. 키 발급: {req['signupUrl']}\n"
            f"  2. 설정 방법 (택1):\n"
            f"     a) dartlab.setup() → {req['setupCmd']}\n"
            f"     b) .env 파일에 직접 입력: {req['envKey']}=발급받은키\n"
            f"     c) 환경변수 설정: export {req['envKey']}=발급받은키\n"
        )

    try:
        from dartlab.core.providers import _PROVIDERS

        spec = _PROVIDERS.get(service)
        if spec and spec.auth_kind == "api_key" and spec.env_key:
            lines = [
                f"\n  {spec.label} API 키가 필요합니다.",
                f"  {spec.description}",
            ]
            if spec.freeTierHint:
                lines.append(f"  ({spec.freeTierHint})")
            lines.append("")
            if spec.signupUrl:
                lines.append(f"  1. 키 발급: {spec.signupUrl}")
            lines.append("  2. 설정 방법 (택1):")
            lines.append(f'     a) dartlab.setup("{service}") → 대화형 입력')
            lines.append(f"     b) .env 파일에 직접 입력: {spec.env_key}=발급받은키")
            lines.append(f"     c) 환경변수 설정: export {spec.env_key}=발급받은키")
            lines.append("")
            return "\n".join(lines)
    except ImportError:
        pass

    return f"\n  '{service}' 서비스의 API 키가 필요합니다.\n  dartlab.setup()으로 설정하세요.\n"


# ── 외부 공유(channel) 안내 ─────────────────────────────────────────


def onCloudflaredMissing(os_name: str = "") -> str:
    """cloudflared 자동 설치 실패 시 수동 설치 안내."""
    lines = ["\n  cloudflared 바이너리를 찾을 수 없습니다."]
    if os_name == "Windows":
        lines.append("  설치(택1):")
        lines.append("    a) winget install --id Cloudflare.cloudflared -e")
        lines.append(
            "    b) https://github.com/cloudflare/cloudflared/releases 에서 cloudflared-windows-amd64.exe 다운로드"
        )
        lines.append("       → ~/.dartlab/bin/cloudflared.exe 로 저장")
    elif os_name == "Darwin":
        lines.append("  설치(택1):")
        lines.append("    a) brew install cloudflared")
        lines.append("    b) https://github.com/cloudflare/cloudflared/releases 에서 darwin 빌드 다운로드")
    elif os_name == "Linux":
        lines.append("  설치(택1):")
        lines.append("    a) https://pkg.cloudflare.com 의 apt/yum 저장소 등록")
        lines.append("    b) https://github.com/cloudflare/cloudflared/releases 에서 linux 빌드 다운로드")
    else:
        lines.append("  https://github.com/cloudflare/cloudflared/releases 에서 OS에 맞는 빌드를 받으세요")
    lines.append("\n  설치 후 다시 실행: dartlab channel --persistent")
    return "\n".join(lines)


def onCloudflareLoginRequired() -> str:
    """최초 1회 Cloudflare 인증 안내."""
    return (
        "\n  영구 URL 모드는 Cloudflare 계정 인증이 1회 필요합니다.\n"
        "  잠시 후 브라우저가 자동으로 열립니다.\n"
        "  → Cloudflare 로그인 → 사용할 도메인(zone) 선택 → Authorize 클릭\n"
        "  (도메인이 없다면 https://dash.cloudflare.com 에서 무료로 도메인 1개를 추가하세요)\n"
        "  인증 후에는 다시 묻지 않습니다."
    )


# cloudflared 흔한 에러 매핑
_CLOUDFLARED_ERROR_HINTS: list[tuple[str, str]] = [
    ("1033", "DNS 전파 대기 중. 1~2분 후 다시 시도하세요."),
    ("1034", "Argo 터널이 활성화되지 않았습니다. cloudflared service start 또는 다시 실행해보세요."),
    (
        "530",
        "DNS route가 이 tunnel을 가리키지 않습니다. cloudflared tunnel route dns <id> <hostname>를 다시 실행하세요.",
    ),
    ("502", "로컬 서버가 응답하지 않습니다. dartlab 서버가 켜져 있는지 확인하세요."),
    ("certificate", "cert.pem이 없거나 만료되었습니다. cloudflared tunnel login으로 재인증하세요."),
    ("permission", "credentials 파일 권한 문제. ~/.cloudflared/*.json 의 권한을 확인하세요."),
]


def onTunnelStartFailed(stderr_excerpt: str) -> str:
    """cloudflared 시작 실패 시 stderr를 분석해 안내."""
    lines = ["\n  cloudflared 터널 시작에 실패했습니다."]
    matched = []
    for needle, hint in _CLOUDFLARED_ERROR_HINTS:
        if needle.lower() in stderr_excerpt.lower():
            matched.append(f"    • {hint}")
    if matched:
        lines.append("  추정 원인:")
        lines.extend(matched)
    else:
        lines.append("  원본 에러:")
        for line in stderr_excerpt.strip().splitlines()[-5:]:
            lines.append(f"    {line}")
    lines.append("\n  추가 점검:")
    lines.append("    • dartlab channel --persistent --dry-run 으로 단계 확인")
    lines.append("    • ~/.cloudflared/cert.pem 존재 확인")
    lines.append("    • cloudflared tunnel list 로 tunnel 상태 확인")
    return "\n".join(lines)


def onShareSecurityWarning(*, mode: str, hostname: str, readonly: bool) -> str:
    """share 첫 실행 시 보안 요약 패널."""
    mode_labels = {
        "cloudflare": "Quick Tunnel (임시 URL, 데모용)",
        "cloudflare-named": "Named Tunnel (영구 URL, 1인 SaaS 표준)",
        "tailscale": "Tailscale Funnel (본인/지인용 ts.net)",
        "ngrok": "ngrok",
        "ssh": "SSH (localhost.run)",
    }
    label = mode_labels.get(mode, mode)
    rw = "읽기 전용 (POST 차단)" if readonly else "읽기/쓰기 (POST /api/ask 허용)"
    return (
        f"\n  ── 외부 공유 보안 요약 ──\n"
        f"  모드        : {label}\n"
        f"  호스트      : {hostname}\n"
        f"  권한        : {rw}\n"
        f"  방어 계층   : 토큰 + 화이트리스트 + Rate Limit + 감사 로그 + Kill Switch\n"
        f"  감사 로그   : ~/.dartlab/audit.jsonl\n"
        f"  종료        : Ctrl+C (포그라운드) / cloudflared service uninstall (서비스 모드)\n"
        f"  주의        : 토큰이 들어간 URL은 노출 = 접근 허용. 토큰 회수는 서버 재시작.\n"
    )


def promptKeyIfMissing(service: str) -> str | None:
    """키가 없으면 안내 출력 + 대화형 입력 시도. 반환: 키 또는 None.

    노트북/REPL 환경에서 키 입력까지 한 흐름으로 처리한다.
    비대화형 환경(서버, CI)에서는 안내만 출력하고 None 반환.
    """
    import os

    req = _KEY_REQUIREMENTS.get(service)
    if req:
        envKey = req["envKey"]
        existing = os.environ.get(envKey)
        if existing:
            return existing
        _log.info(onKeyRequired(service))
        try:
            from dartlab.core.env import promptAndSave

            return promptAndSave(envKey, label=req["label"], guide=req["signupUrl"])
        except (EOFError, KeyboardInterrupt):
            return None

    try:
        from dartlab.core.providers import _PROVIDERS

        spec = _PROVIDERS.get(service)
        if spec and spec.auth_kind == "api_key" and spec.env_key:
            existing = os.environ.get(spec.env_key)
            if existing:
                return existing
            _log.info(onKeyRequired(service))
            try:
                from dartlab.core.env import promptAndSave

                return promptAndSave(spec.env_key, label=spec.label, guide=spec.signupUrl or "")
            except (EOFError, KeyboardInterrupt):
                return None
    except ImportError:
        pass

    return None


# ── 에러 → 사용자 친화 메시지 변환 ──────────────────────────────────


def handleError(error: Exception, *, feature: str | None = None) -> str:
    """에러를 사용자 친화적 안내 메시지로 변환.

    에러 타입별 구체적 분류 → 일반 폴백 순으로 처리. CLI/server 의 에러
    응답 표준 변환기. 직접 호출하지 말고 ``cli.services.errors.wrapError``
    또는 server 의 ``guideDetail`` 을 거쳐 사용한다.
    """
    errType = type(error).__name__
    errStr = str(error)
    errLow = errStr.lower()

    # share/channel 에러 (cloudflared, tunnel)
    if feature == "share" or "cloudflared" in errLow or "tunnel" in errLow:
        if "cloudflared" in errLow and ("not found" in errLow or "missing" in errLow or "찾을" in errStr):
            import platform

            return onCloudflaredMissing(platform.system())
        if "cert" in errLow or "login" in errLow or "unauthenticated" in errLow:
            return onCloudflareLoginRequired()
        return onTunnelStartFailed(errStr[-500:])

    if isinstance(error, FileNotFoundError):
        return (
            f"파일을 찾을 수 없습니다: {errStr}\n  dartlab.downloadAll() 또는 dartlab.collect()로 데이터를 준비하세요."
        )

    if isinstance(error, PermissionError):
        return f"권한 오류: {errStr}\n  dartlab.setup()으로 인증을 확인하세요."

    if errType == "ChatGPTOAuthError":
        if any(kw in errLow for kw in ("token", "expire", "login")):
            return 'ChatGPT 인증이 만료되었습니다.\n  dartlab.setup("chatgpt")으로 다시 로그인하세요.'
        if any(kw in errLow for kw in ("rate", "limit")):
            return "ChatGPT 요청 한도에 도달했습니다. 잠시 후 다시 시도해주세요."
        return f'ChatGPT 연결 오류: {errStr}\n  dartlab.setup("chatgpt")으로 재인증하세요.'

    if errType == "OpenAIError" or "api_key" in errLow or "apikey" in errLow:
        return "AI 설정이 필요합니다.\n  dartlab.setup()으로 API 키를 확인하거나 다른 provider를 선택하세요."

    if (
        errType in ("ServerError", "ClientError", "APIError")
        or "google" in errType.lower()
        or "genai" in errType.lower()
    ):
        if "503" in errStr or "unavailable" in errLow or "high demand" in errLow:
            return "Gemini 서버가 일시적으로 혼잡합니다. 잠시 후 다시 시도해주세요."
        if "429" in errStr or "rate" in errLow or "quota" in errLow or "resource_exhausted" in errLow:
            return "Gemini 요청 한도에 도달했습니다. 잠시 후 다시 시도해주세요."
        if "401" in errStr or "403" in errStr or "unauthenticated" in errLow or "permission" in errLow:
            return 'Gemini API 키가 유효하지 않습니다.\n  dartlab.setup("gemini")으로 키를 확인하세요.'
        if "400" in errStr or "invalid" in errLow:
            return f"Gemini 요청 오류: {errStr}"
        return f"Gemini 연결 오류: {errStr}\n  잠시 후 다시 시도해주세요."

    if "connection" in errLow and ("refused" in errLow or "11434" in errLow):
        return (
            "Ollama가 실행 중이지 않습니다.\n"
            "  ollama serve로 시작한 뒤 다시 시도하세요.\n"
            '  미설치: dartlab.setup("ollama")'
        )

    if isinstance(error, (ConnectionError, TimeoutError)):
        return (
            "AI 서버에 연결할 수 없습니다.\n"
            "  네트워크를 확인하거나 잠시 후 다시 시도해주세요.\n"
            "  다른 provider 시도: dartlab.setup()"
        )

    if any(kw in errLow for kw in ("context", "token limit", "too long", "max_tokens")):
        return f"입력이 너무 깁니다: {errStr}\n  --exclude 옵션으로 컨텍스트를 줄여보세요."

    # 일반 폴백 — feature 정보가 있으면 prefix 추가
    if feature:
        return (
            f"[{feature}] {errType}: {errStr}\n"
            f"  dartlab.capabilities(search='{feature}') 로 사용 가능한 기능을 확인하세요."
        )
    return f"{errType}: {errStr}"
