# 04. Surface 배선 — ask/compose 를 어디에 어떻게 꽂나

상태: 구현 계약 PRD v0.1
범위: viewer·terminal·report·carousel(신규)·blog·landing 각 surface 가 `runtime.ai.ask`/`compose` 를 어떻게 소비하는가. baked vs live 결정, compose 템플릿 계약, 회귀 가드.

---

## 1. viewer — 이미 있는 것을 포트로 정리

viewer 는 이미 ask(Tier0+WebGPU)를 가진 유일 surface다. 본 PRD 에서 viewer 는 **새 기능이 아니라 정리 대상**:

- `answerCompose`·`diff`·`webllm`·`ollama` 직접 import → `runtime.ai` 포트 경유(03 §1 실파일 census·§7). (R2 정정: `evidenceSkill` 은 실존 안 함 — 인용 제거.)
- viewer 의 evidence selection·멀티턴 `history` → `AiAskInput.evidence`·`history` 표준으로 흡수(01 §7, v0 배선).
- **회귀 절대 금지**: 이관 후 viewer ask 동작·답·UX 가 바이트 동일(02 §4). viewer 가 첫 적용이자 회귀 게이트.

산출: viewer 가 edge 티어를 *자동으로* 얻는다(지금 WebGPU 만 → edge 우선+WebGPU 폴백). 사용자 코드 변경 없이 **티어 선택지 확대**(R1 정정: 8B edge 가 1.5B onDevice 보다 *항상* 낫다는 보장은 한국어 기준 미검증, 02 §2 — "품질 상승" 단정 대신 "선택지 확대").

---

## 2. terminal — selection-grounded ask = **단일 킬러** (R1 혁신성 격상)

> 4 surface 중 *유일한 새 경험* 이자 제품의 AI 다움이 *보이는* 자리. 나머지(report·carousel·blog)는 같은 포트의 *부산물* 이다. 여기에 무게중심.

운영자 directive 의 핵심. 터미널에 ask 입력 한 줄 — 단 차별은 입력창이 아니라 **근거가 자동**이라는 데 있다.

```text
터미널 상단/사이드: [무엇이든 물어보세요] 입력
  -> runtime.ai.streamAsk({
       prompt, mode:'terminal', scope:'terminal',
       context:{ code: 현재종목, period: 현재기간, selection: 선택셀/차트커서 }
     })
  -> Grounding = 현재 회사 finance bundle + macro 렌즈 + 선택 셀
  -> edge/onDevice 가 근거 서술, tierUsed 배지 표시
```

- **킬러 가치 = selection-as-evidence("복붙 없는 근거").** 사용자가 보던 셀·차트 커서·선택 섹션이 `evidence`(EvidenceSelection)로 그대로 grounding 이 된다. BYO-key 챗봇은 이 컨텍스트가 없어 복붙을 요구한다. 퍼블릭에서 *키0·로그인0* 으로 "이 화면 그대로, 즉답" 이 경쟁사가 못 하는 한 수(00 §4.3).
- 퍼블릭 ask 의 가치는 *실행이 아니라 해석* 으로 완결된다 — "왜 마진 빠졌나", "동종 대비 어디 서나" 는 read-only 로 충분히 가치. (실행 명령은 advanced 영역, 아래.)
- 터미널은 지금 AI 호출 0(전량 결정론 포트). 본 배선이 첫 AI 진입 — 단 **결정론 계기판은 불변**, ask 는 *그 위에 얹는* 질의 레인.
- terminal mode 의 tool-calling(서비스 커맨드 실행)은 `advanced`(로컬) 전용(01 §2·§5 사다리 밖). 퍼블릭 터미널 ask 는 *분석 서술* 까지(커맨드 실행 X). 이 경계를 capabilities `toolCalling`+`upgradeHint`("로컬에서 실행 명령 가능")로 명시 표시.
- **킬러 합격선(R2 혁신성 — 킬러 자리에 측정).** selection 주입 ask 가 복붙 ask 대비 ① *근거 정확도*(선택 셀이 실제 답 근거에 포함된 비율) ② *시간*(질문→근거포함답 도달, 복붙 0초) ③ grounded 통과율에서 우위. 일반론 체감차(03 §6)가 아니라 *킬러 자체* 의 성공기준이 여기 박힌다.
- 회귀 가드: ask 입력은 추가 UI일 뿐 기존 패널 0 변경.

---

## 3. report — "AI 가 글 더 써주고 추가"

리포트는 현재 전량 결정론(`landing/src/lib/report/build.ts`). 본 PRD 는 결정론 문장을 *대체하지 않고* AI 해설을 **추가**한다.

두 경로:

### 3.1 baked 섹션 리드 (기본·정적)
CI 가 주요 섹션의 1~2 문장 해설을 `compose(template:'sectionLead')` 로 미리 굽고 HF/static 에 저장 → report 가 데이터처럼 로드. 런타임 비용 0·검수 가능·브랜드 일관.

```text
CI(빌드): for 종목, for 섹션 → compose(sectionLead, grounding=섹션 facts)
          → grounded 통과분만 채택 → report/leads/{code}.json {asOf, dataVersion, text} (HF)
report 로드: 결정론 섹션 + baked 리드(lead.asOf === bundle.asOf 일 때만, 아니면 폐기→결정론 폴백)
```

