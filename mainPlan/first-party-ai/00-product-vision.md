# 00. 제품 비전 — DartLab 이 직접 쓰고 분석하는 1급 AI 레인

상태: 비전 PRD v0.1
범위: 사용자 의도, 제품 정의, 두 능력(분석·작성), 커넥터와의 경계, 성공/실패 기준, 왜 "surface 마다 챗봇"이 아니라 "하나의 작성·분석 포트"인가.

---

## 1. 사용자가 원하는 것

운영자가 원하는 것은 surface 마다 AI 채팅창을 하나씩 더 붙이는 게 아니다. 원하는 구조는 이거다.

```text
DartLab 데이터 작업대 = 공시·재무·매크로·스캔 결정론 SSOT
DartLab 자체 AI       = 그 결정론 위에서 문장을 짓고 질문에 답하는 얇은 레인
사용자                = 터미널에서 바로 묻고, 리포트에서 "더 써줘" 누르고, 캐러셀/블로그 카피를 자동으로 받음
```

구체적으로 원하는 장면:

```text
터미널: 종목·국면을 띄운 채 "이 회사 왜 마진이 빠졌어?" -> AI 가 재무 근거로 분석 한 줄
리포트: 결정론 섹션 아래 "이 부분 더 풀어줘" -> AI 가 그 섹션 숫자에 근거해 해설 단락 추가
캐러셀: 종목 카드의 부제·요약 문구를 사람이 매번 안 쓰고 AI 가 초안
블로그: 회사 리포트 초안의 약한 문단을 AI 가 보강 (사람 검수 전제)
랜딩:   기능 소개 카피 일부를 AI 초안으로
```

핵심은 두 동사다. **분석(ask)** 과 **작성(compose)**. 둘은 같은 generation 코어·같은 근거·같은 티어 사다리를 공유해야 한다. 그래야 나중에 "진짜 좋은 API" 가 생겼을 때 surface 를 하나도 안 고치고 티어만 갈아끼운다.

---

## 2. 제품 정의

**DartLab First-Party AI 는 데이터 작업대 SSOT 위에서 DartLab 이 1인칭으로 글을 쓰고(`compose`) 질문에 답하는(`ask`) 단일 AI 포트다. 모델은 퍼블릭에서 Cloudflare Workers AI(우리 워커·무료티어)와 브라우저 WebGPU 를, 로컬에서 기존 ask 엔진을 쓰되, surface 는 어떤 모델인지 모른 채 동사 2개만 부른다.**

세 가지를 분리해 정의한다.

| 평면 | 무엇 | 어디서 생성 | 비용/프라이버시 |
|---|---|---|---|
| 결정론 분석 (Grounding) | 숫자·근거·추세·비율·asOf | runtime 데이터 포트 + 순수 계산 | 비용 0, 디바이스 밖 0 |
| 작성 (compose) | 섹션 해설·카피·요약 문구 | baked(CI) 또는 live(edge/onDevice) | baked=0, live=neuron 또는 디바이스 |
| 분석 대화 (ask) | 사용자 질문에 근거 기반 답 | live(edge/onDevice/advanced) | edge=neuron, onDevice=디바이스, advanced=로컬 |

제품의 최종 그림:

```text
사용자 질문/요청
  -> Grounding SSOT 가 결정론 근거를 먼저 채움 (숫자·evidence·asOf)
  -> 답이 결정론으로 충분하면 거기서 끝 (LLM 0)
  -> 해석·종합·작문이 필요하면 티어 사다리에서 가용한 최고 티어가 *근거를 서술만* 함
  -> 답변에 tierUsed + evidence + 한계 표시
```

---

## 3. 핵심 사용자와 surface

### 3.1 터미널 사용자 (분석 우선)

밀도 높은 계기판을 보다가 "왜?" 가 떠오른다. 차트·재무·매크로를 보던 그 컨텍스트 그대로 한 줄 묻고 싶다. 필요한 것은 종목 추천이 아니라 *지금 화면의 숫자에 대한 해석*이다. → `ask`, 근거 = 현재 회사 finance bundle + 선택 셀.

### 3.2 리포트 독자 (작성 보강)

결정론 리포트는 정확하지만 건조하다. 특정 섹션을 더 풀어 읽고 싶다. → `compose(template='sectionExpand')`, 근거 = 그 섹션의 결정론 facts. 기본 리포트 문장은 그대로 두고, AI 는 *추가*만 한다.

### 3.3 캐러셀/블로그/랜딩 작성자 (배치 작성)

