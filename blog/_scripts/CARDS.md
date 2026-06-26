# 카드(캐러셀) 배포 — 운영 절차

/ cards 와 터미널 「카드뉴스」에 뜨는 인스타식 카드. 짧게 정리.

## 카드는 어디서 오나
- **손글 SSOT = 블로그 글 frontmatter 의 `carousel:` 블록.** (`blog/05-company-reports/{글}/index.md`)
- 화면은 hfMedia `carousels/index.json` **한 파일**을 읽어 그때그때 그린다(**안 굽는다**·디자인은 코드가 정함).
- 같은 회사 다른 주제 글이면 각자 `carousel:` → **자동으로 여러 편**(1:N).

## 카드 새로 올리기 — 3단계
1. 블로그 글 frontmatter 에 `carousel:` 쓴다 (아래 형식).
2. (선택) 검사: `uv run python -X utf8 blog/_scripts/audit_seo.py`  ← 형식·숫자 점검
3. 발행: `uv run python -X utf8 blog/_scripts/build_carousel_contracts.py`
   - hfMedia 에 `carousels/index.json` **한 파일** 올림(옛 파일 자동 삭제).
   - `/cards` 새로고침하면 뜬다. **사이트 재빌드 불필요**(데이터만 올림).
   - `--dry-run` 붙이면 *올릴 것·지울 것*만 미리 본다.

> `HF_TOKEN` 은 `.env` 에 있음(따로 입력 안 함).

## `carousel:` 형식 (예)
```yaml
carousel:
  title: "인스타 제목"
  caption: |
    설명 산문 첫 문단.

    둘째 문단.
  pinnedComment: "근거·면책 한 줄"
  slides:
    - layout: editorial         # 표지
      line: "큰 글씨 한 줄"
      sub: "받침 문장"
      image: imagegen-xxx       # 이미지 '이름'만(hfMedia 에서 실제 파일 찾음)
    - layout: editorialStat     # 큰 숫자
      kicker: "라벨"
      bigNumber: "100"
      unit: "억개"
      context: "설명"
    - layout: editorialBeat     # 헤드라인 비트
      kicker: "라벨"
      line: "한 줄"
      sub: "받침"
```
- layout 은 **3종만**: `editorial`(표지) · `editorialStat`(큰 숫자) · `editorialBeat`(비트).
- 슬라이드 숫자는 본문에 있는 숫자만(없는 숫자 쓰면 audit 가 경고).

## 화면(코드)도 바꿨을 때
- slides 텍스트만 바꿈 → 위 3단계로 끝(데이터만).
- 읽기측 코드/디자인을 바꿈 → **landing push 로 사이트 배포**(공개 화면이라 운영자 눈검수 후).

## 이미지
- 슬라이드는 이미지를 **이름**으로만 가리킴 → 실제 파일은 hfMedia `companies/{code}/` 에서 찾음.
- 이미지 마음에 안 들면 **계약 안 건드리고 hfMedia 이미지만 교체**하면 됨.
- 로컬 원본 = `sns/assets/{code}/{name}.webp` → `build_index.py` 인덱싱 → `publish_assets_hf.py` 가 hfMedia 업로드.
  파일명에 `card`/`thumbnail`/`og-` 토큰만 없으면 hero 로 자동 채택(별도 등록 불필요).

### 이미지 점검 — 쓰레기(평면 벡터·도식·인포그래픽) 먼저 잡기
생성형 hero 중 일부가 실사가 아니라 **평면 도식·막대그래프·텍스트 카드**로 나와 흑백 풀블리드 배경으로 깨진다.
발행 전·수시로 전수 스캔한다. 색복잡도(평면≈수십 색, 실사≈수천 색)로 의심을 잡고 **반드시 눈으로 한 장씩 확정**한다
(자동 판정 아님 — 야간 정유탑·검은 분말 같은 어두운 실사도 같이 잡힌다).
```
uv run python -X utf8 blog/_scripts/audit_carousel_images.py            # 색<600 또는 이름패턴 의심 목록
uv run python -X utf8 blog/_scripts/audit_carousel_images.py --max 250  # 평면 벡터/도식에 집중
```

