"""dartlab-plugin-example — entry-points 등록 예시.

dartlab 의 외부 plugin 시스템 (T5-1) 진입 템플릿. 본 패키지는 *최소* 예시이며,
실제 plugin 은 새 recipe / engine / tool 을 등록한다.

Install (개발 중)::

    pip install -e examples/plugin-example/

확인::

    import dartlab
    from dartlab.core.plugins import discoverPlugins, listPlugins
    for d in discoverPlugins():
        print(d.name, d.kind, d.version)
    # → hello unknown 0.1.0 (load 전)
    listPlugins()
    # → [{name: hello, kind: example, ...}]
"""

from __future__ import annotations

__version__ = "0.1.0"
