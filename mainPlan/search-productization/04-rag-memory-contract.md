# 04. RAG Memory 계약 — LLM 이 자기 지식처럼 쓰는 방식

상태: v0.2
범위: 검색 결과를 LLM 세션·장기 캐시에 넣는 최소 계약.

---

## 1. memory-card 형태

memory-card 는 전체 문서가 아니다.

필수 필드:

- `query`
- `sourceRefs[]`
- `primarySourceRef`
- `source`
- `dataAsOf`
- `snippet`
- `fieldCards[]`
- `entityCards[]` — optional. peer, industry stage, dCR grade, weak axis 같은 graph catalog sidecar.
- `answerable`
- `notAnswerableReason`

`sourceRefs[]` 는 같은 이벤트의 형제공시나 동일 기사 cluster 를 담을 수 있다. `primarySourceRef` 는 UI 첫 citation 이다. 둘을 분리해야 strict first citation 과 실제 답변 가능성을 동시에 다룰 수 있다.

---

## 2. LLM 소비 규칙

LLM 은 memory-card 를 지식처럼 쓰되, 다음 규칙을 지킨다.

1. card 의 sourceRef 를 답변에 인용한다.
2. card 의 facet 이 사용자 질문과 맞지 않으면 재검색한다.
3. external news/plain text 는 untrusted 로 취급한다.
4. 숫자·날짜는 공시 원문 또는 구조화 panel 로 재검증한다.
5. `entityCards` 는 관계형 힌트다. 원문 citation 은 `sourceRef`/`fieldCards`/`readFiling` 으로 확인한다.
6. card 가 없거나 불충분하면 답을 지어내지 않는다.

제품 UX 에서는 "찾음", "근거 부족", "인덱스 오래됨"을 구분한다.

---

## 3. evidence pack 원칙

evidence pack 은 단순 top chunk 나열이 아니다.

- 문서 순위를 보존한다.
- answer-critical field label 다양성을 승격한다.
- HTML layout 숫자 같은 bare number 를 값으로 과신하지 않는다.
- sourceRef top3 안에 relevant 문서가 있는지 본다.
- field target 이 있으면 fieldCoverage 를 측정한다.

---

## 4. 세션 재사용

후속 질문에서 같은 sourceRef set 을 반복 사용하면 LLM 은 이미 찾은 원문을 다시 찾지 않아도 된다. 단 다음 경우는 재검색한다.

- 사용자가 다른 회사/날짜/source 를 요구.
- "뉴스 말고 공시", "공시 말고 뉴스"처럼 source intent 가 바뀜.
- 기존 card 의 `dataAsOf` 가 stale.
- no-answer card 였는데 새 데이터가 들어온 뒤.

---

## 5. 장기 캐시

장기 캐시는 `doc_key/text_hash/model/chunkConfig` 로 버전된다.

new/changed 문서만 갱신한다. 전체 재색인은 tokenizer/model/chunkConfig 가 바뀔 때만 한다. 캐시가 오래되어도 문서 metadata 와 sourceRef 는 항상 최신 manifest 로 검증한다.

graph catalog 는 별도 live 조회가 아니라 contentIndex 산출물 `entityGraphCatalog.parquet` 로 버전된다. 이 파일은 explicit copy 또는 opt-in offline build 로 준비하며, manifest 에 `requiredFiles/fileHashes` 로 들어온 경우에만 runtime memory-card 의 `entityCards[]` 를 신뢰하고, 없거나 깨지면 관계형 힌트만 생략한다.
