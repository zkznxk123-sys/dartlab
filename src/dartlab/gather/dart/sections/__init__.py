"""gather DART sections 생산(build) — zip → 14-col parquet (walker, 손실0/dup0).

acquire+produce plane. zip(획득) → walker 수평화 → 14-col parquet 생산. BUILD
전용 (lxml/zipfile). 계약(schema/bridge/disclosureKey resolve)은 ``core.sections``,
RUNTIME reader 는 ``providers(V2).dart.sections``. build 는 reader 를 import 0
(filesystem + core 계약으로 통신).

CLI: ``python -m dartlab.gather.dart.sections.build.builder --codes 005930,...``
"""

from __future__ import annotations
