# 07. Progress Ledger — 진행 원장

상태: 가변 문서 — 이 문서 세트에서 유일하게 진행 중 갱신된다.  
규칙: append-only — 과거 entry는 수정하지 않는다. 정정은 새 entry로 한다.

---

## NEXT

> 끊긴 세션이 가장 먼저 읽는 단일 포인터. 항상 최신 상태로 유지한다.

```text
다음 작업: 단계-6 (Viewer Surface Extraction — 이동 원자 윈도우 §2.5). **단계-5 전체 완료**(5-1·5-2a·5-2b·5-3a·5-3b,
  entry #16~#21). 가치 도달점 V1 달성 = 로컬 SvelteKit 터미널 첫 구동(ui/apps/local /terminal/[code] 마운트).
운영자 승인 "5단계정도"(3→4a→4b→5→6) + /goal "mainPlan 완벽한 완성·정공법·난제는 전문에이전트 토론" + "나머지 끝까지".

단계-6 = 공시뷰어를 `ui/packages/surfaces/src/viewer` 로 승격(04 §단계-6, 이동 원자 윈도우 — 착수 전 예약 entry 필수,
  07 규칙 6). 목표: terminal overlay + standalone viewer 가 같은 ViewerSurface 사용·local/public viewer adapter 분리·
  TOC/period timeline/panel matrix/compare matrix/ask drawer 통합. filing.panel* 공개 구현 동행(현재 createPublicRuntime
  panelToc/panelInit/panelGrid 가 단계-6 throw 게이트). 착수 시 4b 패턴 재사용(전문 에이전트 surface 경계+적대 이동안전
  토론 → 예약 entry → 무행위변경 git mv → §8.1 정규화). 뷰어는 landing 의 거대 자산이라 결합 census 선행 필수.
  ⚠ 단계-6 후 ui/apps/local·ui/web 의 viewer=external-url(iframe) → embedded-component 승급 검토(terminalShell hosts
    viewerStudio 로더 채움). ⚠ 로컬앱 viewer 라우트(/analysis/[code]/viewer)는 현재 스켈레톤 — 단계-6 에서 ViewerSurface 마운트.
  ⚠ landing 풀 prerender 로컬 환경한계(HF seed 미보유 404) — 로컬 게이트 = check/단위 compile/build, 풀 prerender 는 CI 권위.
잔여 이월(단계-2발): vitest unit + fixture 런타임 대조 — surface 소비 검증과 동행
잔여 이월(누적): scan 프리셋류 포트(단계-8) · map/search 포트 실구현(단계-8) · publish.yml:108 prose 경로 주석 갱신 ·
  ui/apps/local 라이브 dev 클릭스루(dartlab ai 서버 구동 후, 단계-10 Python 전환서 확증) · finance.bundle 로컬 엔드포인트
  (서버 /api 재무 번들 신설 시 — 현재 로컬 터미널 재무카드 빈값, ui/web 패리티)
재개 지점: entry #22 (단계-6 예약·census 완료) — 추출 착수 토론(아키텍트+적대)부터. census·결합 C1~C12·sub-unit
  분해·FilingPort 공개 구현 방식 전부 #22 에 박제됨. ⚠ 15k LOC 이동이라 신선 컨텍스트에서 6-1 git mv 실행 권장.
```

---

## 운영 규칙

1. 모든 작업 단위는 시작 전 이 원장에 entry를 만들고, 완료 또는 중단 시 갱신한다.
2. 커밋 규약: `<카테고리>: 플랫폼(단계-N) <내용>` (카테고리 = repo 허용 접두, hook 정합) — `git log --grep "플랫폼(단계"` 로 전체 이력 추적.
3. 작업 단위는 1세션 완결 크기로 설계한다. 초과가 예상되면 착수 전 sub-unit 분해를 이 원장에 선언한다.
4. 중단 시 의무 기록: 중단 지점 + 다음 행동 1줄. WIP 미커밋 상태로 세션을 끝내지 않는다(완결 커밋 또는 되돌림).
5. 각 단계 완료 entry는 04 §3 완료 공통 기준(1~14)의 체크 결과를 포함한다.
6. 이동 원자 윈도우(단계-4b·6·8·9)는 사전 예약 entry를 먼저 남긴다(04 §2.5).
7. 리팩토링 기간 중 제품 릴리스 발생 시 freeze 기준 commit/tag 재기록 entry를 남긴다.
8. 기준 문서(인덱스 ui-platform-refactor-prd.md + 00~06) 개정 시에도 개정 entry를 남긴다.

## Entry 양식

```text
### [N] 단계-X(단위명) — 상태(완료/중단/예약/개정)
일시:
commit:
변경 파일:
검증: (04 §3 체크 결과)
중단 지점/다음 행동: (중단 시)
rollback:
```

---

## Entries

### [1] 문서 정합화 — v2 개정 완료
일시: 2026-06-13  
commit: (이 변경의 커밋)  
내용: 전문 에이전트 2인(아키텍트·PM) 적대 검증을 반영해 v1 → v2 개정. 핵심 변경 —

