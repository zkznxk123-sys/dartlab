# ops/ — dartlab 모든 설계/규칙 SSOT

> 모든 엔진별 + cross-cutting 문서가 여기에 있다. 엔진 폴더의 README는 포인터만.

## 엔진별 문서

| 문서 | 엔진 | 핵심 내용 |
|------|------|----------|
| [company.md](company.md) | Company facade | 근본 전제, sections 사상, 편의성 3원칙, Dual Access |
| [ai.md](ai.md) | AI 엔진 | P1~P8 원칙, 3 정보원천, override, tool schema |
| [analysis.md](analysis.md) | 재무분석 | 14축, 6막 인과, forecast, valuation |
| [review.md](review.md) | 보고서 | 11 타입 × 7 템플릿, 블록 카탈로그, narrate |
| [scan.md](scan.md) | 시장 횡단 | 정식 7축, EDGAR 11축, 프리빌드 |
| [macro.md](macro.md) | 매크로 | 사이클, 금리, 유동성, 예측, 기업이익 |
| [quant.md](quant.md) | 정량분석 | 8그룹 축, 팩터, 밸류에이션, 시뮬레이션 |
| [gather.md](gather.md) | 외부 수집 | price, flow, macro, news 4축 |
| [industry.md](industry.md) | 산업지도 | 34개 산업, taxonomy, nodes, edges |
| [edgar.md](edgar.md) | EDGAR | 동기화 규칙, companyfacts, bulk |
| [search.md](search.md) | 시맨틱 검색 | n-gram, HF 인덱스, 공시 검색 |
| [guide.md](guide.md) | 안내 데스크 | 4층위, 에러 안내, 키 관리 |

## cross-cutting 문서

| 문서 | 범위 | 핵심 내용 |
|------|------|----------|
| [api-contract.md](api-contract.md) | API 규칙 SSOT | Dual Access, 표준 파라미터명, namespace 금지 |
| [architecture.md](architecture.md) | 레이어 구조 | L0~L4, import 방향, 엔진 독립 |
| [code.md](code.md) | 코드 품질 | camelCase, 독스트링 9섹션, 릴리즈, 검증 |
| [data.md](data.md) | 데이터 파이프라인 | HF 데이터셋, 5개 워크플로우, 수집 |
| [testing.md](testing.md) | 테스트 | 마커 체계, Polars 메모리, CI |
| [issues.md](issues.md) | 이슈 관리 | GitHub Issue ↔ 테스트 ↔ 커밋 |
| [mappers.md](mappers.md) | 데이터 변환 | 계정/topic/alias/flow/notes 매퍼 |
| [experiments.md](experiments.md) | 실험 | 승인 전 밖 수정 금지 |
| [engineAudit.md](engineAudit.md) | 엔진 audit | 검증 절차 |

## 인프라 문서

| 문서 | 범위 |
|------|------|
| [ui.md](ui.md) | Svelte SPA |
| [vscode.md](vscode.md) | VSCode 확장 |
| [viz.md](viz.md) | 차트 + 다이어그램 |
| [channel.md](channel.md) | DevTunnels 외부 공유 |
| [spaces.md](spaces.md) | HF Spaces |
| [pyodide.md](pyodide.md) | 브라우저/Excel WASM |
