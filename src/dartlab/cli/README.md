# cli/ — L4 dartlab 명령행 진입

> `dartlab <subcommand>` 명령행 진입점. 사용자 셸 + 자동화 스크립트.

---

## 명령 카탈로그

```bash
dartlab help "외인 매수"            # 자연어 query → 관련 API 5 (T8-2)
dartlab list scan                    # scan 카테고리 recipe 인덱스
dartlab show 005930 IS               # Company.show("IS") 등가
dartlab analyze 005930 --aspect credit
dartlab mcp                          # MCP 서버 진입
```

| 명령 | 역할 |
|------|------|
| `help` | dartlab.help() — 자연어 query API 발견 (T8-2) |
| `list` | recipe / capability 카테고리 인덱스 |
| `show` | Company.show 등가 |
| `analyze` | 분석 엔진 (analysis / credit / macro / quant / industry) |
| `mcp` | MCP server 진입 (외부 LLM 도구 등록) |
| `download` | 특정 종목 데이터 준비 |
| `setup` | OAuth / API 키 셋업 |

---

## 룰

- L4 소비자 — 다른 계층 import 자유
- `cli/commands/*` 의 매개변수는 *route handler* 면제 (namingConsistency `SKIP_PATH_PREFIXES` 정합)
- CLI 출력은 `print()` 허용 (라이브러리 코드는 `getLogger`)

---

## 관련

- [src/dartlab/skills/specs/operation/cliMaintenance.md](../skills/specs/operation/cliMaintenance.md)
- [docs/DEVELOPMENT.md](../../../docs/DEVELOPMENT.md) — CLI 명령 + 환경 변수 예시
- [docs/API_FLOWCHART.md](../../../docs/API_FLOWCHART.md) — CLI 진입점 의사결정 흐름