- `ui/apps/public` 비채택 — landing이 영구 public shell (01 §3.2, 단계-9 재정의)
- npm 루트 워크스페이스 신설, ui/web 제외 (01 §2.1, 단계-1a 분리) + Windows/OneDrive 검증 항목
- AI 3-티어 계약 — local=advanced / public=deterministic(항상)+onDevice(WebGPU) / test=fake. "public AI=disabled" 폐기 — 출시된 공개 AskDrawer 회귀 금지 (02 §4)
- Port required — optional 메서드 + silent public fallback(`localAdapter()?.x() ?? HF`) 금지 + conformance 기계 검사 (02 §3, 05 §2)
- 단계-4 분할: 4a 제자리 포트화(병행 가능) / 4b 이동(원자 윈도우). terminal→viewer 역의존(RightStack→FinanceDialog, ViewerOverlay→ViewerStudio) 주입 계약 역전 + `window.__DARTLAB_LOCAL_TERMINAL__` 전역 locator 철거를 4a에 편입
- 무중단 대상 확장: landing 공개 route + **ui/web 로컬 터미널** (단계-3·4b 검증에 ui/web smoke)
- 의존 폐쇄 census 확대: hfRange 5·dartlabData 2·browser·scan·viewer 컴포넌트 2·brand·$app/* 13·styles css 2 (단계-0)
- ui/shared 실사용 0 실측(landing·ui/web 모두 import 0, alias 배선만 잔존) — 흡수 확정이 아니라 단계-0 census + 운영자 처분 결정으로 변경. ChartRenderer 정본 참조 문서 동시 갱신 조건
- 기능 승격 게이트 신설 (02 §10) + 열화 티어 UX 원칙 — 숨김 금지, tier badge + upgradeHint + 설치 CTA (03 §1, 00 §5-12)
- 활성 제품 작업 공존 규칙 신설 (04 §2.5) — 병행 가능 단계 / 이동 원자 윈도우 / 제품 PRD 우선
- 배포 파이프라인 하드코딩 3종(deploy-landing.yml paths · publish.yml UI build · dependabot.yml directory)을 단계 완료 기준에 편입 (04 §3-13, 단계-4b·10)
- 가치 도달점 표기: V1=단계-5(로컬 SvelteKit 터미널), V2=단계-7(로컬 고급 Ask). 재배열 대안(scaffold 선행)은 기각 — ui/web이 이미 로컬 터미널 제공 중이라 가치 공백 없음, landing 내부 3번째 소비자 신설 금지
- 이 원장(07) 신설 + 06 §9 완료 로그 이관 + 인덱스 문서표·핵심 결정 13건으로 개정
- 커밋 규약을 `<카테고리>: 플랫폼(단계-N) <내용>` 형식으로 확정 — 첫 커밋 시도에서 ai-policy hook(허용 접두 강제 + 금지 단어)과 충돌해 실측 교정

검증: 문서 변경만 — build 영향 없음.  
rollback: 이 commit revert.

### [2] 문서 정합화 — 제품 작업면 경계 원칙 + 전수 지도 (운영자 정정 반영)
일시: 2026-06-13  
commit: (이 변경의 커밋)  
내용: 운영자 정정 — "터미널·뷰어만이 아니라 블로그 자산 빼고 전부가 제품 기능"을 문서에 박음.

- 경계 원칙 신설(00 §2-11): 콘텐츠 자산(blog/docs/about/skills/legal/SEO/static) 제외 전부 = 제품 작업면
- **제품 작업면 전수 지도 단일 표** 신설(01 §4.1): route → surface → port → 추출 단계 — 헷갈림 방지 단일 참조
- scan(DataExplorer·SQL 노트북·ScreenBuilder, lib/scan 36파일)·map/industry·search를 1급 surface로 편입 (01 §4 트리, 03 §1)
- ScanPort·MapPort·SearchPort 계약 신설(02 §3.5) — 쿼리 엔진(duckdb-wasm)은 surface 내부 detail, port는 소스 공급만
- 단계-0 분류 의무 확장(changes·insights·embed·lab·playground·site-signals — site-signals는 타 세션 작업 중이라 소유자 확인 후)
- 단계-8 범위 명시 확장: "services + 잔여 제품 surface 전부" (06 §4 route 표·§5 source 표 동반 확장)

검증: 문서 변경만 — build 영향 없음.  
rollback: 이 commit revert.

### [3] 문서 정합화 — 이름 대칭 규칙 (운영자 원칙: 트리가 지도다)
일시: 2026-06-13  
commit: (이 변경의 커밋)  
내용: "폴더 구조를 잘 설계하고 직관적 트리 체계를 만들면 헷갈릴 수 없다" 원칙을 강행 규칙으로 명문화(01 §8.1).

- 이름 대칭: 작업면 한 단어가 route → surfaces 폴더 → Surface 컴포넌트 → runtime port → service command → 커밋·원장 표기까지 관통
- 한 작업면 = 한 폴더, 공개 API = index.ts 하나, 내부 깊이 ≤ 2, 내부 형태 표준화(index/XxxSurface.svelte/components/lib)
- 새 작업면 추가 레시피 5수 고정(contracts → port+adapter 2 → surfaces 폴더 → wrapper 2) — "어디에 두지?" 질문 발생 = 설계 위반 신호
- 01 §4 surfaces 트리에 route·port 대응 주석 부착 — 트리만 보고 전체 지도 파악 가능

검증: 문서 변경만 — build 영향 없음.  
rollback: 이 commit revert.

### [4] 문서 정합화 — 최종본 이중 점검 반영 (정합성 감사 31건 + 스트레스 테스트 5건)
일시: 2026-06-13  
commit: (이 변경의 커밋)  
내용: 최종 문서 cold-read 정합성 감사(결함 31건 전수)와 10개 미래 시나리오 스트레스 테스트(허점 5건)를 2차 에이전트 검증으로 수행, 전부 반영. 구조 판정 = "균열은 전부 계약 확장형, 구조 재설계형 아님 — 채택 타당".

핵심 교정 ("지시된 사고" 경로 2건 포함):
- 02 §7 public registry의 v1 잔재 "disabled AI descriptor" 제거(그대로 구현 시 공개 AskDrawer 회귀) + 02 §6.2 "숨기거나 disabled" 잔재 + 05 §3 "graceful disabled" 잔재 동시 교정 — deterministic/onDevice tier + localOnly/upgradeHint로 통일
- FinancePort 계약 스케치 신설(02 §3.5) — 표면은 단계-0 census로 확정, 개정 entry 의무
- 착수 게이트 3원 불일치 해소 — "단계-0은 PyPI 릴리스 전 착수 가능" 단서를 인덱스 §4-3·00 §4-1에 명문화
- 이름 대칭 자기모순 해소(01 §8.1): 의도된 비대칭 2건만 허용(screener→scan·compare→viewer 보조 route / ask↔ai port) + "route 없는 기능은 작업면 아님"(백테스팅=terminal 내부) 명문
- 트리 정합: contracts에 scan/map/search/evidence.ts, runtime ports에 scanPort/mapPort/searchPort/featureFlagPort 추가, 01 §2 주석·04 단계-9 "/company" 오기 교정(landing에 /company route 없음 실측)
- 미정의 계약 보충: TelemetryPort·FeatureFlagPort 스케치, AiTier 'none'=test 전용 정의, AG-UI allowlist=단계-1b에서 현행 ui/web agent gateway 스키마 census로 확정(02 §5-9)
- StoragePort 키를 surface 네임스페이스 템플릿(`terminal.backtestConfig` 등)으로 개정 — surface 기능 추가가 contracts 개정을 강제하지 않게
- 시장 축 규칙(02 §3 원칙): 시장 고유 식별자는 source-namespace(`dart:`/`edgar:`) + discriminated union으로만 — KR 필드 직박기 금지
- ui/web 생존 기간 svelte 메이저 업그레이드 금지(01 §3.4) — 파일경로 alias가 surfaces를 구식 컴파일러에 결합
- ScanPort 진화 경로 예약(02 §3.5): 로컬 1차=parquet URL 소스 공급(wasm 유지) → 필요 시 query() 승격은 계약 개정 단위로만
- 공용 부품 신설 게이트(01 §8.1-7): 2-surface 실소비·도메인 명명·design 선판정·원장 entry 4조건
- 누락 보충: 단계-5에 settings route, 단계-8 검증에 scan/map/search/prerender, 05 §8·§10에 /ask, 06 §6에 finance/scan/map/search 행, /cheatsheet·/health 분류 행, 'limited'→enum 정합, 03 ViewerSurfaceProps에 initialCompare, 03 §10 tier 스크린샷, 전 문서 헤더 v1→v2
- 잔여 주의(허점 아님, 인지 항목): landing 빌드 비용은 수용 부채(01 §3.1), 차트 3스택 통합(단계-8)은 과소평가 주의, 우월성은 단계-4b/5 완주 후 실현 — 중도 포기 시 현행보다 나쁨(원장 NEXT가 보험)

검증: 문서 변경만 — build 영향 없음.  
rollback: 이 commit revert.

### [5] 단계-0 Inventory and Boundary Map — 완료
일시: 2026-06-13  
commit: (이 변경의 커밋)  
내용: 개발 착수(운영자 go). 에이전트 2병렬(의존 폐쇄 실측 / route·운영 실사)로 단계-0 산출 완료 — 원자료는 06 §10, 표 채움은 06 §1~§6, 지도 확정은 01 §4.1.

- terminal 폐쇄 실측(55파일): 외부 표면 좁음 — $lib 데이터 모듈 7종+viewer 컴포넌트 2(주입 역전)+$app 2종(15파일)+klinecharts+tokens.css CSS 변수 상속. 나머지 ~40파일 자급
- 포트 초안 확정: localAdapter 25메서드가 합집합 95% — 4a 본질은 "optional+전역 locator(6파일)+silent fallback(13파일/33개소) → 필수 계약+주입" 기계적 치환, ~25파일 2~3세션
- 설계 결정 3건: **MacroPort 신설**(회사 무관 시리즈 — PricePort 오염 방지) / **ReportPort 분리**(reportSeries 10종 패널 직호출 → port 단일화, CompanyPort 비대 방지) / bootstrap 7종 JSON은 god-port 금지 — port별 분해 (02 §2·§3.5 반영)
- route 분류 확정: changes·insights=제품(경량, map 파생), embed=제품(위젯), playground=제품(데모), cheatsheet=콘텐츠, health·lab=시스템, **/search=블로그 검색(콘텐츠) — 전수 지도 정정**(회사 검색 실체=terminal/map 내장 인덱스+viewer 본문, 전용 route 없음), /screener=/scan redirect stub, site-signals=보류(타 세션)
- ui/shared census 확정: 20파일(chart 15·api 3·markdown 2)·실 import 0. 단 Skill OS viz 계약이 ChartRenderer 경로 정본 참조 — 처분 권고: api·markdown 폐기 / chart=viz SKILL.md+산출물 JSON+alias 3곳 동시 갱신 조건부, **운영자 결정 대기**, 집행=단계-8
- freeze ② 충족 실측: v0.10.7 PyPI 발행 성공(run 27432180934, 2026-06-12 18:09Z), pyproject=tag=CHANGELOG 3자 일치. 기준 commit=e3e296bd5
- 스트레이 판정·결정: ui/node_modules(2026-04-04 stale 169폴더)·ui/build(옛 "DartLab AI" 웹챗 SPA 빌드) 둘 다 gitignored 고아 — 삭제 결정, 집행=단계-1a

