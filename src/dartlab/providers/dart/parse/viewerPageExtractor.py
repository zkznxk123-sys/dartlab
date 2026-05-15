"""DART viewer 페이지 파싱 호환 re-export.

새 SSOT 는 ``dartlab.core.parse.dartViewerPage`` 다. 기존
``dartlab.providers.dart.parse.viewerPageExtractor`` import 경로를 보존하기 위해
이 모듈은 상수와 헬퍼만 다시 내보낸다.
"""

from __future__ import annotations

from dartlab.core.parse.dartViewerPage import (
    DART_MAIN_BASE as DART_MAIN_BASE,
)
from dartlab.core.parse.dartViewerPage import (
    DART_VIEWER_BASE as DART_VIEWER_BASE,
)
from dartlab.core.parse.dartViewerPage import (
    MULTI_PAGE_RE as MULTI_PAGE_RE,
)
from dartlab.core.parse.dartViewerPage import (
    SINGLE_PAGE_RE as SINGLE_PAGE_RE,
)
from dartlab.core.parse.dartViewerPage import (
    htmlToText as htmlToText,
)
from dartlab.core.parse.dartViewerPage import (
    parseSubDocs as parseSubDocs,
)
from dartlab.core.parse.dartViewerPage import (
    tableToMarkdown as tableToMarkdown,
)
