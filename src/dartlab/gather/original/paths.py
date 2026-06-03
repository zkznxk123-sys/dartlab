"""`data/original/` 원본 백업 store 경로 SSOT — gather 자체포함.

「공시 오리지널 수집」 모듈의 모든 저장 경로를 한 곳에서 해석한다. core 로 벌리지
않는다(사용자 결정 2026-06-03) — 경로 규칙은 본 모듈 안에서만 산다.

레이아웃 (가공 0 원본, 로컬 백업, HF 미공개)::

    data/original/dart/docs/{stock_code}/{rcept_no}.zip        # 정기보고서
    data/original/dart/allFilings/{stock_code}/{rcept_no}.zip  # 비정기
    data/original/edgar/docs/{cik}/{accession_no}.txt          # 전 form full submission

gated — ``DATA_RELEASES`` 미등록 + ``.gitignore`` + ``bulkUploadHf`` "original" 거부로
HF 업로드 경로 진입 0. 공개 전환은 운영자 명시 결정 시 별도.
"""

from __future__ import annotations

from pathlib import Path

import dartlab.config as _cfg

_ORIGINAL_DIR = "original"


def originalRoot() -> Path:
    """`data/original/` 백업 루트 경로.

    Capabilities:
        - ``dartlab.config.dataDir`` 기준 ``original/`` 루트 Path 해석 — 모든 하위
          경로 헬퍼의 공통 base.

    Args:
        없음.

    Returns:
        Path — ``{dataDir}/original``. 디렉토리 생성은 하지 않음(호출자 책임).

    Raises:
        없음.

    Example:
        >>> originalRoot().name
        'original'

    Guide:
        - 직접 파일을 쓰지 말고 ``dartDocsDir`` / ``dartFilingsDir`` / ``edgarDir`` 로
          종목·종류별 디렉토리를 받는다.

    SeeAlso:
        - ``dartDocsDir`` · ``dartFilingsDir`` · ``edgarDir`` — 하위 경로 헬퍼.

    Requires:
        - ``dartlab.config.dataDir`` (env ``DARTLAB_DATA_DIR`` 또는 기본 repo ``data/``).

    AIContext:
        원본 백업 경로 SSOT — AI 가 저장 위치를 인용할 때 본 헬퍼 결과를 사용한다.

    LLM Specifications:
        AntiPatterns:
            - 경로 문자열 하드코딩 X — 항상 본 헬퍼 경유(이전·테스트 격리 위해).
            - HF 업로드 대상으로 취급 X — 로컬 백업 전용.
        OutputSchema:
            - pathlib.Path.
        Prerequisites:
            - ``dartlab.config.dataDir`` 설정.
        Freshness:
            - 정적(프로세스 dataDir 설정 시점).
        Dataflow:
            - config.dataDir → 본 헬퍼 → collect 모듈 write 경로.
        TargetMarkets:
            - KR(DART) · US(EDGAR) 원본 백업 공용.
    """
    return Path(_cfg.dataDir) / _ORIGINAL_DIR


def dartDocsDir(stockCode: str) -> Path:
    """DART 정기보고서 원본 zip 디렉토리 — ``original/dart/docs/{stock_code}/``.

    Capabilities:
        - 한 종목의 정기보고서(사업·반기·분기) ``document.xml`` zip 보관 디렉토리 해석.

    Args:
        stockCode: 6자리 종목코드 (예: ``"005930"``).

    Returns:
        Path — ``{dataDir}/original/dart/docs/{stockCode}``. 생성은 호출자 책임.

    Raises:
        없음.

    Example:
        >>> dartDocsDir("005930").parts[-3:]
        ('dart', 'docs', '005930')

    Guide:
        - 비정기공시는 ``dartFilingsDir`` 로 분리(panel/refScan 혼입 차단).

    SeeAlso:
        - ``dartFilingsDir`` — 비정기 디렉토리. ``originalRoot`` — 공통 base.

    Requires:
        - ``dartlab.config.dataDir``.

    AIContext:
        정기보고서 원본 위치 — sections/panel 재파생 시 ground truth 출처.

    LLM Specifications:
        AntiPatterns:
            - 비정기 zip 을 본 디렉토리에 저장 X — refScan 전수 스캔 오염.
            - corp_code 로 호출 X — 키는 6자리 stock_code.
        OutputSchema:
            - pathlib.Path.
        Prerequisites:
            - ``dartlab.config.dataDir`` + 6자리 stockCode.
        Freshness:
            - 정적.
        Dataflow:
            - stockCode → 본 헬퍼 → ``archiveDartOriginals`` write.
        TargetMarkets:
            - KR(DART) 정기보고서.
    """
    return originalRoot() / "dart" / "docs" / stockCode


