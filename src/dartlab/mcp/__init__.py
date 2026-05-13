"""DartLab MCP server public facade.

설정 정본은 사전 설치된 `dartlab` entry point 직접 호출이다.

```json
{
  "mcpServers": {
    "dartlab": {
      "command": "dartlab",
      "args": ["mcp"],
      "env": {"PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"}
    }
  }
}
```
"""

from __future__ import annotations

from dartlab.mcp.config import installMcpConfig
from dartlab.mcp.protocol import (
    MCP_INSTRUCTIONS as _MCP_INSTRUCTIONS,
)
from dartlab.mcp.protocol import (
    advertisedTools as _advertisedTools,
)
from dartlab.mcp.protocol import (
    executeWorkspaceAgentTool as _executeWorkspaceAgentTool,
)
from dartlab.mcp.protocol import (
    recipeSkillsForPrompts as _recipeSkillsForPrompts,
)
from dartlab.mcp.protocol import (
    resourcePayload as _resourcePayload,
)
from dartlab.mcp.server import createServer
from dartlab.mcp.transports import createSseApp, runSse, runStdio

__all__ = [
    "createServer",
    "createSseApp",
    "installMcpConfig",
    "runSse",
    "runStdio",
]
