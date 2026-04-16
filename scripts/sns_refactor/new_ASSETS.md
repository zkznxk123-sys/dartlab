---
name: SNS 공유 이미지 자산 SSOT
description: 캐러셀·릴스·쇼츠·영상·블로그 어디서든 같은 기업 이미지 1벌. 한 번 만든 Flux/블로그 실물 이미지를 포맷마다 복제하지 않고 공유.
type: feedback
---
# SNS 공유 이미지 자산

**`sns/assets/` = 기업 이미지 단일 진실의 원천 (SSOT).** 어떤 포맷(캐러셀·릴스·쇼츠·영상)이든 같은 기업을 다룰 때 이 폴더에서 가져온다. 같은 Flux를 두 번 생성하지 않는다.

## 폴더 구조

```
sns/assets/
├── index.json                        (자동 생성: 회사별 자산 목록 + similarTo 체인)
├── {stockCode}-{slug}/               KR 예: 352820-hybe/
├── {ticker}-{slug}/                  해외 예: meta-meta-platforms/
├── _topics/{concept}/                회사 없는 테마 예: _topics/ai-power/
└── _misc/                            일회성·분류 보류 자산
```

**회사 폴더 내부**:

```
sns/assets/{code-or-ticker}-{slug}/
├── meta.json                         (선택) 기업 메타 + similarTo + 사용 이력
├── {semanticName}.webp               실물 이미지 (blog 출처)
├── {semanticName}.webp               Flux 생성 이미지
└── ...
```

**예**:

```
sns/assets/
├── 267260-hd-hyundai-electric/
│   ├── thumbnail.webp                 (blog 08-thumbnail.webp)
│   ├── power-grid.webp                (blog 08-power-grid.webp)
│   ├── transformer-factory.webp       (blog 08-transformer-factory.webp)
│   ├── bg-hook-industrial.webp        (Flux 005 hook용)
│   └── winding.webp                   (Flux 권선 공정)
├── 352820-hybe/
│   ├── concert-stage.webp             (blog 39-kpop-concert-stage.webp)
│   └── empty-studio.webp              (blog 39-empty-recording-studio.webp)
├── meta-meta-platforms/
│   ├── datacenter.webp                (blog 37-meta-ai-datacenter.webp)
│   └── ad-network.webp                (blog 37-meta-advertising-network.webp)
├── _topics/
│   └── ai-power/
│       └── bg-gpu-farm.webp
└── _misc/
    └── Screenshot-2025-12-04.png     (임시 보관)
```

## 명명 규칙 (현실 반영)

- **파일명 = 의미명** — 내용을 가리키는 단어 (`winding`, `houston-port`, `shipyard`, `concert-stage`).
- **`bg-` 접두사 허용** — 배경이미지임을 명시할 때 사용 가능. (`bg-hook-industrial`, `bg-gpu-farm`).
- **포맷종속 suffix 금지** — `-hook`, `-scene1`, `-thumbnail-short`, `-carousel-slide1` 같은 포맷 용도 부착 금지. 재사용 막음.
- **사본 금지** — blog 경로 재복사 말고 assets/ 로 한 번만 이관. 블로그 assets 폴더는 렌더 직전 copy 대상.
- **의미명 유지 원칙** — 같은 컨셉은 같은 파일명. 포스트 번호·회차 표기 금지.

## 폴더 키 규칙

| 유형 | 폴더 키 | 예 |
|---|---|---|
| KR 상장사 | `{stockCode}-{slug}` | `352820-hybe/` |
| 해외 상장사 | `{ticker 소문자}-{slug}` | `meta-meta-platforms/` |
| 테마/개념 | `_topics/{concept}/` | `_topics/ai-power/` |
| 일회성·보류 | `_misc/` | `_misc/Screenshot-*.png` |

회사 폴더 슬러그(`-slug`)는 필수 — 티커 단독(`META/`)은 의미가 빈약하고 미래 충돌 위험.

## 수집 경로 (3가지)

| 경로 | 용도 | 위치 |
|------|------|------|
| **blog assets 재활용** | 실제 회사/제품 사진 | `blog/05-company-reports/{NN}-{code}-{slug}/assets/*.webp` |
| **Flux 신규 생성** | 블로그에 없는 장면 (특수 상황 · 클로즈업 · 가상 장면) | Replicate `flux-1.1-pro` |
| **공식 보도자료/제품샷** | (수동 수집, 상용 라이선스 확인 후) | 회사 IR/보도자료 페이지 |

