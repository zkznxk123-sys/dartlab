# 에디토리얼 카드뉴스 파이프라인 — SSOT

> 터미널 + 인스타에 발행하는 **에디토리얼 카드뉴스**. 검증된 기업 데이터를 *확실하게 후킹되는* 매거진 카드로 증류한다.
> 정체: 인스타 매거진 스타일 멀티카드(모노크롬 사진 풀블리드 + 한 구절만 dartlab 핑크-레드 강조 + 키포인트 비트). **기존 차트 캐러셀(`sns/carousels` 30+ 컴포넌트)은 반려** — 무겁고 인포그래픽 위주.
> 전문에이전트 2라운드 토론 기록 = [`expert-debate.md`](expert-debate.md).

---

## 0. 한 줄 정의

**카드 = 발명이 아니라 증류.** 사람이 이미 검증한 기업 리포트의 가장 강한 사실을, *약한 훅은 구조적으로 차단하는* Hook Engine으로 골라, 한 화면 0.5초 안에 멈추게 만든다.

dartlab의 비대칭: 일반 크리에이터의 강한 훅은 *신뢰를 깎아* 만들지만, dartlab의 강한 훅은 *데이터가 떠받쳐* 신뢰를 안 깎는다. "이 숫자 진짜야?" → "전자공시 봐" 가 끝나는 순간 충격과 신뢰가 **동시에** 올라간다.

---

## 1. 카드 시스템 (as-built)

거처: `sns/remotion-sns/src/cards/HookCard.tsx` (sns/ 전체 gitignored). 1080×1350 4:5.

| 레이아웃 | 역할 | 구성 |
|---|---|---|
| `editorial` | 커버(훅) | 모노 사진 + 작은 임팩트 날짜 + 빅 헤드라인(`[[ ]]` 한 구절 강조) + 3~4줄 payoff |
| `editorialBeat` | 내용 비트(키포인트) | 임팩트 키커 라벨 + 헤드라인 + 본문 |
| `editorialStat` | 숫자 모먼트 | 키커 + 거대 숫자(임팩트 컬러) + 한 줄 맥락 |

공통: 좌상단 회사명 태그(주식=실명 노출 OK) · 우상단 페이지 점 · 좌하단 dartlab 마크.

**시각 규칙 (강행):**
- 사진 = 컬러 webp를 렌더 시 `filter: grayscale(1) contrast(1.06) brightness(0.9)` (사전가공 금지·SSOT 1벌).
- 강조색 = dartlab SNS 임팩트 컬러 **핑크-레드 `#fb3f6c`** (`colors.accentImpact`). **레퍼런스 주황 클론 금지** — 우리 색.
- 강조 = 헤드라인당 정확히 1구절(`[[ ]]`). 2개+ = 시선 분산 = 강조 0과 동일.
- 첫 줄 ≤ 12~14자(줄넘김 orphan 금지). 헤드라인 90px·본문 34px(2026-06-18 "글자 키움" 반영).
- 가짜 도메인(dartlab.io) 워터마크 금지. 추상 그라데·금융 클립아트 금지(회사 상징 실물만).
- image_gen·Flux 신규 이미지는 반드시 `sns/assets/{sourceCompany}/{semantic}.webp` 공유자산으로 저장하고, 포스트 폴더에는 직접 저장하지 않는다. 캐러셀은 `meta.json.sourceCompany` → `sync_assets.py` → `public/{postId}/` 복사 경로만 소비한다.
- 카드 수는 템플릿으로 고정하지 않는다. 인스타 캐러셀은 최대 20장까지 염두에 두되, 기본은 6~12장이고 10장 이상은 새로운 판단 근거가 계속 있을 때만 쓴다.
- 숫자는 뒷부분의 판단 근거로 쓴다. 모든 카드에 숫자를 억지로 넣지 말고, 주가 배수·이익률·목표가 분산·점유율·전력 규모처럼 질문을 바꾸는 숫자만 핵심 카드로 올린다.
- 기업·주식 에디토리얼 캡션은 스레드에도 올릴 수 있게 짧게 쓴다. 기본 톤은 `입니다/아닙니다` 존댓말이며, 카드 본문을 다시 풀어쓰는 긴 해설은 피한다.
- 캐러셀을 만들 때 같은 `hook.json` 으로 9:16 릴스도 함께 뽑는다. `sns/reels/from_carousel.py {post}` 가 표준이며, 원본 이미지는 공유자산 1벌만 사용한다. 4:5 PNG를 이어붙이지 말고 Remotion `CarouselReel` 이 9:16 안전영역에 맞게 재배치한다. 좌하단 브랜드 푸터는 캐러셀과 같은 `avatar-discover.webp` + `dartlab` 조합만 쓴다. 별도 아바타 장식은 쓰지 않는다. `reel.json.brand.accent` 는 dartlab 임팩트 컬러 `#fb3f6c` 로 기록한다.