검증: 04 단계-0 기준 — 코드 변경 0(mainPlan 문서만), build 영향 없음, landing 공개 route 목록 보존(분류만 확정). ✅  
rollback: 이 commit revert.

### [6] 단계-1a 부분 집행 — 스트레이 삭제 + 본체 분할 (사용 리밋 96%)
일시: 2026-06-13  
commit: (이 변경의 커밋 — 원장 갱신만, repo 코드 무변경)  
내용: 운영자 "멈추지말고 끝까지" go로 1a 착수 → 사용 리밋 96% 통지로 **비가역 구간(lockfile 삭제·워크플로 개정) 직전에서 의도적 분할**. 집행분 = ui/node_modules·ui/build 스트레이 삭제(gitignored 고아 — repo 무영향, 검증 True/True). 사전 조사 확정분 = landing/package.json 전문(이름 dartlab-landing·prepare sync 존재·svelte ^5.56.3) + **publish.yml `cd landing && npm ci` 즉사 경로 발견**(1a 동시 개정 필수 — NEXT ⑤ 반영).  
중단 지점/다음 행동: NEXT ①(루트 package.json 신설)부터 — NEXT만 보고 재개 가능.  
rollback: 스트레이는 gitignored라 rollback 불요(재생성 가능).

### [7] 단계-1a npm 워크스페이스 기반 — 완료
일시: 2026-06-13  
commit: (이 변경의 커밋)  
변경 파일: package.json(신설)·package-lock.json(신설)·landing/package.json(svelte 5.56.3 정확 고정 + build 스크립트 viteHeap 래퍼)·landing/scripts/viteHeap.mjs(신설 — 옛 `./node_modules/vite/bin/vite.js` 고정 경로가 호이스팅으로 소멸, require.resolve 우회)·landing/package-lock.json(삭제)·landing/vite.config.ts(d3 alias 핵 4줄 제거)·.github/workflows/deploy-landing.yml(루트 npm ci + `build -w landing`)·.github/workflows/publish.yml(landing 단독 npm ci 즉사 경로 → 루트 npm ci)·.github/dependabot.yml(npm directory /landing→/)