> **R1 데이터 W3 해소 — stale 방지.** build.ts 의 원칙은 "정적 bake JSON 폐기, 숫자는 조회 시점 finance.bundle 직독" 이다. baked lead 가 이를 깨지 않으려면 **lead 는 *데이터가 아니라 문장 캐시*** 다 — 숫자는 여전히 런타임 직독(결정론 섹션), AI 는 그 위 *서술만* baked. lead 에 `{asOf, dataVersion}` 동봉(03 §3), report 로드 시 현재 bundle 의 asOf 와 불일치하면 **즉시 폐기 → 결정론 폴백**. [[feedback_terminal_hf_ssot_local_compute]] "stale 을 fresh 처럼 안 보임" 을 baked 레인에 코드화. lead 는 build.ts `findings`(이미 존재, 03 §7) 위에 서술하므로 중복 빌더 0.

### 3.2 live "더 풀어줘" (인터랙티브·온디맨드)
섹션 하단 [이 부분 더 자세히] → `streamCompose(template:'sectionExpand', context:섹션 facts)` → 그 자리에 해설 단락 스트리밍 추가. edge/onDevice. 결정론 facts 에 근거, 숫자 환각 가드.

- 기본 리포트는 baked+결정론으로 완결. live 는 *선택적 심화*. AI 실패(폴백)해도 리포트는 멀쩡.
- landing 은 UI 변경 → **운영자 명시 push 승인 대상**(CLAUDE.md ⛔ UI 자동 push 금지). 06 phasing 에서 landing 적용은 후순위.

---

## 4. carousel (신규) — baked 카피

신규 캐러셀의 카드 부제·요약. **baked 가 정답**(00 §3.3): 100 종목 카드를 매번 손으로 안 쓰고, CI 가 `compose(template:'cardSubtitle', grounding=종목 핵심 facts)` 로 초안 → grounded 통과분 채택 → 캐러셀 데이터에 포함.

- 런타임 LLM 0. 캐러셀은 그냥 데이터를 렌더(SNS image_gen 자산 파이프라인과 동형 — 빌드 산출물).
- 톤: 종목별 실물·숫자 근거(SNS 카피 규칙 계승 — 추상·범용 금융 문구 금지, 메모리 SNS 규칙).
- 검수: baked 라 발행 전 사람이 본다(블로그 검수 철학).

---

## 5. blog — 약문단 보강 (검수 전제)

블로그는 사람 작성 + AUTO. AI 는 **약한 문단 보강 초안** 만(blog-master-writer skill 결과의 보조).

- `compose(template:'blogParagraph', tone:'reader-first', grounding=회사 facts)` → 초안 → **사람 검수 후 채택**.
- 절대 자동 발행 금지(공개 콘텐츠 눈검수, [[project_blog_quality_overhaul]] 교훈: AUTO 자체오염 → dartlab 교차검증 필수).
- 거처: 블로그 파이프라인(빌드타임), 런타임 아님.

---

## 6. landing — 기능 카피 초안 (선택)

기능 소개 블러브 일부를 `compose(template:'featureBlurb')` 초안. 우선순위 최하(랜딩 카피는 대부분 손작성이 적절). UI push 승인 필요. v0 범위에서 제외 가능(06).

---

## 7. surface × 동사 × 경로 매트릭스

| surface | 동사 | 경로 | 티어 | 회귀 위험 | push |
|---|---|---|---|---|---|
| viewer | ask | live | edge→onDevice→det | **높음**(기존 기능) | UI 승인 |
| terminal | ask | live | edge→onDevice→det | 낮음(추가 UI) | UI 승인 |
| report | compose | baked + live | CI / edge→onDevice | 중(landing) | UI 승인 |
| carousel | compose | baked | CI | 낮음(신규) | UI 승인 |
| blog | compose | 빌드타임 초안 | CI | 낮음(검수) | 콘텐츠 검수 |
| landing | compose | baked(선택) | CI | 낮음 | UI 승인 |

**공통 규칙**: 어느 surface도 webllm/edge/fetch 를 직접 부르지 않는다. `runtime.ai` 만. surface 안 `runtime.env.kind`·티어 분기 코드 금지(02 §1 계승) — 티어는 표시(배지)에만.

**baked vs live 의 사용자 체감(R1 혁신 해소)**: baked = *보이지 않는 품질 향상*(잘 쓰인 정적 텍스트, "AI 가 썼다" 마케팅 금지 — 사용자는 AI 개입을 몰라도 됨). live = *보이는 AI 능력*(터미널 ask·report "더 풀어줘"). **신경험 주장은 live 두 곳에만 건다** — baked 를 "AI 기능" 으로 과장하면 K4·한계 표기 원칙 위반. 제품의 AI 다움 간판 = 터미널 selection-grounded ask(§2).

---

## 8. compose 템플릿 카탈로그 (v0)

```ts
// ⚠ 계약상 ComposeTemplateId 는 열린 string(01 §3). 아래는 *v0 레지스트리 키 카탈로그* 일 뿐 계약 union 아님.
//   (R3 유연성: 같은 심볼명에 두 정의 병존 혼선 방지 — 계약 정의는 01 §3, 여기는 templates.ts 초기 키 목록)
const V0_TEMPLATE_KEYS = [
  'sectionLead',      // 리포트 섹션 1~2문장 리드 (baked)
  'sectionExpand',    // 리포트 섹션 심화 단락 (live)
  'cardSubtitle',     // 캐러셀 카드 부제 (baked)
  'blogParagraph',    // 블로그 약문단 보강 초안 (검수)
  'featureBlurb',     // 랜딩 기능 카피 (선택)
] as const;
```

각 템플릿 = { 결정론 폴백 문장(LLM 불가 시), LLM 프롬프트 골격, maxTokens, tone 기본, grounding 요구 facts 키 }. `analysis/compose/templates.ts` 단일 정의(레지스트리). 새 카피 자리 = 레지스트리에 키 1개 추가(surface·contracts 수정 없이).
