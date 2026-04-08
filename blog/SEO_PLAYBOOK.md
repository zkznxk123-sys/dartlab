# Blog SEO Playbook

블로그 글 단위 SEO 체크리스트. 인프라(robots/sitemap/JsonLd)는 이미 갖춰져 있고, 이 문서는 **개별 글 한 편이 검색/AI 인용에서 잡히게** 만드는 조치 모음.

관련 문서:
- 글 단위 품질: [QUALITY_STANDARDS.md](QUALITY_STANDARDS.md)
- dartlab 데이터: [DARTLAB_USAGE.md](DARTLAB_USAGE.md)

---

## 1. 현재 인프라 (이미 갖춰진 것 — 건드리지 않음)

| 항목 | 위치 | 상태 |
|---|---|---|
| robots.txt | `landing/static/robots.txt` | ✅ AI(GPTBot/ClaudeBot/PerplexityBot 등) + Google + 네이버 다 허용 |
| sitemap.xml | `landing/static/sitemap.xml` | ✅ 카테고리/시리즈 페이지 포함, prerender |
| JSON-LD | `landing/src/lib/seo.ts` | ✅ Article + Breadcrumb + FAQ |
| og:image | 1200×630 | ✅ 글로벌 `og-image.png` 공용 (개선 여지 — §5) |
| twitter:card | summary_large_image | ✅ |
| article:published_time | frontmatter date 사용 | ✅ |
| article:author | "eddmpython" | ✅ |
| 카테고리/시리즈 메타 페이지 | `/blog/category/*`, `/blog/series/*` | ✅ |

새 글 추가 시 인프라는 자동 동작. 운영자가 신경 쓸 건 글 단위 콘텐츠 시그널.

---

## 2. 글 단위 SEO 체크리스트 (12개)

### 제목 (≤60자)

- 검색형 질문 또는 판단 문장
- 회사명만 + "분석" 같은 일반어 단독 금지
- "전자공시" 키워드 자연 포함 권장 (네이버 검색 매칭)
- 60자 넘으면 검색 결과에서 잘림

```
✅ 좋음: SK하이닉스 (000660) — 한국 반도체 30년의 미스터리, 그리고 영업이익률 58%
✅ 좋음: 두산에너빌리티 (034020) — 부채비율 305%에서 129%까지, 9년 다이어트의 진짜 모습
❌ 나쁨: SK하이닉스 분석
❌ 나쁨: 두산에너빌리티 리뷰
```

### description (≤160자)

- 글의 핵심 결론을 한 줄로
- 첫 2문단 후킹과 일관
- 검색 결과 스니펫에 그대로 노출됨
- 160자 넘으면 잘림

### slug

- 영문 케밥-케이스
- 회사명(또는 핵심 키워드) + 한두 단어
- URL에 노출되므로 짧고 명확하게

```
✅ 좋음: 01-000660-skhynix (카테고리 폴더), URL: /blog/skhynix
❌ 나쁨: sk-hynix-detailed-financial-analysis-30-years
```

### frontmatter `tags` (신규 도입 — 2026-04-08)

검색·필터링용 5~8개 태그. 회사명, 종목코드, 산업, 핵심 키워드.

```yaml
tags:
  - SK하이닉스
  - 000660
  - 반도체
  - HBM
  - 메모리 사이클
  - 가격결정력
```

`landing/src/lib/blog/posts.ts`가 frontmatter `tags`를 읽어 검색/필터에 노출. (구현 별도 plan)

### 본문 H2 구조

- H1(제목)이 던진 핵심 질문에 H2들이 단계적으로 답하는 흐름
- H2 텍스트가 그대로 검색 가능한 한국어 문장
- 영문 H2 금지
- 같은 글 안에 H2 5~8개 권장

H2 자체가 GEO/SGE에서 인용 단위가 된다. "5막 — 어떻게 영업이익률이 -67%에서 +58%로 갔나" 같은 H2는 그대로 LLM이 발췌한다.

### 첫 2문단 (200~300자)

- 글의 핵심 답변이 들어가야 함
- Featured Snippet과 LLM 인용 대상
- "안녕하세요", "오늘은", "이번 글에서는" 같은 도입부 금지
- 첫 문장이 후킹 한 줄

```
✅ 좋음: 1983년 어느 날, 현대그룹 정주영 회장은 새 사업을 시작하기로 했다. 메모리 반도체였다.
❌ 나쁨: 안녕하세요. 이번 글에서는 SK하이닉스의 30년 역사를 살펴보겠습니다.
```

### 내부 링크 ≥3