검증 (04 단계-1a 기준 전부 green):
- npm install ✓(345pkg·50s·lockfile 생성) / **npm ci 2회 연속 ✓**(각 40s) / junction ✓(node_modules/dartlab-landing) / svelte 5.56.3 단일 deduped ✓ / vite 8.0.16 단일 ✓
- landing check ✓(4365파일·에러 0) / **landing 풀빌드 ✓**(viteHeap 실전, pre/post 파이프라인 정상) / **ui/web 단독 npm ci+build ✓**(522pkg·22s — 워크스페이스 오염 0, cross-import가 루트 호이스팅 위에서 정상)
- 스트레이 ui/node_modules·ui/build 삭제 집행 ✓(entry #6)

실측 사건 1건 (Windows/OneDrive 검증 항목의 실현): 첫 npm ci에서 lightningcss 네이티브 .node EPERM — 원인은 OneDrive 동기화 아님(프로세스 미실행 확인), 고아 delete-pending 핸들(Defender/인덱서 추정·고아 SID ACL 동반). takeown·icacls 무효 → **잠긴 디렉토리 rename-aside로 해소**, 이후 ci 2연속 무재발. 프로토콜 박제: 로컬 EPERM 시 잔여 `.{pkg}-{hash}` 임시 디렉토리를 repo 밖으로 rename 후 재시도.

남은 위험: publish.yml 개정분은 다음 릴리스 태그에서 실검증(다음 publish 1회 주시). deploy-landing은 이 push로 즉시 실검증됨.  
rollback: 이 commit revert + `cd landing && npm install`로 구 lockfile 재생성.

### [8] 단계-1b ui/packages/contracts — 완료
일시: 2026-06-13  
commit: (이 변경의 커밋)  
변경 파일: ui/tsconfig.base.json(신설)·ui/packages/contracts/{package.json,tsconfig.json,src/19파일}(신설)·package-lock.json(워크스페이스 등록)

내용: 타입 계약을 **발명 0, 기존 코드 승격**으로 작성 — 사전 census(landing 실타입 12파일 + AG-UI 이벤트 emitter/수신 SSOT 대조 + viewer panel 타입 인벤토리) 기반.

- 도메인 계약 14: company(ProductIndexItem·CompanyRelations·LiveCompanyReportFact)·price(Candle·CompanyPrices)·filing(Regular/NonRegular + panel Toc/Grid/Init — ui/web HTTP판 기준 + leafType superset로 양앱 발산 해소)·finance(TerminalFinanceBundle 전계층)·macro(MacroPort 신설분)·report(10종 + ReportPort 분리분)·scan·map·search(IndexRow 승격)·viewer·ai·services·navigation·storage
- AG-UI allowlist 15종 박제(ai.ts) — emitter SSOT=server/agentGateway.py `_ALLOWED_EVENTS`, 발행 12종 + reserved 3종(TOOL_CALL_ARGS·MESSAGES_SNAPSHOT·ACTIVITY_SNAPSHOT) 주석 명시. refDetails 실형태 = EvidenceRef(evidence.ts)
- 계약 위생 결정: `Num` 1회 정의 수렴(옛 3중 재정의)·parquet 원어 행(한글 컬럼·snake)은 어댑터 내부 비밀로 계약 제외·Map→Record(JSON-safe)·port 메서드 전부 required·빈값 규약 주석 박제([]=해당없음 / null=미존재)·StoragePort 네임스페이스 키·잠정 표면(ScanTableSource/Preset·IndustryMapData)은 단계-8 전 확정 주석
- 02 §3 스케치와의 의도적 발산(현실 우선): CompanyPort recent 메서드 제외(storage 키로)·MacroPort.getLatest() 무인자(실표면)·liveQuote 미포함(미실측 — 4a에서 추가). **02 §3 스케치는 초안 지위 — 확정 SSOT = contracts**

검증: npm install 워크스페이스 등록 ✓ / tsc strict(noUncheckedIndexedAccess·verbatimModuleSyntax) exit 0 ✓ / 외부 import 0 (no-dependency 기계 확인) ✓ / fixture type conformance 는 fake runtime(단계-2 산출) 전제 — **단계-2로 이월(정직 기록)**  
rollback: 이 commit revert (신설 파일만 — 기존 코드 무접촉).

### [9] 단계-2 ui/packages/runtime — 완료
일시: 2026-06-13  
commit: (이 변경의 커밋)  
변경 파일: ui/packages/runtime/{package.json,tsconfig.json,src/9파일}(신설)·package-lock.json(등록)·mainPlan/01(트리 교정 1건)

- **createFakeRuntime — 전 16포트 결정론 fixture 전구현**(난수·현재시각 금지). DartLabRuntime 타입 통째 구현이므로 tsc가 "전 포트 required 메서드 구현 존재"를 컴파일 타임에 기계 강제 — 05 §2 conformance의 절반이 구조적으로 달성. navigationCalls 기록으로 surface 테스트에서 이동 검증 가능
- public/local adapter skeleton — **미구현 포트 접근 = 명시적 throw**("단계-4a에서 구현 — 보이면 배선 순서 위반"). silent fallback 금지 구조를 골격부터 강제
- createRuntime kind 디스패처(앱 shell 1곳 전용) + runtimeContext.svelte.ts(getContext 주입 — 전역 locator 대체) + createServiceRegistry(localOnly/disabled 실행 거부 + descriptor 렌더 분리) + RuntimeCache(상한 필수 LRU+TTL)·RequestDedup
- 트리 교정(01 §4): runtime/ports/ 중복 폴더 비채택 — port 정의 SSOT는 contracts (덕지덕지 방지)

검증: tsc strict exit 0 ✓ / 전역 직접 참조($app/·window.·localStorage) grep 0 ✓ / 워크스페이스 등록 ✓. vitest unit + 런타임 fixture 대조는 첫 surface 소비와 동행(NEXT 이월 기록)  
rollback: 이 commit revert (신설 파일만).

### [10] 단계-3 ui/packages/design — 완료 (토큰 1:1 이동)
일시: 2026-06-13  
commit: (이 변경의 커밋)  
변경: landing lib/styles 3종(tokens·typography·v2-tokens, --dl-* 원천) → ui/packages/design/src/styles **git mv 순수 이동(내용 불변)**. landing +layout 2곳 → `@dartlab/ui-design/styles/*` 재배선(+의존 명시). ui/web deep import 2줄 → packages 파일경로 재배선(워크스페이스 밖 — 01 §3.4).  
범위 결정: semantic/aliases 계층화·primitive 세트는 **실소비 등장 시점**(빈 스캐폴딩 금지, 4b/6에서 terminal.css 흡수와 동행). 시각 회귀 스크린샷은 내용 불변 이동이라 구조적 비대상 — 토큰 내용 변경이 생기는 첫 단위부터 baseline 운영.  
검증: landing check 에러0 ✓ / landing 풀빌드 ✓ / ui/web build ✓ (양 무중단 대상 green)  
rollback: 이 commit revert.

### [11] 단계-4a-1 데이터 클라이언트 runtime/data 이관 — 완료
일시: 2026-06-13  
commit: (이 변경의 커밋)  
변경: hfRange·origin·cacheStore·dartlabData 4파일 git mv → `@dartlab/ui-runtime/data/*` 공개 subpath(과도기 표면 — viewer/scan도 과도기 소비, 단계-8 후 비공개화 검토). 수술 3건 — ① origin `import.meta.env` 안전 캐스트(런타임 tsc는 vite/client 무의존) ② cacheStore `$app/environment`→`typeof window` ③ dartlabData `$app/paths base`→`setStaticBase()` 주입(landing +layout 1회 호출, 4a-2에서 RuntimeEnvironment.basePath 정식화). 소비처 **26파일** 기계 재배선(sed — terminal 로더·viewer panelLoad/queryCanon/companyNames·scan financeLiteRuntime·browser 4종·lib/data 잔존 6종·lab route 3종·ViewerStudio). runtime deps에 hyparquet 2종. landing fs.allow에 ui/packages 추가(dev 차단 방지). ui/web vite alias 3종(@dartlab/ui-{runtime,design,contracts} → packages src 파일경로 — 워크스페이스 밖 해석).  
검증: runtime tsc strict 0 ✓(이관 파일 무수정 통과) / landing check 에러0 ✓ / landing 풀빌드 ✓ / ui/web build ✓ / 옛 `$lib/data/{4종}` 참조 grep 0 ✓  
rollback: 이 commit revert.

### [12] 복구 — 단계-3 커밋 누락분(ui-design package.json) + deploy red 해소
일시: 2026-06-13  
commit: 634c09b75  
내용: 단계-3 path 명시 커밋(5f4f78d5a)에서 **신설 `ui/packages/design/package.json` 이 누락**됨 — 로컬 검증은 파일 존재로 전부 통과해 사각. 원격은 워크스페이스 미해석 → `@dartlab/ui-design/styles/*` import 해석 실패 → **Deploy Landing 2연속 failure**(run 27450780309·27451313133, GH Pages 는 직전 성공 배포로 잔존 = 사이트 무중단 유지). 누락 파일 단독 복구 커밋·push.  
교훈(룰 강화): ① path 명시 커밋은 staging 후 `git status --short` 로 신설 파일 ?? 잔존 0 을 기계 확인 ② 원격 paths 트리거 점검 — 복구 push 가 deploy 를 못 깨운 2차 사각 발견(entry #13 에서 paths 편입).  
rollback: 해당 없음(누락 복구).

### [13] 단계-4a-2 포트 조립 + 호출부 치환 + 브리지 재조립 — 완료
일시: 2026-06-13  
commit: (이 변경의 커밋)  
변경 (3축):
- **어댑터**: 로더 9종 git mv → `runtime/src/adapters/public/sources/`(priceSource·govPriceSource·financeSource·reportSource·macroSource·relationsSource·productIndexSource·regularFilingsSource·nonRegularFilingsSource — localTerminalAdapter fallback 가지 전부 절제, `$app/environment`→`typeof window`, 타입은 contracts 소비로 로컬 재정의 제거). createPublicRuntime 실구현 조립 — **shared 필수 주입 계약**(reportFacts=companyLive·changes=duckSql, landing 잔류라 의존 방향 보존) + viewer 포트 셸 주입. 옛 workbench price.initial 합성(gov∥recent 병합→seed→date 폴백)은 PricePort.initial 로 승격. filing.panel*(단계-6)·scan 프리셋류(단계-8)·navigation/storage/map/search/ai 는 명시 throw 게이트 유지. createRuntime kind 디스패처는 discriminated union 으로 개정. contracts 보강: GOV_ATTRIBUTION(price)·MACRO_SERIES+MACRO_ATTRIBUTION(macro) 상수 승격. govRecent·productIndex Map→Record(JSON-safe 계약 정합).
- **landing**: 컴포지션 루트 `lib/runtime/publicRuntime.ts` 신설(getPublicRuntime 싱글턴 — route·scan 글루 전용, 컴포넌트는 컨텍스트). Terminal.svelte `runtime` 필수 prop + setDartLabRuntime 컨텍스트 배포. 패널 6종(CenterStack·RightStack·LeftRail·FinFullscreen·ViewerOverlay·SourcesModal)·PriceChart·finTabs(ReportPort 파라미터 주입)·routeLoad(warmup)·scan 2곳(Detail·+page) 호출부 전부 포트 치환. 차트 순수수학은 `charts/candleMath.ts` 분리(어댑터 아님). lastSymbol·warmup 신설. **workbench.ts·localAdapter.ts 삭제**. /terminal·/lab/terminal-dev 라우트가 runtime 주입.
- **ui/web**: localTerminalData 를 **DartLabRuntime 재조립**(price/finance/company/filing(panel* HTTP 정규화기 — toc 메타 null 정직·sectionKey 파생)·report=null 정직·scan.changes=[]·viewer=external-url·macro=createHfMacroPort 명시 재사용). LandingTerminalSurface 가 runtime 을 mount prop 주입 — **`window.__DARTLAB_LOCAL_TERMINAL__` 전역 locator 철거**. landingDataShims.ts 삭제 + vite 데이터 alias 5종 제거. tsconfig paths 에 @dartlab 2종.
- **배포 가드(entry #12 후속)**: deploy-landing.yml paths 에 `ui/packages/**`+루트 package.json/lock 편입(원래 4b 예정 — 단계-3부터 빌드 의존이라 앞당김. 누락 시 패키지만 바뀐 push 가 deploy 를 건너뜀).

검증: runtime tsc strict 0 ✓(noUncheckedIndexedAccess 마찰 40건 → 근원 수정: pk 파싱 destructuring·grid 조회·인덱스 가드 — 전부 동작 불변 보강) / landing check 0 에러·4395파일 ✓ / landing 풀빌드+prerender ✓ / ui/web build(tsc -b 포함) ✓ — 로컬 HTTP 패널 타입과 계약의 실제 발산 3건(toc block 메타·chapter null·init first 포인터)을 tsc 가 적발, 정규화기로 해소 / `localTerminalAdapter`·`__DARTLAB_LOCAL_TERMINAL__`·옛 모듈 경로 grep 0 ✓ / 신설 파일 staging 후 ?? 잔존 0 확인 ✓(entry #12 룰)  
rollback: 이 commit revert (이동·삭제·신설 모두 단일 커밋).

### [14] 단계-4a-3 viewer 주입 역전 + $app 결합 제거 — 완료 (4a 전체 종료)
일시: 2026-06-13  
commit: (이 변경의 커밋)  
내용: 4a 마지막 sub-unit. terminal → viewer **역의존 주입 역전** + 포터블 surface 트리의 SvelteKit 전역 결합 제거.
- **viewer 주입 역전**: `data/hosts.ts` 신설(TerminalHosts 계약 — viewerStudio·financeDialog lazy 로더, 둘 다 nullable). Terminal.svelte `hosts` 필수 prop → RightStack·ViewerOverlay 로 전달. 동적 import 리터럴(`$lib/components/viewer/*`)은 **셸 소유**로 이동(landing 두 라우트가 주입) — 청크 분리 유지(⤢ 클릭 전 0바이트 불변). ui/web 셸은 `hosts={viewerStudio:null,financeDialog:null}` 주입 → 뷰어=viewer port URL(iframe)·재무모달=열화 안내(숨김 금지 원칙). **ViewerStudioShim·FinanceDialogShim 2종 삭제** + vite alias 2종·terminalShimDir 제거.
- **$app 결합 제거**: 포터블 트리 6파일 `$app/environment browser` → `typeof window` (chartState·drawStore·templateStore·PriceChart·livePrice + 4a-2 stores). `$app/paths base` → `runtime.env.basePath`(Terminal·LeftRail·RightStack). livePrice `import.meta.env` 안전 캐스트(origin.ts 패턴). **routeLoad.ts 는 의도적 잔류** — getPublicRuntime·$app/paths 에 이미 묶인 landing 셸 글루(이식 surface 아님)라 $app/environment 정당, 4b 에서 라우트 폴더로 분리.
- 경계 판정: 포터블 surface(charts·panels·livePrice·stores)는 $app·전역 locator·shim 전부 0 / 셸 글루(routeLoad·publicRuntime)만 $app 정당 보유.

검증: `$app/environment|$app/paths|__DARTLAB_LOCAL_TERMINAL__|localTerminalAdapter|*Shim|landingDataShims` grep — 포터블 트리 0(주석·routeLoad 셸글루 제외) ✓ / ui/web 전역 locator·shim grep 0 ✓ / landing check 0 에러·4396파일 ✓ / landing 풀빌드+prerender ✓ / ui/web build ✓  
rollback: 이 commit revert (hosts.ts 신설 + shim 2종 삭제 + 컴포넌트 prop 배선 — 단일 커밋).

### [15] 단계-4b Terminal Surface 이동 — 예약 (이동 원자 윈도우 §2.5, 07 규칙 6)
일시: 2026-06-13  
commit: (예약 — 본 entry 자체는 문서)  
사전 설계: 전문 에이전트 2인 토론(아키텍트 surface 경계 설계 + 적대 이동안전 검토) 수행. 핵심 합의·결정:
- **landing 결합 정확히 3종**(터미널 트리 grep 실측): Terminal.svelte(GithubIcon·brand)·GiscusPanel(brand, 단 이미 REPO 상수 보유라 1줄 제거)·routeLoad(getPublicRuntime+$app, 이동 불가).
- **brand 처분 = `links` 데이터 prop**(셸이 자기 brand subset 주입). Snippet 슬롯(아키텍트 1안)은 ui/web React→Svelte 경계서 null→SNS바 소실=행위변경이라 기각. 양쪽 brand.ts SNS URL 동일 실측 → 무행위변경. GithubIcon=인라인 SVG 흡수(의존0, 패키지 승격·design primitive 불요).
- **폴더 = §8.1 mandate(components/+lib/) vs 원자윈도우**: 4b-1(이동, 내부구조 보존)·4b-2(§8.1 정규화) 분해. NEXT 참조.
- **ui/web 딥임포트 3곳**(에이전트2 발견 — localTerminalData.ts:35 `data/types` 가 2곳 통념의 누락분). 파일경로 alias로 재배선.
- **R6 checkDevIsolation.js = 조용한 파괴자**: `landing/src/lib/terminal` 소멸 시 ENOENT crash 또는 vacuous-pass로 dev 격리 가드(무중단 #10) 무력화 → 경로 갱신 필수.
- **R7 prebuild contract test = 이미 방어됨**(entry #13 후속 e90699a9e가 디렉토리 glob화). 4a-2 재발 위험 사전 차단 확인. repo 전수 grep: tests/.github 에 `lib/terminal` 하드코딩 경로 0(publish.yml:108 prose 주석 1건만, 비차단).
- **R8 svelte-check = CI 부재**: 어느 워크플로도 svelte-check 안 함(운영자 로컬 게이트). landing check include=`../src/**` 라 이동분 미커버 → surfaces 자체 check 스크립트 필수 + 로컬 pre-push 동반.
범위/검증: NEXT 블록 4b-1 ①~⑨ 참조. 무중단 = landing + ui/web 양쪽 동시 green(이동 원자 윈도우라 타 제품 PRD 격리).  
착수 게이트: CI Fast e90699a9e green 확인 후 4b-1 착수.  
rollback: 4b-1 단일 커밋 revert(git mv 이동·패키지 신설·배선 모두 1커밋).

### [16] 단계-4b-1 Terminal Surface 이동+배선 — 완료
일시: 2026-06-13  
commit: (이 변경의 커밋)  
변경 (이동 원자 윈도우, 단일 커밋):
- **결합 제거 3종**: ① GiscusPanel `$lib/brand`→기존 `REPO` 상수(discussions 링크 1줄) ② TerminalSurface
  `$lib/components/GithubIcon`→인라인 SVG(의존0)·`$lib/brand`→`links: TerminalBrandLinks` 데이터 prop → **TerminalSurface $lib import 0** ③ routeLoad → `landing/src/lib/terminal-shell/routeLoad.ts` 분리(getPublicRuntime·$app 의존이라 잔류, 2 라우트 공용 SSOT).
- **이동**: `git mv landing/src/lib/terminal → ui/packages/surfaces/src/terminal`(rename 보존), `Terminal.svelte→TerminalSurface.svelte`. **내부 data/panels/charts/ui/dev 구조 보존**(상대 import 재작성 0 — 무행위변경). dev/ 는 패키지 유지 + 전용 subpath `@dartlab/ui-surfaces/terminal/dev`(본진 ./terminal 과 export 경로 분리 = 격리 보강).
- **패키지 신설 `@dartlab/ui-surfaces`**: package.json(exports `./terminal`+`./terminal/dev`·deps contracts/runtime/klinecharts·svelte-check check)·tsconfig(base 확장, noUncheckedIndexedAccess·verbatimModuleSyntax override=landing 작성계약 동등 강도, 하드닝은 이연)·src/index.ts·terminal/index.ts(공개표면)·terminal/dev/index.ts·ambient.d.ts(css). 루트 워크스페이스 등록.
- **landing 셸**: terminal-shell/terminalShell.ts 신설(hosts lazy 로더+links brand 파생, 2 라우트 DRY). /terminal·/lab/terminal-dev +page.svelte·+page.ts 재배선(@dartlab/ui-surfaces/terminal·/terminal/dev·terminal-shell routeLoad·links 주입).
- **ui/web**: vite alias `@dartlab/ui-surfaces`+tsconfig path 추가·`$lib→landing` alias 제거(소비처 grep 0 선확인)·딥임포트 3곳(LandingTerminalSurface Terminal→TerminalSurface·engine 통합 import·localTerminalData types) 재배선·links=자체 brand subset 주입.
- **R6**: checkDevIsolation.js 경로를 surface 트리(ui/packages/surfaces/src/terminal)+공개 라우트로 갱신, terminal/dev 서브패스·내부 ./dev/ 위반 검출. (`landing/src/lib/terminal` 소멸 ENOENT/vacuous-pass 무력화 방지)

검증 (양쪽 무중단 green): surfaces svelte-check 0에러·173파일 ✓(신규 패키지 자체 check, R8 — landing 작성계약 동등 강도) / landing check 0에러·4396파일 ✓(surface 를 패키지 심볼릭링크로 graph 포함) / runtime tsc strict 0 ✓ / landing 풀빌드+prerender ✓(prebuild dev-isolation guard OK) / ui/web build(tsc -b 포함) ✓ / dev guard standalone OK ✓ / grep `$lib/terminal` 실 import 잔재 0(주석·contracts prose 제외) ✓  
rollback: 이 commit revert (git mv·패키지 신설·배선 단일 커밋).

### [17] 단계-4b-2 §8.1 lib/ 정렬 (data/→lib/) — 완료 (단계-4b 종료)
일시: 2026-06-13  
commit: (이 변경의 커밋)  
내용: 전문 아키텍트 A1 채택 — surface 내부 `data/` → `lib/` git mv(§8.1 "lib/(로직·셀렉터·정규화)" 충족,
depth 보존 저위험). 내부 상대 import 25파일 sed(`'./data/`·`'../data/` → `lib/`, index.ts 포함). **panels/charts/ui
top-level 유지** — components/ 중첩(A2)은 depth 민감 66 import 재작성인데 panels/charts/ui 가 flat components/
보다 명료한 버킷이라 명료성 이득 0·churn 만 — 전문가 권고대로 이연(viewer surface 등장 시 components/ wrapper
교차 surface 가치 재검토). surface tsconfig 의 noUncheckedIndexedAccess·verbatimModuleSyntax override(landing
작성계약 동등 강도) → base 강도 하드닝(245건)도 별개 단위 이연.

검증: surfaces svelte-check 0에러·173파일 ✓ / landing check 0에러·4396파일 ✓ / terminal surface landing vite
client+server 컴파일 ✓(33.75s) / ui/web build 0 ✓ / `'./data/`·`'../data/` import 잔재 grep 0 ✓.  
※ landing 풀 prerender 는 로컬 HF seed(산업맵·피드 데이터) 미보유로 blog WIP·`/feed/industry/*.xml` 404
  (CI 'Seed from HF' 단계가 제공 — 터미널 무관·환경 한계, CI 권위 빌드가 검증. 4b-1 Deploy 64768487a green 으로 이동 자체는 프로덕션 확증).  
rollback: 이 commit revert (단일 git mv + import sed).

### [18] 단계-5 Local SvelteKit App Scaffold — 예약 + sub-unit 분해 선언 (07 규칙 3)
일시: 2026-06-13
commit: (예약 — 본 entry 자체는 문서)
사전 설계: 전문 에이전트 2인 토론(아키텍트 분해·포트계약 + 적대 무중단 파괴자) 수행. 핵심 합의·실측 확정:
- **포트 계약 SSOT = 코드**(`@dartlab/ui-contracts`), 02 문서 이상형 아님. 터미널 surface 가 렌더 중 실제 호출하는 포트
  실측(grep): `finance.bundle`·`price.{initial,older,loaded,govCandles,govRecent}`·`company.productIndex`·
  `viewer.urlForCompany(code,{vs})`(CenterStack·RightStack·ViewerOverlay)·`report.{capitalChanges,auditTrail,
  topExecPay,workforce,shareholderReturn,investments}`·`scan.changes(code,8)`(RightStack:83)·`filing.{regular,nonRegular}`.
  → 이들은 throw 금지(honest-empty/null 또는 실구현). **호출 안 됨 = throw 정당**(배선순서 트립와이어): `scan.{listTableSources,
  getPresets,savePreset}`·`map.*`·`search.*`(LeftRail 검색은 eng.suggest, search 포트 무호출).
- **createLocalRuntime = FRESH 구현**(fetch `/api/*`, apiBase 주입). ui/web `buildBridgeRuntime` 은 React 결합
  (`@/features/dashboard/api/client`)·동결이라 비이식 — 같은 /api 계약을 새로 구현(정규화기 tocToContract/gridToContract/
  initToContract 는 로직만 미러). macro=`createHfMacroPort()` 재사용(회사무관 HF 공용).
- **서버 게이트웨이 실측**: 라우터 13종 등록(`__init__.py:226~238`) — `/api/agent`(AG-UI SSE `POST /api/agent/runs`)·
  `/api/company`·`/api/data`·`/api/macro`·`/api/dartlab`(price-events)·`/api/ai`·`/api/ask`·`/api/dart`·`/api/dl` 등.
  **dev 포트 = 8400**(기본, HF Spaces 7860; `__main__.py:21`), CORSMiddleware 존재 → vite proxy `/api`→127.0.0.1:8400.
- **adapter = adapter-static + `fallback:'index.html'`(SPA)** + 루트 `+layout.ts ssr=false` — `[code]` 동적 라우트는
  prerender 불가(3000+사)라 SPA fallback 필수(적대 R2). landing(adapter-static·fallback 404.html) 툴체인 미러(Vite 8·
  kit ^2.65·vite-plugin-svelte ^7.1.2·svelte 5.56.3 루트 override·svelte-check ^4.6·ts ^6).
- **AiPort 정직 강등**(적대 R5): `capabilities()` 는 provider 상태 probe → 설정 시 `tier:'advanced'`, 미설정 시
  `tier:'deterministic'`+`upgradeHint`(throw 금지). `streamAsk`→`POST /api/agent/runs` SSE→AiStreamEvent.
  `runTool`/`explainEvidence` 는 V1 에서 honest error 결과 반환(throw 아님, surface-safe). 깊은 advanced Ask UX=단계-7.
- **viewer = hosts.viewerStudio:null + ViewerPort URL-embed**(ui/web 기출시 패턴): 로컬앱은 hosts 양 로더 null 주입,
  `viewer.urlForCompany(code)`→`${base}/analysis/${code}/viewer?...&terminalEmbed=1`(iframe). 단계-6(viewer 추출) 선점 안 함.
- **Python `_ui_path.py` 무변경**(적대 R6 교정 — 기본 UI 전환은 단계-**10**, 단계-9 아님). DARTLAB_UI_DIR 이미 임의경로 지원.
  ui/web fallback flag = 아무것도 안 건드림으로 보존.

sub-unit 분해 (각 1커밋, 비순환 — 5-1 placeholder 라우트는 surface 무import·runtime 무호출로 컴파일):
- **5-1 scaffold + workspace**: `ui/apps/local` 생성(package.json `@dartlab/ui-local`·svelte.config adapter-static fallback·
  vite.config sveltekit+proxy·tsconfig(`.svelte-kit` 확장·ui/web 배제 적대 R7)·app.html·app.d.ts·+layout ssr=false·
  7 라우트 placeholder `<h1>` 스텁). 루트 package.json 무편집(workspaces `ui/apps/*`·svelte override 이미 정합).
  게이트: 루트 `npm ci` **2연속 결정성**(적대 R1/R8 OneDrive junction)·svelte 단일버전 증명·ui/apps/local build+check 0·
  landing build green(무영향)·ui/web 단독 build green(무영향).
- **5-2 createLocalRuntime 채움**: runtime/adapters/local/ 에 localApiClient + sources/ (company·price·filing·finance·ai)
  — public sources/ 구조 미러. 포트별 매핑(위 계약대로): 호출 포트 실구현/honest-empty, scan-presets/map/search throw.
  AiPort 정직 강등. 게이트: runtime tsc strict 0(필수 메서드 컴파일 강제)·landing build green(같은 패키지 공유)·ui/web build green.
- **5-3 라우트 배선 + TerminalSurface 마운트 + chat→terminal + viewer overlay**: lib/runtime/localRuntime(getLocalRuntime
  컴포지션 루트)·lib/shell/{terminalShell(hosts null+links),routeLoad(RawData 조립)}·/terminal/[code] 풀스크린 마운트+컨텍스트·
  /chat·/ask 네비(navigation.toTerminal goto·recentCompanies=storage)·/analysis/[code]/viewer 스켈레톤(overlay iframe 대상).
  게이트: ui/apps/local build+dev server·검증 매트릭스(chat→terminal·Ask→recent company·filing viewer overlay)·console 0·
  landing+ui/web 무영향.

미해소 구현세부(블로커 아님, 각 sub-unit 내 해소): finance.bundle 명세표 엔드포인트(company.py 확인 — 없으면 honest null,
  V1 재무카드 열화 수용)·capabilities provider 상태 필드(api/ai.py)·createEngine 최소 RawData 허용(ui/web 브리지가 입증).
무중단 = landing(공유 runtime 패키지 변경분) + ui/web(동결) 양쪽 동시 green.
착수 게이트: 4b-2 (ff9099ba0) Deploy green ✓·CI Fast green ✓(landing 무중단 프로덕션 확정). CI Full in-progress 는 설계 무관.
rollback: 각 sub-unit 단일 커밋 revert (5-1 디렉토리 삭제·5-2 skeleton 복원·5-3 배선 revert).

### [19] 단계-5-1 + 5-2a 완료 — 로컬앱 scaffold + createLocalRuntime 데이터 포트
일시: 2026-06-13
commit: 5-1 = 4fae2d536 / 5-2a = (이 변경의 커밋)
정정(entry #18 분해 세분): 5-2 를 5-2a(터미널 데이터 포트) + 5-2b(AiPort SSE)로 분할 — AiPort 는 chat/ask(5-3)
  소비라 분리, 5-2a 만으로 터미널은 완전 작동(렌더 중 ai 무호출 실측). 또 전문 에이전트 구현스펙으로 확정한 핵심:
  **createLocalRuntime = 얇은 lazy-fetch 포트 객체**(RuntimeSeed 프리로드 기계 아님 — RawData/createEngine seed 는
  5-3 셸 책임). **finance.bundle = null**(로컬 서버 정규화 재무 엔드포인트 부재; ui/web 브리지도 tables={} 라 실질
  null) → 781줄 재무 재조립 비포팅. report.* 전부 null·scan.changes []·map/search/ai/services/navigation/storage throw.
- **5-1**(4fae2d536): ui/apps/local 신설(SPA·adapter-static fallback:index.html·ssr=false·7 라우트 placeholder·
  dev proxy /api→8400·디자인토큰 import·tailwind 불요). 게이트: npm install +1·svelte 5.56.3 단일·lockfile +25줄
  idempotent·local check 0/build green·landing check 0·ui/web build 0.
- **5-2a**(이 커밋): `runtime/src/adapters/local/` 채움 — fetchJson(getJson+notWiredYet)·localTypes(서버응답
  CompanyMeta·PriceEventsPayload·ClientPanel* + LocalCaches)·sources/{company,price,filing,report,scan,viewer}Source·
  createLocalRuntime 조립. 포트 매핑: company.products/relations=/api/company/{code}/meta(productIndex=null 미지원)·
  price.initial/loaded/govCandles=/api/dartlab/price-events OHLC(govRecent=null·older=[])·filing.regular/panelInit=
  /panel/init·panelToc=/panel/toc·panelGrid=/panel?section·nonRegular=price-events events(정규화기 tocToContract/
  gridToContract/initToContract/regularFilingsFromPanel/nonRegularFromEvents 를 ui/web 브리지서 verbatim 포팅,
  단 합성캔들 fallback 제거)·finance.bundle=null·report.* null·scan.changes []·viewer external-url(/analysis/[code]/
  viewer). 회사단위 fetch 1회 공유 캐시(priceEvents·loadedCandles·panelInit·meta, 런타임 인스턴스 범위).
  LocalRuntimeOptions={env,apiBase} 유지(shared/navigation 주입 불요 — 5-2b/5-3). 호출처 없음(셸 배선=5-3)이라
  컴파일만 검증.
검증 (양쪽+신규 무중단): runtime tsc strict 0 ✓(전 포트 계약 정합 컴파일 강제) / landing check 0에러 4404파일 ✓
  (신규 어댑터 8파일 graph 포함·전부 통과) / ui/web build EXIT0 ✓(동결).
rollback: 5-2a 커밋 revert (adapters/local 신규 8파일 삭제 + createLocalRuntime skeleton 복원).

### [20] 단계-5-2b 완료 — AiPort SSE 배선
일시: 2026-06-13
commit: (이 변경의 커밋)
내용: `adapters/local/sources/aiSource.ts` 신설 + createLocalRuntime `get ai()` throw → `localAiPort(apiBase)` 치환.
  서버 진실 실측: `POST /api/agent/runs`(AgentRunRequest{messages:[{role,content}],agentId='dartlab-research',
  workspaceContext,stream})·SSE `_event`(data JSON 에 type+계약 필드명 그대로 = AG-UI allowlist 가 ai.ts 계약 SSOT)·
  `/api/status`(providers{secretConfigured,available}). 구현:
  - capabilities() = /api/status probe → provider available/secretConfigured 있으면 tier:'advanced', 없으면
    tier:'deterministic'+upgradeHint(throw 금지·정직 강등, 02 §4).
  - streamAsk = fetch POST SSE → ReadableStream reader → `\n\n` 블록 분할 → data JSON 파싱 → AiStreamEvent
    (서버 필드명 일치라 통과). 네트워크/HTTP 실패는 RUN_ERROR 이벤트로 정직 표기.
  - ask = streamAsk 수집(TEXT_MESSAGE_CONTENT delta 누적·TOOL_CALL_RESULT refDetails·RUN_ERROR throw).
  - runTool/explainEvidence = honest error/빈 결과(throw 아님, surface-safe). listModes/setMode/getMode = 로컬 상태.
검증 (양쪽+신규 무중단): runtime tsc strict 0 ✓(AiPort 전 메서드 계약 정합) / landing check 0에러 4405파일 ✓
  (신규 aiSource graph 포함) / ui/web build EXIT0 ✓(동결). 호출처 없음(셸 배선=5-3)이라 컴파일 검증.
  push 는 5-2a (eccfcab25) CI Fast 완료 후(concurrency cancel-in-progress 취소가드).
rollback: 이 커밋 revert (aiSource 삭제 + createLocalRuntime AiPort getter throw 복원).

### [21] 단계-5-3 완료 — 라우트 배선 + TerminalSurface 마운트 (가치 도달점 V1) · 단계-5 종료
일시: 2026-06-13
commit: 5-3a = d2a585425 / 5-3b = (이 변경의 커밋)
- **5-3a**(d2a585425): createLocalRuntime 셸-주입 계약 완성 — storageSource(localStorage StoragePort·네임스페이스·
  비브라우저 in-memory 폴백)·services=createServiceRegistry([])·navigation=options.navigation(LocalRuntimeOptions 에
  navigation: NavigationPort 추가, 어댑터 framework-agnostic 유지). 16포트 전부 확정 — map·search 만 단계-8 throw.
- **5-3b**(이 커밋): ui/apps/local 셸 + 마운트.
  · `lib/runtime/localRuntime.ts` — getLocalRuntime() 컴포지션 루트(createLocalRuntime{env,apiBase:'',navigation}).
    NavigationPort 를 $app/navigation goto + $app/paths base 로 구현(toTerminal/toViewer/toCompany/toAsk/href).
  · `lib/shell/terminalShell.ts` — localHosts{viewerStudio:null,financeDialog:null}(→ViewerOverlay 가 viewer 포트
    URL iframe)·localLinks(brand SNS).
  · `lib/shell/routeLoad.ts` — **단일 회사 최소 RawData 조립**(시장 전체 데이터셋은 로컬 /api 미보유 → ui/web 패리티):
    빈 FinanceCompany + price.initial 캔들 기반 PriceRow + /api meta corpName/sector → index 1행, eco/quarters/macro
    null, finance.years=fallback 5년. 실시간 상세(차트·패널·재무)는 runtime 포트 공급. 270줄 buildRaw 포팅 대신 ~50줄
    (타입 정합·마운트·ready 가드 충족).
  · `/terminal/[code]/+page.{ts,svelte}` — TerminalSurface 풀스크린 마운트(eng=createEngine(raw)·runtime·hosts·links·
    initial). `/chat` 종목코드 입력 → navigation.toTerminal(chat→터미널 전환). `/ask` 최근종목(LAST_SYM_KEY 재사용)
    → toTerminal. 깊은 Ask 엔진 대화·근거 코파일럿은 단계-7.
  · surface index 에 PriceRow 타입 export 추가(FinanceCompany/IndexRow 와 동일 카테고리 — 셸 RawData 조립 소비, additive).
검증 (양쪽+신규 무중단): ui/apps/local svelte-check 0에러 414파일 / ui/apps/local build green(adapter-static SPA·터미널
  surface 번들) / landing check 0에러 4406파일(surface PriceRow additive 무영향) / ui/web build EXIT0(동결).
  ※ 라이브 dev 클릭스루(chat→terminal·Ask→recent·filing viewer overlay 실동작)는 `dartlab ai` 로컬 서버(/api·8400)
    구동 필요 — 빌드/체크가 로컬 게이트(landing prerender 와 동일 디스시플린), 실서버 통합은 단계-10 Python 전환서 확증.
rollback: 5-3b 커밋 revert(ui/apps/local 셸·라우트 + surface PriceRow export) / 5-3a 커밋 revert.

### [22] 단계-6 Viewer Surface Extraction — 예약 + 결합 census (이동 원자 윈도우 §2.5, 07 규칙 6)
일시: 2026-06-13
commit: (예약 — 본 entry 자체는 문서. 추출은 신선 컨텍스트 실행 단위)
**규모 실측(census)**: 뷰어 = **15,219 LOC 이동 대상** — 컴포넌트 14개 4,482(`landing/src/lib/components/viewer/`:
  ViewerStudio 1150·AskDrawer 1038·FinanceStatementPane 480·PanelMatrix 280·CellContent 250·나머지 TOC/timeline/
  compare/companySearch/commandPalette/finance/giscus) + 데이터레이어 45파일 10,737(`landing/src/lib/viewer/`: panelLoad·
  panelWide·search·compare/engine·finance/financeQuery(DuckDB)·askSession·webllm·ollama·answerCompose 등). **터미널의 ~22배** —
  단일 턴 불가, 다중 턴 이동 윈도우. 라우트 4파일(`routes/viewer/`)은 landing 잔류(goto 글루).
**결합 census(C1~C12)**:
- EASY: C1 `$app/paths base`→basePath 데이터 prop(ViewerStudio·AskDrawer·CompanySearch) / C2 `$app/navigation goto`→
  onNavigate 콜백(CompanySearch, ViewerStudio 이미 onNavigate 보유=대부분 완료) / C3 `$lib/brand`→links 데이터 prop(터미널 패턴).
- MEDIUM: C4 localStorage 4키(`dartlab:cmpHint`·`dartlab:lastViewer`·`contributeQuestions`·`webllmModel`)→storage 추상화
  (createLocalRuntime 에 이미 StoragePort 있음·landing 셸은 localStorage 래퍼 주입). try/catch 우아한 강등 유지.
- SAFE(무변경): C5 matchMedia·C6 window/document 리스너(Esc·Cmd+K)=브라우저 전용 surface라 그대로.
- ZERO-break(surface 와 함께 이동): C7 hfRange·C8 panelLoad/panelWide/compare/finance 데이터함수·C10 compare/engine·
  C11 finance/DuckDB — 전부 순수 계산, shell 무의존. `$lib/viewer/*` 45파일은 **복사(import 아님)** = surface 자급(터미널 선례).
- **HARD: C9 AskDrawer(1038 LOC) WebGPU+web-llm+Worker+IndexedDB** — surface 잔류(전역 결합 과다). iframe 임베드 시
  열화 계약 필요(sameOrigin=WebGPU 작동, cross-origin=Tier-0 결정론 검색만+"메인창서 모델 다운로드" 안내). 터미널엔 없던 신영역.
- C12 라우트 param/vs 정규화=landing 잔류(goto 글루).
**FilingPort 공개 구현(단계-6 동행)**: 현재 createPublicRuntime panelToc/panelInit/panelGrid = throw 게이트. 공개 구현 =
  **landing buildPanelBundle(브라우저 parquet read=panelLoad+panelWide) 래핑** — `/api` 서버 아님(공개 landing 무서버),
  shared 주입 패턴(reportFacts/changes 처럼 landing 잔류 모듈 주입). 로컬 어댑터는 이미 /api 로 구현됨(filingSource).
**주입 표면(props)**: code·vs·embedded(터미널=헤더숨김·100%높이)·onNavigate·onclose·basePath·brand·storage.
**추출 sub-unit 분해(4b 패턴)**: ①예약(본 entry) ②전문 에이전트 2인 토론(아키텍트 surface 경계 + 적대 이동안전 R1~Rn —
  AskDrawer iframe 계약·DuckDB wasm 싱글턴·compare 분기 lockstep·checkDevIsolation 감사) ③6-1 git mv 59파일+EASY 결합 C1~C4
  +§8.1(무행위변경) ④6-2 FilingPort 공개 구현(buildPanelBundle 래핑) ⑤6-3 터미널 hosts viewerStudio 로더 재배선(현 lazy import
  경로 갱신)+ui/apps/local viewer 라우트 ViewerSurface 마운트(현 스켈레톤). 무중단=landing 표준 뷰어+터미널 오버레이+ui/web iframe.
**top 위험**: ① AskDrawer WebGPU/Worker iframe 시나리오(선례 없음) ② DuckDB.wasm 싱글턴 공유 vs 인스턴스별 로드 ③ compare/engine
  landing↔surface 분기 방지(복사 후 lockstep). **미해소 open Q**: SceMatrix 사용처·ui/web React 뷰어 병렬 구현 통합 여부·
  Ollama origin CORS·checkDevIsolation 최상위 가드 유무 — 추출 착수 토론서 확정.
착수 게이트: 단계-5 전체 원격 green(c680c96e3 CI Fast) 확인 후 추출 토론·예약 갱신. 신선 컨텍스트 권장(15k LOC 이동).
rollback: 해당 없음(예약 문서). 추출은 6-0a/6-1 각 단일 커밋 revert.

**[22-b] 단계-6 추출 실행계획 확정 — 전문 에이전트 2인 토론(아키텍트 실행계획 + 적대 이동안전)**
census 의 "데이터레이어 순수" 주장이 **적대 검토로 부분 반증** — 숨은 landing-셸 결합 발견. 확정 설계:
- **★duckdb 결합(census 누락·둘 다 발견)**: `lib/viewer/finance/financeQuery.ts` → `$lib/data/duckdb`(loadDartDb·sqlEscape). duckdb.ts 는
  `$app/environment`+`@vite-ignore`(SvelteKit/Vite 전용)라 vanilla-svelte surface 비이식. **해법=`provideDuckDb` 주입 seam**
  (financeQuery 는 surface 이동, 엔진 loader 는 landing 이 `provideDuckDb(loadDartDb)` 주입·미주입=null→정직 fallback). sqlEscape
  는 1줄 순수 유틸 인라인. 적대의 "financeQuery 2분할+wrapper"보다 깔끔(아키텍트 채택).
- **★lab/viewer-* 3 라우트 = 무거운 importer(census 누락)**: `routes/lab/{viewer-dev,viewer-search,viewer-analyze}` 가 viewer
  컴포넌트 8종+`$lib/viewer/*` 12종 직수입(landing svelte-check 게이트 포함) → 원자 커밋서 전부 `@dartlab/ui-surfaces/viewer`
  named export 로 재배선 필수. 이 때문에 viewer index 공개 API 가 ~30 심볼(컴포넌트+데이터함수)로 커짐 — 수용(게이트 대상).
- **R1(CRITICAL) terminalShell lazy import**: `$lib/components/viewer/{ViewerStudio,FinanceDialog}.svelte` → `import('@dartlab/
  ui-surfaces/viewer').then(m=>({default:m.ViewerSurface}))`(+FinanceDialog named export). 미재배선 시 ViewerOverlay 조용한 파괴.
- **R3 webllm Worker**: `new Worker(new URL('./webllmWorker.ts',import.meta.url))` → webllm.ts+webllmWorker.ts 원자 동반 이동(상대경로 보존).
- **R6 prerender**: `routes/viewer/company/[stockCode]/+page.svelte`(★param=[stockCode] not [code]) import 재배선 — 누락 시 GH Pages 404.
- **basePath=PROP**(터미널처럼 runtime.env.basePath 불가 — 공개 viewer 라우트엔 runtime 컨텍스트 조상 없음). links=prop(repo만). Header=
  snippet prop(비embedded·fullscreen 숨김 보존). localStorage 4키=typeof-guard 유지(추상화 안 함, 위험 0 이득).
- **FilingPort 공개**: `PublicRuntimeSharedPorts` 에 panelToc/panelInit/panelGrid 추가 → publicFilingPort 가 throw→shared 소비.
  landing glue 가 buildPanelBundle(panelLoad+panelWide)→계약shape `bundleToContract`(~40줄 순수 필드복사, local filingSource 정규화기와
  별개 재구현 — PanelBundle≠Client* shape) 매핑 주입. runtime↔surfaces 직결 회피(landing 이 매퍼 소유).
- **surfaces deps 추가**: @mlc-ai/web-llm·dompurify·lucide-svelte(+@types/dompurify). hyparquet 은 runtime 경유라 불추가.
- **buildIntentModel.py:35** BUNDLE_PATH → `ui/packages/surfaces/src/viewer/lib/intentModel.json` 재배선. **dev/ 는 landing 잔류**(viewer-dev 전용·격리가드 회피, 저위험).
- **★원자성**: 이동+전 재배선은 ONE 커밋(green 중간상태 불가). 단 **6-0a**(FilingPort shared 배선·무이동·panelLoad 는 landing 잔류서
  주입·독립 green) 선행 → **6-1**(git mv 59파일+import sed+결합수술 3파일+lab3+terminalShell+viewer라우트+FilingPort import flip+
  buildIntentModel 경로, 단일 원자). 게이트 순서(싼것부터): runtime tsc → surfaces check → landing check(이동안전 oracle) → local build → ui/web build → checkDevIsolation.
- 미해소(6-1 착수 직전 재grep 확정): CompanyQuickSearch 가 $lib/viewer 수입 여부·기타 신규 importer.
착수: 신선 컨텍스트에서 6-0a 부터(아키텍트 plan + 적대 R1~R10 = 실행 SSOT, 재조사 불필요).
