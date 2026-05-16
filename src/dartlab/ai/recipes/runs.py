"""Recipe validation run 기록 — append-only Parquet.

저장 위치: `~/.dartlab/recipeRuns/<skillIdSlug>.parquet`. 사용자 home, gitignored.
[ai/memory/registry.py:217-227](src/dartlab/ai/memory/registry.py#L217-L227) 의 `~/.dartlab/decisions/`
와 같은 tier — repo 루트에 stray 파일 두지 않음 (CLAUDE.md "⛔ 워크스페이스 청결").

자기개선 사다리 회피: 본 모듈은 *append-only*. status frontmatter 자동 변경 없음.
승격은 운영자 CLI (`scripts/dev/recipe_promote.py`) 단독 권한.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import polars as pl


def _runsDirDefault() -> Path:
    """운영 default: `~/.dartlab/recipeRuns/`. 환경변수 `DARTLAB_RECIPE_RUNS_DIR` 로 override 가능 (테스트용)."""
    override = os.environ.get("DARTLAB_RECIPE_RUNS_DIR")
    if override:
        return Path(override)
    return Path.home() / ".dartlab" / "recipeRuns"


# 함수 노출 — 매 호출마다 env 다시 평가 (테스트 monkeypatch 호환).
def RECIPE_RUNS_DIR() -> Path:  # noqa: N802 - 의도적 SCREAMING_SNAKE 노출 (api 안정성)
    """recipe runs 저장 디렉토리 — env 변경 호환 위해 매 호출 재평가."""
    return _runsDirDefault()


_SCHEMA: dict[str, pl.DataType] = {
    "runId": pl.Utf8,
    "skillId": pl.Utf8,
    "asOf": pl.Utf8,
    "target": pl.Utf8,
    "market": pl.Utf8,
    "ok": pl.Boolean,
    "evidenceKinds": pl.List(pl.Utf8),
    "headlineMetric": pl.Utf8,
    "headlineValue": pl.Utf8,  # float / str 혼용 — string 으로 정규화
    "durationMs": pl.Int64,
    "refs": pl.List(pl.Utf8),
    "errorClass": pl.Utf8,
    "capturedAt": pl.Utf8,
}


@dataclass(frozen=True)
class RecipeRunRecord:
    """단일 ValidateRecipe 실행 1 row.

    Notes
    -----
    headlineValue 는 스키마 단순화를 위해 str — float / int 모두 ``str(value)`` 로 정규화하여 저장.
    스코어카드 산출 시 다시 float 시도 (실패하면 categorical 처리).
    """

    runId: str
    skillId: str
    target: str
    market: str
    ok: bool
    evidenceKinds: list[str] = field(default_factory=list)
    headlineMetric: str = ""
    headlineValue: str = ""
    durationMs: int = 0
    refs: list[str] = field(default_factory=list)
    errorClass: str | None = None
    asOf: str | None = None
    capturedAt: str | None = None

    def toDict(self) -> dict[str, Any]:
        """RunRecord 직렬화 — None 필드는 빈 문자열로 정규화."""
        d = asdict(self)
        if d["asOf"] is None:
            d["asOf"] = ""
        if d["errorClass"] is None:
            d["errorClass"] = ""
        if d["capturedAt"] is None:
            d["capturedAt"] = datetime.now(timezone.utc).isoformat()
        return d


def _slug(skillId: str) -> str:
    return skillId.replace("/", "_").replace("..", "_")


def _pathFor(skillId: str, *, runsDir: Path | None = None) -> Path:
    base = runsDir if runsDir is not None else RECIPE_RUNS_DIR()
    return base / f"{_slug(skillId)}.parquet"


def appendRun(record: RecipeRunRecord, *, runsDir: Path | None = None) -> Path:
    """단일 RecipeRunRecord 를 해당 skillId 의 parquet 에 append.

    Parameters
    ----------
    record : RecipeRunRecord
        저장할 run 1 건.
    runs_dir : Path, optional
        override directory (테스트용). 미지정시 `RECIPE_RUNS_DIR()`.

    Returns
    -------
    Path
        쓰여진 parquet 경로.

    Notes
    -----
    Polars 의 native append 가 없으므로 read → vstack → write_parquet. 파일이 없으면 새로 생성.
    동시 쓰기 보호 없음 (단일 운영자 가정). 본 함수는 ValidateRecipe tool 이 직렬로 호출.
    """
    if not record.skillId:
        raise ValueError("RecipeRunRecord.skillId is required")
    base = runsDir if runsDir is not None else RECIPE_RUNS_DIR()
    base.mkdir(parents=True, exist_ok=True)
    path = _pathFor(record.skillId, runsDir=base)

    new_row = pl.DataFrame([record.toDict()], schema=_SCHEMA)
    if path.exists():
        existing = pl.read_parquet(path)
        # 누락 컬럼 (스키마 진화 대비) 채움 후 vstack.
        for col, dtype in _SCHEMA.items():
            if col not in existing.columns:
                existing = existing.with_columns(pl.lit(None, dtype=dtype).alias(col))
        existing = existing.select(list(_SCHEMA.keys()))
        out = existing.vstack(new_row)
    else:
        out = new_row
    out.write_parquet(path)
    return path


def loadRuns(skillId: str, *, runsDir: Path | None = None) -> pl.DataFrame:
    """skillId 의 누적 run 기록 로드. 파일 없으면 빈 DataFrame (스키마 일치) 반환."""
    path = _pathFor(skillId, runsDir=runsDir)
    if not path.exists():
        return pl.DataFrame(schema=_SCHEMA)
    return pl.read_parquet(path)
