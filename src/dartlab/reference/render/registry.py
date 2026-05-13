"""하위호환 렌더러 registry re-export."""

from dartlab.core.render.registry import getRenderer, register

__all__ = ["getRenderer", "register"]
