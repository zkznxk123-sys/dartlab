"""dartlab AI fine-tuning 인프라 — 마스터 플랜 v2 트랙 8.

`traceToDataset` (PR-T1) → SFT dataset 변환. `dpoPairs` (PR-T2) → DPO preference pair.
`runSft` (PR-T5) → 실 학습 trigger. 운영자 명시 트리거 (trace 200+ + GPU 24GB AND).

기본 install 에는 의존성 0 — `pip install dartlab[ft]` 명시 시만 transformers/peft/trl 활성
(PR-T4 에 등록). 본 패키지 import 자체는 추가 의존성 없음.
"""

from __future__ import annotations

__all__ = [
    "traceToSftSample",
    "loadTraceDir",
    "writeJsonl",
    "buildSftDataset",
    "extractDpoPairs",
    "buildDpoDataset",
]

_TRACE_NAMES = {"traceToSftSample", "loadTraceDir", "writeJsonl", "buildSftDataset"}
_DPO_NAMES = {"extractDpoPairs", "buildDpoDataset"}


def __getattr__(name: str):
    if name in _TRACE_NAMES:
        from dartlab.ai.training import traceToDataset as _td

        return getattr(_td, name)
    if name in _DPO_NAMES:
        from dartlab.ai.training import dpoPairs as _dpo

        return getattr(_dpo, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
