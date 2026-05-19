---
id: operation.mappingRefresh
title: accountMappings 보강 4 단계 파이프라인
category: operation
status: observed
lastUpdated: 2026-05-18
purpose: DART finance parquet 의 nonstd_ fallback (미커버 한글 계정명) 을 운영자가 수동으로 검토 후 standardAccounts.snakeId 와 짝지어 accountMappings.json 에 박는 4 단계 절차. 자동 학습/추론 아닌 *수동 박기 정공* 이며, 본 파이프라인은 후보 추출·검증·박기 작업을 효율화하는 도구.
whenToUse:
  - "nonstd_ fallback 행이 finance 매핑 로그에 등장"
  - "매퍼 정리 / 표준화 후보 정리 / 분기 매퍼 업데이트"
  - "신규 회사 점검 시 새 한글 계정명 흡수"
  - "accountMappings.json 미커버 계정 보강"
procedure:
  - "Step 1 — polars lazy + anti-join 으로 전 종목 finance parquet 2~3 초 스캔, 미커버 그룹 추출"
  - "Step 2 — mapper.map() 11 단계 fallback 더블체크, false-positive 제거"
  - "Step 3 — SA korName substring 매칭 + 5 가드 후보 추출"
  - "Step 4 — 운영자가 한 줄씩 의미 검토 + SA hard check + 짝 동시 박기"
examples:
  - "사용자 nonstd_ 로그 보고 후 cycle 박기"
  - "전수 anti-join 후 strong top occ 사람 검토"
  - "유입/유출 짝 매핑 동시 박기"
expectedOutputs:
  - "accountMappings.json 매핑 dict 추가 (compact JSON 보존)"
  - "_metadata.addedCount + lastUpdate 갱신"
  - "mapper.map() PASS 검증 결과"
  - "commit -o 명시 path commit"
requiredEvidence:
  - "SA hard check 통과 snakeId"
  - "사전 유사 매핑 패턴"
  - "옛 운영자 fold 결정 일관성"
  - "액션 단어 양쪽 일치"
failureModes:
  - "Ghost snakeId 박기 — SA 부재 snakeId 가 사전에 가짜로 박힘 (현재 4,368 누적 부채, 12.6%)"
  - "액션 손실 — '취득/처분/회수' 한글에 *자산 자체* snakeId 매핑 (예: 단기금융상품 취득 → shortterm_financial_instruments 자산 자체)"
  - "반대어 회귀 — 비유동↔유동, 비금융↔금융, 장단기↔단기 한쪽만 박힘"
  - "VALUE 단어 손실 — 평가손실/평가이익을 자산 자체로 fold"
  - "짝 부재 — 유입 박고 유출 안 박음 (cycle 12→17 회귀 사례)"
forbidden:
  - "자동 sweep 만으로 박기 (사람 검토 없이)"
  - "Ghost SA snakeId 박기 (standardAccounts hard check 부재 매핑)"
  - "사전 매핑 자동 codemod / 일괄 변환"
  - "git add -A 또는 git add . (매핑 외 다른 변경 섞임 위험)"
  - "_metadata.addedCount 갱신 누락"
  - "compact JSON → indented JSON 변환 (git diff 폭증)"
---

# mappingRefresh — accountMappings.json 보강 4 단계 파이프라인

## 0. 핵심 원칙

mapper 의 34,000+ 매핑은 *모두 운영자가 미커버 한글명을 보고 직접
`standardAccounts.snakeId` 와 짝지어 박은 결과*. 자동 학습/추론 아님.
본 파이프라인은 그 *수동 박기 작업* 을 효율화하는 도구이며,
*최종 매핑 결정은 사람이 의미 검토 후 직접*.

## 1. 단계 요약

| 단계 | 진입점 | 권한 | 산출 |
|---|---|---|---|
| 1. 전수 미커버 추출 | Bash inline (`polars.scan_parquet` + 4 단 `anti-join`) | 읽기 | 미커버 그룹 ≈ 33k |
| 2. mapper 더블체크 | Python (`mapper.map()` 11 단계 fallback) | 읽기 | 진짜 미커버 ≈ 20k |
| 3. SA 매칭 후보 추출 | Python (SA korName substring + 5 가드 + score) | 읽기 | 강한 후보 ≈ 1.5k |
| 4. 운영자 박기 | 사람 검토 + JSON 직접 patch + `AccountMapper.release()` | prod patch | `accountMappings.json` 매핑 추가 |

