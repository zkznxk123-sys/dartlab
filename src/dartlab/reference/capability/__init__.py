"""capability — dartlab 능력 기준 SSOT (the WHAT).

dartlab 의 독스트링·calc 함수·엔진 메서드를 한데 모은 자기 기술 카탈로그.
``skills`` 가 "AI 가 능력을 상황에 맞게 사용하는 절차서 (the HOW)" 라면,
``capability`` 는 그 절차서가 가리키는 능력 자체의 정의·검색·관계 그래프다.

Submodules
----------
- ``registry`` — ``CapabilityKind`` / ``CapabilitySpec`` / ``CapabilityRegistry``
  / ``build_capability_summary`` / ``ANALYSIS_CONTRACTS`` (런타임 등록 SSOT).
- ``search``   — ``searchCapabilities`` / ``formatSearchResults`` (자연어 검색).
- ``analysisGraph`` — graph loader / queries (``loadAnalysisGraph`` 등).
- ``_generated`` — ``CAPABILITIES`` 카탈로그 dict (자동 생성, 직접 수정 금지).
- ``_generated_analysis_graph`` — ``ANALYSIS_GRAPH`` (자동 생성).

공개 함수 ``dartlab.capabilities()`` (복수, root) 와는 이름이 분리돼 있어
충돌 없음 — 본 패키지는 단수 ``capability`` (서브패키지).
"""

from __future__ import annotations
