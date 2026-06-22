# 02 — 로컬↔퍼블릭 공통배선 + 기능차 안내

> 사용자 요구: "공통배선으로 로컬과 퍼블릭의 기능차이도 같이 설명되면 좋겠다." 이 문서가 그 SSOT를 확정한다.

## 0. 코드 실측 지형 (출발점)

- `runtime.ts` — `RuntimeEnvironment`는 `kind`(`'public'|'local'|'test'`)·`readonly`·`buildVersion`만. **capability 목록이 아니라 환경 한 줄.**
- `services.ts` — `ServiceAvailability='available'|'localOnly'|'disabled'|...` + `upgradeHint?`("로컬에서 사용 가능")가 *타입으로 이미 정의*. 그러나:
  - `serviceRegistry.listServices`는 **등록된 registration만** 나열.
  - 유일한 실제 등록(export)은 `availability:'available'`. **오늘 `localOnly`를 emit하는 descriptor는 0개**(`localOnly` 분기는 미사용 데드 경로, 미래 예약).
  - `createPublicRuntime.ts` — 퍼블릭은 `services` getter 자체가 `notWiredYet()` **throw**. 빈 목록이 아니라 *접근 시 throw*.
  - `createLocalRuntime.ts` — 로컬만 `createServiceRegistry([export])` 배선.

→ **결정적 사실**: services descriptor는 "기능차 SSOT"가 될 수 없다. 퍼블릭에서 호출 자체가 throw이고, 로컬에서조차 export 1건만 등록돼 AI·저장·네비 같은 차이를 *표현하는 descriptor가 존재하지 않는다*.

기존 기능차 표시 선례 2개(재발명 금지 근거):
- `TerminalSurface.svelte` — `allowTerminalAsk = runtime.env.kind === 'local'` → `{#if allowTerminalAsk}` AI 버튼 조건부. **이미 env.kind로 기능 게이팅 중.**
- `ViewerOverlay.svelte` / `hosts.ts` — `tier={rt.env.kind === 'local' ? 'local' : 'public'}` export tier 라벨. **이미 env.kind로 tier 라벨 주입 중.**

## 1. SSOT 판정 = `runtime.env.kind` (+ `env.readonly` 보조)

**services descriptor 아님.** 근거:
1. **services는 퍼블릭에서 throw**. 투어가 `runtime.services.listServices()`를 호출하면 퍼블릭에서 *즉시 막다른 throw* — 적대검증 §3의 첫 실패 모드를 투어가 직접 유발.
2. **descriptor가 차이를 안 담는다**. `localOnly` emit 0, 핵심 차이(AI/저장/네비)는 *포트 미배선*(throw)이지 descriptor가 아니다. services는 "command palette에 뭘 그릴까"용이지 "퍼블릭 vs 로컬 capability 매트릭스"가 아니다.
3. **선례가 이미 env.kind.** 다른 SSOT를 쓰면 동일 사실에 두 진실원천 — feedback_always_check_clutter 위반.

### 2층 모델

- **런타임 분기 SSOT = `runtime.env.kind`** (`'local'`=풍부 / 그 외=floor). "이 스텝이 현재 런타임에서 *동작하는가*"의 단일 판정.
- **카드 자체의 가용성 메타 = 콘텐츠 데이터 1필드**(신규 데이터, 신규 포트 아님):

```ts
interface TourStep {
  // ...
  requires?: { kind: 'always' | 'localOnly' | 'service'; serviceId?: string };
  publicNote?: string;   // localOnly일 때만 의미. 퍼블릭에서 어떻게 보일지 명시
}
```

엔진은 `requires.kind==='localOnly' && env.kind!=='local'` → `showLocalOnly`(안내 모드), 그 외 → `show`. **env.kind를 카드마다 if 난발하는 게 아니라** `requires` 데이터 1필드 × `env.kind` *한 번* = 선언적 매핑([01](01-shared-tour-engine-architecture.md) §3 `evalStep`).

### 미배선 services 포트, 지금 살릴지? → 아니오

- 살리려면 `createPublicRuntime`의 throw를 빈 레지스트리로 바꿔야 하는데, 이건 ui-platform-refactor 단계-5의 소유지 튜토리얼 PRD가 손댈 곳이 아니다("신 포트 남발 금지").
- 살려봤자 빈 목록이라 "AI는 로컬 전용"을 *말해주지 않는다*.
- env.kind 2층 모델이 services 배선 0으로도 완전히 동작 — "퍼블릭 floor에서 throw 없이 동작" 원칙과 정확히 일치.

