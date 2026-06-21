# 06. Scope · Phasing · Guardrails

상태: 실행 계획 PRD v0.1
범위: phase 분해, 각 phase 게이트·롤백, 테스트 매트릭스, 가드, 개발자+PM 이중 평가. 착수는 본 문서 게이트가 우선(README).

---

## 1. Phase 분해 (의존 순서)

### Phase 0a — census 선결 (코드 0, 문서만) — R1 BLOCKER 해소
구현 전 *실측 census* 를 박는다(R1 이 적발한 "존재 안 하는 파일 인용"·"breaking 을 계승으로 위장" 재발 방지):
1. **계약 census**: `AiAskInput` 비파괴 마이그레이션 경로(viewer streamAsk 호출부 전수) + `AiPort` 10 메서드(기존 8 + compose 2)의 public/local/test 구현 또는 unavailable 정책 표(01 §0·§8).
2. **심볼 census**: 03 §1 이관 대상 실파일·실 시그니처·의존 그래프(`answerCompose.ts`·`diff.ts`·`viewerAnalyst.ts`·`webllm.ts`·`searchIndex.ts`) 확정. `viewerAnalyst.ts` 역할 분류.
3. **search 모호성 census**: viewer `searchIndex(parseConstraint/SearchHit)` vs runtime `SearchPort` 동일 SSOT 여부(03 §7).
4. **build.ts findings 매핑**: report `findings.push({key,finding,sourceEngine})` ↔ `GroundingFact` 매핑(03 §7) — 중복 빌더 0 확인.
- 게이트: census 문서가 ≥90 재평가에 첨부. 구현 0.

### Phase 0b — 계약 + Grounding 추출 (코드 기반, UI 0)
- `contracts/ai.ts`: 01 §0 diff 표대로(전부 비파괴 옵셔널 추가 + compose 2메서드 + `GenChunk`·브랜디드 `ComposeTemplateId`). `getter ai()`→eager(프로브 lazy).
- `runtime/src/ai/analysis/`: 심볼 census 대로 *의존 동반 이관*(intent·signals·ratios·**formats**·evidence·grounding·verifyGrounded). 로직 불변.
- `runtime/src/ai/generate.ts`(GenChunk 사다리) + `backends/deterministic.ts`.
- 게이트: vitest — `buildGroundingPack` 결정론 출력·`verifyGrounded` **false-positive 율 측정(임계 통과)**·viewer Tier0 답 스냅샷 동일·`AiPort` 10 메서드 conformance. **UI 변경 0 → 자동 push 가능**.

### Phase 1 — onDevice 백엔드 + viewer 포트 전환
- `backends/onDevice.ts`: viewer webllm.ts 끌어올림(web-llm·webgpuUsable·worker). 로직 불변.
- viewer: 직접 import → `runtime.ai` 포트 경유.
- 게이트: viewer ask 회귀 0(스냅샷+수동 눈검수) + **멀티턴 턴 누적 동작 스냅샷**(history v0 배선, 01 §7). **UI(viewer) → 운영자 push 승인.**

### Phase 2 — edge 워커 + 백엔드 + 관측
- `infra/workers/aiEdge/`: 워커·`[ai]` 바인딩·`budgetDO`(Durable Object)·라우트·CF Rate Limiting·Turnstile.
- `backends/edge.ts`: `EdgeBackend`(health·budget 버킷·generate·강등).
- `registry.ts`: `aiEdge` origin. `deploy-ai-edge.yml`(별도) 조건부 deploy + `VITE_DARTLAB_AI_PROXY`(deploy-landing env).
- `/ai/_metrics` + `monitorEdgeAi.yml` cron(같은 Issue 싱크) — 관측(02 §9). **siteSignals(D1) 경로를 쓸 거면 D1 프로비저닝(`database_id`)이 Phase 2 선결**; v0 1차는 `/ai/_metrics` 직노출.
- 게이트: 워커 단위 테스트(mock AI binding)·DO 원자 budget·reserve/settle·CF 429 차단·origin/rate-limit/Turnstile·강등·로깅 0. 토큰 없는 환경 폴백 무에러. **배포전 체크리스트(spend cap·BUDGET_HARD·Turnstile 키) 확인. 워커 배포 = 운영자(CF 자격) 트리거.**

### Phase 3 — terminal ask + compose 코어
- terminal: ask 입력 UI → `streamAsk`. compose 동사 + 템플릿 카탈로그.
- 게이트: terminal 기존 패널 회귀 0·ask grounded. **UI → 운영자 push 승인.**

### Phase 4 — baked compose (carousel·report lead·blog)
- CI compose 배치 → grounded 통과분 HF/static. carousel·report lead·blog 초안 소비.
- 게이트: baked 산출물 grounded 100%(미통과는 결정론 폴백). 콘텐츠 검수.

각 phase 는 독립 가치(0=정리, 1=viewer 품질↑, 2=edge 가용, 3=terminal 신기능, 4=배치 카피). 중단해도 앞 phase 는 산다.

---

## 2. 가드레일 (기계 강제)