각 cycle 마다 step 4 에서 5~100 매핑 박음. cycle 반복하며 점진 정리.

## 2. Step 1 — polars lazy + anti-join 전수 미커버 추출

`mapper.map()` 의 11 단계 fallback 중 핵심 4 단 (account_id 직 hit,
account_nm 직 hit, account_id prefix 제거 후 hit, account_nm 정규화 hit)
을 polars expression 으로 재현해 **2~3 초** 만에 전 종목 finance parquet
에서 미커버 행 추출. 사전 변형 흡수 (noSpace/noParen/noHyphen 역인덱스
+ suffix 흡수) 는 step 2 mapper 더블체크에서 처리.

```python
import polars as pl, json
mp = json.loads(open('src/dartlab/reference/data/accountMappings.json',
                     encoding='utf-8').read())['mappings']
keys = pl.LazyFrame({'key': list(mp.keys())})

nm_n = pl.col('account_nm').str.replace_all(r'[\s()\[\]/.,_\-]','').alias('nm_n')
id_n = pl.col('account_id').str.replace_all(r'^(?:ifrs-full_|ifrs_|dart_)','').alias('id_n')

out = (
    pl.scan_parquet('data/dart/finance/*.parquet',
                    extra_columns='ignore', missing_columns='insert')
    .select(pl.col('stock_code').cast(pl.String).fill_null(''),
            pl.col('sj_div').cast(pl.String).fill_null(''),
            pl.col('account_id').cast(pl.String).fill_null(''),
            pl.col('account_nm').cast(pl.String).fill_null(''))
    .filter(pl.col('account_nm') != '')
    .with_columns(nm_n, id_n)
    .join(keys, left_on='account_id', right_on='key', how='anti')
    .join(keys, left_on='id_n',       right_on='key', how='anti')
    .join(keys, left_on='account_nm', right_on='key', how='anti')
    .join(keys, left_on='nm_n',       right_on='key', how='anti')
    .group_by(['account_id','account_nm','sj_div'])
    .agg(pl.len().alias('occ'),
         pl.col('stock_code').unique().alias('stockCodes'))
    .with_columns(pl.col('stockCodes').list.len().alias('disp'))
    .collect(engine='streaming')
)
```

산출 → 메모리 또는 `/tmp/mapping_candidates_raw.parquet` (gitignored).
시간 약 1~2 초 / 2,927 종목.

## 3. Step 2 — mapper.map() Python 더블체크

anti-join 결과는 *입력쪽 normalize 만* 재현. mapper.map() 의 11 단계
fallback (synonym, prefix, 사전 변형 noSpace/noParen/noHyphen 역인덱스,
suffix 흡수) 로 매핑되는 false-positive 제거:

```python
from dartlab.providers.dart.finance.mapper import AccountMapper
from dartlab.core.utils.labels import _loadAccountMappings
_loadAccountMappings.cache_clear()
AccountMapper.release()
mapper = AccountMapper.get()

true_um = [r for r in out.to_dicts()
           if mapper.map(r['account_id'] or '', r['account_nm'] or '') is None]
new = pl.DataFrame(true_um).sort('occ', descending=True)
```

진짜 미커버 ≈ 20k (false-positive 약 35% 제거). 시간 0.3 초.

**sj_div 분포 — SCE 4,107 그룹 무시**: finance pivot 은 BS/IS/CF/CIS 만
처리하고 SCE 는 별도 `buildSceMatrix` 흐름이므로 SCE 한글명이 미커버로
잡혀도 mapping 추가 대상 아님. 강한 후보 filter 에 SCE 제외:

```python
strong = new.filter(
    pl.col('sj_div').is_in(['BS','IS','CF','CIS']) &
    ((pl.col('occ') >= 5) | (pl.col('disp') >= 3))
)
```

## 4. Step 3 — SA korName 매칭 + 5 가드

`standardAccounts.korName` 정규화 후 미커버 한글명과 양방향 substring
일치 → 5 가드 통과 후보만 추출:

### 가드 1: 액션 단어 양쪽 일치

```python
ACTION_KOR = ['증가','감소','증감','순증감','조정','취득','처분','회수','지급',
              '수령','상환','발행','감액','매각','매입','환입','대체','차환',
              '상각','유입','유출']
# 길이 우선 매칭 (순증감 > 증감 > 증가 — substring 중복 회피)
```

