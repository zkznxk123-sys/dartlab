"""news headline sentiment scoring — 3 층 fallback (Phase B).

Layered model selection — KoFinBERT (snunlp, F1 0.85) → KLUE-RoBERTa (Apache 2.0,
F1 0.82) → LM-dict (의존성 0, F1 0.65). 가용한 가장 강한 옵션 자동 선택.

CI / 무모델 환경에서도 동작 — LM-dict 만으로도 narrative pulse 생성 가능.
실제 inference 는 optional 그룹 `narrative` 활성 시 transformers pipeline batch=32.
"""

from __future__ import annotations

import logging
from typing import Literal

import polars as pl

from .lmDict import NEGATIVE_EN, NEGATIVE_KR, POSITIVE_EN, POSITIVE_KR

log = logging.getLogger(__name__)

# 모델 우선순위 — 가용한 첫 번째 사용.
_MODEL_PRIORITY_KR = [
    ("snunlp/KR-FinBert-SC", "kofinbert"),
    ("klue/roberta-base", "klue_roberta"),
]
_MODEL_PRIORITY_US = [
    ("ProsusAI/finbert", "finbert_en"),
    ("nlptown/bert-base-multilingual-uncased-sentiment", "multilingual"),
]


def _lmDictScore(title: str, market: str) -> tuple[float, str]:
    """LM-dict 단어 매칭 — (score -1~+1, label).

    Sig: ``_lmDictScore(title, market) -> (score, label)``

    Capabilities: 한/영 LM 사전 (Loughran-McDonald) tokenize-free 단어 매칭.
    AIContext: 3 층 fallback 의 최하층 — 모델 미가용 시 항상 동작.
    Guide: 단순 substring 매칭이라 F1 0.65 한계. KoFinBERT 가용 시 자동 강등.
    When: scoreNewsBatch 가 모델 없는 환경에서 호출.
    How: title 소문자/원문 → POS/NEG 사전 hit 카운트 → (pos-neg)/(pos+neg+ε).

    Args:
        title: 헤드라인.
        market: "KR" | "US".

    Returns:
        (score: float, label: "pos"|"neg"|"neutral").

    Raises:
        없음.

    Example::

        _lmDictScore("반도체 호황 가속화", "KR")  # → (0.5, "pos")

    Requires:
        lmDict 모듈 (POSITIVE/NEGATIVE 사전).

    See Also:
        ``scoreNewsBatch``: 본 함수의 batch caller.
    """
    if market == "KR":
        pos_set, neg_set = POSITIVE_KR, NEGATIVE_KR
        text = title or ""
    else:
        pos_set, neg_set = POSITIVE_EN, NEGATIVE_EN
        text = (title or "").lower()

    pos = sum(1 for w in pos_set if w in text)
    neg = sum(1 for w in neg_set if w in text)
    if pos == 0 and neg == 0:
        return 0.0, "neutral"
    score = (pos - neg) / (pos + neg)
    label = "pos" if score > 0.1 else ("neg" if score < -0.1 else "neutral")
    return score, label


def _hfPipelineOrNone(market: str):
    """transformers pipeline 가용 시 (model_name, hf_pipe, version) 반환, else None.

    Sig: ``_hfPipelineOrNone(market) -> tuple | None``

    Capabilities: 우선순위 모델 순회 + 첫 가용 모델 캐싱 (lru-like 함수 캐시).
    AIContext: B2 sentiment 의 1·2 층 fallback gate. transformers 미설치면 즉시 None.
    Guide: HF cache 미보유 시 첫 호출 1 회 다운로드 (~410MB KR / ~440MB EN).
    When: scoreNewsBatch 가 model="auto" 시.
    How: import transformers → 우선순위 model 시도 → 성공한 첫 모델 반환.

    Args:
        market: "KR" | "US".

    Returns:
        (model_name, pipe, version_str) 또는 None.

    Raises:
        없음 — 모든 import/load 에러 silent.

    Example::

        result = _hfPipelineOrNone("KR")  # (None) if no transformers

    Requires:
        optional 그룹 `narrative` 의 transformers + torch.

    See Also:
        ``scoreNewsBatch``: caller.
    """
    try:
        from transformers import pipeline
    except ImportError:
        log.debug("transformers 미설치 — LM-dict fallback")
        return None

    priority = _MODEL_PRIORITY_KR if market == "KR" else _MODEL_PRIORITY_US
    for model_name, label in priority:
        try:
            pipe = pipeline("sentiment-analysis", model=model_name, top_k=None)
            log.info("sentiment 모델 로드: %s (%s)", model_name, label)
            return model_name, pipe, label
        except Exception as exc:
            log.debug("모델 %s 로드 실패: %s", model_name, type(exc).__name__)
            continue
    return None