| 가드 | 무엇 | 어디 |
|---|---|---|
| surface 직접 AI 호출 금지 | surface 가 webllm/edge/fetch 직접 호출 차단 | `tests/audit` TS 가드 확장(작업대 가드 패턴) |
| 숫자 환각 | `verifyGrounded` 결정론 테스트 | `runtime/src/ai/analysis/*.test.ts` |
| agent boundary | edge/onDevice 에 5패스·고정노드 금지 | `checkAgentBoundary.py` 범위 확인 |
| untrusted-wrap | 외부 본문 마커 | [[untrusted-wrap-check]] |
| viewer 회귀 | Tier0 답 스냅샷 | vitest snapshot |
| no-scripts-dir | 워커 setup 은 `infra/workers/aiEdge/` (repo `scripts/` 금지) | `noScriptsDir.py` |
| 포트 conformance | public/local/test AiPort 10 메서드(기존 8+compose 2) 구현/unavailable | 02-runtime-ai-services §3.6 conformance |
| surface 티어 분기 금지 | surface 가 `capabilities().tier`/`tierUsed` 로 분기 차단(표시만) | TS 가드(surface 직접 AI 호출 가드 확장, K7) |
| 배포전 체크리스트 파일 | `aiEdge/README.md` 에 spend cap·Turnstile 키·`BUDGET_HARD` 초기값 체크리스트 존재 | 문서 가드(파일 존재 검사) |

---

## 3. 테스트 매트릭스

| 영역 | 도구 | 핵심 |
|---|---|---|
| Grounding 결정론 | vitest | facts·intent·asOf 안정, 합성키·분모정의 |
| **환각 가드 정밀도** | vitest | `verifyGrounded` **false-positive 율 ≤ 임계**(정상답 코퍼스), renderedForms·derivedForms 매칭, 반올림 미탐 0 |
| 티어 강등 | vitest(mock backends) | edge fail→onDevice→det 순서·tierUsed 정직·**전체 타임아웃 예산** 준수·스트림중 무전환 |
| **강등 답 품질 floor** | snapshot | determinismAnswer 가 *읽을 만한* 한국어(00 §5) |
| 워커 budget 동시성 | wrangler test | **Durable Object 원자 increment**·reserve/settle·CF 429 ground-truth 차단(02 §6) |
| 워커 남용 | wrangler test | origin·Rate Limiting·Turnstile·spend cap·`BUDGET_HARD=0` 즉시차단 |
| 워커 SSE | wrangler test | 시작 reserve→종료 settle·중간소진 over-run 0·로깅 0(프롬프트 echo 금지) |
| **관측성** | 통합 | 강등율·stray율·5xx 집계→monitorPipeline 게이트 발화(02 §9) |
| 폴백 무에러 | 통합 | env 없음→onDevice→det, 에러 0 |
| viewer 회귀 | snapshot + 눈검수 | 바이트 동일, `AiPort` 10 메서드 conformance |
| compose grounded | vitest | baked 산출물 100% grounded + asOf 무효화(04 §3.1) |
| ci-fast 동일 | `tests/run.py preflight` | 푸시 전 ([[ci-fast-local]]) |

---

## 4. 롤백

- Phase 0~1(코드/viewer): 포트 경계 뒤 변경 → revert 1 commit. viewer 회귀 시 직접 import 복원.
- Phase 2(워커): `VITE_DARTLAB_AI_PROXY` 제거 = edge 즉시 비활성(런타임 자동 onDevice). 워커 자체는 켜둬도 무해(아무도 안 부름). 과금 사고 시 budget 0 또는 워커 삭제.
- Phase 3~4(UI/baked): UI revert, baked 산출물 삭제 → 결정론으로 복귀. 결정론이 항상 바닥이라 어느 단계 롤백도 "AI 없던 상태" 로 안전 착지.

**핵심 안전판**: 결정론 티어가 항상 살아있어 어떤 롤백도 기능 0 이 아니라 "AI 이전" 으로 내려갈 뿐.

---

## 5. 이중 평가 (착수 전)

### 5.1 전문 개발자 관점
- 계약 변경(`compose`·`edge`)이 기존 `AiPort` 소비자(viewer)를 안 깨나? → Phase 0 스냅샷 게이트.
- `TierBackend` 추상이 실 API 추가를 정말 1파일로 만드나? → `RealApiBackend` 더미로 검증.
- 워커 budget 카운터가 동시성에 안전한가? → KV 원자성 한계 인지, soft 임계로 보수적.
- runtime 에 ai/ 추가가 L 계층 import 방향 안 깨나? → runtime 은 surface 아래, 포트 소비 정상.

### 5.2 PM 관점
- 사용자 가치 순서가 맞나? viewer 품질↑(P1) → terminal 신기능(P3) → 배치 카피(P4). edge(P2)는 인프라.
- "퍼블릭 무료" 가 과장 아닌가? budget·강등·정직 고지로 방어(K4).
- UI push 승인 병목? Phase 0/2 는 비-UI 라 선행 가능, UI 는 묶어서 승인 요청.
- 커넥터와 혼동되지 않나? 00 §7·K6 경계 명시.

---

## 6. 착수 게이트

```text
GO 조건: 운영자 go + (UI phase 는) push 승인 체계 확인.
선행(비-UI): Phase 0(계약+Grounding 추출)은 자동 push 가능 — 운영자 go 시 즉시.
워커(Phase 2): CF 자격(CLOUDFLARE_API_TOKEN) 운영자 주입 트리거.
NO-GO: viewer 회귀 게이트 미통과 시 Phase 1 진행 금지.
```

본 PRD 는 *설계 완료* 상태. 구현 착수는 운영자 go + 07 전문가 평가 ≥90 수렴 후.
