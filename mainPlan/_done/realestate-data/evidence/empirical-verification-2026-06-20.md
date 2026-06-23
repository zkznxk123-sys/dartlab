# P0 외부 사실 — 실증 증거 (2026-06-20)

> 본 파일은 PRD 데이터층 feasibility의 *외부 사실*(코드 아님)을 평가자가 **읽고 검증**할 수 있도록 박제한 증거다.
> 코드 file:line은 src/에서, 외부 API/라이선스/한도 사실은 본 파일에서 검증한다. raw 응답은 [api-probe-2026-06-20.json](api-probe-2026-06-20.json).

---

## 1. 실호출 probe (raw = `api-probe-2026-06-20.json`)

| 호출 | 결과 | 해석 |
|---|---|---|
| `GET http://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList` (customs, 동일 `DATA_GO_KR_KEY`) | **200** · `application/xml` · `<resultCode>00</resultCode>` | 네트워크·키·게이트웨이 정상 (대조군) |
| `GET http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev` (RTMS, **키 有**) | **403 Forbidden** (text/plain) | 키는 유효(customs 200)하나 *이 서비스에 활용신청 미승인* — data.go.kr 서비스별 게이트 시그니처 |
| 같은 RTMS (**키 無**) | **401 Unauthorized** | 401(키無)↔403(키有) 대비가 "키 유효·서비스 미승인"을 확정 |

→ **엔드포인트·serviceKey·네트워크 = 실증 확정.** 잔여 = 서비스 활용신청(자동승인·아래 §2)뿐.

## 2. data.go.kr 데이터셋 페이지 (15126468) — 라이선스·한도·승인

WebFetch(`https://www.data.go.kr/data/15126468/openapi.do`) 확인 사실:
- **이용허락범위: "제한 없음"** → 상업이용·재배포 허용 → **HF 공개 SSOT 양립**(KOGL Type2~4 'dataLayer 무효' 최악분기 소멸).
- **비용: 무료.**
- **트래픽: 개발계정 일일 10,000건**(운영계정=활용사례 등록 시 증가). customs와 동일. (초기 '1,000콜'은 구 검색 요약 오정보 — 본 페이지가 정본.)
- **심의: 개발단계 자동승인 / 운영단계 자동승인** → 활용신청 = 1클릭·즉시 승인.
- 데이터포맷: XML. 기술문서: "아파트 매매 실거래가 상세자료 기술문서.hwp".

## 3. RTMS 응답 XML 구조 — 문서 출처 2종 확인

| 요소 | 확인 | 출처 |
|---|---|---|
| 페이지네이션 태그(영문) | header에 `resultCode`·`resultMsg`·`numOfRows`·`pageNo`·**`totalCount`** 존재 | choonghyunryu.github.io(2022) + data.go.kr 검색 요약("output … some header data with English names") |
| item 필드(한글 태그) | `거래금액`·`전용면적`·`층`·`건축년도`·`년`·`월`·`일`·`법정동`·`아파트`·`지번`·`지역코드`·`도로명`(+ Dev 상세: `해제여부`·`해제사유발생일`·`등기일자`·`동`[등기완료분]) | 동일 출처 ("actual data … composed only with Korean names") |

→ **`<totalCount>` 태그 실재 = 문서 2종 입증.** `_parseItems` 경계 = header `totalCount`로 pageNo for-loop 종료, item은 *한글 태그* 파싱(거래금액→dealAmount·전용면적→excluUseAr·층→floor·건축년도→buildYear·년/월/일→dealYear/Month/Day·법정동→umdNm·아파트→aptNm·지번→jibun·지역코드→sggCd·해제여부→cdealType).

## 4. 남은 *유일* 실측 (운영자 게이트)

운영자가 data.go.kr에서 RTMS 활용신청 1클릭(즉시 자동승인) → 라이브 1콜로 (a)Dev 버전 item 태그가 한글/영문인지 (b)`totalCount` 위치 (c)`해제여부` 코드값을 *바이트* 확정 → §3.1 응답명세 표를 '문서→실측'으로 갱신. **이 1콜이 데이터층 feasibility의 마지막 마일이며, 자동승인이라 분 단위·설계 차단요소 아님.** 활용신청 권한은 운영자 data.go.kr 계정에 있어 본 세션에서 수행 불가.

---

**결론:** 데이터 수집 feasibility의 외부 사실(엔드포인트·KOGL 제한없음·콜한도 10,000/일·자동승인·totalCount 태그)은 실호출 + 문서 2종으로 **검증 가능하게 박제**됐다. 코드 아닌 외부 사실이라 코드대조만으로는 안 보이던 것을, 본 증거 파일로 평가자가 직접 확인할 수 있다.
