"""calc 함수 메모이제이션 — core/memory.py로 이동됨.

하위호환 re-export. 신규 코드는 dartlab.core.memory.memoized_calc 직접 import.
"""

from dartlab.core.memory import memoized_calc  # noqa: F401

__all__ = ["memoized_calc"]
