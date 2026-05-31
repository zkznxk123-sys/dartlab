"""panel build CLI entry — ``python -X utf8 -m dartlab.providers.dart.panel.build``.

``batch._main`` 위임 (argparse: --codes / --ref / --out / --all).
"""

from __future__ import annotations

from .batch import _main

if __name__ == "__main__":
    _main()