- 같은 카테고리의 다른 글
- 같은 시리즈의 인접 글
- 같은 회사의 다른 각도 글 (있으면)
- 시리즈 정의 페이지 (`/blog/series/{id}`)
- 핵심 운영 문서 (DARTLAB_USAGE.md 등 — 단, 외부 사용자가 볼 수 없는 운영 문서는 제외)

내부 링크는 주제 권위(topical authority) 시그널. 같은 카테고리 안에서 글이 서로를 가리키면 검색 엔진이 "이 사이트는 이 주제의 권위 사이트"로 본다.

### 외부 출처 ≥3

- 보도 (신문/뉴스)
- 공식 문서 (회사 IR, SEC, 정부)
- 위키 (Wikipedia/나무위키)

신뢰도 시그널. 본문 안에 직접 링크.

### 이미지 alt 텍스트

- 단순 설명 (`"SK 하이닉스 칩 사진"`) 금지
- **figcaption 첫 줄과 동일한 본문 한 줄** (예: "정주영 명예회장 1998 — 70억 자본금으로 메모리 회사를 세웠다")
- 한글 OK
- 이미지 검색에서 잡힘

### 표 캡션 / 코드블록

- 표 위에 한 단락(2~4문장)으로 표가 보여주는 한 줄을 설명
- 표 아래에 한 줄 풀이 (`표시: **5,221** = 4년 만에 첫 증액`)
- 코드블록은 dartlab 호출을 그대로 (독자가 복사 → 실행 가능해야 함)

### 단락당 한 사실

- 한 문단에 한 사실만
- AI가 인용할 때 단락 단위로 잘림
- 너무 긴 단락(200자+)은 둘로 쪼갬

### 시간 표기

- "YYYY년 Q분기" 또는 "YYYY-MM-DD" 통일
- "작년", "지난주" 같은 상대 표현 금지 (글이 오래되면 깨짐)
- "2025Q4", "2026-04-08" OK

### 종목 코드 / 회사 식별자

- 첫 100자 안에 종목 코드 + 한국어 회사명 + (가능하면) 시장 (KOSPI/KOSDAQ)
- 검색 매칭 + AI 식별

```
✅ "SK하이닉스 (000660) — 한국 반도체 30년의 미스터리, 그리고 영업이익률 58%"
```

---

## 3. GEO/SGE/LLM 친화 조치

검색 엔진(Google/네이버)뿐 아니라 AI 답변(ChatGPT/Perplexity/Gemini)에서 인용되도록.

### 한 단락에 한 사실

LLM은 단락을 인용 단위로 자른다. 한 단락에 두 사실이 있으면 둘 다 인용되지 않거나, 잘린 채 인용된다.

```
❌ 나쁨 (한 단락에 5사실):
SK하이닉스는 1983년 정주영이 세웠고, 2001년 채권단 관리를 받았으며, 2012년 SK가 인수했고, 2025년 영업이익 47조를 벌었으며, 2025Q4 분기 영업이익률 58%를 찍었다.

✅ 좋음 (단락 분리):
1983년 정주영이 현대전자를 세웠다.
2001년 채권단 관리에 들어갔다.
2012년 SK텔레콤이 3조 4,267억에 인수했다.
2025년 영업이익 47.21조원, 모회사 삼성전자(43.6조)를 사상 처음 추월했다.
2025Q4 분기 영업이익률은 58.40%였다.
```

### 표 헤더 = 검색 가능한 한국어 명사

표 헤더가 그대로 검색 키워드. 영문/약어 단독 금지.

```
✅ 좋음: 매출액 / 영업이익 / 당기순이익 / 부채비율
❌ 나쁨: Sales / OP / NI / D/E
```

### dartlab 자체 출력은 코드블록으로 명시

LLM은 코드블록을 "출처"로 인식한다. dartlab의 자체 분석 결과를 본문에서 인용할 때:

````markdown
```python
c.analysis("financial", "수익성")["roicTree"]["history"][0]
# {'period': '2025', 'roic': 36.13, ..., 'marginDriver': '높은 가격결정력 (매출총이익률 > 40%)'}
```
````

이렇게 박으면 LLM이 "dartlab의 분석에 따르면 SK하이닉스의 marginDriver는 '높은 가격결정력'"으로 인용한다. 그냥 풀어 쓰면 인용 안 됨.

### llms.txt에 핵심 글 노출 (별도 plan)

`landing/static/llms.txt`는 AI 크롤러용 사이트맵. 회사 종합편 같은 핵심 글의 요약·URL을 직접 노출하면 AI 답변에서 인용 빈도가 올라간다.

