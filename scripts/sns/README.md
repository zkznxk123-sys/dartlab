# dartlab-sns — Instagram 캐러셀 파이프라인

블로그 `blog/05-company-reports/*` 한 편에서 **사람이 흥미로울 만한 꼭지 1개**를 뽑아
5장짜리 Instagram 캐러셀(1080x1350) + 캡션 2,200자를 만든다.

블로그/영상 CTA로 dartlab 전체 생태계 유입을 만드는 게 목표.

## 폴더 분리

```
scripts/sns/              ← COMMIT (파이프라인 코드)
dartlab-sns/              ← GITIGNORE (렌더 산출물만)
```

## 5장 구조 (고정)

| # | 카드 | 목적 |
|---|------|------|
| 1 | HookCard | 한 줄 후크 + Flux 배경 |
| 2 | ContextCard | 왜 흥미로운가 (질문형) |
| 3 | ChartCard | 핵심 숫자 1개 큰 글자 + 비교 막대 |
| 4 | InsightCard | 1문장 결론 + 2~3줄 근거 |
| 5 | CtaCard | 블로그 / YouTube / GitHub 링크 |

## "사람 흥미" 후크 6패턴

재무지표 자체가 아닌 **감정적·인간적** 프레이밍:

1. **불평등/권력** — "순이익 7배를 배당으로"
2. **의외의 규모** — "보일러 만드는 회사가 세계 1위"
3. **역사 아이러니** — "5번 죽을 뻔한 회사"
4. **지리/문화 격차** — "인도에서 번 돈 vs 한국"
5. **라이프스타일 밀착** — "라면 1봉지당 가져가는 돈"
6. **인물/창업 서사** — "사모펀드가 10년간 쥐어짠 것"

## 사용법

### 1. 수동 생산 (MVP)

```bash
# 1. 한 편에 대한 hook.json + caption.txt 를 수작업으로 작성
#    (dartlab-sns/posts/001-018880-hanon-systems/ 아래)

# 2. Flux 배경 이미지 생성 (선택)
python scripts/sns/generate_flux.py --post 001-018880-hanon-systems

# 3. Remotion 5장 렌더
bash scripts/sns/render_carousel.sh 001-018880-hanon-systems

# 결과:
#   dartlab-sns/posts/001-018880-hanon-systems/carousel/01-hook.png ... 05-cta.png
```

### 2. 자동 생산 (Phase 3 이후)

```bash
# 블로그 → 후크 후보 추출 (Claude API)
python scripts/sns/extract_hook.py blog/05-company-reports/17-018880-hanon-systems

# 후크 → 캡션
python scripts/sns/build_caption.py dartlab-sns/posts/001-018880-hanon-systems/hook.json
```

## 파일 구조 (산출물)

```
dartlab-sns/posts/{NNN}-{stockCode}-{slug}/
├── hook.json            # { hook, pattern, whyInteresting, numbers, insight, cta }
├── flux/                # Flux 생성 배경 (선택)
│   └── bg-hook.webp
├── carousel/            # Remotion 렌더 결과
│   ├── 01-hook.png
│   ├── 02-context.png
│   ├── 03-chart.png
│   ├── 04-insight.png
│   └── 05-cta.png
├── caption.txt          # 인스타 본문 2,200자 이내
└── meta.json            # { blogSlug, youtubeId, stockCode, publishedAt }
```

## hook.json 스키마

```json
{
  "pattern": "inequality",
  "company": {
    "code": "018880",
    "name": "한온시스템",
    "sector": "자동차부품"
  },
  "hook": {
    "line": "순이익의 7배를 배당으로",
    "sub": "사모펀드가 10년간 쥐어짠 것"
  },
  "context": {
    "question": "어떤 회사가 버는 것의 7배를 주주에게 돌려주는가?",
    "setup": "순이익 267억원. 배당금 1,850억원. 어딘가 이상하다."
  },
  "chart": {
    "title": "2022년 한온시스템",
    "items": [
      { "label": "순이익", "value": 267, "unit": "억원", "highlight": false },
      { "label": "배당금", "value": 1850, "unit": "억원", "highlight": true }
    ],
    "caption": "배당 / 순이익 = 692%"
  },
  "insight": {
    "headline": "배당을 메우려고 빚을 냈다.",
    "body": "2014년 사모펀드 인수 후 총차입금이 4천억에서 4.5조로 11배 급증. 이자비용이 이익을 먹기 시작했고, 2024년 첫 영업적자를 찍었다."
  },
  "cta": {
    "blogSlug": "hanon-systems",
    "youtubeId": "",
    "tagline": "dartlab으로 직접 확인"
  }
}
```

## 링크 생성 규칙

- 블로그: `https://eddmpython.github.io/dartlab/blog/{slug}` ← frontmatter `slug` 없으면 폴더명의 slug 부분
- 유튜브: `https://youtu.be/{youtubeId}` ← frontmatter `youtubeId` 있을 때만
- GitHub: `https://github.com/eddmpython/dartlab`

## 브랜드 컬러 (brand.ts와 동기화)

```ts
primary:     '#ea4647'
primaryDark: '#c83232'
accent:      '#fb923c'
bgDark:      '#050811'
bgCard:      '#0f1219'
text:        '#f1f5f9'
textMuted:   '#94a3b8'
success:     '#34d399'
warning:     '#fbbf24'
```

## Replicate FLUX 모델 (기존 패턴 재사용)

- 모델: `black-forest-labs/flux-1.1-pro`
- aspect_ratio: `"4:5"` (1080x1350 캐러셀용) 또는 `"1:1"` (범용)
- output_format: `"webp"`, quality 90
- rate limit: 분당 6건 → 호출 간 12초 대기

참조: `video/toolkit/projects/015-korea-zinc/generate_flux.py`
