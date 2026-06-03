"""수집 파이프라인 공용 타입 — StageSpec·StageResult·StageReport·PipelineMode.

``dartlab.pipeline`` 은 L4 sink 패키지(gather fetch + providers build 를 합법 조합).
본 모듈은 core 보다 위 의존이 없는 순수 dataclass 만 정의 — 모든 stage 와
orchestrator 가 공유하는 결과/집계 계약이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

PipelineMode = Literal[
    "recent",
    "full",
    "new",
    "online",
    "offline",
    "incremental",
    "backfill",
    "changed",
]


@dataclass
class StageReport:
    """per-item 집계 누산기 — 회사/티커 1개 실패가 run 을 중단시키지 않게 한다.

    각 stage 의 item 루프가 ok/skip/err/fail 을 누적하고 실패 식별자를 모은다.
    orchestrator 가 단일 summary 로 롤업(흩어진 GITHUB_STEP_SUMMARY 대체).
    """

    ok: int = 0
    skip: int = 0
    err: int = 0
    fail: int = 0
    failures: list[str] = field(default_factory=list)

    def merge(self, other: "StageReport") -> None:
        """다른 report 를 누적 병합한다.

        Args:
            other: 합칠 StageReport.

        Returns:
            없음 (in-place 갱신).

        Raises:
            없음.

        Example:
            >>> a = StageReport(ok=1); a.merge(StageReport(ok=2)); a.ok
            3
        """
        self.ok += other.ok
        self.skip += other.skip
        self.err += other.err
        self.fail += other.fail
        self.failures.extend(other.failures)


@dataclass
class StageResult:
    """stage 1 회 실행의 최종 결과.

    ``changedFiles`` 는 HF 증분 업로드 대상(빈 list = 변경 0 → 업로드 skip).
    ``skipped`` 는 전제조건 부재(refDf 없음 등)로 stage 자체를 건너뛴 경우.
    """

    category: str
    report: StageReport = field(default_factory=StageReport)
    changedFiles: list[str] = field(default_factory=list)
    rows: int = 0
    uploaded: int = 0
    skipped: bool = False


@dataclass(frozen=True)
class StageSpec:
    """category → fetch/build/upload 메타.

    ``fetch``/``build`` 는 stage 의 run 함수가 채우며, registry 에서 조립된다.
    ``online`` False = offline(prebuild) stage — enforceOffline 경계 대상.
    """

    category: str
    run: Callable[..., StageResult] | None = None
    uploadCategories: tuple[str, ...] = ()
    online: bool = True
    label: str = ""

    def describe(self) -> dict[str, Any]:
        """stage 메타를 dict 로 — `dartlab sync --list` 표시용.

        Args:
            없음.

        Returns:
            category/online/uploadCategories/label 을 담은 dict.

        Raises:
            없음.

        Example:
            >>> StageSpec("finance").describe()["category"]
            'finance'
        """
        return {
            "category": self.category,
            "online": self.online,
            "uploadCategories": list(self.uploadCategories),
            "label": self.label,
        }
