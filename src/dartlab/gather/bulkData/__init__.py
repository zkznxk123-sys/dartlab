"""gather bulk data 로더 — HuggingFace dataset SSOT 진입점.

KRX 가격·지수 long parquet (`eddmpython/dartlab-data`) + macro wide parquet 을
일괄 로드한다. 사용자 기본 경로 (API 키 불필요). 운영자 publish 는 hfDeploy.

호출자는 명시 path 사용:
    from dartlab.gather.bulkData.hfBulk import loadFiltered
    from dartlab.gather.bulkData.hfIndexBulk import loadFiltered
    from dartlab.gather.bulkData.macroHf import fetchSeries, fetchMulti
    from dartlab.gather.bulkData.hfDeploy import deployKrxToHF

facade re-export 하지 않는다 (alias 금지 룰).
"""
