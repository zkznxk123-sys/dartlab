"""core layer 진입점 — L0 primitive 만.

L0 primitive (logger·env·types·memory·polarsUtil·formatting·constants·protocols·
naming·utils·cache·di·credentials·dualAccess·palette + DIP Protocol) 만 노출 책임.
re-export 0 — 사용자는 각 위치에서 직접 import (dartlab.core.dataLoader,
dartlab.providers._common.notesExtractor 등).

룰 (operation.architecture SSOT): core 는 상위 계층 (gather/providers/scan/frame/
synth/reference/analysis/macro/quant/industry/credit) import 금지.
"""

__all__: list[str] = []