현재 llms.txt는 자동 생성(`scripts/generateSpec.py`). 회사 종합편을 거기에 추가하는 건 별도 plan에서.

---

## 4. 회사명 SEO 강화 패턴

회사 종합편 글의 일관 패턴 (모든 회사 글이 따른다):

### 제목

```
{한국어 회사명} ({종목코드}) — {핵심 후킹 한 줄}
```

예:
- SK하이닉스 (000660) — 한국 반도체 30년의 미스터리, 그리고 영업이익률 58%
- 두산에너빌리티 (034020) — 부채비율 305%에서 129%까지, 9년 다이어트의 진짜 모습
- 삼양식품 (003230) — 라면 빅3 꼴등이 매출 2.3조 글로벌 식품 거인이 되기까지

### description

```
{핵심 사실 한 줄}. {반전 또는 메커니즘 한 줄}.
```

### frontmatter

```yaml
title: ...
date: YYYY-MM-DD
description: ...
category: company-reports
series: company-reports
seriesOrder: N
stockCode: "000660"            # 회사 글 한정
corpName: "SK하이닉스"          # 회사 글 한정
storyTemplate: "장기 사이클"     # 6막 템플릿 키
grade: "dCR-AA"                # 회사 글 한정
tags:                           # 신규
  - SK하이닉스
  - 000660
  - 반도체
  - HBM
  - 가격결정력
  - 메모리 사이클
thumbnail: /avatar-chart.png
youtubeId: ""
```

### 첫 2문단

- 1막 시작 또는 핵심 한 줄 위에
- 종목 코드 + 회사명 + 시장 + 핵심 후킹 1개
- 100자 이내에 위 4가지가 다 나와야 함

---

## 5. OG 이미지 — 글마다 자체 생성 (개선 사항)

현재는 모든 글이 글로벌 `og-image.png`(1200×630) 공용. 이건 검색 결과 카드/소셜 공유 카드에서 모든 글이 같은 썸네일로 나옴 → 클릭률 낮음.

권장 개선 (별도 plan):

1. 글마다 자체 OG 이미지 생성
   - SVG → PNG 변환, 1200×630
   - 제목 + 핵심 숫자 1개 + 회사 로고 또는 색
2. frontmatter에 `ogImage: ./assets/01-og-skhynix.png` 추가
3. `landing/src/routes/blog/[slug]/+page.svelte`에서 frontmatter ogImage 우선, 없으면 글로벌 fallback

이 작업은 글 14편이 안정화된 후 별도 plan으로.

---

## 6. 카테고리 단위 SEO

`/blog/category/company-reports` 페이지의 제목·description·H1이 카테고리 핵심 키워드를 담고 있어야 한다.

현재:
- 카테고리 라벨: "기업분석 보고서"
- URL: `/blog/category/company-reports`

개선 권장:
- 카테고리 description에 "DartLab으로 본 한국 상장사 9년 재무 서사 — 6막 인과 구조" 같은 일관 패턴
- 카테고리 H1 = 라벨, H2 = "이 카테고리가 답하는 질문 5가지"
- 검색 키워드: "기업분석", "재무 서사", "전자공시 분석"

이 부분은 `landing/src/routes/blog/category/[category]/+page.svelte` 손봐야 함 → 별도 plan.

---

## 7. 발행 후 검증

글 발행 후 1~2주 뒤 다음을 확인:

- Google Search Console — 노출/클릭 수, 검색 키워드, CTR
- 네이버 검색 — "회사명 + 전자공시" 키워드로 글이 잡히는지
- 직접 검색 — Perplexity/ChatGPT/Gemini에서 회사명으로 물었을 때 우리 글이 출처로 인용되는지

CTR이 낮으면 제목/description 재작성. 노출이 0이면 키워드 매칭 재검토.

---

## 8. 현재 인프라 한계 (다음 plan 후보)

| 한계 | 다음 plan |
|---|---|
| OG 이미지 글로벌 공용 | 글마다 자체 OG 생성 |
| llms.txt에 블로그 글 미반영 | generateSpec.py 확장 |
| frontmatter `tags` 미렌더 | posts.ts + 태그 페이지 라우트 |
| 카테고리 페이지 SEO 메타 약함 | category/[category]/+page.svelte 강화 |
| 회사명 한영 동시 매칭 (SK하이닉스 / SK Hynix) | frontmatter `corpNameEn` 추가 + JsonLd alternateName |
| 검색 결과 페이지 (sitemap에 없음) | `/blog/search` 라우트 |

이 한계들은 글 14편이 안정화된 후 분리 plan으로 다룬다.
