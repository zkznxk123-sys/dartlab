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

### 이미지가 부실할 때 — 저작권 없는(CC0/PD) 이미지 가져오는 곳
회사 카드 이미지가 모자라거나 부실하면 아래 두 길로 **저작권 의무 0** 이미지를 받아 `sns/assets/{code}/` 에 채운다.
받은 뒤 `build_index.py` → `publish_assets_hf.py` 로 올리고, 슬라이드에서 `image: <이름>` 으로 가리키면 끝(별도 배선 없음).

1. **스톡 (CC0/PD) — `fetch_cc0_images.py`**: Wikimedia Commons(실사 적중률 1순위) + Openverse 에서 PD/CC0 만 받는다.
   `cc0-*.webp` 로 저장. 출처는 회사 폴더 `CREDITS.md` 에 자동 기록(의무 아니나 감사 추적).
   ```
   uv run python -X utf8 blog/_scripts/fetch_cc0_images.py --jobs sns/assets/_plans/cc0FetchJobs.json
   ```
   jobs = `[{"code","name","queries":[...],"keywords":[...]}]`. **반드시 받은 이미지를 눈으로 확인** —
   스톡은 특정 회사 피사체(정유탑·병입라인 등) 적중률이 들쭉날쭉해 오매치가 섞인다(실측: 받은 것 중 절반은 폐기).
2. **생성형 (주제 정확) — `gen_company_flux.py`**: Replicate FLUX 로 4:5 hero 를 생성. 특정 피사체 적중률 1순위.
   비용 사전충전이며 잔액 있을 때만 동작(잔액 부족 = HTTP 402). jobs = `[{"code","name","prompt"}]`.

> 원칙: 스톡(CC0/PD)이 1차(공짜·합법), 안 맞으면 생성형. 둘 다 받은 즉시 눈검수 후 채택. 출처는 `CREDITS.md` 에 남긴다.

## 도구
| 파일 | 역할 |
|---|---|
| `blog/_scripts/build_carousel_contracts.py` | **발행** — blog frontmatter → hfMedia 단일 파일 |
| `blog/_scripts/audit_seo.py` | carousel 형식·숫자 검사 |
| `blog/_scripts/migrate_carousels_to_blog.py` | 1회성 이관(sns/carousels → blog frontmatter, **완료**) |
| `blog/_scripts/test_carousel_contracts.py` | 발행/이관 테스트 |

설계 SSOT: `mainPlan/blog-carousel-ssot/01-unified-slug-ssot.md`
