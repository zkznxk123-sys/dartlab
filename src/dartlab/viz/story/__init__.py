"""viz/story — story block orchestration (구 src/dartlab/story/renderer.py 이동).

포함 예정 (Phase A.2 에서 채움):
- renderer.py — 구 story/renderer.py (275줄) 의 Rich 콘솔 렌더링

block list (story 가 생산) → viz/format/* (4 포맷 출력) → 최종 rich Panel / HTML /
Markdown / JSON / ASCII. story/__init__.py 가 shim 으로 BC 유지.
"""

from __future__ import annotations
