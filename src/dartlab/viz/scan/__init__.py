"""viz/scan — scan markdown digest 렌더 (구 src/dartlab/scan/watch/digest.py 이동).

포함 예정 (Phase A.2 에서 채움):
- digest.py — buildDigest (~100줄)

dartlab scan watch 결과 → viz/scan/digest (markdown / json / dataframe digest).
scan/watch/__init__.py 가 shim 으로 BC 유지.
"""

from __future__ import annotations
