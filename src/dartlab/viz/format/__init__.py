"""viz/format — HTML / Markdown / JSON / ASCII 4 포맷 렌더.

포함 예정 (Phase A.2 + B 에서 채움, 구 story/formats.py 629줄 흡수):
- html.py — renderHtml
- markdown.py — renderMarkdown
- json_.py — renderJson
- ascii.py — renderAscii (기존 viz/ascii.py 통합)
- block.py — block 단위 render(format) 표준

story block (TextBlock / TableBlock / ChartBlock / FlagBlock) 이 자신의 표현을 4
포맷으로 통일 출력하는 SSOT.
"""

from __future__ import annotations