입력에 액션 단어 있으면 SA snakeId 도 동일 의미 영문 (increase/decrease/
acquisition/purchase/disposal/disposition/collection/recovery/payment/...)
포함 필수. 다중 액션 ALL-match.

### 가드 2: 반대어 짝 차단

```python
ANTONYM_PAIRS = [
    ('비유동', '유동'),    # 비유동 vs 유동
    ('비금융', '금융'),    # 비금융 vs 금융
    ('장단기', '단기'),   # 장단기 합산 vs 단기 단독
    ('장단기', '장기'),
    ('관계기업', '종속기업'),
    ('관계회사', '종속회사'),
    ('보통주', '우선주'),
    ('이익', '손실'),
    ('수익', '비용'),
    ('유입', '유출'),
]
```

한쪽에 a 있고 다른쪽에 a 없으면 SKIP. `비유동성장기차입금 → current_portion_of_longterm_borrowings`
같은 *정반대* 매핑 차단.

### 가드 3: VALUE 종류 검증

`평가손실/평가이익/평가손익/처분손실/처분이익/손상차손/환입익` 한글이
있으면 SA snakeId 도 동일 의미 영문 (`losses_on_valuation`/
`gains_on_valuation`/`losses_on_disposition`/`gains_on_disposition`/
`impairment`/`reversal`) 일치 필수.

### 가드 4: 노이즈 패턴 차단

`주석|총액|적립|적용|note|gross|연결조정` 한쪽에만 있으면 SKIP.

### 가드 5: SA hard check

`v not in standardAccounts` 인 snakeId 박기 차단. 사전 ghost (현재 4,368
누적 부채) 추가 회피.

### 가드 6: 짝 동시 박기 룰 (cycle 12→17 회귀 fix)

유입↔유출 / 증가↔감소 / 취득↔처분 한쪽 박을 때 반대쪽 변형도 동시 확인.
예: `상환의무 있는 정부보조금...현금유입액` 박을 때 `...현금유출액` 도 동시.

### score 임계

| 임계 | cycle | 위험 |
|---|---|---|
| score ≥ 0.85 | 자동 sweep (cycle 6) | 낮음 |
| 0.80 ≤ score < 0.85 | 강 가드 후 자동 sweep (cycle 7~8) | 중간 |
| 0.70 ≤ score < 0.80 | 강 가드 + 수동 검토 (cycle 8) | 높음 |
| 0.65 ≤ score < 0.70 | 수동 선택만 (cycle 9) | 매우 높음 |
| < 0.65 | 수동 박기만 (cycle 10~17) | sweep 비효율 |

## 5. Step 4 — 운영자 박기

후보 list 를 한 줄씩 검토 → *액션 단어 보존* + *SA 의미 일치* + *옛
운영자 패턴 일관성* 검증 후 박을 것만 선택.

### 5.1 박기 OK 패턴

- **prefix 추가** — 회사 자체 prefix 변형
- **숫자/로마 prefix** — `1. 금융수익` / `V. 이익잉여금`
- **suffix 보존** — *조정·등·총액·순액* 일반 suffix
- **오타·축약** — 끊긴 한글
- **유동/단기 fold** — SA 에 분리 snakeId 없을 때 일반 매핑 fold
- **공백 위치 변형** — `영업양도로 인한 현금 유입` ↔ `영업양도로 인한 현금유입` (mapper noSpace idx 가 처리하지만 사전 부재 시 patch)

### 5.2 박기 SKIP

- **액션 빠진 환각** — 자산 자체 snakeId 박으면 액션 손실
- **장기/단기 정반대** — `장기사채의 증가` → `increase_in_shortterm_bonds` SKIP
- **반대어 짝** — 비유동/유동 정반대
- **회사 1 disp 단일 라벨** — 일반화 무리
- **SA 정확 매핑 부재** — SA 자체에 적합 snakeId 없으면 SA 보강 트랙 별

### 5.3 박기 + AccountMapper.release()

