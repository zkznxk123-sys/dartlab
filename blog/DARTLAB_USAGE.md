# DartLab Data Cookbook for Blog Writing

블로그 한 편을 쓸 때 dartlab 데이터를 최대로 뽑는 방법. 미래의 내가 펴 놓고 작업할 cookbook.

관련 문서:
- 글 단위 품질 기준: [QUALITY_STANDARDS.md](QUALITY_STANDARDS.md)
- 자산/SVG 규칙: [ASSET_POLICY.md](ASSET_POLICY.md)

---

## 1. 공통 호출 패턴 8가지

블로그에 자주 등장하는 dartlab 호출. 이 패턴을 그대로 본문 코드블록에 박는다 — 독자가 복사 → 실행 → 검증할 수 있어야 한다.

### 1) IS 9년 시계열 (1년 합산)

```python
import dartlab
c = dartlab.Company("000660")  # SK하이닉스

c.select("IS", ["매출액","매출원가","매출총이익","판매비와관리비","영업이익","당기순이익"])
```

dartlab은 분기 컬럼(`2025Q4`, `2025Q3`, ...)을 반환한다. 1년치 합산이 필요하면 분기를 더한다:

```python
df = c.select("IS", ["매출액"])
row = df.row(0, named=True)
annual = {y: sum(row.get(f"{y}Q{q}", 0) or 0 for q in range(1, 5)) for y in range(2017, 2026)}
```

⚠ "분기 단독값"과 "1년 합산"을 표 안에 절대 섞지 말 것.

### 2) BS Q4 스냅샷

```python
c.select("BS", ["자산총계","부채총계","자본총계","현금및현금성자산","단기금융상품"])
```

BS는 시점 데이터다. 합산하지 말고 각 연도의 Q4 컬럼만 골라낸다:

```python
df = c.select("BS", ["자산총계"])
row = df.row(0, named=True)
snapshots = {y: row.get(f"{y}Q4") for y in range(2017, 2026)}
```

### 3) CF 9년 시계열 + 잉여현금 파생행

```python
c.select("CF", ["영업활동현금흐름","유형자산의 취득","배당금지급"])
```

CF에 들어갈 핵심 파생행: **영업CF − CAPEX = 잉여현금 (FCF)**.

이 한 행이 회사가 영업으로 번 돈만큼 공장을 짓는지, 아니면 곳간까지 깎고 있는지를 한눈에 보여준다. 본문 표에 반드시 포함.

### 4) 비율 분기 시계열

```python
c.select("ratios", ["영업이익률 (%)","매출총이익률 (%)","부채비율 (%)"])
```

`ratios` 토픽은 분기 단위. 본문 표 헤더는 `(분기, %)` 또는 `(Q4, %)`로 명시.

⚠ 같은 비율이 `c.analysis("financial","수익성")["marginWaterfall"]`에서는 1년치로 나온다. 두 출처를 같은 표에 섞으면 거짓이 생긴다.

### 5) 수익성 분석 — marginWaterfall, roicTree, penmanDecomposition

```python
prof = c.analysis("financial", "수익성")

prof["marginWaterfall"]["history"][0]   # 가장 최근 1년치 마진 분해
prof["roicTree"]["history"][0]          # ROIC 트리 (marginDriver 자체 출력)
prof["penmanDecomposition"]["history"]  # Penman RNOA/FLEV/NBC/Spread
```

`marginDriver`는 dartlab 자체 분류이므로 본문에 직접 인용 가능. 인용 시 코드블록으로 명시:

```
"marginDriver": "높은 가격결정력 (매출총이익률 > 40%)"
```

### 6) 자금조달 — capitalOverview vs notesDetail.borrowings (가장 거짓이 많이 났던 자리)

```python
fund = c.analysis("financial", "자금조달")

fund["capitalOverview"]   # 표시용 요약 (총자산/총부채/자기자본/순차입금만)
fund["fundingSources"]["notesDetail"]["borrowings"]  # 차입금 항목별 상세
```

`capitalOverview`의 "순차입금"은 dartlab 내부 정의가 있어 그대로 인용 OK. 단 **"총 차입금"이 필요하면 반드시 `notesDetail.borrowings`의 "합계" 행**을 써야 한다.

지난 라운드 거짓 사례: SK하이닉스 본문 "차입금 8.16조"는 `notesDetail.borrowings`의 "소계, 유동" 행이었다. 진짜 합계는 22.25조 (소계 유동 + 비유동).

### 7) 자본배분 — 배당 (두 출처 차이 주의)

```python
ca = c.analysis("financial", "자본배분")
ca["dividendPolicy"]["history"]  # CF dividendsPaid 1년치 합산

# 별도 출처
c.report.dividend.dps  # 주당 현금배당금 시계열 (DART 정기보고서 기반)
```