100 종목 카드 부제, 블로그 약문단 보강, 기능 카피를 매번 손으로 못 쓴다. → `compose`, **CI 에서 baked** 가 기본(검수 가능·브랜드 일관·런타임 비용 0). live 는 인터랙티브에만.

---

## 4. 차별화 — 두 축, 서열대로 (R1 혁신성 재서열)

### 4.1 [1번 차별] 금융 도구가 전부 AI 를 로그인+유료키 뒤에 가두는 시장에서, 키0·로그인0·끊김없음

경쟁 금융/주식 도구(Bloomberg ASKB·AlphaSense·Koyfin·FinChat·Simply Wall St)는 **전원 AI 를 로그인 + 유료 서버키 뒤에 가둔다.** 진지한 금융 도구 중 키0·로그인0 퍼블릭 AI 는 사실상 부재다. DartLab 은:

```text
GitHub Pages 정적 사이트가, 사용자 API 키·로그인 0 으로,
Cloudflare 무료티어 8B 로 답한다 → 안 되면 사용자 GPU(WebGPU) → 그것도 안 되면 결정론.
경쟁사가 "로그인하세요/유료입니다/키 넣으세요" 로 *끊는* 자리에서, DartLab 은 *항상 답한다*.
```

"never-breaks in a market that always gates." 이것이 진짜 희소한 차별이고, 자동 프로비저닝(토큰만 secret 에 넣으면 다음 배포에 AI 자동 ON, 빼면 자동 WebGPU 강등, [02](02-edge-ai-cloudflare.md) §4)이 그 운영 우아함이다.

> **해자 깊이(R2 혁신성 해소).** 1번 차별의 *인프라*(Cloudflare 무료티어)는 한 곳에 의존하고 희소성 반감기가 있다(경쟁사도 같은 티어를 쓰거나 CF 정책이 바뀌면 증발). 그래서 **진짜 해자는 인프라가 아니라 grounding(2번)+selection(3번)의 조합** 이다 — edge 가 사라져도 onDevice·결정론·근거 묶음·"보던 셀이 근거" 는 남는다. 1번은 *지금* 가장 눈에 띄는 차별이고, 2·3번이 *오래 가는* 차별이다.

### 4.2 [2번 차별] 그 위에서 틀린 숫자를 못 쓰게 묶는 신뢰 척추

```text
일반 LLM 카피:  그럴듯하지만 숫자·출처·asOf 가 없거나 환각
DartLab:        숫자는 Grounding SSOT 가 박고, 모델은 그 숫자를 한국어로 서술만 (사후검증으로 환각 stray 거부)
```

grounded generation 자체는 2026 commodity 다 — 그래서 1번이 아니라 2번이다. 하지만 *키0 퍼블릭에서도* 근거에 묶이는 조합이 DartLab 의 신뢰 포지션이다. 포지션 = "AI 가 글을 잘 쓰는 서비스" 가 아니라 **"끊기지 않으면서, 틀린 숫자를 못 쓰는 AI."**

### 4.3 명명된 능력 — selection-as-evidence ("복붙 없는 근거")

터미널/뷰어에서 사용자가 *보고 있는 셀·차트 커서·섹션* 이 곧 prompt 의 grounding 이 된다([01](01-tier-architecture.md) §7, [04](04-surface-wiring.md) §2). BYO-key 챗봇은 구조적으로 이 컨텍스트가 없어 복붙을 요구한다. **"보던 셀이 자동 근거"** 가 commodity grounding 과 갈리는 지점이며, 터미널 ask 가 단일 킬러인 이유(04 §2).

---

## 5. 성공 기준

성공은 "AI 가 말을 잘 하는가" 가 아니다.

| 기준 | 의미 |
|---|---|
| 동사 2개로 전 surface 커버 | viewer/terminal/report/carousel/blog 가 `ask`·`compose` 만 부르는가 (surface 별 AI 구현 0) |
| 숫자 환각율 0 | 출력의 모든 수치가 Grounding facts 에 존재하는가 (사후검증 통과) |
| 티어 강등 무중단 | edge 예산 소진·WebGPU 부재에도 답이 끊기지 않고 한 단계 내려가 답하는가 |
| 퍼블릭 무료 가동 | 키·로그인 0 으로 공개 사이트에서 edge 또는 onDevice 가 실제로 답하는가 |
| baked 정적 카피 채택 | 캐러셀/블로그 카피가 런타임 비용 0 으로 데이터처럼 서빙되는가 |
| 티어 교체 비용 | "진짜 좋은 API" 추가 시 surface 수정 0, 어댑터에 티어 1개 추가로 끝나는가 |
| LLM 부가가치 체감 | LLM 서술이 결정론 템플릿(determinismAnswer) 대비 *체감 차이* 가 있는가 — 미미하면 LLM 경로 재검(03 §6) |
| 강등 답 품질 floor | edge 소진·WebGPU 부재로 결정론까지 내려가도 답이 *읽을 만한* 한국어인가(06 게이트) |

