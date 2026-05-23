# `tests/_attempts/` — 시도 폴더

**회귀 가드 아님**. 토론·실험·POC 코드 영구 보관소.

## 규약

- pytest 가 자동 skip (`_` prefix + `python_files = test_*.py` 불일치)
- CI 게이트 통과 의무 0
- 결과가 부정적이어도 코드 *남긴다* — 미래의 누군가가 "이거 해봤네" 알 수 있게
- 새 시도 = 카테고리 폴더 안에 `xxxTest.py` 또는 `xxxBench.py`
- 같은 카테고리 안에서 파일명으로 시도 구분

## 카테고리

| 폴더 | 무엇을 |
|---|---|
| [speed/](speed/) | 검색·인덱스 *속도* 시도 (FM-index, suffix array, mmap 등) |
| [semantic/](semantic/) | *의미 검색* 시도 (doc2query, 분포 의미 해시, query expansion) |

확장 시 카테고리 폴더 추가 + 본 README 표 업데이트.

## 실행

각 파일 상단 docstring 에 *목적* + *기대 결과* + *결론* 기록. 실행은 `uv run --no-sync python -X utf8 tests/_attempts/{category}/{file}.py`.

## 결론 표

| 시도 | 카테고리 | 결론 |
|---|---|---|
| fmIndexBench | speed | 1.5GB 본문 → 7~16µs 검색 (naive 600~1300ms 대비 50000~80000× 빠름). 단 SA = 텍스트 4× 메모리 |
| fmIndexMmap | speed | mmap suffix array → RAM 거의 0 (2.7MB delta), warm 검색 21~43µs. 디스크 5× 텍스트 |
| doc2queryTest | semantic | 100 공시·5 질문/공시 LLM sweep. 어휘 갭 ("돈 빌렸나" → 차입금) 명확히 매움. 다만 100 표본 + 단순 token-count 라 *압도적* 차이 보이진 않음 |
| riVsaHash | semantic | v1. 30K 섹션·trigram·256bit. 분포 의미 *작동*: 전환사 ↔ 사채/채권(d=63~70), 자기주 ↔ 취득/소각(d=58~71). 빌드 13 분. 한계: 자기주↔자사주 d=130 (= 무작위), 저빈도 stem (HBM freq 16) 노이즈 |
| riVsaHashV2 | semantic | v2. scipy.sparse + bigram·trigram. 빌드 **77초** (v1 의 10× 빠름). distance 폭격: 의미 family d=4~25 / 자기 vs 자사 d=27 (v1 의 130 에서 메움). HBM (freq 26) → 반도체 family d=16~22. 한계: baseline mean=72.5 (편향). 변별력 약화 |
| riVsaHashV3 | semantic | v3. IDF 가중 + 풀 corpus (allFilings + docs 4.7M 섹션 → 60K reservoir). baseline=89.1 (이론 128 회복). 변별력 폭증 — 가까운 쌍 d=18~53 vs 멀어야 d=50~79 *분리*. 새 매칭: 합병 ↔ 분할 d=27, 취득 ↔ 처분 d=21, 대표이사 ↔ 최대주주 d=9. 자기 vs 자사 d=40 (rand 89 대비 -49). 저장: data/_scratch_fm/riVsaV3/ |
| riVsaSearch | semantic | v4. v3 의 contextHash 위에 sectionHash 빌드 (417K allFilings 섹션, 13.4MB) + 자연어 쿼리 인터페이스. 쿼리당 100~130ms. 12 자연어 쿼리 중 9 개 정확 매칭 (75%): "주주총회 결과" d=9, "최대주주 변경" d=10, "유상증자한 회사" d=14, "전환사채 발행" d=15, "배당 지급" d=16 (현금ㆍ현물배당결정 5 종목 직접). vector/RAG 없이 *RAG 품질 검색* 달성 |
| riVsaLM | semantic | v5. 분포 LM 흉내 — contextHash 의 nearest neighbor 로 next-stem 예측. 학습/weights 0. 자연스러운 도메인 흐름 자가 조립: 차입금 → 손익계산서, 합병 → 흡수합병, 주주총회 → 위원회, 최대주주 → 대표이사. GPT 수준 X 하지만 *분포 의미가 살아있는 생성* |
| riVsaHashV6 | semantic | v6. Resonance Hash — char Bloom 128b + random 128b. 부분문자열 (유상→유상증) 인식 폭격. 자기↔자사 d=25 (v3 의 40 메움). 한계: baseline 89→49 폭격, char spurious (자사→랜드/이센스) |
| riVsaHashV7 | semantic | v7. Tier 1 (jamo+char+bigram+rand 4-region) + Tier 2 self 포함 identity (M.T@M@char 에서 self subtract 제거). 사용자 idea 정확 구현. PROBE A d=0-3 응집, 자기↔자사 d=9 (v3 40 → 31점 메움), 차입금 family d=0-3 perfect cluster. 검색 application 압도적. 한계: baseline=23.4 폭격, 자기↔농업 d=12 분류 변별력 약함. 저장 data/_scratch_fm/riVsaV7/ |