---

## 2. Hook Engine — "확실한 후킹"의 핵심 (2라운드 토론 산물)

후킹은 운빨이 아니다. **generate-many → score → pick → (약하면 스킵)** 의 결정론 구조가 *발행된 모든 카드의 훅 하한선*을 보장한다.

### 2.1 후크 taxonomy 8종

| Type | 심리기제 | 공식 | dartlab 예시 |
|---|---|---|---|
| **A 숫자충격** | 직관 척도 초과 → 불신 → 검증욕구 | `[열등상태]가 [시간압축]에 [절대숫자]` | "망하기 직전 회사가 한 분기에 **19조**" |
| **B 역설** | 양립불가 두 사실 → 부조화 해소욕구 | `[A인데] [정반대 B]` | "순손실인데 영업이익 사상 최대"(고려아연) |
| **C 버려진것의 반전** | 권위자 오판 + 약자 승리 | `[권위자]가 [헐값]에 버린 게 [거대가치]` | "삼성이 8,400억에 버린 무기가 수주 37조"(한화) |
| **D 꼴등의 역전** | 정체성 전복 | `[최하위]가 [거대정체성]이 되기까지` | "라면 꼴등이 글로벌 거인"(삼양) |
| **E 미스터리 질문** | 닫고싶은 열린 루프 | `[주체]는 왜 [의외행동]했을까` | "미래에셋은 왜 한 주도 못 받았을까" |
| **F 의외의 정체** | "안다고 생각한 것" 전복 | `[익숙한 것]은 사실 [전혀 다른 것]` | "주가의 90%는 사이클이 결정"(HMM) |
| **G 권력/불의** | 분노·정의감(최강 공유동력) | `[강자]가 [약자]에게서 부당하게` | 데이터가 정당화할 때만 |
| **H 정체성 위협** | 손실회피 + 자기관련 | `너 같은 [독자]가 먼저 당한다` | 시리즈 톤 한정·품격 주의 |

**주력 = A·B·C·D** (검증 숫자로 자기완결). G·H는 정직성/품격 리스크 최대 — 데이터가 그 감정을 직접 정당화할 때만.

### 2.2 후보 생성 (결정론, 4개 기존 자산 소비 — 신규 계산 0)

| 소스 | 위치 | → 후크 type |
|---|---|---|
| frontmatter `ai.*` | `blog/05-company-reports/*/index.md` (`keyMetrics·strengths·weaknesses·archetype`) | A 숫자충격 · B 역설(strength×weakness 충돌) |
| `detectThreads` | `story/narrative.py` (NarrativeThread{title,evidence,severity}) | D/F 의외정체 · 리스크 |
| `narrate._classify` | `story/narrate.py` (값→임계 레이블) | A 숫자충격 임계 판정 |
| `getRankOrBuild` | `scan/screen/rank.py` (RankInfo) | C/극단치 "업종 1위/상위 10%" |

**fallback 사다리** (밋밋한 대형주 보장): S1 절대숫자충격 → S2 횡단순위 → S3 변화율 → S4 정체반전 → S5 미스터리질문(`buildActTransitions`가 항상 의문형 1개 생성 = 0 안 됨). 5단계 전부 비면 **카드 스킵**(데이터 없는 종목).

### 2.3 reject-gate (점수 이전 hard block)

| 게이트 | 차단 | 성격 |
|---|---|---|
| G1 무숫자·추상 | 숫자 0 + 추상명사("성장/혁신/저력")만 | 강도 |
| G2 첫 줄 길이 | > 18자 | 강도 |
| G3 강조 구절 | 0개 또는 3개+ | 강도 |
| G4 과장어 | "세계급/유일/최고/전무후무" NEVER-CLAIM grep | **정직성·우회불가** |
| G5 막연 서술 | "회사가 ~했다" 수치·고유명사 0 | 강도 |
| G6 갭 자폭 | 첫 줄에 원인+결과 모두 명시 | 강도 |
| G7 근거 미검증 | 인용 수치가 panel/scan ref에 매칭 안 됨 | **정직성·우회불가** |

