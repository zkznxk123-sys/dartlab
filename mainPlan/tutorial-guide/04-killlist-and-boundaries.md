# 04 — KILL/DEFER/KEEP + 경계 + 안내 가드

## 1. KILL / DEFER / KEEP 판정표 (전수)

| 항목 | 판정 | 근거 |
|---|---|---|
| **CHANGELOG.md 자동파싱 → 신규기능 피드** | **KILL** | 자동생성 금지 문화 위반·개발자 언어 노이즈·브리틀 파서. `whatsNew.ts` 큐레이션([03](03-whatsnew-feature-announcement.md) §1). |
| **비디오/Lottie 애니메이션 투어** | **KILL** | spotlight가 코드로 화면을 *실제로* 바꿔 "보여주기"를 이미 달성. 영상=무거움·정적 호스팅 floor 위반·유지보수 부채. tutorial_video_pipeline은 *SNS 마케팅 영상*이지 in-app 투어 아님(경계). |
| **13스텝 풀 복제 (map 동등 분량)** | **KILL→DE-SCOPE** | 터미널은 회사 1개 컨텍스트, 13스텝 자동 데모가 상태(전체화면·탭)를 휘저음. **5~7스텝 + 비파괴 데모**로 깎음. "스텝 수=성공"은 반-성공기준. |
| **강제 첫방문 자동시작 (터미널)** | **DEFER (조건부)** | 사용자 "항상 on 금지" 명시. 터미널은 `?sym=` 딥링크 진입(블로그·SNS)이 많아 *맥락 침입*. Phase 0=버튼만, Phase 1=`?sym` 없는 순수 진입에 *코치마크*(자동 모달 아님, [00](00-product-value-and-pedagogy.md) §7). |
| **진척 게임화 (배지·"3/10 배움"·완료율·숙달 점수)** | **KILL** | 다크패턴·정체성 오염. 사용자는 forensic 분석가지 게임 플레이어 아님. 진행률 바(스텝 N/M)는 OK, *학습 완료도 게이미피케이션*은 금지. |
| **다국어 투어 변형 (ko/en i18n 시스템)** | **DEFER→최소** | map 투어는 한국어 단일. i18n 시스템화=유지보수 2배. Phase는 한국어 단일(map 패리티), en 후속. feedback_no_patterns "영어 변형 금지"와 정합. |
| **텔레메트리/analytics (스텝 이탈 추적)** | **KILL (퍼블릭)** | `TelemetryPort` 존재하나 public=무PII. 이탈 추적=서버 의존+PII 위험+가치 불명. 퍼블릭 floor 불가, 표시 원칙 위반. |
| **"신규기능" 다중 뱃지/항목별 읽음 누적** | **DEFER→단일** | localStorage 키 증식(SSOT 분열). 단일 `seenVersion` 1키, 뱃지 1개. |
| **별도 "신규기능" 패널 (LeftRail·RightStack 신설)** | **KILL** | 붐비는 화면에 패널 *또* 추가 = 1순위 덕지덕지. 가이드 버튼 메뉴 항목으로 흡수, 새 패널 0. |
| **외부 투어 라이브러리 (driver.js/shepherd/intro.js)** | **KILL** | 자체구현이 마스크·데모액션·퀵/풀·바텀시트까지 더 풍부. 새 의존성=문화 위반. driver.js는 requires/runtime·actionId·신규기능 못 해 래핑 필요=순손실. |
| **별도 엔진/커널/그래프/노드/디스패처** | **KILL** | `Step[] + spotlight 1컴포넌트` 상한. no-graph-regression 동형. |
| **헤더 `?`(가이드) 버튼** | **KEEP (코어)** | map과 동일. hdrLinks 군집에 1개 — 새 표면 0, 패턴 재사용. |
| **map 투어 → 공유 엔진 추출** | **KEEP** | 사용자 "유지보수 편리·공통배선" 명시 요구. 단 레드팀 가드 박음([01](01-shared-tour-engine-architecture.md) §0). |
| **로컬/퍼블릭 기능차 설명 스텝** | **KEEP** | 이미 `allowTerminalAsk` 분기가 라이브 — *말로 옮기는 것*. 기능차 표시 원칙 필수([02](02-local-public-common-wiring.md)). |
| **cardGuide 39개 → 투어 스텝화** | **KILL** | 39스텝 백과사전. cardGuide는 just-in-time 툴팁이 정답. 투어는 "있다"만 1스텝([00](00-product-value-and-pedagogy.md) §5). |
| **첫방문 코치마크 (펄스 말풍선)** | **KEEP (Phase 1)** | 자동 모달 거부 + 발견성 역설 해소의 유일한 절충([00](00-product-value-and-pedagogy.md) §7). |

**KILL 상위 5**: ① CHANGELOG 자동파싱 ② 비디오/Lottie 투어 ③ 진척 게임화 ④ 별도 신규기능 패널 신설 ⑤ 퍼블릭 텔레메트리 트래킹.

## 2. 정체성 가드

- 투어는 **발견성 도구**지 *온보딩 의식*이 아니다. 7스텝으로 못 가르치면 UI 결함 신호([00](00-product-value-and-pedagogy.md) §1).
- 사용자 = forensic 분석가. 게임화·축하 애니메이션·"레벨업" 금지.
- 큰 글씨·"유도"는 **가독성·발견성**이지 조작이 아니다.

