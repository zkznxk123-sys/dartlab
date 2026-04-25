---
title: Review
---

# Review — 보고서 렌더링

analysis + credit 결과를 블록식으로 조합하여 보고서를 만든다.

## 사용법

```python
c = dartlab.Company("005930")

# 섹션별 보고서
c.story("수익성")                      # 수익성 섹션만
c.story("신용평가")                    # 신용평가 섹션만

# 출력 형식
rv = c.story("수익성")
rv.toMarkdown()                        # 마크다운
rv.toHtml()                            # HTML
rv.toJson()                            # JSON
print(rv)                              # Rich 콘솔
```

## 보고서 섹션 (6막 구조)

| 막 | 섹션 | 핵심 질문 |
|------|------|---------|
| 1막 사업이해 | 수익구조, 성장성 | 뭘 하는가, 얼마나 성장하는가 |
| 2막 수익성 | 수익성, 비용구조 | 얼마나 잘 버는가 |
| 3막 현금전환 | 현금흐름, 이익품질 | 이익이 현금으로 전환되는가 |
| 4막 안정성 | 자금조달, 안정성, **신용평가** | 자본 구조는 안전한가 |
| 5막 자본배분 | 자산구조, 효율성, 투자효율, 자본배분 | 번 돈을 어떻게 쓰는가 |
| 6막 전망 | 가치평가, 지배구조, 매출전망 | 앞으로 어떻게 되는가 |

### 비교분석 블록 (피어·산업)

| 블록 | 설명 | 소스 엔진 |
|------|------|-----------|
| `peerRanking` | 시장 내 백분위 순위 | scan |
| `peerPosition` | 전종목 수익성·성장·부채 백분위 | scan |
| `chainPosition` | **산업 밸류체인 내 위치** — 전 상장사 × 산업 × 공정·역할·스트림 + 같은 공정 피어 | **industry** |
| `sectorKpi` | 업종 특수 KPI (건설·반도체·게임·제약) | analysis |

```python
c.story(only=["chainPosition"])      # 산업 밸류체인 블록만
```

## review vs analysis

- **analysis**: 원본 데이터를 dict로 반환 → AI/코드가 직접 해석
- **review**: analysis 결과를 렌더링된 보고서로 조합 → 사람이 읽는 형태

## reviewer — AI 의견 추가

```python
dartlab.ask()                           # review + AI 종합의견
dartlab.ask(guide="반도체 관점에서")      # 가이드 지시
```

## 주의

```python
# ⚠ 전체 review() 금지 — 83초 타임아웃
c.story()            # ← 매우 느림 (전체 14섹션)

# ✓ 섹션별로 호출
c.story("수익성")     # ← 빠름 (해당 섹션만)
c.story("안정성")     # ← 빠름
```
