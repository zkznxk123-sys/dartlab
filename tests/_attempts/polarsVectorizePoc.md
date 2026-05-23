# Polars Vectorize POC — `_expandStructuredRows` 큰 refactor

## 검증된 가능성 (2026-05-23)

Polars `fill_null(strategy='forward')` 로 **cumulative-latest heading snapshot 패턴** 가능.

```python
sample.with_columns(
    pl.when(pl.col('blockType') == 'text').then(pl.col('rowIdx')).otherwise(None).alias('checkpoint')
).with_columns(
    pl.col('checkpoint').fill_null(strategy='forward').alias('latest_text_idx')
)
# → 각 table row 가 그 시점의 latest text rowIdx (heading state snapshot 인덱스) 받음
```

## Refactor 청사진

**현재 (Python loop):**
```python
for row in orderedRows:
    if row.blockType == "text":
        # heading state 업데이트
        finalHeadings = parseTextStructureWithState(...)
        headingStateByTopic[topic] = finalHeadings
    else:  # table
        # 현재 heading state 의 path strings 생성
        currentHeadings = headingStateByTopic[topic]
        # 5 path strings build per table row (Python ' > '.join)
```

**Vectorize (2-pass Polars):**
```python
# Pass 1: text rows 만 처리 → finalHeadings snapshot DataFrame
text_rows = polars_df.filter(pl.col('blockType') == 'text')
# 각 text row 의 finalHeadings 를 별도 column 으로 누적 (sequential)
# → snapshot_df = (text_row_idx, finalHeadings_serialized)

# Pass 2: 전체 df 에 latest_text_idx 부여 → snapshot_df 와 join
# → path strings build via pl.col(...).list.eval() 또는 .map_elements
```

## 잠재 win 추정

- 현재 (`_expandStructuredRows`): 5.3s cumtime / 035720
- Polars vectorize: text 처리 ~3s + Polars join + path build ~0.5s = ~3.5s
- **잠재 win ~2s/corp** (035720 7.5s → 5.5s)
- 작은 corps 는 비례 감소
- 5 baseline cold 28s → 약 18s 예상

## 위험

1. **heading state serialization** — finalHeadings 는 list[dict]. Polars 안 serialize 어려움.
   - 회피: tuple-of-tuples 로 encode → struct column
2. **redundantTopicAlias mutation** — Polars 안 mutation 불가 → 변경 단계 분리 필요
3. **회귀 risk 큼** — 5 baseline parity 0 깨질 가능성

## 본진 투입 결정

큰 refactor — 단일 세션 내 위험. 별도 트랙 ("폴라스 벡터라이즈") + 5 baseline parity
0 검증 통과 후 마이그레이션.

## 추정 마법 수준 달성 시 최종 metric

| 영역 | 현재 (37.7×) | Polars vectorize 후 |
|---|---|---|
| 5 baseline cold | 27.91s | ~18s (1.4× 추가) |
| Per-corp cold | 5.58s | ~3.6s (1.5× 추가) |
| Per-corp cached (disk hit) | 1.0s | 1.0s (변화 X) |
| Memory peak | 168MB | ~100MB (40% 감소 추정) |
