"""panel TOC 수평화 검열기 — 전종목 lazy 스캔으로 수렴 불변식 위반 탐지 (운영 도구).

read-time 수렴(canonical 챕터 + ``sectionLeafConvergeExpr`` 3룰)을 **lazy frame 위에 그대로** 적용해
전 종목 TOC 를 모으고, 수평화가 깨지는 패턴을 구조 불변식으로 탐지한다. 매퍼 체계의 품질 게이트 —
새 era 변형·오배정이 생기면 본 검열기가 잡고, 수정은 데이터 SSOT(``canonical/canonicalData.py``)에
한 줄 추가로 끝난다(이상한 파서 신설 금지).

매퍼 체계 (파일·구분·순서 — SSOT):
    ① ``canonical/canonicalData.py`` — 운영자 수동 데이터 (CANONICAL_L1 14챕터·NARRATIVE_ERA_ALIASES·CERT)
    ② ``canonical/__init__.py``     — 챕터 수렴 Expr (sectionPath deepest + XII-우선 + NT_→III)
    ③ ``read.sectionLeafConvergeExpr`` — 섹션 수렴 단일 Expr (자기행·SPINE 코어·era-alias)
    ④ ``audit``(본 모듈)            — 위 수렴 적용 후 불변식 검열 (read 와 같은 Expr 재사용, 별도 파서 0)

LLM Specifications:
    AntiPatterns:
        - 검열 로직에 별도 파싱/수렴 재구현 금지 — read 와 같은 Expr 공용(드리프트 차단).
        - 발견을 자동 수정 금지 — 보고만. 수정은 운영자가 canonicalData 에 등재(bounded).
    OutputSchema:
        - ``auditToc(...) -> pl.DataFrame`` [corp, chapter, kind, detail].
    Prerequisites:
        - ``data/dart/panel/*.parquet``.
    Freshness:
        - 호출 시점 read 파생.
    Dataflow:
        - scan_parquet(lazy, 5컬럼) → 수렴 Expr → distinct TOC → 불변식 탐지.
    TargetMarkets:
        - KR (DART). EDGAR 는 form 챕터 체계 별도.
"""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

from .canonical import CANONICAL_RANK, canonicalChapterExpr
from .read import sectionLeafConvergeExpr

_NUM_RE = re.compile(r"^\s*(\d+)(?:-\d+)?\.")
_HDR_RE = re.compile(r"^\s*(?:[IVXLCDM]+\s*\.|【)")
_CORE_NUM = re.compile(r"^\s*\d+(-\d+)?\.?\s*")
_CORE_ETC = re.compile(r"\s*등\s*$")
_CORE_NORM = re.compile(r"[()·\s]")

# 검열 종류 — kind 컬럼 값.
AUDIT_KINDS: tuple[str, ...] = ("misplacedDetail", "duplicateNumber", "selfVariant", "coreVariant")


def _tocFrame(paths: list[Path]) -> pl.DataFrame:
    """전종목 lazy 스캔 → read 와 동일 수렴 Expr 적용 → distinct (corp, chapter, sectionLeaf)."""
    lf = pl.scan_parquet(paths).select(["corp", "chapter", "sectionPath", "sectionLeaf", "disclosureKey"])
    lf = lf.with_columns(pl.col("disclosureKey").cast(pl.Utf8))  # 전부-null 파티션 Null dtype 방어
    lf = lf.with_columns(canonicalChapterExpr("chapter", "sectionPath", noteKeyCol="disclosureKey").alias("chapter"))
    lf = lf.with_columns(sectionLeafConvergeExpr())
    return lf.select(["corp", "chapter", "sectionLeaf"]).unique().collect()


def _core(s: str) -> str:
    return _CORE_NORM.sub("", _CORE_ETC.sub("", _CORE_NUM.sub("", s).strip()))