가장 중요한 기준 하나:

```text
surface 코드는 어느 모델이 답하는지 영원히 모른다.
```

---

## 6. 실패 기준

다음으로 흐르면 실패다.

- surface 마다 webllm/ollama/fetch 를 직접 부르는 분산 구현이 다시 생긴다(현재 viewer 상태의 확산).
- 모델이 Grounding 에 없는 숫자를 지어내고 그게 그대로 표시된다.
- edge 예산이 소진됐는데 "AI 사용 불가" 로 끊긴다(폴백 실패).
- "무제한 무료 AI" 로 과장한다.
- 투자 조언(매수/매도/목표주가)으로 미끄러진다.
- 퍼블릭 브라우저에서 5패스 노드 그래프 같은 무거운 에이전트를 재현하려 한다([[feedback_no_graph_regression]]).
- 외부 AI 노출(MCP/OpenAPI)과 섞여 `ai-workbench-connector` 와 정체성이 겹친다.

---

## 7. 커넥터와의 경계 (혼동 금지)

| | ai-workbench-connector | **first-party-ai (본 PRD)** |
|---|---|---|
| 방향 | 아웃바운드 — 외부 AI 가 DartLab 을 호출 | 인바운드 — DartLab 이 직접 생성 |
| 모델 | DartLab 은 모델 *제공 안 함* | DartLab 이 모델 *씀*(edge/onDevice/local) |
| 표면 | `/mcp`·`/openapi.json` read-only 근거 도구 | `runtime.ai.ask`·`compose` surface 동사 |
| 워커 | `infra/workers/dartlabConnector` | `infra/workers/aiEdge` |
| 사용자 | ChatGPT/Claude/Gemini 사용자 | DartLab 화면을 직접 쓰는 사용자 |

둘은 보완이다(외부 AI 는 근거를 받아가고, DartLab 자체 AI 는 화면 안에서 쓴다). 하지만 **코드·워커·정체성은 분리**한다. 공유 가능한 건 Grounding SSOT 의 근거 빌더뿐이며, 그 공유도 [05](05-killlist-and-non-goals.md) 에서 명시 경계로만 허용한다.

---

## 8. 제품 원칙

1. **동사 2개.** surface 는 `ask`(분석)·`compose`(작성)만 안다. 모델·티어·프로바이더는 포트 뒤.
2. **근거 먼저.** 모든 생성은 Grounding SSOT 의 facts 위에서만. 숫자는 결정론, 서술만 모델.
3. **끊기지 않음.** edge → onDevice → deterministic 우아한 강등. 답은 항상 나온다.
4. **공통배선.** 공개/로컬이 같은 포트·같은 Grounding. 로컬은 명시 없으면 공개 경로 재사용([[feedback_terminal_hf_ssot_local_compute]]).
5. **티어 명시.** 어느 티어가 답했는지·근거·한계를 표시. 강등을 숨기지 않음.
6. **baked 우선(정적).** 정적 surface 카피는 CI 에서 구워 데이터로. live 는 인터랙티브만.
7. **교체 가능.** 새 모델/API 는 티어 추가일 뿐. surface 불변, 계약 불변.

---

## 9. 북극성 (R2 혁신성)

당장의 산출은 "터미널 한 줄 질문 + 카피 초안" 이지만, selection-grounded ask 가 성숙하면 향하는 곳은 **터미널 전체가 대화형 분석 표면** 이 되는 그림이다. 지금은 계기판을 *보다가* 묻지만, 결국 묻는 것이 계기판을 *움직이는*(로컬 advanced 에서 tool-calling 으로 셀 포커스·차트 오버레이·필터) 단계로 — 부산물이 아니라 미래 간판. 이 북극성은 한계 표기 원칙을 *안 깬다*: 모든 단계에서 숫자는 결정론, 근거는 표면, 끊김은 없음. 야심은 "AI 가 더 똑똑해진다" 가 아니라 **"근거에 묶인 채로 화면과 대화가 하나가 된다"** 다. 단 이 비전은 *방향* 이지 v0 약속이 아니다(과장 금지, [05](05-killlist-and-non-goals.md)).
