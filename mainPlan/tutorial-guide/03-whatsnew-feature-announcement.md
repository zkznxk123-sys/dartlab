# 03 — 신규기능 안내 (정직 모델)

> 사용자 요구: "최근 신규 기능이 있으면 안내도 하고." 투어(신규 사용자)와 다른 채널(재방문 사용자)이다([00](00-product-value-and-pedagogy.md) §3).

## 1. 데이터 소스 = 큐레이션, CHANGELOG 자동파싱 ❌

CHANGELOG.md는 존재하나 UI 노출 0. 순진한 접근: "CHANGELOG를 파싱해서 What's New에 뿌리자." **반대.**

- **자동 sync/자동생성 금지 문화 정면 위반**(CLAUDE.md "자동 생성물·도구 금지" + feedback_no_patterns).
- CHANGELOG는 *개발자용·주체중립 기술체*다 — "py.typed 블로커 해소"·"`_ratiosToWide` DRY"·"pip 번들 웹 UI를 공유 터미널로 전환" 같은 항목을 일반 사용자에게 그대로 보여주면 무의미한 노이즈.
- 2513줄·SemVer·"Unreleased" 구조라 파서가 브리틀. 매 릴리스마다 무의미 항목이 토스트로 샘.

**정답: `whatsNew.ts` 사람 큐레이션 SSOT (cardGuide.ts 패턴 복제)**

`cardGuide.ts` 헤더가 박은 원칙 — *"환각 0: 데이터 기반 자동 문장 생성 금지, 본 큐레이션 텍스트만"* — 을 그대로 계승한다. 새 기능을 머지하는 PR이 이 파일에 1줄 추가. 릴리스 노트(개발자) ≠ 사용자 노트(큐레이션).

```ts
// ui/packages/surfaces/src/_shared/tour/whatsNew.ts
export interface WhatsNewItem {
  id: string;            // 'scan-grade-explainer' — 식별
  version: string;       // '0.11.0' — semver, seenVersion 비교 기준
  date: string;          // '2026-06-14' — 정렬·"N일 전"
  surface: 'map' | 'terminal' | 'all';
  title: string;         // 사용자 언어 ("스캔등급, 왜 이 등급인지 보여줍니다")
  body: string;          // 2~3문장, 개발자 언어 금지
  tourTrack?: { tourId: string; track: string };  // 클릭 시 관련 투어 챕터로 점프 (재사용!)
  anchor?: string;       // data-tour — "여기 있어요" 하이라이트
}
export const WHATS_NEW: WhatsNewItem[] = [ /* 사람 큐레이션 */ ];
```

`tourTrack` 필드가 킬러: 항목 클릭 → 해당 투어 챕터로 점프. **투어와 What's New가 같은 steps 자산을 공유** — 중복 0. SSOT 1개로 "튜토리얼 + 신규기능 안내" 2요구를 묶는 지점.

## 2. seen 추적 = 단일 키 `seenVersion`

`localStorage['dartlab.${surface}.tour.seenVersion']` = 마지막 본 최고 버전. 마운트 시:

```ts
const fresh = WHATS_NEW
  .filter(i => semverGt(i.version, seenVersion) && surfaceMatch(i.surface))
  .sort(byDateDesc);
```

`fresh.length > 0`이면 헤더 가이드 버튼에 **✨N 뱃지 1개**. 클릭 → 메뉴 → "새로워진 기능 (N)" → 리스트 → 항목 클릭 시 `tourTrack`으로 점프. 닫으면 `seenVersion`을 최고 버전으로 갱신.

**투어 done 키와 별개**(투어는 1회, 신규기능은 버전마다 재발화). 키 예산은 [05](05-scope-phasing-guardrails.md) §4.

## 3. 정직 가드 — 뱃지 숨김 ≠ "신규 없음"

위험: "신규 없음"이라 표시하는 순간 *완결성 주장*(정직모델 위반: "다 봤음"·"신규 없음" 금지). 사용자가 안 본 항목이 0이어도 "당신은 모든 새 기능을 봤습니다"라 단언하면 안 된다.

- **뱃지 = unseen 개수. 0이면 뱃지를 숨긴다**(뱃지 없음 = 중립, "없음" 단언 아님).
- 패널은 전체 항목을 *시간순*으로 보여주되 안 본 것에 `● NEW` 점만. "이게 전부입니다"·"더 이상 없습니다" 카피 금지. 하단에 중립적으로: "더 오래된 변경은 CHANGELOG에서 →"(완결성 회피 + 개발자용 전체 목록으로 escape hatch).
- **자동 "다 봤다" 처리 금지** — 스크롤로 지나친 것까지 seen 처리하면 거짓. 패널을 *연* 시점에 `seenVersion`을 갱신하되, 그 의미는 "이 사용자가 이 버전 목록을 *열어봤다*"지 "다 읽고 이해했다"가 아니다. 과장 카피 0.

## 4. 경계 — 실재 기능만, "곧 출시" 금지

**★미출시 기능 광고 함정**: "신규기능 안내"가 *아직 코드에 없는* PRD 기능(워치리스트·시뮬·reverseDCF 등)을 "곧 나옵니다"로 광고하면 = **완결성·미래 약속 위반**.

> **규칙**: 투어/신규기능은 *현재 머지되어 화면에 실재하는 기능만* 가리킨다. "coming soon"·로드맵 노출 0. 기능이 머지되는 *그 PR에서* `whatsNew.ts` 항목과 투어 스텝을 같이 추가 — **투어/신규기능은 진실의 후행 지표**(선행 약속 아님).

이로써 신규기능 안내가 다른 5 PRD([04](04-killlist-and-boundaries.md) §3)의 미구현 기능을 광고하는 일이 원천 차단된다.

## 5. KILL 목록

1. **❌ CHANGELOG/git tag 자동파싱** — 자동생성 금지 문화. 큐레이션만.
2. **❌ 별도 "신규기능" 패널/위젯 신설**(LeftRail·RightStack에) — 이미 붐비는 화면에 패널 추가 = 1순위 덕지덕지. 가이드 버튼 메뉴 항목으로 흡수, 새 패널 0.
3. **❌ 다중 뱃지·항목별 읽음표시·dismiss 키** — localStorage 키 증식. 단일 `seenVersion` 1개.
4. **❌ "곧 출시"·로드맵 노출** — 실재 기능만(§4).
5. **❌ "신규 없음"·"다 봤음" 단언** — 뱃지 숨김(중립). 완결성 카피 0.
6. **❌ 비디오/Lottie 신규기능 데모** — 정적 호스팅 floor 위반·번들 부채. tutorial_video_pipeline은 *SNS 마케팅 영상*이지 in-app 안내가 아님(경계).

## 핵심 주장 3줄

1. 신규기능 데이터는 `whatsNew.ts` 사람 큐레이션(cardGuide 패턴) — CHANGELOG 자동파싱은 개발자 언어 노이즈·자동생성 금지 문화 위반.
2. seen은 단일 키 `seenVersion` + unseen 시 뱃지 1개. "신규 없음"은 단언 않고 뱃지를 숨긴다(완결성 회피).
3. 실재 머지된 기능만 가리킨다(후행 지표) — "곧 출시"·로드맵 광고 0, 기능 PR과 같은 커밋에서 항목 추가. `tourTrack`으로 투어 챕터 재사용해 SSOT 1개.