두 출처는 다를 수 있다. CF는 자본 재구성/우선주/자기주식 매입까지 포함, report는 보통주 현금배당만. 본문에서 어느 출처를 썼는지 검증표에 명시.

### 8) 신용등급

```python
cr = c.credit("등급")
cr["grade"]                 # "dCR-AA" 등
cr["score"]                 # 0~100 위험점수 (낮을수록 안전)
cr["healthScore"]           # 100 - score
cr["divergenceExplanation"] # dartlab 자체 경고 (직접 인용 OK)
```

---

## 2. 분기 vs 연간 vs Q4 스냅샷 — 단일 라벨 표

| 데이터 종류 | 단위 | 컬럼 | 표 헤더 라벨 |
|---|---|---|---|
| IS (매출/원가/이익) | 1년치 합산 | 연도 | `(1년치 합산, 조원)` |
| IS — 단일 분기 | 분기 단독 | YYQ# | `(분기, 조)` |
| BS (자산/부채/자본) | 시점 스냅샷 | 연도 Q4 | `(Q4 스냅샷, 조원)` |
| CF (영업/투자/재무) | 1년치 합산 | 연도 | `(1년치 합산, 조원)` |
| 비율 (`ratios`) | 분기 | YYQ# | `(분기, %)` |
| marginWaterfall | 1년치 | 연도 | `(1년치 분해, %)` |
| roicTree.history | 1년치 | 연도 | `(1년치, %)` |

**한 표 안에 여러 단위를 절대 섞지 않는다.** 분기 ratios 9개 + 연간 marginWaterfall 1개를 같은 표에 박으면 거짓이 된다.

---

## 3. 표 작성 규칙 (CSS와 정합)

랜딩 빌드는 `landing/src/routes/blog/[slug]/+page.svelte`의 표 CSS로 처리한다. 지난 라운드에 다음을 적용:

- `display: block` + `overflow-x: auto` (모바일 가로 스크롤)
- `table-layout: auto` (컬럼 폭 자동)
- 첫 컬럼 `white-space: nowrap` (계정명 줄바꿈 방지)

### 마크다운 표 규칙

1. **컬럼 = 시점, 좌측이 가장 최신** (예: 2025 → 2024 → ... → 2017)
2. **첫 컬럼 = 항목명**, 짧고 명확하게 (`매출액`, `영업이익`, `OCF`)
3. **단위는 표 헤더에 명시** (`항목 (조원)`, `항목 (억원)`, `항목 (%)`)
4. **숫자 컬럼은 `---:`로 우측 정렬** — 자릿수 정렬용
5. **강조는 `**굵게**`** — 정점/바닥/사상 최대 등
6. **표 아래에 한 줄 풀이** — `표시: **+58.40** = 사상 최대 / **-66.87** = 사상 최악`

### 단위 결정 기준

모든 행이 0.5~1000 범위에 들어가는 단위를 고른다.

| 회사 | 권장 단위 | 이유 |
|---|---|---|
| 대형 (SK하이닉스, 삼성전자, 두산) | 조원 | 매출 10조 이상 |
| 중형 (삼양식품) | 억원 | 매출 0.5~3조, 조원 단위로 가면 0.X로 깔림 |
| 비율 | % | 표 헤더에 `(%)` 명시 |

같은 글 안에서 단위 혼용 가능 (IS는 조원, 영업이익만 보조 억원 표기) — 단, 표마다 헤더에 명시.

---

## 4. 글 한 편당 최소 데이터 단위 (회사 종합편)

회사 종합편 한 편에 다음 6가지가 다 들어 있어야 한다. 빠지면 종합편으로 부족하다.

| # | 데이터 | 호출 | 본문 위치 |
|---|---|---|---|
| 1 | IS 9년 시계열 표 | `c.select("IS", [...])` 분기 합산 | 수익성/마진 막 시작 |
| 2 | BS 9년 Q4 스냅샷 표 | `c.select("BS", [...])` Q4만 | 안정성/자금조달 막 시작 |
| 3 | CF 9년 시계열 표 + 잉여현금 파생행 | `c.select("CF", [...])` 분기 합산 | 현금/자본배분 막 시작 |
| 4 | 핵심 비율 분기 시계열 표 1~3개 | `c.select("ratios", [...])` | 핵심 변곡점 막 |
| 5 | dartlab 자체 분석 인용 ≥1 | `c.analysis(...)` 의 marginDriver/flag/divergence | 메커니즘 막 |
| 6 | 신용등급 카드 | `c.credit("등급")` | 안정성 막 |

