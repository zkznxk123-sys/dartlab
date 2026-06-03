"""EdgarBuildProvider 구현 + register (정공법 B — DIP).

gather/edgar 수집이 core.edgarBuild seam 으로 sections build·소비자 smoke-check 를
얻는다 (gather↛providers module-level 회피). 본 모듈은 import 시점에 register 만
수행 — 실제 build/consume 모듈은 ``call`` 시점에 lazy import.
"""

from __future__ import annotations

from dartlab.core.edgarBuild import registerEdgarBuildProvider


class _EdgarBuildProvider:
    """core.edgarBuild.EdgarBuildProvider 구현 — providers/edgar 가 build/consume 전담."""

    def call(self, module, func, *args, **kwargs):
        """providers/edgar.<module>.<func> 위임 호출 (build/consume — gather seam).

        Args:
            module: providers/edgar 하위 모듈명 (예 "docs.sections.pipeline", "company").
            func: 모듈 내 함수/심볼명.
            *args: 위임 함수로 forward.
            **kwargs: 위임 함수로 forward.

        Returns:
            위임 함수의 반환값 (build/consume 출력).

        Raises:
            ImportError: module 미존재. AttributeError: func 미존재.

        Example:
            >>> _EdgarBuildProvider().call("docs.sections.pipeline", "sections", "AAPL")  # doctest: +SKIP
        """
        import importlib

        mod = importlib.import_module(f"dartlab.providers.edgar.{module}")
        return getattr(mod, func)(*args, **kwargs)


registerEdgarBuildProvider(_EdgarBuildProvider())