```python
import json, os
path = 'src/dartlab/reference/data/accountMappings.json'
data = json.loads(open(path, encoding='utf-8').read())
mp = data['mappings']
sa = data['standardAccounts']

adds = {
    '단기상각후원가금융자산': 'financial_assets_at_amortised_cost',
    # ...
}

# 가드 6 SA hard check
for k, v in adds.items():
    assert v in sa, f'GHOST: {k} -> {v}'

added = 0
for k, v in adds.items():
    if k in mp: continue                           # idempotent
    mp[k] = v
    added += 1

data['_metadata']['addedCount'] = int(data['_metadata'].get('addedCount', 0)) + added
data['_metadata']['lastUpdate'] = '2026-MM-DD'

tmp = path + '.tmp'
open(tmp, 'w', encoding='utf-8').write(
    json.dumps(data, ensure_ascii=False, separators=(',', ':'))  # single-line 보존
)
os.replace(tmp, path)

# 캐시 무효화
from dartlab.providers.dart.finance.mapper import AccountMapper
from dartlab.core.utils.labels import _loadAccountMappings
_loadAccountMappings.cache_clear()
AccountMapper.release()
```

### 5.4 commit 규약

```bash
git commit -o src/dartlab/reference/data/accountMappings.json -m "$(cat <<'EOF'
수정: accountMappings.json cycle N — 미커버 M 매핑 (요약)

<패턴 요약 — prefix variant / 숫자 prefix / suffix 보존 / 동의어 그래프 / 짝 동시>

_metadata.addedCount 누적 N.
EOF
)"
```

`commit -o` 명시 + 주체 중립 톤 강행 (다른 파일 staged 섞임 차단).

## 6. mapper.py 정공 보강 — 11 단계 fallback

본 cycle 들에서 mapper.py 에 도입된 정공 (회귀 가드 tests/providers/dart/finance/test_mapperFallbackVariants.py 7 PASS):

1. account_id `_stripPrefix` (ifrs-full_/ifrs_/dart_/ifrs-smes_ 제거)
2. `ID_SYNONYMS` 영문 ID 동의어 통합
3. `ACCOUNT_NAME_SYNONYMS` 한글명 동의어 통합
4. 사전 한글명 직접 조회 (우선)
5. 사전 영문 ID 조회 (fallback)
6. 입력 공백 제거 후 사전 조회
7. **사전 noSpace 역인덱스** (사전 키 공백/tab/ZWSP 흡수)
8. 입력 괄호+공백 제거 후 사전 조회
9. **사전 noParen 역인덱스** (예: `현금의 기타유입` ↔ `현금의기타유입(유출)`)
10. 입력 하이픈 제거 + 사전 noHyphen 역인덱스 (실험 081-001)
11. **입력 짧은 한국어 suffix 흡수** (`액`/`등`/`외` — `영업양도 현금유입액` ↔ `영업양도 현금유입`)
12. 미매핑 → None

## 7. cycle 운용

| cycle | 추가 매핑 | 누적 | 특징 |
|---|---|---|---|
| 1~4 | 100 | 100 | prefix/suffix 변형 흡수 |
| 5 | 31 | 131 | sample 51~170 |
| 5b | 3 | 141 | 공백 변형 (cycle 5 누락 fix) |
| 5c | 3 | 144 | nonstd_ 사용자 보고 3 |
| 6 | 103 | 247 | 자동 sweep score ≥ 0.85, 액션 보존 + 반대어 차단 |
| 7 | 39 | 286 | 0.80~0.85, VALUE 가드 추가 |
| 8 | 20 | 306 | 0.70~0.80, 액션 사전 강화 (증감/조정/유입/유출) |
| 9 | 7 | 313 | 0.65~0.70, 수동 안전 |
| 10 | 5 | 318 | 사용자 회사 잔여 |
| 11 | 3 | 321 | 삼성전자 수동 의미 분석 |
| 12 | 5 | 326 | 신규 회사 (정부보조금/사채발행비용/영업양도) |
| 13 | 6 | 332 | 전수 strong top |
| 14 | 12 | 344 | top 30 잔여 |
| 15 | 9 | 353 | top 30~70 |
| 16 | 11 | 364 | top 30~50 |
| 17 | 9 | 373 | 신규 회사 + 본 세션 짝 부재 fix |

**한계 도달 신호**: cycle 당 추가 < 10 + 잔여 strong 후보 score 0.65 미만
다수. 이 시점부터는 SA 보강 (action-prefix `purchase_of_`, `decrease_in_`,
`losses_on_` 별) 또는 `ACCOUNT_NAME_SYNONYMS` (mapper.py in-code dict) 보강이
다음 진전 영역.

## 8. 한계 분석 — XBRL ID 정공 한계 (Tier 1 진단)