## 3. 경계 — 5 PRD 소유 침범 금지

투어는 **설명만, 재발명·기능제공 0**. 각 스텝이 가리키는 기능의 *소유*는 그 PRD에:

1. **워치리스트·섹션점프·커맨드바** = `terminal-improvement`. 투어는 *가리킬* 뿐, 섹션점프 문법을 *구현*하면 침범.
2. **reverseDCF·compare·동종백분위** = `financial-statement-lab`. 투어가 "적정주가" 류 카피 쓰면 그 PRD 가드 위반.
3. **시뮬·이벤트레일·지수·백테스팅** = `scenario-simulator`. 투어 카피가 "미래 예측" 암시하면 침범.
4. **스캔등급 다이얼로그** = `scan-grade-explainer`. 투어는 "헤더 클릭하면 등급 설명 열린다"를 *가리킴*, 다이얼로그 내용 복제하면 중복 SSOT.
5. **테이블 내보내기** = `table-export`. **포트 원칙·StoragePort** = `ui-platform-refactor`.

**★ServicesPort 소비 금지 가드** — 투어가 `localOnly`/`upgradeHint`를 *처음 소비하는 클라이언트*가 되려는 유혹이 크다(타입이 미소비라 "비었으니 내가 쓰자"). command-palette/service-registry 소비는 terminal-improvement/ui-platform-refactor 소유. **투어는 `runtime.env.kind`만 읽어 카피 분기**, ServiceDescriptor 렌더링은 안 건드린다([02](02-local-public-common-wiring.md) §1).

**★미머지 광고 함정** — "신규기능 안내"가 아직 코드에 없는 PRD 기능을 "곧 나옵니다"로 광고하면 완결성·미래 약속 위반. 규칙: 실재 머지된 기능만, 기능 PR과 같은 커밋에서 스텝 추가([03](03-whatsnew-feature-announcement.md) §4).

## 4. 안내 가드 (출시 차단 항목)

- **완결성 주장 금지** — "이제 다 배웠습니다"·"모든 기능을 익혔습니다" 0. map 마지막 스텝("툴은 만들었고 인사이트는 당신이")처럼 *겸손한 종료*. "7/7 완료"는 진행률이지 숙달 주장 아님.
- **"신규" 범위 명시** — *이 기기의 마지막 본 버전 이후 추가분*이지 절대적 신규 아님(기기종속). 크로스기기 동기화 불가를 숨기지 않음(terminal-improvement "기기·시점 명시" 계승).
- **로컬/퍼블릭 = 열등 프레이밍 금지** — "퍼블릭은 부족"이 아니라 "AI 직접질의는 로컬 LLM이 필요해 로컬 버전에서 켜집니다" *중립·설치 CTA*. 퍼블릭 floor=완전한 제품, 로컬=bonus.
- **큰 글씨·"유도" ≠ 다크패턴** — 금지: 닫기 숨김, "지금 안 보면 못 봄" 압박, 자동 재팝업, 강제 완주. map처럼 *항상* Esc/건너뛰기/여기서 끝내기(탈출 자유 패리티).
- **자동생성 카피 금지** — cardGuide 원칙("환각 0, 큐레이션만"). 데이터/CHANGELOG 생성 0.
- **푸시 전 스크린샷 눈검수** — 안내 문구·큰 글씨 레이아웃은 픽셀 검수(feedback_ui_rules). 정량 PASS가 카피 과장을 못 본다.

## 5. 적대검증 — 6개월 뒤 회귀/방치 + 가드

1. **투어 카피 stale**: 기능 바뀌었는데 투어가 옛 화면을 가리킴 → 신규자가 *틀린 안내*로 신뢰 붕괴. → 가드: 카피 ≤7스텝 *작게* 유지 + 스텝을 기능 PR과 *같은 커밋*에서 갱신. selector 부재 시 dev 가드가 시끄럽게([01](01-shared-tour-engine-architecture.md) §2.3).
2. **신규기능 방치돼 6개월 전 게 영원히 "신규"**: → 가드: 신규카피는 *옵트인 큐레이션*, 비면 뱃지 0(빈 게 정상). "신규 없음" 출력 안 함.
3. **누군가 "투어 엔진"을 새 그래프/노드 시스템으로 키움**(`TutorialEngine·StepGraph·OnboardingKernel`): → 가드: `Step[] + spotlight 1컴포넌트`에서 못 벗어남(map이 증명). 별도 엔진/디스패처/그래프 신설 = reject.
4. **localStorage 키 증식**(`done`·`seenVersion`·스텝별 읽음·뱃지dismiss…): → 가드: 키 상한([05](05-scope-phasing-guardrails.md) §4). 초과 = 설계 재검토. StoragePort 정합 시 이관.
5. **CHANGELOG 파싱이 "편리해 보여" 슬그머니 들어옴**: → 가드: Phase 2 AC "CHANGELOG import 0"을 자동 게이트(grep).
6. **투어가 복잡성의 핑계가 돼 UI 단순화가 영영 미뤄짐** ("투어 있으니 괜찮아"): → 가드: "투어는 발견성이지 단순화의 대체가 아니다"([00](00-product-value-and-pedagogy.md) §1).