### 이미지 가져오는 곳 — 저작권 없는(무료) 소스만
⛔ **핀터레스트·구글 이미지 금지** — 거기 올라온 사진은 대부분 **저작권 있음**(긁어온 것)이라 가져다 쓰면 침해다.
아래 무료 소스만 쓴다.
- **Wikimedia Commons / Openverse** — PD/CC0 (귀속 의무 0). `fetch_cc0_images.py` 가 이 둘에서만 받는다.
- 보강 여지(필요 시 API 키로 추가): **Unsplash·Pexels·Pixabay**(무료 라이선스·상업 OK), **NASA·각국 공공기관**(PD).

회사 카드 이미지가 모자라거나 부실하면 아래 두 길로 받아 `sns/assets/{code}/` 에 채운다.
받은 뒤 `build_index.py` → `publish_assets_hf.py` 로 올리고, 슬라이드에서 `image: <이름>` 으로 가리키면 끝(별도 배선 없음).

1. **스톡 (CC0/PD) — `fetch_cc0_images.py`**: Commons(실사 적중률 1순위) + Openverse 에서 PD/CC0 만 받아 `cc0-*.webp` 저장.
   출처는 회사 폴더 `CREDITS.md` 에 자동 기록(의무 아니나 감사 추적).
   ```
   uv run python -X utf8 blog/_scripts/fetch_cc0_images.py --jobs sns/assets/_plans/cc0FetchJobs.json
   ```
   jobs = `[{"code","name","queries":[...],"keywords":[...]}]`. **반드시 받은 이미지를 눈으로 확인** —
   스톡은 특정 피사체(정유탑·병입라인 등) 적중률이 들쭉날쭉해 오매치(엉뚱한 사진·텍스트 광고·도식)가 섞인다(실측: 받은 것 절반 폐기).
2. **생성형 (주제 정확) — `gen_company_flux.py`**: Replicate FLUX 로 4:5 hero 생성. 특정 피사체 적중률 1순위.
   비용 사전충전이며 잔액 있을 때만 동작(잔액 부족 = HTTP 402). jobs = `[{"code","name","prompt"}]`.

> 원칙: 스톡(무료 PD/CC0)이 1차, 안 맞으면 생성형. **둘 다 받은 즉시 눈검수 후 채택**(쓰레기 거르기). 출처는 `CREDITS.md` 에.

## 발행 전 전문가 검토 게이트 — 작가 패널 토론·평가
**캐러셀은 공개물이라 발행 전에 전문가 검토를 반드시 거친다.** 자동 통과 금지.
1. **작가 패널 토론** — 서로 다른 렌즈(훅 강도·서사·디자인/이미지 적합성·정직성)로 독립 검토 후 토론으로 약점 합의.
2. **정직성·근거 평가** — 본문 숫자가 전부 `## 검증표`에 있는가, 외부/실측이 분리됐나, 과장·투자권유 표현 없나.
3. **이미지 적합성 평가** — 위 색복잡도 감사 통과 + 주제 적합 + 눈검수 완료(쓰레기·텍스트·도식 0).
4. **평가 점수**가 기준 미달이면 발행 보류·수정. (점수는 실가치 proxy 가 아니라 게이트 — 미빌드 점수 인플레 금지.)

> 운영자 검토 흐름: 큰 변경·신규편은 위 패널을 거쳐 합의된 수정 반영 후에만 `build_carousel_contracts.py` 발행.

## 도구
| 파일 | 역할 |
|---|---|
| `blog/_scripts/build_carousel_contracts.py` | **발행** — blog frontmatter → hfMedia 단일 파일 |
| `blog/_scripts/audit_carousel_images.py` | **이미지 감사** — 평면 벡터·도식·인포그래픽(쓰레기) 색복잡도로 탐지 |
| `blog/_scripts/fetch_cc0_images.py` | 무료(PD/CC0) 이미지 수급 — Commons·Openverse |
| `blog/_scripts/gen_company_flux.py` | 생성형 hero(4:5) — 잔액 충전 시 |
| `blog/_scripts/audit_seo.py` | carousel 형식·숫자 검사 |
| `blog/_scripts/migrate_carousels_to_blog.py` | 1회성 이관(sns/carousels → blog frontmatter, **완료**) |
| `blog/_scripts/test_carousel_contracts.py` | 발행/이관 테스트 |

설계 SSOT: `mainPlan/blog-carousel-ssot/01-unified-slug-ssot.md`