def scoreNewsBatch(
    df: pl.DataFrame,
    *,
    market: str = "KR",
    model: Literal["auto", "lm_dict"] = "auto",
    batchSize: int = 32,
) -> pl.DataFrame:
    """헤드라인 batch sentiment scoring — 3 층 fallback.

    Capabilities:
        - model="auto" — 우선순위: KoFinBERT/KLUE-RoBERTa (KR) / FinBERT/multilingual (US) → LM-dict
        - model="lm_dict" — LM 사전 강제 (CI/베이스라인 측정)
        - 결과 컬럼 추가: sentiment_score (-1~+1), sentiment_label (pos/neg/neutral), model_version
        - batchSize 단위 transformers pipeline 호출 (CPU 1000 헤드라인 ≈ 5 초)

    AIContext:
        Phase B 의 sentiment SSOT. enrichNewsHeadlines cron 호출 +
        narrativePulse.buildNarrativePulse 가 직접 호출.

    Guide:
        model="auto" 가 default — transformers 미설치 환경에서도 LM-dict 로 자동 동작.
        명시 model="lm_dict" 는 모델 영향 없이 사전 베이스라인만 필요할 때.

    When:
        - 일별 enrichNewsHeadlines cron (어제자 raw archive enrich)
        - narrativePulse 일간 aggregate 직전

    How:
        title 컬럼 추출 → 모델 가용 시 pipeline batch / 미가용 시 _lmDictScore row-wise
        → with_columns 추가.

    Args:
        df: title 컬럼 보유 DataFrame (newsHeadlines.loadNewsArchive 결과).
        market: "KR" | "US".
        model: "auto" (최강 자동) | "lm_dict" (강제 사전).
        batchSize: transformers pipeline batch.

    Returns:
        pl.DataFrame — 원본 + (sentiment_score, sentiment_label, model_version).

    Raises:
        없음 — 빈 df 면 동일 schema + 신규 3 컬럼 (null) 반환.

    Example::

        from dartlab.gather.bulkData.newsHeadlines import loadNewsArchive
        from dartlab.synth.newsSentiment import scoreNewsBatch
        df = loadNewsArchive("2026-05-01","2026-05-28","KR")
        df = scoreNewsBatch(df, market="KR")

    Requires:
        title 컬럼. 모델 가용 시 transformers + torch (optional 그룹 narrative).

    See Also:
        ``_hfPipelineOrNone``: 모델 선택 gate.
        ``_lmDictScore``: LM 사전 fallback.
        ``narrativePulse.buildNarrativePulse``: 본 함수의 다운스트림.
    """
    if "title" not in df.columns:
        log.warning("title 컬럼 부재 — sentiment 계산 skip")
        return df.with_columns(
            pl.lit(0.0).alias("sentiment_score"),
            pl.lit("neutral").alias("sentiment_label"),
            pl.lit("none").alias("model_version"),
        )
    if df.is_empty():
        return df.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("sentiment_score"),
            pl.lit(None, dtype=pl.Utf8).alias("sentiment_label"),
            pl.lit(None, dtype=pl.Utf8).alias("model_version"),
        )

    titles = df["title"].to_list()

    # 1·2 층 — transformers 모델 시도
    pipeRes = _hfPipelineOrNone(market) if model == "auto" else None
    if pipeRes is not None:
        modelName, pipe, version = pipeRes
        scores: list[float] = []
        labels: list[str] = []
        for i in range(0, len(titles), batchSize):
            chunk = titles[i : i + batchSize]
            try:
                outs = pipe(chunk)
                for out in outs:
                    # top_k=None → list of dicts; take highest score + sign
                    if isinstance(out, list):
                        best = max(out, key=lambda x: x["score"])
                    else:
                        best = out
                    label_raw = best["label"].lower()
                    score_raw = float(best["score"])
                    if "pos" in label_raw or label_raw in {"positive", "4 stars", "5 stars"}:
                        scores.append(score_raw)
                        labels.append("pos")
                    elif "neg" in label_raw or label_raw in {"negative", "1 star", "2 stars"}:
                        scores.append(-score_raw)
                        labels.append("neg")
                    else:
                        scores.append(0.0)
                        labels.append("neutral")
            except Exception as exc:
                log.warning("pipeline batch %d 실패: %s — LM-dict fallback", i, exc)
                for t in chunk:
                    s, lab = _lmDictScore(t, market)
                    scores.append(s)
                    labels.append(lab)
        return df.with_columns(
            pl.Series("sentiment_score", scores, dtype=pl.Float64),
            pl.Series("sentiment_label", labels, dtype=pl.Utf8),
            pl.lit(version).alias("model_version"),
        )

    # 3 층 — LM-dict fallback
    pairs = [_lmDictScore(t, market) for t in titles]
    scores = [p[0] for p in pairs]
    labels = [p[1] for p in pairs]
    return df.with_columns(
        pl.Series("sentiment_score", scores, dtype=pl.Float64),
        pl.Series("sentiment_label", labels, dtype=pl.Utf8),
        pl.lit("lm_dict_v1").alias("model_version"),
    )
