# ops/ — dartlab 모든 설계·규칙 SSOT

**주체**: dartlab 전체 (엔진 · cross-cutting · 콘텐츠 작업).
**현재**: 29 문서. 엔진별 설계 + api-contract + architecture + testing + code + data + issues + experiments + 콘텐츠.
**방향**: 공개 기여자 기준 톤 통일 · 운영자↔AI 약속은 memory 로 분리 유지 · 엔진 추가 시 라우팅 테이블 갱신.

모든 엔진별 + cross-cutting 문서가 여기에 있다. 엔진 폴더의 README 는 포인터만.

각 문서는 **"이렇게 한다"** 명제 중심으로 구조화되어 있고, 반복된 실수는 각 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 0. 사상 SSOT · 운영 SSOT

| 문서 | 역할 |
|---|---|
| [philosophy.md](philosophy.md) | **사상 SSOT** — AI↔사람 상호 의존 · 시야×관점 격자 · 3 축 행동규약 · 투톱 진입점 · 3 정보층. 모든 ops 문서의 정점 |
| [coreloop.md](coreloop.md) | **운영 SSOT** — 자가개선 루프 O/P/R/F/A · 스크립트·스키마·PR workflow · RACI |

---

## 1. 엔진별 문서

| 문서 | 엔진 | 핵심 내용 |
|---|---|---|
| [company.md](company.md) | Company facade | 사람의 최상위 관문 · 모든 엔진 접근 · 편의성 3 원칙 · Dual Access |
| [ai.md](ai.md) | AI 엔진 | P1~P8 원칙 · 3 정보원천 · override · tool schema |
| [mcp.md](mcp.md) | MCP 서버 | 외부 LLM 클라이언트 노출 · 26 도구 · stdio·SSE |
| [analysis.md](analysis.md) | 재무분석 | 14 축 · 6 막 인과 · forecast · valuation |
| [story.md](story.md) | 보고서 | 11 타입 × 7 템플릿 · 블록 카탈로그 · narrate |
| [skills.md](skills.md) | 스킬 사상 | docstring 이 SSOT · 별도 skill 파일 없음 · 자가 개선 5 Phase · 축 개선 규칙 |
| [scan.md](scan.md) | 시장 횡단 | 정식 7 축 · EDGAR 11 축 · 프리빌드 |
| [macro.md](macro.md) | 매크로 | 사이클 · 금리 · 유동성 · 예측 · 기업이익 |
| [quant.md](quant.md) | 정량분석 | 8 그룹 축 · 팩터 · 밸류에이션 · 시뮬레이션 |
| [gather.md](gather.md) | 외부 수집 | price · flow · macro · news 4 축 |
| [industry.md](industry.md) | 산업지도 | 34 산업 · taxonomy · nodes · edges |
| [edgar.md](edgar.md) | EDGAR | 동기화 규칙 · companyfacts · bulk |
| [search.md](search.md) | 시맨틱 검색 | n-gram · HF 인덱스 · 공시 검색 |
| [guide.md](guide.md) | 안내 데스크 | 4 층위 · 에러 안내 · 키 관리 |

---

## 2. cross-cutting 문서

| 문서 | 범위 | 핵심 내용 |
|---|---|---|
| [api-contract.md](api-contract.md) | API 규칙 SSOT | Dual Access · 표준 파라미터명 · namespace 단일화 |
| [architecture.md](architecture.md) | 레이어 구조 | L0~L4 · import 방향 · 엔진 독립 |
| [code.md](code.md) | 코드 품질 | camelCase · 독스트링 9 섹션 · 릴리즈 · 검증 |
| [data.md](data.md) | 데이터 파이프라인 | HF 데이터셋 · 5 워크플로우 · 수집 |
| [testing.md](testing.md) | 테스트 | 마커 체계 · Polars 메모리 · CI |
| [issues.md](issues.md) | 이슈 관리 | GitHub Issue ↔ 테스트 ↔ 커밋 |
| [mappers.md](mappers.md) | 데이터 변환 | 계정·topic·alias·flow·notes 매퍼 |
| [experiments.md](experiments.md) | 실험 | 사용자 승인 후 본체 반영 |
| [engineAudit.md](engineAudit.md) | 엔진 audit | 검증 절차 |
| [refactor-checklist.md](refactor-checklist.md) | 대규모 rename / API 폐기 | 6 단계 점검 + 자동 게이트 (stale_references) |

---

## 3. 인프라 문서

| 문서 | 범위 |
|---|---|
| [ui.md](ui.md) | Svelte SPA |
| [vscode.md](vscode.md) | VSCode 확장 |
| [viz.md](viz.md) | 차트 + 다이어그램 |
| [channel.md](channel.md) | DevTunnels 외부 공유 |
| [spaces.md](spaces.md) | HF Spaces |
| [pyodide.md](pyodide.md) | 브라우저·Excel WASM |