def auditToc(codes: list[str] | None = None) -> pl.DataFrame:
    """전종목(또는 지정 종목) TOC 수평화 불변식 검열 — 위반 findings 테이블 반환.

    검열 4종 (전부 read 수렴 *적용 후* 잔존 위반 = 수렴 체계가 못 잡은 것):
        - ``misplacedDetail``: '(상세)' 섹션이 XII(상세표) 밖 챕터에 — 챕터 오배정.
        - ``duplicateNumber``: 한 챕터 안 같은 절번호 2+ 라벨 — era 슬롯충돌(의도적 분리 포함, 운영자 판독).
        - ``selfVariant``: 챕터-자기행(헤더형) 변형 2+ 잔존 — 자기행 수렴 누락.
        - ``coreVariant``: 같은 제목코어 라벨 2+ — 표면변형 미수렴.

    Args:
        codes: 검열 대상 종목코드 목록. None(기본) = ``data/dart/panel`` 전종목.

    Returns:
        ``pl.DataFrame`` [corp, chapter, kind, detail] — 위반 0 이면 빈 frame.
        detail = 사람이 판독할 위반 내용(라벨 목록 등).

    Raises:
        없음 — panel 디렉토리 부재 시 빈 frame.

    Example:
        >>> findings = auditToc(codes=["000020"])  # doctest: +SKIP
        >>> findings.filter(pl.col("kind") == "misplacedDetail")  # doctest: +SKIP

    Capabilities:
        - polars lazy projection(5컬럼)으로 전종목도 단일 스캔 — Company 객체·panel 전체 로드 0(OOM 안전).
        - read 와 동일 수렴 Expr 재사용 — 검열 결과 = 사용자가 실제 보는 TOC 와 동형.

    Guide:
        - 위반 발견 → 같은 항목이 명백하면 ``canonicalData.NARRATIVE_ERA_ALIASES`` 등재(운영자),
          다른 항목이면 honest 분리 유지. 자동 수정 금지.
        - ``duplicateNumber`` 는 의도적 분리(다른 항목 슬롯충돌)도 포함 — 운영자 판독 후 결정.

    When:
        - 새 filing 수집 후·수렴 룰 변경 후 회귀 확인. CI 정기 게이트 후보.

    How:
        - scan_parquet → canonicalChapterExpr + sectionLeafConvergeExpr → distinct TOC → 챕터별 불변식 검사.

    SeeAlso:
        - ``read.sectionLeafConvergeExpr`` — 수렴 룰 SSOT (본 검열기와 공용).
        - ``canonical.canonicalData`` — 위반 수정 등재처.

    Requires:
        - ``data/dart/panel/{code}.parquet``.

    AIContext:
        - 상태 없는 read 도구. findings 는 보고용 — 수정 판단은 운영자.
    """
    panelDir = Path(_cfg.dataDir) / "dart" / "panel"
    if not panelDir.is_dir():
        return pl.DataFrame(schema={"corp": pl.Utf8, "chapter": pl.Utf8, "kind": pl.Utf8, "detail": pl.Utf8})
    paths = (
        [panelDir / f"{c}.parquet" for c in codes if (panelDir / f"{c}.parquet").exists()]
        if codes is not None
        else sorted(panelDir.glob("*.parquet"))
    )
    if not paths:
        return pl.DataFrame(schema={"corp": pl.Utf8, "chapter": pl.Utf8, "kind": pl.Utf8, "detail": pl.Utf8})
    toc = _tocFrame(paths)
    canonSet = set(CANONICAL_RANK)
    xii = next(c for c in canonSet if c.startswith("XII"))
    rows: list[dict] = []
    for (corp, chapter), grp in toc.group_by(["corp", "chapter"]):
        secs = [s for s in grp["sectionLeaf"].to_list() if s]
        if chapter in canonSet and chapter != xii:
            for s in secs:
                if "(상세)" in s:
                    rows.append({"corp": corp, "chapter": chapter, "kind": "misplacedDetail", "detail": s})
        nums: dict[int, set[str]] = {}
        for s in secs:
            m = _NUM_RE.match(s)
            if m:
                nums.setdefault(int(m.group(1)), set()).add(s)
        for n, labs in nums.items():
            if len(labs) >= 2:
                rows.append(
                    {"corp": corp, "chapter": chapter, "kind": "duplicateNumber", "detail": " | ".join(sorted(labs))}
                )
        selfs = [s for s in secs if _HDR_RE.match(s)]
        if len(selfs) >= 2:
            rows.append({"corp": corp, "chapter": chapter, "kind": "selfVariant", "detail": " | ".join(sorted(selfs))})
        cores: dict[str, set[str]] = {}
        for s in secs:
            cores.setdefault(_core(s), set()).add(s)
        for labs in cores.values():
            if len(labs) >= 2 and not all(_NUM_RE.match(x) for x in labs):
                # 번호만 다른 쌍(7-1/7-2 류 구조분할)은 duplicateNumber 가 아니라 정상 — 코어중복은 비번호 변형만
                rows.append(
                    {"corp": corp, "chapter": chapter, "kind": "coreVariant", "detail": " | ".join(sorted(labs))}
                )
    if not rows:
        return pl.DataFrame(schema={"corp": pl.Utf8, "chapter": pl.Utf8, "kind": pl.Utf8, "detail": pl.Utf8})
    return pl.DataFrame(rows).sort(["kind", "chapter", "corp"])
