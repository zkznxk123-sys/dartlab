# 실험 110: AI용 데이터 맥락 보강

## 가설
analysis calc 결과에 "비교 맥락"(5년 평균, YoY 판단, 업종 백분위)을 함께 제공하면
AI의 해석 품질이 구조적으로 올라간다.

## 결과: 가설 확인

### A/B 실측 (삼성전자 수익성, GPT-5.4)

| 항목 | A (raw) | B (enriched) |
|------|---------|-------------|
| 응답 길이 | 3,339자 | **1,141자** (3배 짧음) |
| 코드 실행 | 필요 (2라운드) | **불필요** (0라운드) |
| 판단 명확성 | "좋아지는 중" (모호) | **"좋다, 역대 최고는 아닌 회복"** (명확) |
| 비교 맥락 | 없음 | 5년 평균 +1.2pp, 상위 79.9% |
| "왜" 설명 | 부분적 | 완전 (5년 평균, 전기 비교, 업종 위치) |

### 추가 비용
- Raw TOON: 872자 (~290토큰)
- Enriched TOON: 2,060자 (~686토큰)
- 추가: +1,188자 (~400토큰)
- 하지만 코드 실행 0라운드 → **총 토큰 절약** (코드 실행 피드백 2,000~8,000토큰 절약)

## 근거 논문
- Kim et al. (시카고대, 2024): 재무제표 + CoT → 이익 방향 60% 정확도 (인간 53-57% 초과)
- TAP4LLM (EMNLP 2024): 서브테이블 + 보강 → +7.93%p
- FinSheet-Bench (2026): "결정론적 계산과 LLM 해석을 분리하는 아키텍처 필요"

## 구현 방향

### 공통 변환 레이어: `AIView`

```python
# 위치: src/dartlab/ai/context/aiview.py
# 각 엔진의 dict/DataFrame → AI가 이해하기 좋은 enriched dict

class AIView:
    """엔진 결과를 AI 해석용으로 변환하는 공통 레이어.
    
    원칙:
    - 원본 데이터 변경 금지 (기존 API 유지)
    - AI 경로(ContextBuilder)에서만 호출
    - 각 축별 enrichment 로직을 등록
    """
    
    @staticmethod
    def enrich(engine: str, axis: str, result: dict, company=None) -> dict:
        """엔진 + 축에 따라 적절한 맥락 보강."""
        # 공통: history 시계열에 5년 평균, YoY 판단 추가
        # 공통: scan에서 업종 백분위 조회
        # 공통: 핵심 1줄 요약 생성
```

### 적용 경로

```
현재: c.analysis("수익성") → dict → encodeAuto(TOON) → LLM
제안: c.analysis("수익성") → dict → AIView.enrich() → enriched dict → encodeAuto(TOON) → LLM
```

ContextBuilder의 `_selectCalcForIntent()` → `_calcToContextPart()` 사이에 AIView 삽입.

### 보강 항목 (엔진별)

| 엔진 | 추가 맥락 |
|------|----------|
| analysis | 5년 평균, YoY 변화+판단, 업종 백분위, 핵심 1줄 요약 |
| credit | 등급 의미 해석, 업종 대비 위치 |
| scan | 상위/하위 N개 하이라이트, 분포 통계 |
| macro | 현재 국면 판단, 이전 사이클 대비 |
| quant | 신호 강도 + 과거 적중률 |

## 실험 110-2: auto_enrich — 엔진별 수작업 0

### 결과: 성공

`auto_enrich(data, company=c)` 하나로 **analysis 6축 + credit + quant + scan + show + macro** 전부 자동 보강.

**원리**: dict 구조를 자동 탐지.
- `history[]` 패턴 → period + 숫자 필드 감지 → 5년 평균/YoY/판단 자동
- DataFrame → 스키마 + 통계 + 샘플 자동
- flat dict → 핵심 필드 자동 요약
- 비율 vs 금액 자동 구분 (필드명 + 값 범위)

**엔진이 새 축을 추가해도**: `history + period + 숫자` 패턴만 유지하면 enrichment 자동.

### 흡수 방향

`auto_enrich()`를 `src/dartlab/ai/context/aiview.py`로 이동.
ContextBuilder의 `_calcToContextPart()` 단계에서 자동 호출.

```
현재: calc result → encodeAuto(TOON) → LLM
제안: calc result → auto_enrich() → encodeAuto(TOON) → LLM
```

## 상태: 실험 성공 → 흡수 대기