## 2. 기능차 안내 가드 — 카피·톤

퍼블릭=floor(모든 기능 동작해야)·로컬=headroom(같은 코드 bonus). "local-only 기능 금지"는 *새 기능을 로컬에만 만들지 말라*는 **설계 규율**이지, *이미 존재하는 구조적 한계*(AI 질의=로컬 LLM·서버 SSE)를 숨기라는 게 아니다. 투어는 이 구분을 있는 그대로 말해야 한다.

### upgradeHint/publicNote 카피 3원칙

1. **없는 걸 있는 척 금지** — 퍼블릭에서 AI 버튼은 `{#if allowTerminalAsk}`로 *안 보인다*. 투어가 퍼블릭에서 "AI에게 질문하세요" 카드를 *동작하는 양* 띄우면 클릭 시 막다른 길 = 거짓. → "이 기능은 로컬 버전에서" 명시 + 비활성 스타일.
2. **퍼블릭을 열등하게 프레이밍 금지** — "퍼블릭은 제한됨/열화판" ❌. *역할 분리*로: "지금 보는 공개 터미널은 설치 없이 즉시 전체 분석·차트·공시를 봅니다. 로컬 버전을 설치하면 *추가로* AI 직접 질의·작업 저장이 켜집니다." **퍼블릭=완결된 floor, 로컬=추가 headroom.**
3. **막다른 길 금지(CTA 명시)** — localOnly 카드의 `publicNote`는 *행동 가능한 안내*: "로컬 설치 안내 →"(실재 링크 `eddmpython.github.io/dartlab`, feedback_no_fabricated_urls 준수). 안내만 하고 갈 곳 없으면 좌절.

### 카피 예시 (kr)

| 기능 | 퍼블릭 (env.kind==='public') | 로컬 (env.kind==='local') |
|---|---|---|
| AI 직접 질의 | "AI에게 회사를 직접 질문 — **로컬 버전에서 켜집니다**. (공개 터미널은 검색·차트·공시·종합판정을 설치 없이 제공)" + [설치 안내] | "헤더 AI 버튼 → 로컬 LLM에 직접 질문" (정상 투어) |
| 작업 저장/복원 | "차트 설정·종목은 **이 브라우저에 저장**됩니다(기기 종속). 로컬 버전은 작업 공간을 더 풍부하게 보관" | "작업 저장 — 다음 방문에 복원" |
| 데이터 신선도 | (양쪽 동일 — HF 공유, **차이 언급 안 함**) | (동일) |

**핵심**: price/finance/macro/company는 `publicPricePort` 재사용으로 **양쪽 동일**(로컬 어댑터 주석 "퍼블릭과 동일"). 여기 가짜 차이를 만들면 기능차 표시 원칙 위반. 차이는 *오직* AI·storage·navigation·services(=퍼블릭 throw 포트들)에만.

## 3. "공통배선"의 의미 — (a)와 (b) 둘 다

사용자의 "공통배선으로 기능차이도 같이 설명"은 **두 층 모두**다:

**(a) 하나의 투어 엔진이 양쪽에서 동작** — surface 컴포넌트가 단일 공유이고 `runtime` prop만 다르게 주입. 투어도 *같은 엔진·같은 콘텐츠 데이터*로, public route와 local app 양쪽에 한 번 마운트하면 둘 다 뜬다. 콘텐츠 2벌 쓰면 분열 → KILL.

**(b) 기능차 주석이 런타임에서 자동 갈림** — 같은 `TourStep[]`가 `runtime.env.kind`를 보고 스텝마다 다르게 렌더:
- `requires` 없음/`always` → 양쪽 **동일 렌더**(투어 진행).
- `requires.kind:'localOnly'`:
  - 로컬 → **정상 투어 스텝**.
  - 퍼블릭 → **스킵 아님·회색만 아님 — *안내 카드*로 변환**. `publicNote` 카피 + [설치 안내] CTA. *보이되 + 이유 + CTA*.

**스킵 vs 회색 vs 안내 판정 = 안내(변환)가 정답.** 스킵하면 퍼블릭 사용자가 "로컬엔 뭐가 더 있는지" 모름("숨김 금지" 위반). 회색만 하면 막다른 길(좌절). → services.ts가 의도한 "존재는 보이되 실행 불가 + upgradeHint" UX를 **services 포트 없이 콘텐츠 층에서** 실현.

## 4. 미래 수렴 (지금 의존 금지)

