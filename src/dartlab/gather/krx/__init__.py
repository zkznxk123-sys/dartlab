"""gather KRX 도메인 — 한국거래소 데이터 + 종목 registry + 시총 합성.

호출자는 명시 path 사용:
    from dartlab.gather.krx.listing import getKindList, fuzzySearch, codeToName, nameToCode
    from dartlab.gather.krx.krxApi import fetchKrxBydd
    from dartlab.gather.krx.krxIndex import gatherKrxIndex
    from dartlab.gather.krx.marketCap import marketCap

facade re-export 하지 않는다 (alias 금지 룰).
"""