def dartFilingsDir(stockCode: str) -> Path:
    """DART 비정기공시 원본 zip 디렉토리 — ``original/dart/allFilings/{stock_code}/``.

    Capabilities:
        - 한 종목의 비정기공시(주요사항·발행·지분·기타 등) ``document.xml`` zip 디렉토리 해석.

    Args:
        stockCode: 6자리 종목코드.

    Returns:
        Path — ``{dataDir}/original/dart/allFilings/{stockCode}``. 생성은 호출자 책임.

    Raises:
        없음.

    Example:
        >>> dartFilingsDir("005930").parts[-3:]
        ('dart', 'allFilings', '005930')

    Guide:
        - 정기보고서는 ``dartDocsDir`` 로 분리.

    SeeAlso:
        - ``dartDocsDir`` — 정기 디렉토리.

    Requires:
        - ``dartlab.config.dataDir``.

    AIContext:
        비정기공시 원본 위치 — allFilings parquet(content_raw)의 무손실 백업.

    LLM Specifications:
        AntiPatterns:
            - 정기보고서 zip 혼입 X.
        OutputSchema:
            - pathlib.Path.
        Prerequisites:
            - ``dartlab.config.dataDir`` + 6자리 stockCode.
        Freshness:
            - 정적.
        Dataflow:
            - stockCode → 본 헬퍼 → ``archiveDartOriginals`` write.
        TargetMarkets:
            - KR(DART) 비정기공시.
    """
    return originalRoot() / "dart" / "allFilings" / stockCode


def edgarDir(cik: str) -> Path:
    """EDGAR full submission 원본 디렉토리 — ``original/edgar/docs/{cik}/``.

    Capabilities:
        - 한 발행자(CIK)의 전 form full submission ``.txt`` 보관 디렉토리 해석. ``docs/``
          한 단계를 둬서 향후 다른 EDGAR 원본 종류(예: XBRL 벌크)를 ``edgar/`` 밑에 형제로 추가 가능.

    Args:
        cik: SEC CIK. zero-padding 무관(내부에서 10자리 정규화).

    Returns:
        Path — ``{dataDir}/original/edgar/docs/{cik10}``. 생성은 호출자 책임.

    Raises:
        없음.

    Example:
        >>> edgarDir("320193").parts[-2:]
        ('docs', '0000320193')

    Guide:
        - accession 별 파일명은 ``{accession_no}.txt`` (full submission, SGML 전체).

    SeeAlso:
        - ``originalRoot`` — 공통 base.

    Requires:
        - ``dartlab.config.dataDir``.

    AIContext:
        EDGAR 원본 위치 — sections(content_raw) 재파생 ground truth.

    LLM Specifications:
        AntiPatterns:
            - ticker 로 호출 X — 키는 CIK(전 form 통합 식별자).
        OutputSchema:
            - pathlib.Path.
        Prerequisites:
            - ``dartlab.config.dataDir`` + CIK.
        Freshness:
            - 정적.
        Dataflow:
            - cik → 본 헬퍼 → ``archiveEdgarOriginals`` write.
        TargetMarkets:
            - US(SEC EDGAR) 전 form.
    """
    return originalRoot() / "edgar" / "docs" / str(cik).strip().zfill(10)