### 2.4 scoring 루브릭 (0~100)

`숫자충격 22 + 호기심갭 20 + 의외성 18 + 감정전하 14 + 1초가독 12 + 구체성 8 + 강조선명 6`. (A+B+C+D = 74 = 충격·갭·역설·생존에 집중. 약한 훅은 정확히 이 4축이 빈다.)

### 2.5 pick 임계

- **≥ 75** : 자동 발행 (강함 보장)
- **60~74** : 보강 큐 — 사람이 더 강한 대안으로 끌어올리거나 *천재 훅 구제* override
- **< 60** : 회사 스킵 (약한 발행보다 정직한 스킵)

보장의 정체 = "최고 훅 강제"가 아니라 **"약한 훅 발행 거부"** = 훅 하한선.

### 2.6 A/B 학습 루프 (경량·과설계 금지)

발행 후 인스타 **저장율·공유율**(좋아요·노출은 노이즈)을 훅 type별로 수집 → 월 1회 사람이 표 한 장(type×축×저장율) 보고 **루브릭 7축은 고정, 가중치만 ±10% 캡** 보정(`rubric_v` 태그). ML·자동분기 금지. `OutcomeLog` 패턴 재사용. override 발행물 성과 = 루브릭 진화의 입력.

---

## 3. 콘텐츠 소스 · 자동화 경계

- **blog-first 증류**: `title`→커버 헤드라인 후보(거의 자동), `keyMetrics/strengths/weaknesses`→비트 소재. engine-first(detectThreads 전종목)는 3단계.
- **자동화 경계 (적대검증 핵심)**: `ai.verdict` 길이가 이중분포(초기 100~160자 vs 최근 878~1844자)라 **sub 자동추출 불가**. → **숫자·title·후보생성·스코어링은 자동 · sub·키포인트 큐레이션·인과 프레이밍은 사람.** "숫자 역설 자동, 인과 서사 사람."
- **정직성**: 모든 헤드라인 숫자 = blog 원문 역추적(`sourceReport` 링크) + evidence ref. 점검 질문 = **"이 훅의 충격이 사라져도 숫자는 여전히 사실인가?"** Yes만 발행.

---

## 4. 발행

- **인스타 먼저** (도달 증명·시각 회귀 0). 생성·렌더·caption 자동, 발행 클릭 + 30분 engagement 루틴 수동(Graph API 무인발행 비권장).
- **터미널** `CardFeed.svelte`(`ui/packages/surfaces/.../terminal`)는 2주차 — 라이브 렌더(이미지 사본 금지), `landing routeLoad.ts`+`runtime dartlabData.ts` 한 줄씩(HF-first 캐시 공짜 상속). **UI push 운영자 승인 게이트.**
- 단일 SSOT = `cards.json` (StoryCard: headline/highlightSpan/sub/date/imageRef/sourceReport/sourceEngine) → 두 발행면 공통 소비.

---

## 5. 3단계 로드맵

| 단계 | 산출물 | 완료 게이트 |
|---|---|---|
| **1주차 (MVP·인스타 단독)** | `buildCardsJson.py`(offline) + 비주얼 + 카드 5장 렌더→발행. Hook Engine 원칙을 *수동 적용* | 5장 중 3장 손 안 대고 발행 가능 |
| **2주차** | frontmatter `card.{headline,sub,highlight}` 전용필드 + 터미널 CardFeed | 새 글 1편 카드필드 +5분 이내 |
| **3단계** | Hook Engine 본진 = `tests/_attempts/hookEngine/` 졸업 후 `story/hooks.py`(`generateHooks`+`scoreHook`+reject-gate). engineRef 게이트 활성 | 자동후보 10개 중 3개 발행가치(저장율 상위) |

---

## 6. as-built (2026-06-18)

- ✅ 레이아웃 3종 `HookCard.tsx` + `accentImpact #fb3f6c` + `date/kicker/bigNumber/unit/context` 필드.
- ✅ 샘플 `sns/carousels/E01-000660-skhynix-editorial/` — SK하이닉스 8장, 전부 frontmatter 검증, Hook Engine 채점 반영(커버 92·NVIDIA 81 S급, 보강 카피 적용).
- ✅ bg 자산 `sns/remotion-sns/public/_editorial-sample/`.

**다음 TODO:** ① 회사 더(삼양 003230·아마존 등) ② `buildCardsJson.py` + caption 자동생성 ③ Hook Engine `_attempts` 졸업 빌드.