cycle 17 시점 전수 strong 7,609 중 미커버 분포:

| 영역 | 그룹 | 비율 |
|---|---|---|
| `-표준계정코드 미사용-` (한글만 의존) | 5,389 | 70.8% |
| XBRL id 있는데 미커버 | 2,220 | 29.2% |

XBRL id 있는데 미커버 = 37,364 행. 이 중 같은 id 가 *39 개 다른 한글명*
으로 등장하는 케이스도 발견.

**B 트랙 시뮬레이션** — XBRL id 정공 자동화 시도:

| 항목 | 수 | 결과 |
|---|---|---|
| 미커버 XBRL id (unique) | 809 | — |
| snake_case 변환 후 SA 존재 | 30 (3.7%) | 자동 변환 효과 적음 |
| 명백 OK (모든 한글 변형 일치) | 20 | 535 행 흡수 가능 |
| 부분 위험 (XBRL id 오박 회사) | 5 | 220 매칭 + 100 불일치 |
| 자동 snake 무용 (SA 부재) | 779 | dart 자체 확장 라벨 |

**핵심 발견 — 회사가 XBRL id 오박**: `dart_DecreaseInEquityInvestments`
(출자금의감소) 한 id 에 `'비유동 기타포괄손익-공정가치측정 금융자산의 반환'`
같은 *완전 다른 의미* 한글명을 박은 회사 존재. **XBRL 자체가 자유 입력**.

**결론**: B 트랙 (XBRL id 자동 일괄 박기) 비효율 + 회귀 위험. 본 cycle
11~17 의 *사용자 회사 점검 단위 수동 박기* 가 정합성 우수 (회귀 0).

## 9. 장기 트랙 — Tier 1~3

### Tier 1 (1~2 주, 안전)

- **짝 동시 박기 룰 정형화** (cycle 17 짝 부재 fix 의 영구 적용) — 본 문서
- **suffix 화이트리스트 확장** — 현재 `액/등/외`. 검증 후 후보: `금`/`품`/`분`
  (부작용 검토 필요)
- **ghost snakeId 4,368 정리 cycle** — 옛 매핑 부채 청산 (큰 작업, 별 트랙)

### Tier 2 (1~3 개월, 도메인)

- **ID_SYNONYMS 강화** — IFRS XBRL id 동의어 정확 매핑 우선 확장 (영문 ID
  가 한글명보다 안정)
- **ACCOUNT_NAME_SYNONYMS 도메인 사전 확장** — *영업양도 ↔ 사업양도 ↔ 사업매각*
  같은 동의어 그래프 박기. mapper.py in-code dict.
- **옛 운영자 fold 패턴 룰화** — 유동/단기 fold, 총액 fold, 숫자 prefix
  자동 적용 검증 (cycle 6 자동 sweep 의 발전형)
- **mapper 우선순위 검토** — 한글명 우선 → XBRL id 우선 후보 (위험성 평가
  필요, 회사 오박 케이스 회귀 위험)

### Tier 3 (3~6 개월, 혁신)

- **closed-loop with embedding + LLM** — 한국어 sentence transformer
  (KoSimCSE 등) 로 SA korName + mappings 키 vector 빌드. 새 nonstd 입력 →
  top-k 추천 + LLM 의미 검증 + 운영자 1-tap 승인. dartlab 의존성 정신과
  충돌 위험 (모델 크기 ~400MB) 검토.
- **DART 표준계정 승격 루프** — cycle 마다 빈도 높은 미커버 변형을 SA
  표준으로 승격 (운영자 review 후 `standardAccounts` 보강). ghost 부채 감소.
- **DART OpenAPI 표준 한글명 활용** — DART 가 발행하는 *정규 한글 표기*
  를 사전 시드로 사용. API 미커버 회사는 fallback.

## 10. 혁신 방법 후보

| 방법 | 장점 | 위험/비용 |
|---|---|---|
| **embedding 매칭 (KoSimCSE/sentence-bert-ko)** | 의미 유사도 자동, cold-start 효율 | 모델 크기, 의존성, 결정 비투명 |
| **LLM 추천 + 운영자 승인 UI** | 의미 추론 강력, 매번 cold-start 가능 | API 비용, 결정 정합성 가변 |
| **XBRL ID 정공 + 한글명 display only** | 영문 ID 안정 표준 | DART XBRL 미사용 회사 다수 (-표준계정코드 미사용-) → 70.8% 적용 불가 |
| **crowd-sourced ontology** | 다른 dartlab 사용자 결정 공유 → 동의어 그래프 누적 | 사용자 base 작음, 거버넌스 어려움 |
| **active learning ML** | 확신도 자동 cut, 사람은 uncertainty 만 검토 | 학습 데이터 sparse, 결정 정합성 |
| **DART OpenAPI 표준 한글명** | DART 정규 표기 활용 | API 미커버 회사 다수, 분기 lag |

