# notebooks 정책 — Colab vs Marimo

**주체**: 노트북 배포 (`notebooks/colab/*.ipynb` + `notebooks/marimo/*.py`).
**현재**: 두 포맷 동일 내용 유지 · 마크다운 설명 전략 포맷별 분리 · 코드 셀 상단 짧은 주석 1 줄.
**방향**: marimo 인터랙티브 셀 확대 · Colab 배지 자동 삽입 · 노트북↔docs 교차 링크.

`notebooks/colab/*.ipynb` 와 `notebooks/marimo/*.py` 는 **같은 내용** 을 두 포맷으로 유지한다. 단, 마크다운 처리 차이가 있어 **포맷별 설명 전략이 다르다**. 각 섹션은 **"이렇게 한다"** 명제로 열고, 반복된 실수는 섹션 하단 **"반복 실패"** 에 정리한다.

---

## 1. 설명 전략 — Colab 은 마크다운 허용, Marimo 는 주석으로만

| 포맷 | 마크다운 설명 셀 | 주석 |
|---|---|---|
| **Colab** (`.ipynb`) | **허용 — 간결하게 조금** | 코드 셀 맨 위 짧은 주석 1 줄 |
| **Marimo** (`.py`) | **쓰지 않는다** | 코드 셀 맨 위 짧은 주석 1 줄 |

**왜**: 마리모 노트북은 `.py` 텍스트 한 셀로 마크다운을 렌더하는 UX 가 약하다 (별도 `mo.md(...)` 호출 필요, 편집 모드에선 plain text). 반면 콜랩은 마크다운 셀이 네이티브로 렌더되고 설명 가독성이 높다.

- **Colab 은 마크다운 셀로 섹션 설명** — 학습·공유용 독자가 맥락을 빠르게 잡게.
- **Marimo 는 코드만** — 실습·실행용. 설명은 코드 옆 짧은 주석으로.

**적용**: 셀 구성 (코드 셀 개수·순서) 과 코드 내용은 **두 포맷이 동일**. Colab 만 그 위에 마크다운 설명 셀을 듬성듬성 추가한다.

---

## 2. Colab 마크다운 분량 — 3~4 코드 셀마다 1 마크다운으로 간다

- 노트북 최상단 1 장: 제목 + 한 줄 요약 + "이 노트북에서 다루는 것" 2~3 줄.
- 주요 섹션 전환점에만 1 장씩 — **3~4 코드 셀마다 1 마크다운**.
- 한 마크다운 셀 길이 **2~4 줄**.
- "왜 이 코드를 쓰는가" 중심. "이 코드가 뭘 하는지" 는 주석으로.

**반복 실패** — 코드 셀마다 마크다운 추가 / 한 마크다운에 문단 여러 줄 장황한 설명 / "이 코드는 ~ 한다" 식 반복 서술.

---

## 3. Marimo 노트북 — 코드 셀 + 첫 줄 한글 주석으로 간다

- `# /// script` 헤더 + `import marimo` + `app = marimo.App(...)` 그대로.
- 각 셀은 `@app.cell` 함수. 함수 첫 줄에 짧은 한글 주석 1 줄이 설명 역할.
- `mo.md(...)` 호출은 쓰지 않는다. 예외: 사용자가 `mo.md` 도구 시연을 위해 명시적으로 요청한 경우만.

---

## 4. 공통 — 같은 코드·같은 순서로 동기화한다

- 두 포맷은 **같은 코드·같은 순서** 유지. 셀 추가·삭제가 한쪽만 바뀌면 다른 쪽도 동기화.
- API 키가 필요한 셀은 주석으로 전제조건 표시 (예: `# AI provider 키 필요 (GEMINI_API_KEY)`).
- 결과가 큰 출력 (`c.show(...)` 테이블 등) 은 **한 셀에 한 호출**. 여러 결과를 한 셀에 몰지 않는다.

**반복 실패** — Marimo 만 셀 추가해놓고 Colab 동기화 누락. 한 셀에 여러 `c.show()` 몰아 넣어 출력 겹침.

---

## 5. 파일 매핑

| 순번 | 주제 | Marimo | Colab |
|---|---|---|---|
| 01 | Company — 종목코드 하나, 재무제표·공시 | `marimo/01_company.py` | `colab/01_company.ipynb` |
| 02 | gather — 가격·수급·매크로·뉴스 | `marimo/02_gather.py` | `colab/02_gather.ipynb` |
| 03 | scan — 전종목 횡단 | `marimo/03_scan.py` | `colab/03_scan.ipynb` |
| 04 | quant — 25 지표 + 9 신호 | `marimo/04_quant.py` | `colab/04_quant.ipynb` |
| 05 | analysis — 14 축 + 전망·가치평가 | `marimo/05_analysis.py` | `colab/05_analysis.ipynb` |
| 06 | macro — 사이클·금리·자산 | `marimo/06_macro.py` | `colab/06_macro.ipynb` |
| 07 | credit — dCR 7 축 등급 | `marimo/07_credit.py` | `colab/07_credit.ipynb` |
| 08 | story — 구조화 보고서 | `marimo/08_review.py` | `colab/08_review.ipynb` |
| 09 | ai — ask · chat | `marimo/09_ai.py` | `colab/09_ai.ipynb` |
| 10 | search — 공시 검색 | `marimo/10_search.py` | `colab/10_search.ipynb` |
| 11 | listing — 법인·공시 목록 | `marimo/11_listing.py` | `colab/11_listing.ipynb` |

---

## 6. 실행 경로

- **Colab**: `https://colab.research.google.com/github/eddmpython/dartlab/blob/master/notebooks/colab/{file}`
- **Molab**: `https://molab.marimo.io/github/eddmpython/dartlab/blob/master/notebooks/marimo/{file}`
- **로컬 Marimo 편집**: `uv run marimo edit notebooks/marimo/{file}` — 진입점. 새 노트북 작업도 여기서 시작.

---

## 7. 신규 노트북 — 4 단계로 추가한다

1. Marimo 먼저 작성 — 셀 구성·코드 확정.
2. 동일한 코드 셀 구성으로 Colab 작성 + 마크다운 설명 셀 **3~4 코드 셀당 1 개** 삽입.
3. `notebooks/STATUS.md` + `ops/notebooks.md` 파일 매핑 표 갱신.
4. 랜딩 Notebooks 섹션 (`landing/src/lib/components/sections/Notebooks.svelte`) 목록 갱신.

---

## 요약 — 명제 5 줄

1. Colab 은 마크다운 허용 (3~4 코드 셀당 1 개), Marimo 는 주석으로만 간다.
2. Colab 마크다운은 한 셀 2~4 줄, "왜 이 코드를 쓰는가" 중심.
3. Marimo 는 `@app.cell` + 첫 줄 한글 주석, `mo.md()` 는 쓰지 않는다.
4. 두 포맷 같은 코드·같은 순서 유지, 셀 변경 시 양쪽 동기화.
5. 신규 노트북은 Marimo → Colab → STATUS → 랜딩 4 단계로 추가한다.