주제 심화편(한 회사 한 각도)은 1·5·6만 필수, 나머지는 주제에 따라.

---

## 5. 금지 패턴 (지난 라운드 거짓 19건의 공통 원인)

### 패턴 A — 분기값을 연도 라벨로 표기

```markdown
❌ 나쁨:
| 연도 (Q4) | 매출 | 영업이익 |
|---|---|---|
| 2025 | 4.86 | 2,121 |   ← Q4 단독값인데 "2025"로 라벨

✅ 좋음:
| 항목 (Q4 단독, 조원) | 2025Q4 | 2024Q4 |
|---|---|---|
| 매출액 | 4.86 | 4.59 |
```

### 패턴 B — 비율 분기값과 1년치 marginWaterfall을 같은 표에

```markdown
❌ 나쁨:
| 분기 | GP마진 |
|---|---|
| 2023Q1 | -32% (사상 최악)
| ...
| 2025 | 60.41% ← 1년치 값을 분기 표에 끼움
```

연간 GP마진은 별도 표 또는 본문 한 줄로.

### 패턴 C — capitalOverview 소계를 총합으로 인용

`capitalOverview["순차입금"]`은 dartlab 내부 정의 (현금성자산 - 차입금).
"총 차입금" 절대값이 필요하면 반드시 `fundingSources.notesDetail.borrowings`의 "합계" 행.

### 패턴 D — dartlab 출력을 풀어 쓰면서 단위 변환 실수

```python
print(c.analysis("자본배분")["dividendPolicy"]["history"][0])
# {'period': '2025', 'dividendsPaid': 522052000000.0, ...}
```

→ 본문 "5,220.52억" 또는 "5,221억". 절대로 "약 2,631억" 같이 다른 숫자가 나오면 안 된다 (지난 라운드 SK 거짓).

### 패턴 E — 검증 안 된 외부 출처 수치

보도자료 수치(체코 5.6조, 사우디 3조 등)는 `c.select`로 검증 불가. 검증표에 "외부 인용"으로 명시하고 출처 링크 첨부.

---

## 6. 검증 스크립트 템플릿

블로그 한 편의 모든 인용 수치를 발행 직전 한 번에 dartlab으로 재호출해 비교.

```python
# .claude/scripts/verifyBlogNumbers.py (별도 plan에서 본격 구현)
import dartlab

def verify_skhynix():
    c = dartlab.Company("000660")
    checks = []

    # 본문 핵심 후킹
    is_df = c.select("IS", ["매출액","영업이익"])
    rev_2025 = sum(is_df.row(0, named=True).get(f"2025Q{q}", 0) or 0 for q in range(1,5))
    op_2025 = sum(is_df.row(1, named=True).get(f"2025Q{q}", 0) or 0 for q in range(1,5))

    checks.append(("매출 97.15조", abs(rev_2025/1e12 - 97.15) < 0.05))
    checks.append(("영업이익 47.21조", abs(op_2025/1e12 - 47.21) < 0.05))

    # 차입금
    borrowings = c.analysis("financial","자금조달")["fundingSources"]["notesDetail"]["borrowings"]
    total = next(r["2025"] for r in borrowings if r["계정명"] == "합계")
    checks.append(("차입금 22.25조", abs(total/1e12 - 22.25) < 0.05))

    # 결과
    for name, ok in checks:
        print(f"{'✅' if ok else '🔴'} {name}")
    return all(ok for _, ok in checks)

if __name__ == "__main__":
    verify_skhynix()
```

이 스크립트를 글마다 만들어두면 데이터 갱신 후에도 회귀 검증이 가능하다.

---

## 7. 실측 한 번 더 — 분기/연간 헷갈릴 때

작성 중 "이 숫자가 분기인지 1년치인지" 헷갈리면:

```python
df = c.select("IS", ["매출액"])
row = df.row(0, named=True)

# 검증 1: 4분기 합산 vs Q4 단독값
annual = sum(row.get(f"2025Q{q}", 0) for q in range(1,5))
q4_only = row.get("2025Q4")
print(f"2025 연간 {annual/1e12:.2f}조 / Q4 단독 {q4_only/1e12:.2f}조")
```

이 두 숫자를 본문에 박을 때 절대 한 표에 섞지 않는다.

---

## 8. 데이터 갱신 시점 처리

dartlab 데이터는 분기마다 새 공시가 들어오면서 갱신된다. 글 발행 시점과 검증 시점이 다를 수 있다.

권장:
- 글 제목 옆에 "데이터 기준: 2026-04-08 dartlab" 명시
- 검증표에 "📅 dartlab 실측 2026-04-08"
- 큰 분기 변동(예: Q4 결산 발표) 후에는 회사 종합편 핵심 후킹 한 번 더 검증