### 가장 가성비 + 정공

**Tier 1 (a) 짝 동시 박기 룰 + (b) suffix 화이트리스트 확장 + Tier 2 (c)
ACCOUNT_NAME_SYNONYMS 동의어 그래프 확장** 조합. dartlab 의존성 정신 유지
+ 즉시 효과.

### 가장 혁신

**XBRL ID 우선 정공 (Tier 2) + ACCOUNT_NAME_SYNONYMS 동의어 그래프** 조합.
한글명 비표준화 문제를 *영문 ID layer* 로 우회. 단 회사 오박 케이스 가드
필수. B 트랙 테스트 결과 (cycle 17 시점) = 자동화 부적합, 수동 review
필수.

## 11. 트러블슈팅

### 11.1 자동 후보 환각 (snakeId 부재)

후보 snakeId 가 `standardAccounts` 에 없으면 *환각된 매핑*. SA hard check
필수 (`v in sa` assert). 사전 4,368 누적 ghost (12.6%) 부채.

### 11.2 액션 단어 손실

후보 한글에 *처분/감소/증가* 가 있는데 SA korName 에는 *자산 자체* 만
있는 경우. SKIP 하고 SA 에 `purchase_of_X` / `decrease_in_X` 별도 snakeId
검색.

### 11.3 종목별 특수 변형

특정 종목 (예: 005380 현대차) 의 23 미커버 그룹이 SA korName substring
매칭 점수 0 인 케이스 — 회사 사내 라벨. mapping 추가 무리.
`ACCOUNT_NAME_SYNONYMS` 보강 또는 그대로 nonstd 유지.

### 11.4 회사 XBRL id 오박

DART XBRL id 가 *자유 입력* 이라 회사가 잘못된 id 박을 수 있음. 자동
snake_case 변환 박기 전 *한글명 의미 일치 가드* 필수.

### 11.5 짝 부재 회귀

유입/유출, 증가/감소, 취득/처분 한쪽만 박으면 *반대 변형* 매번 재발. cycle
12 → 17 사례. 박을 때 반대쪽 짝도 동시 확인.

### 11.6 staging 손상

`/tmp/mapping_candidates_*.parquet` 손상 시 Step 1 재실행 (1~2 초).
`data/` 자체는 gitignored.

## 12. 가드 정공 — registry/CI 강제

- **SA hard check** — 부재 snakeId 차단 (현재 수동 assert; 향후 lint 룰화
  후보)
- **single-line JSON 보존** — git diff 폭증 회피 (`separators=(',', ':')`)
- **AccountMapper 캐시 무효화** — apply 직후 동일 프로세스 캐시 정합
  (`_loadAccountMappings.cache_clear()` + `AccountMapper.release()`)
- **SCE 무시** — finance pivot 대상 아님 (SCE 는 `buildSceMatrix` 별도 흐름)
- **commit -o 명시 path** — 다른 변경 섞임 차단 (`.claude/hooks/check_git_commit_only.ps1`)

## 13. 참조

- `src/dartlab/providers/dart/finance/mapper.py::AccountMapper` — mapper
  본체 (11 단계 fallback, 사전 변형 noSpace/noParen/noHyphen 역인덱스 +
  suffix 흡수)
- `src/dartlab/providers/dart/finance/pivot.py::_pivotToSeries` — nonstd
  로그 출력 위치
- `src/dartlab/reference/data/accountMappings.json` — prod 매핑 사전
  (single-line compact JSON, 34,000+ 매핑)
- `src/dartlab/reference/mapping/mappingPromote.py` — prod JSON patch CLI
  (staging parquet 우회 경로, step 4 inline batch 와 동치)
- `src/dartlab/reference/mapping/mappingReview.py` — staging review CLI
- `tests/providers/dart/finance/test_mapperFallbackVariants.py` — 회귀
  가드 7 케이스 (사전 변형 흡수 + suffix 흡수)
