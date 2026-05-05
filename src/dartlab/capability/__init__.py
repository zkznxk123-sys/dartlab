"""capability 계층 — AI capability registry · CAPABILITIES 카탈로그 · Analysis Graph.

core 위에 얹히는 generated/registry SSOT. core 가 직접 의존해서는 안 되며,
공개 함수 ``dartlab.capabilities()`` 는 ``dartlab/__init__.py`` 에 정의된
함수이고 본 패키지 ``dartlab.capability`` (단수) 와는 이름이 분리되어 있다.

Submodules
----------
- ``capability.registry``  — ``CapabilityKind`` / ``CapabilitySpec`` / ``CapabilityRegistry``
  / ``build_capability_summary`` / ``ANALYSIS_CONTRACTS``.
- ``capability.search``   — ``searchCapabilities`` / ``formatSearchResults``.
- ``capability.analysisGraph`` — graph loader/queries (``loadAnalysisGraph`` 등).
- ``capability._generated`` — ``CAPABILITIES`` (자동 생성, 직접 수정 금지).
- ``capability._generated_analysis_graph`` — ``ANALYSIS_GRAPH`` (자동 생성).
"""

from __future__ import annotations