**Flux 생성 규칙**: 출력 경로는 **반드시 `sns/assets/{code-or-ticker}-{slug}/{semantic}.webp`**. 포스트 폴더(`posts/`, `carousels/`, `reels/`, `shorts/`)에 직접 쓰지 않는다.

## index.json — similarTo 체인

자동 생성되는 `sns/assets/index.json`은 회사 간 자산 재사용 허용을 위한 lookup.

```json
{
  "version": 1,
  "generatedAt": "2026-04-16T12:00:00Z",
  "companies": {
    "267260-hd-hyundai-electric": {
      "displayName": "HD현대일렉트릭",
      "market": "KOSPI",
      "similarTo": ["058850-ls-electric"],
      "assets": ["thumbnail.webp", "power-grid.webp", "transformer-factory.webp", "bg-hook-industrial.webp"]
    },
    "meta-meta-platforms": {
      "displayName": "Meta Platforms",
      "market": "NASDAQ",
      "similarTo": ["googl-alphabet"],
      "assets": ["datacenter.webp", "ad-network.webp"]
    }
  }
}
```

렌더 스크립트가 자사 자산 부족 시 `similarTo` 체인 1-hop 참조 허용 (2-hop 금지 — 무분별 재사용 방지).

## 포맷별 소비 경로

Remotion은 `remotion-sns/public/` 에서 `staticFile()` 로 로드한다. 각 포스트 렌더 직전 공유 자산을 `public/{post}/` 로 **복사**한다 (symlink가 안 되는 OS 고려).

```
sns/assets/267260-hd-hyundai-electric/power-grid.webp
    ↓ (copy at render time)
sns/remotion-sns/public/005-267260-hd-hyundai-electric/power-grid.webp
    ↓ hook.json "bgImage": "005-267260-hd-hyundai-electric/power-grid.webp"
    ↓
Remotion HookCard (staticFile)
```

hook.json / short.json / reel.json 의 `bgImage` 는 여전히 `{post}/{name}.webp` 로 쓰되, 원본은 `sns/assets/` 에서 관리.

## 렌더 전 sync

```bash
python sns/scripts/sync_assets.py <post-folder>
# 또는
python sns/scripts/render_carousel.py <post-folder>   # sync 포함 실행 권장
```

`meta.json` (선택) 에 `sourceCompany: "267260-hd-hyundai-electric"` 를 두면 render 스크립트가 `sns/assets/` → `public/` 을 자동 sync.

## 중복 방지 원칙

- **같은 기업·같은 장면**: 한 번만 Flux 생성. 캐러셀·릴스·쇼츠·영상 모두 이 하나를 공유.
- **생성 전 반드시 assets/ 폴더 확인.** 이미 있으면 재생성 금지. Replicate 요금 낭비.
- **블로그 자산 먼저 확인** — `sns/scripts/ingest_blog.py`로 블로그 자산을 먼저 흡수한 뒤 부족할 때만 Flux.
- Flux 프롬프트를 파일명 + 해시 맵으로 관리하면 "같은 개념 다른 파일명" 실수를 줄인다.

## 블로그 ↔ sns 양방향 규칙

- **블로그 → sns**: 일방향 흡수. `sns/scripts/ingest_blog.py`로 블로그 포스트 지정 시 자산을 `sns/assets/{key}-{slug}/`로 의미명 리네이밍 복사.
- **sns → 블로그**: 불가. 블로그 mdsvex는 `./assets/` 상대경로 기반. 외부 참조는 public 배포에서 깨짐. 블로그용 자산은 블로그 폴더 내에 별도 보관.

## 관련 문서

- 캐러셀: [INSTAGRAM.md](INSTAGRAM.md), [CAROUSEL_DESIGN.md](CAROUSEL_DESIGN.md), [TUTORIAL_CAROUSEL.md](TUTORIAL_CAROUSEL.md)
- 쇼츠: [SHORTS.md](SHORTS.md)
- 릴스: [REELS.md](REELS.md)
- 영상: [video/PHILOSOPHY.md](video/PHILOSOPHY.md), [video/PIPELINE.md](video/PIPELINE.md)
- 블로그 → 영상 변환: [BLOG_TO_VIDEO.md](BLOG_TO_VIDEO.md)
- 업로드: [UPLOAD_PLAYBOOK.md](UPLOAD_PLAYBOOK.md)
