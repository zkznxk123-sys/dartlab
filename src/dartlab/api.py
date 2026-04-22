"""dartlab 명시적 공개 API — IDE 자동완성·정적 타입검사 친화 경로.

기존 ``dartlab.__init__`` 은 ``sys.modules`` 를 직접 수정해 scan / analysis
/ quant / macro / industry 모듈을 callable 로 패치한다 (magic). IDE 와
mypy 가 이 패턴을 이해하지 못해 ``dartlab.scan.`` 탭 자동완성이 0개인
문제가 있다.

본 모듈은 같은 엔진 인스턴스를 **평범한 module-level 이름으로 명시적
export** — IDE 가 즉시 이해하는 타입 시그니처 제공.

사용법::

    from dartlab.api import scan, analysis, credit, macro, industry, quant
    scan("governance")            # IDE: Scan.__call__ 시그니처 표시
    analysis("수익구조")            # IDE: Analysis.__call__ 시그니처 표시

기존 ``dartlab.scan("governance")`` 경로도 동일하게 동작 — 본 모듈은 추가
진입점일 뿐 기존 API 를 깨지 않는다. 1.0.0 이후 점진적으로 본 경로를
권장하고 callable module magic 을 폐기할 수 있도록 마련한 기반.

Notes
-----
- 각 엔진 객체는 Pyodide 환경에서 import 불가할 수 있음 — 해당 플랫폼에서
  는 이 모듈 사용 금지 (``dartlab.scan`` 은 자동 fallback).
- Company 는 class 이므로 이 모듈 아님 — ``from dartlab import Company``.
"""

from __future__ import annotations

from dartlab.analysis.financial import Analysis as _AnalysisClass
from dartlab.credit import credit as _creditFn
from dartlab.industry import Industry as _IndustryClass
from dartlab.macro import Macro as _MacroClass
from dartlab.quant import Quant as _QuantClass
from dartlab.scan import Scan as _ScanClass

# 각 엔진의 singleton instance — ``dartlab.__init__`` 이 callable module
# 패치로 만들던 것과 동일. 여기서는 type 을 정확히 유지해 IDE 가 인식.
scan: _ScanClass = _ScanClass()
analysis: _AnalysisClass = _AnalysisClass()
credit = _creditFn  # 함수형 (이미 callable)
macro: _MacroClass = _MacroClass()
industry: _IndustryClass = _IndustryClass()
quant: _QuantClass = _QuantClass()

__all__ = [
    "scan",
    "analysis",
    "credit",
    "macro",
    "industry",
    "quant",
]
