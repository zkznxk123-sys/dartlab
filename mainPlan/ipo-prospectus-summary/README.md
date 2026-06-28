# ipo-prospectus-summary

GitHub Discussion #70 — IPO 증권신고서(지분증권) 수요예측 6카테고리 구조화 요약.

- **[00-prd.md](00-prd.md)** — 전문가 토론 + 실측 박제. 결론·실측·D1-D5·phasing·운영자 결정 5건.

## 한 줄 요약
새 엔진 신설 없이 3곳 분산(providers 단건파서 `securitiesRegistration.py` · scan 횡단 `scan("ipo")` · story builder L3). 런타임-SSOT(allFilings content_raw) 직독 기본. `tests/_attempts/ipo/` 졸업 후 본진(order-flow-scan 동형).

## 실측 핵심
- 데이터 풍부(9개월 531건, 단일 XML, 6섹션 앵커 전부 검출). 테이블 구조파싱 필요(flat regex 실패).
- ★ **`corp_cls=="E" + stock_code==""` = 신규상장 IPO 기계 ground-truth**(사람 라벨 불필요). corp_cls Y/K(stock_code 보유)는 유상증자/DR — SK하이닉스·계양전기 자동 비-IPO.

## 상태
기획 확정·미착수. 운영자 결정 5건 대기. professional-report-engine·order-flow-scan 동급 활성.
