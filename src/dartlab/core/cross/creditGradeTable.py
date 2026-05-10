"""[shim] core/cross/creditGradeTable → credit/gradeTable 도메인 복귀 (0.10 까지 BC).

본체: src/dartlab/credit/gradeTable.py
0.11 release 시 본 shim 제거. 직접 사용처는 `from dartlab.credit.scoring.gradeTable import ...` 로 갱신.

module-level import 가 새 core ↔ credit cycle 을 만들어 __getattr__ lazy 패턴 사용
(import 시점에는 credit 로드 안 함, 사용 시점 동적 lookup).
"""

from __future__ import annotations


def __getattr__(name: str):
    """0.10 BC — 사용 시점에 credit/gradeTable 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.credit.scoring.gradeTable")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.core.cross.creditGradeTable' has no attribute {name!r}") from exc
