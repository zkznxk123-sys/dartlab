# 07. Progress Ledger — 진행 원장

상태: 가변 문서 — 이 문서 세트에서 유일하게 진행 중 갱신된다.  
규칙: append-only — 과거 entry는 수정하지 않는다. 정정은 새 entry로 한다.

---

## NEXT

> 끊긴 세션이 가장 먼저 읽는 단일 포인터. 항상 최신 상태로 유지한다.

```text
다음 작업: 단계-1a 본체 (npm 워크스페이스) — 1세션 1단위로 집행. 운영자 go 기득(2026-06-13 "멈추지말고 끝까지", 리밋으로 분할만).
선행 조건: ② PyPI freeze ✅ v0.10.7 / ③ 스트레이 ✅ 삭제 집행 완료(ui/node_modules·ui/build, entry #6) / ① site-signals 비충돌 = 운영자 go로 해제
1a 본체 순서 (사전 조사 완료분 포함):
  ① 루트 package.json 신설 — private, workspaces=["landing","ui/packages/*","ui/apps/*"], overrides.svelte="5.56.3"
  ② landing/package.json svelte "^5.56.3"→"5.56.3" 정확 고정 (이름="dartlab-landing", prepare="svelte-kit sync" 있음 — 워크스페이스 install 시 sync 자동)
  ③ landing/package-lock.json 삭제 → 루트 npm install(lockfile 생성) → npm ci 2회(재현성·junction 확인)
  ④ landing/vite.config.ts d3 alias 핵 4줄 제거(호이스팅이 해소)
  ⑤ 워크플로 3종 동시 개정 ⚠: deploy-landing.yml(루트 npm ci + npm run build -w landing + 캐시 경로) ·
     **publish.yml(`cd landing && npm ci`가 lockfile 부재로 즉사 — 루트 npm ci로 교체 필수)** · dependabot.yml(/landing→/)
     + ci-fast/ci-full 등 다른 워크플로의 landing npm ci 사용처 grep 후 동일 교체
  ⑥ 검증: npm ls svelte 단일·landing build(-w)·landing check·ui/web 단독 npm ci+vite build·OneDrive 동기화 제외 확인
재개 지점: entry #6 — 이 NEXT만 보고 ①부터 실행
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
