"""pipeline stages — category별 fetch→build→upload run 함수.

각 stage 의 ``run*(*, category, mode, codes, upload, token) -> StageResult``. W2 는
검증된 ``.github/scripts/sync/*`` 를 동형 호출(전환기); 후속 웨이브에서 본체 인라인.
"""