ui-platform-refactor 단계-5에서 services가 퍼블릭에 빈 레지스트리로 배선되고 누군가 `availability:'localOnly'`+`upgradeHint`를 emit하기 시작하면, 투어의 `publicNote`는 그 `upgradeHint`를 *소비/공유*하도록 진화할 수 있다(동일 카피 SSOT). `requires.kind:'service'`가 그 훅이다. **단 지금 의존하지 않는다** — env.kind floor로 완결. 이게 "혁신적 유지보수"의 미래 호환선이다(지금 안 막고, 나중에 자동 흡수).

## 5. 적대검증 — capability 안내가 틀리는 5 + 방어

1. **런타임 오판** — env.kind 대신 *추론*(navigation 포트 try / apiBase 존재)으로 로컬 감지 → `test` kind·미래 변종 오판. → 방어: `env.kind`를 *유일* 판정원천. `'local'`만 풍부, 그 외(public/test) floor. 포트 존재 추론 금지.
2. **미배선 포트 접근해 throw** — 퍼블릭에서 `runtime.services`/`ai`/`navigation`은 getter라 *읽기만 해도 throw*. → 방어: `localOnly` 스텝의 퍼블릭 렌더는 **포트를 절대 touch 안 함** — 정적 `publicNote`만. 로컬에서만 실제 포트 호출(AI 버튼이 `{#if allowTerminalAsk}` 안에서만 호출하는 기존 가드와 동일).
3. **로컬기능 광고만 하고 막다른 길** — "AI 질의 가능!" 띄우고 클릭하면 throw. → 방어: localOnly 카드는 **클릭 불가 + [설치 안내] 실재 링크**.
4. **데이터 차이 날조** — "퍼블릭은 데이터 오래됨/제한"이라 *틀리게* 안내. 실제론 양쪽 HF 공유로 동일. → 방어: 차이 안내를 **AI/storage/navigation/services 4개로 한정**. 데이터 포트는 "동일" 또는 무언급. 신선도는 `RuntimeDataEnvelope.stale`이 따로 표현 — 혼동 금지.
5. **readonly 의미 혼동** — 퍼블릭 `readonly:true`를 "아무것도 저장 못함"으로 과장. 실제론 localStorage 차트/종목 저장은 *퍼블릭에서도 동작*. → 방어: `readonly`는 *백엔드 쓰기* 부재지 *브라우저 저장 부재가 아니다*. 카피는 "이 브라우저에 저장(기기 종속)".

## 6. KILL 목록 (이 렌즈)

1. **❌ `env.kind` 하드코딩 if 난발** — `TourStep.requires` 1필드 × env.kind 한 번 매핑.
2. **❌ 미배선 포트 try/catch로 capability 감지** — getter throw를 probe로 악용. silent fallback 금지 위반.
3. **❌ 튜토리얼 위해 퍼블릭 services 포트 조기 배선** — ui-platform-refactor 단계-5 소유.
4. **❌ `localOnly` descriptor를 지금 만들어 SSOT로** — 0개가 현실. 콘텐츠 `requires`가 SSOT, services는 미래 수렴만.
5. **❌ 데이터 신선도/품질을 로컬↔퍼블릭 차이로 안내** — 양쪽 HF 공유라 거짓. 차이는 4개뿐.
6. **❌ 로컬 우월·퍼블릭 열등 프레이밍** — floor=완결·headroom=추가, 역할 분리만.
7. **❌ 별도 투어 데이터 2벌(public/local)** — 단일 `TourStep[]` × env.kind 분기.

## 핵심 주장 3줄

1. 기능차의 진실원천은 `env.kind` 한 줄 — services descriptor는 퍼블릭에서 throw이고 차이를 안 담아 SSOT가 못 된다. 단일 `TourStep[]`를 env.kind로 한 번 갈라 양쪽에 옳게 렌더.
2. 기능차 표시 원칙은 "퍼블릭=완결된 floor, 로컬=추가 headroom" 역할분리 — 퍼블릭 열등 프레이밍 금지, 차이는 AI·storage·navigation·services 4개에만(데이터는 양쪽 동일), localOnly 카드는 비활성+이유+설치 CTA로 막다른 길 차단.
3. 퍼블릭 미배선 포트는 접근만 해도 throw이므로 localOnly 스텝의 퍼블릭 렌더는 포트를 절대 touch 않고 정적 `publicNote`만 — try/catch 감지·env.kind 난발·조기 포트 배선 전부 KILL.
