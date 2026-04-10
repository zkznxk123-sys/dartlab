---
title: dartlab
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# dartlab — 한국 전자공시 분석 API + MCP 서버

설치 없이 사용:
- **REST API**: `https://eddmpython-dartlab.hf.space/api/*`
- **MCP (Claude Desktop)**: `https://eddmpython-dartlab.hf.space/mcp/sse`

## MCP 설정

`claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "dartlab": {
      "url": "https://eddmpython-dartlab.hf.space/mcp/sse"
    }
  }
}
```

## API 예시

```bash
# 공시 목록
curl "https://eddmpython-dartlab.hf.space/api/dart/filings?corp=005930"

# 재무제표
curl "https://eddmpython-dartlab.hf.space/api/dart/finance/005930?year=2024"
```
