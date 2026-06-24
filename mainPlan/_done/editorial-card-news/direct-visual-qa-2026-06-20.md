# Direct Visual QA - 2026-06-20

Purpose: recent carousel outputs are not accepted by batch render alone. Each post must be rendered as an explicit single post and inspected card by card before it is marked complete.

## Rules

- Do not mark a post complete from batch render output.
- Render one post explicitly.
- Open every generated PNG for that post.
- Check text clipping, unintended line breaks, bottom-left dartlab avatar+wordmark, page dots, internal jargon, and final card payoff.
- If one card fails, fix the source copy and rerender that post before continuing.

## Completed

### D01-dartlab-search-sidecar-evidence-os

- Render: `python -X utf8 sns\carousels\render.py D01-dartlab-search-sidecar-evidence-os`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\D01-dartlab-search-sidecar-evidence-os`
- Cards checked: 01 through 09.
- Initial fail: card 01 and public copy used internal terms such as `검색 OS`, `sidecar`, `BM25`, and related implementation language.
- Fix: rewrote hook, story brief, caption, threads, comment, review, loop, meta, and source language rule around reader-language points.
- Final visual result: pass.
- 2026-06-20 internal-code recheck: rerendered card 01 and confirmed the top badge shows `DartLab Search` only, with no public `D01` classification number.
- Final payoff: 필요한 문서만 읽는가, 결과가 원문까지 이어지는가, 틀린 결과를 걸러내는가.

### D02-dartlab-table-export-evidence-os

- Render: `python -X utf8 sns\carousels\render.py D02-dartlab-table-export-evidence-os`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\D02-dartlab-table-export-evidence-os`
- Cards checked: 01 through 08.
- Initial fail: public copy used internal terms such as `rowspan`, `colspan`, `OOXML`, `CRC32`, `mergeCell`, `SheetJS`, `ExportDrawer`, and `PanelMatrix`.
- Second fail: card 07 used `로컬 완전판`, which read like internal project language.
- Fix: rewrote hook, story brief, caption, threads, comment, review, loop, meta, and source language rule around reader-language points.
- Final visual result: pass.
- 2026-06-20 internal-code recheck: rerendered card 01 and confirmed the top badge shows `DartLab Table Export` only, with no public `D02` classification number.
- Final payoff: 숫자가 숫자로 남는가, 병합 셀이 망가지지 않는가, 빈칸이 0으로 바뀌지 않는가.

### D03-dartlab-backtest-honesty-os

- Render: `python -X utf8 sns\carousels\render.py D03-dartlab-backtest-honesty-os`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\D03-dartlab-backtest-honesty-os`
- Cards checked: 01 through 10.
- Initial fail: public copy used internal/trading terms such as `OOS`, `B&H`, `Sharpe`, `t+1`, and action-style buy/sell wording.
- Visual fail found during direct check: card 07 used `봉`, which is chart jargon for general readers.
- Fix: rewrote the carousel/caption/thread around plain-language honesty checks and changed card 07 to `60거래일`.
- Final visual result: pass.
- 2026-06-20 internal-code recheck: rerendered card 01 and confirmed the top badge shows `DartLab Backtest` only, with no public `D03` classification number.
- Final payoff: 신호가 나온 날과 실제 거래일, 비용과 실제 체결 차이, 처음에 안 쓴 기간의 경계, 사라진 표본.

### E01-000660-skhynix-editorial

- Render: `python -X utf8 sns\carousels\render.py E01-000660-skhynix-editorial`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E01-000660-skhynix-editorial`
- Cards checked: 01 through 10.
- Initial fail: caption/story/review used automatic assembly language such as `직접 확인와`, `종목코드 하나로`, and did not answer the reader's "so what" question.
- Visual fail found during direct check: card 01 used awkward wording `좋은 회사냐가`.
- Metadata fail: post missed `meta.json`, so render warned that shared assets could not sync under the post rule.
- Fix: rewrote the carousel/caption/thread around the current question of HBM excess profit durability, added `meta.json`, and changed card 01 to `좋은 회사냐는`.
- Final visual result: pass.
- Final payoff: HBM4 출하, 영업이익률, 서버 메모리 가격.

### E02-035420-naver-ai-factory-editorial

- Render: `python -X utf8 sns\carousels\render.py E02-035420-naver-ai-factory-editorial`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E02-035420-naver-ai-factory-editorial`
- Cards checked: 01 through 10.
- Initial fail: caption/story/review used automatic assembly language such as `읽는 법와`, `질문은 AI가 아니라`, and did not explain what AI factory means for a general reader.
- Fix: rewrote the carousel/caption/thread around the business question of whether the AI factory can earn money, and translated the concept into data center, electricity, cooling, usage, and customers.
- Final visual result: pass.
- Final payoff: 55MW 가동 시점, 외부 고객, 비용을 이기는 매출.

### E03-000660-sk-hynix-ai-memory-editorial

- Render: `python -X utf8 sns\carousels\render.py E03-000660-sk-hynix-ai-memory-editorial`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E03-000660-sk-hynix-ai-memory-editorial`
- Cards checked: 01 through 10.
- Initial fail: caption used `이다` style, card 03 used awkward `좋은 회사냐가`, and card 01 used date-sensitive `오늘 종가`.
- Visual fail found during direct check: card 07 used `패키징`, which could read as semiconductor jargon.
- Fix: changed card 01 to `2026. 06. 18 기준`, rewrote caption in polite style, changed card 03 wording, updated source/meta details, and rewrote card 07 with `칩을 묶는 방식`.
- Final visual result: pass.
- Final payoff: 영업이익률 유지, HBM4 실제 물량, 공급 확대 뒤 가격.

### E04-336260-doosan-fuel-cell-company-map

- Render: `python -X utf8 sns\carousels\render.py E04-336260-doosan-fuel-cell-company-map`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E04-336260-doosan-fuel-cell-company-map`
- Cards checked: 01 through 10.
- Initial fail: original public/editorial files used public-unfriendly terms such as `PAFC`, `SOFC`, `CHPS/HPS`, and auto-assembled language such as `두산퓨얼셀은와`.
- Visual fail found during direct check: card 02 kicker `뭘 파나` could read as `물 파나`; card 06 used awkward `든 해였습니다`; card 08 used accounting term `환입`; cards 09 and 10 used `수율`; card 10 said `세 가지만` but visually split the final point into four items.
- Fix: rewrote the carousel/caption/thread/review/source language around the plain-language company map: 발전용 연료전지 설비, 장기정비, 입찰 가격, 원가를 뺀 이익, 새 제품 안정성과 정비 매출.
- Recheck: rerendered the post and reopened cards 02, 06, 08, 09, and 10 after fixes.
- Final visual result: pass.
- Final payoff: 입찰 가격, 원가를 뺀 이익, 새 제품 안정성과 정비 매출.

### E05-010120-ls-electric-power-grid-editorial

- Render: `python -X utf8 sns\carousels\render.py E05-010120-ls-electric-power-grid-editorial`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E05-010120-ls-electric-power-grid-editorial`
- Cards checked: 01 through 10.
- Initial fail: caption, threads, story brief, and review used broken automatic assembly such as `AI 뉴스보다와 전력실을 본다을`; card 11 was a fragment-style extra ending after card 10 had already delivered the payoff.
- Fix: removed card 11, rewrote caption/thread/review/loop/source language, and aligned the story around `AI 칩 회사가 아니라 전력실 장비 회사`.
- Direct visual result: cards 01 through 10 opened one by one; no clipping, no missing dartlab avatar+wordmark, and final card reads clearly.
- Final visual result: pass.
- Final payoff: 북미 새 주문, 받아둔 주문의 매출 전환, 원자재가 올라도 버티는 이익률.

### E06-003230-samyang-buldak-export-engine

- Render: `python -X utf8 sns\carousels\render.py E06-003230-samyang-buldak-export-engine`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E06-003230-samyang-buldak-export-engine`
- Cards checked: 01 through 09.
- Initial fail: story brief, review, loop, caption, and threads used automatic assembly such as `반복성와`, plus stiff terms such as `가동률·출하` and `마진`.
- Visual fail found during direct check: card 06 used `반복성`; this was changed to `반복 판매`.
- Fix: rewrote the public copy and editorial records around the plain-language question: 불닭의 유명함이 반복 주문과 남는 이익으로 바뀌는가.
- Recheck: rerendered the post and reopened card 06 after the fix.
- Final visual result: pass.
- Final payoff: 해외 매대에서 반복 판매, 새 공장이 실제로 돌아가는지, 원재료와 환율 뒤 이익.

### E07-CPNG-coupang-breach-cost-loop

- Render: `python -X utf8 sns\carousels\render.py E07-CPNG-coupang-breach-cost-loop`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E07-CPNG-coupang-breach-cost-loop`
- Cards checked: 01 through 10.
- Initial fail: story brief, review, and loop used broken automatic assembly such as `쿠팡은 유출보다와 습관과 비용을 본다을`; source language also kept public-unfriendly terms such as `Product Commerce`, `Developing Offerings`, `EBITDA`, and `마진`.
- Fix: rewrote story brief, caption, threads, comment, review, loop, source report, and card language around the plain-language question: after the breach, do customers keep ordering and how much cost remains?
- Visual fail found during direct check: card 08 used stiff business wording. Changed it to `본업 쇼핑` and `실제 이용 고객`, rerendered the post, and reopened card 08.
- Final visual result: pass.
- Final payoff: 고객 재주문과 본업 이익률, 과징금의 현금 부담, 새 사업 손실 감소.

### E08-207940-samsung-biologics-cdmo-factory

- Render: `python -X utf8 sns\carousels\render.py E08-207940-samsung-biologics-cdmo-factory`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E08-207940-samsung-biologics-cdmo-factory`
- Cards checked: 01 through 09.
- Initial fail: story brief, review, loop, caption, and source report used broken automatic assembly and public-unfriendly terms such as `CDMO`, `Plant 5`, `kL`, `마진`, `램프업`, and `Fact Sheet`.
- Visual fail found during direct check: editorial and editorialBeat headline copy missed the `[[ ]]` highlight markers, so headline accent color rendered only on badges and numbers, not on the key phrase.
- Fix: rewrote the carousel/caption/thread/review/source language around the plain-language question `신약보다 공장을 본다`, added one explicit highlight phrase per editorial/editorialBeat headline, and added a gate that blocks missing or multiple headline highlights.
- Recheck: rerendered the post and reopened card 04 first, then cards 01 through 09 one by one.
- Final visual result: pass.
- Final payoff: 5공장이 얼마나 돌아가는지, 계약이 매출과 남는 이익으로 바뀌는지, 증설 뒤 영업이익률.

### E09-035720-kakao-chatgpt-in-talk

- Render: `python -X utf8 sns\carousels\render.py E09-035720-kakao-chatgpt-in-talk`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E09-035720-kakao-chatgpt-in-talk`
- Cards checked: 01 through 10.
- Initial fail: story brief, caption, threads, review, and loop used broken automatic assembly such as `카카오은`, `카카오을`, `AI보다와`, and the last 10th and 11th cards gave conflicting endings.
- Fix: removed the broken 11th card, rewrote the carousel/caption/thread/review/source language around the plain-language question: does ChatGPT inside KakaoTalk become repeated use, paid conversion, and talk-business revenue?
- Visual fail found during direct check: card 04 used awkward `4.9천만`; card 09 had a stiff ad-product phrase that broke badly across lines.
- Recheck: changed card 04 to `4,900만명`, shortened card 09 to `화면 광고`, rerendered the post, and reopened cards 04 and 09.
- Final visual result: pass.
- Final payoff: 채팅방 안 실제 사용 빈도, 유료 서비스 전환, 톡비즈 광고와 메시지 매출.

### E09-278470-apr-beauty-device-dtc-engine

- Render: `python -X utf8 sns\carousels\render.py E09-278470-apr-beauty-device-dtc-engine`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E09-278470-apr-beauty-device-dtc-engine`
- Cards checked: 01 through 09.
- Initial fail: story brief, caption, threads, review, and loop used stiff or broken language around 비용·판매 경로 and carried an automatic sentence shape.
- Fix: rewrote the carousel/caption/thread/review/source language around the plain-language question: does the beauty device increase first payment and then lead to repurchase without selling costs overwhelming the story?
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, numbers, and final payoff were readable.
- Final visual result: pass.
- Final payoff: 뷰티기기 매출 비중, 해외·온라인 판매 경로, 재구매와 판매 비용.

### E10-259960-krafton-pubg-cash-engine

- Render: `python -X utf8 sns\carousels\render.py E10-259960-krafton-pubg-cash-engine`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E10-259960-krafton-pubg-cash-engine`
- Cards checked: 01 through 09.
- Initial fail: story brief, review, loop, caption, and source language used stiff terms such as `IP`, `BGMI`, `트래픽`, `Early Access`, `Franchise`, and noun-style payoff language such as `지속성`.
- Fix: rewrote the carousel/caption/thread/review/source language around the plain-language question: is PUBG still a repeat money engine, and do mobile users keep paying while new-game costs rise?
- Visual fail found during direct check: final card used noun-style payoff points that did not clearly answer what to watch next.
- Recheck: changed the final card to explicit questions, changed card 05 from `결제 지속성` to `결제가 이어지는지`, rerendered the post, and reopened cards 05 and 09 after the fix.
- Final visual result: pass.
- Final payoff: PUBG 매출이 계속 이어지는지, 모바일 접속이 결제로 이어지는지, 신작 비용이 이익을 누르는지.

### E10-373220-lg-energy-solution-ess-backlog

- Render: `python -X utf8 sns\carousels\render.py E10-373220-lg-energy-solution-ess-backlog`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E10-373220-lg-energy-solution-ess-backlog`
- Cards checked: 01 through 10.
- Initial fail: hook cards 01, 02, 05, 07, 09, 10, and 11 missed explicit headline highlight markers; story brief, caption, review, and loop contained broken automatic assembly such as `EV보다와`, `본다을`, and a duplicate 11th ending.
- Fix: removed the broken 11th card, rewrote the carousel/caption/thread/review/source language around the plain-language question: do the large orders become revenue, profit, and manageable cash burden?
- Direct visual result: cards 01 through 10 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Final visual result: pass.
- Final payoff: 수주가 매출로 바뀌는 속도, 전력 저장장치에서 남는 이익, 영업손실이 현금 부담으로 번지는지.

### E11-267260-hd-hyundai-electric-transformer-backlog

- Render: `python -X utf8 sns\carousels\render.py E11-267260-hd-hyundai-electric-transformer-backlog`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E11-267260-hd-hyundai-electric-transformer-backlog`
- Cards checked: 01 through 10.
- Initial fail: hook cards 01, 02, 03, 06, 08, 09, 10, and 11 missed headline highlight markers; story brief, caption, review, and loop contained broken automatic assembly such as `마진이다와`, `본다을`, and a duplicate 11th ending.
- Fix: removed the broken 11th card, rewrote the carousel/caption/thread/review/source language around the plain-language question: do power-equipment orders become revenue and high operating margin?
- Visual fail found during direct check: cards 04 and 05 used awkward `억$` unit labels.
- Recheck: changed those units to `억달러`, rerendered the post, and reopened cards 04 and 05.
- Final visual result: pass.
- Final payoff: 새 주문이 계속 늘어나는지, 수주잔고가 매출로 바뀌는지, 24.9% 이익률이 버티는지.

### E12-ORCL-oracle-rpo-cash-gap

- Render: `python -X utf8 sns\carousels\render.py E12-ORCL-oracle-rpo-cash-gap`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E12-ORCL-oracle-rpo-cash-gap`
- Cards checked: 01 through 10.
- Initial fail: old copy used public-unfriendly terms such as `RPO`, `FCF`, `남은 계약 의무`, `자유현금흐름`, and an awkward phrase `주식성 50억달러`.
- Fix: rewrote carousel, caption, threads, review, loop, and source language around the plain-language question: is Oracle's giant contract number turning into revenue and cash?
- Visual fail found during direct check: card 08 used `자유현금흐름`; card 09 used `주식성 50억달러`.
- Recheck: changed card 08 to `투자하고 남은 현금`, changed card 09 to `주식으로 50억달러`, rerendered the post, and reopened cards 01, 03, 05, 08, 09, and 10 after the fix.
- Final visual result: pass.
- Final payoff: 남은 계약이 매출로 바뀌는 속도, 투자 뒤 현금 회복, 돈을 더 끌어오지 않고 버틸 수 있는지.

### E13-005930-samsung-memory-profit-engine

- Render: `python -X utf8 sns\carousels\render.py E13-005930-samsung-memory-profit-engine`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E13-005930-samsung-memory-profit-engine`
- Cards checked: 01 through 10.
- Initial fail: hook cards 01, 02, 05, 07, 08, 09, 10, and 11 missed headline highlight markers; caption, threads, story brief, review, and loop were broken automatic assembly text.
- Fix: removed the broken 11th card, rewrote the carousel/caption/thread/review/source language around the plain-language question: where did Samsung Electronics earn the profit, and what should readers check next?
- Visual fail found during direct check: card 05 used a stiff headline shape.
- Recheck: changed card 05 to `지금 질문은 [[이익의 출처]]입니다`, rerendered the post, and reopened card 05 after the fix.
- Final visual result: pass.
- Final payoff: 반도체 이익이 유지되는지, AI 메모리 샘플이 고객 매출로 바뀌는지, 칩 위탁생산 손익이 나아지는지.

### E14-257720-silicon2-kbeauty-tollgate

- Render: `python -X utf8 sns\carousels\render.py E14-257720-silicon2-kbeauty-tollgate`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E14-257720-silicon2-kbeauty-tollgate`
- Cards checked: 01 through 09.
- Initial fail: hook cards 01, 02, 05, 07, 09, 10, and 11 missed headline highlight markers; caption, threads, story brief, review, and loop were broken automatic assembly text.
- Fix: removed the broken 11th card, rewrote the carousel/caption/thread/review/source language around the plain-language question: is Silicon2 a K-beauty brand story or the overseas distribution route?
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Final visual result: pass.
- Final payoff: 유럽 매출이 계속 늘어나는지, 매출에서 남는 이익 비율이 버티는지, 재고와 운반비가 커지지 않는지.

### E15-064350-hyundai-rotem-defense-profit

- Render: `python -X utf8 sns\carousels\render.py E15-064350-hyundai-rotem-defense-profit`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E15-064350-hyundai-rotem-defense-profit`
- Cards checked: 01 through 10.
- Initial fail: hook cards 01, 02, 09, 10, and 11 missed headline highlight markers; caption, threads, story brief, review, and loop were broken automatic assembly text.
- Fix: removed the broken 11th card, rewrote the carousel/caption/thread/review/source language around the plain-language question: is Hyundai Rotem's 1Q profit a rail story or a defense-profit and backlog-conversion story?
- Direct visual result: cards 01 through 10 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Final visual result: pass.
- Final payoff: 수주잔고가 매출로 바뀌는 속도, 방산에서 남는 이익 비율이 유지되는지, 새 주문이 다시 붙는지.

### E16-352820-hybe-stage-outside-numbers

- Render: `python -X utf8 sns\carousels\render.py E16-352820-hybe-stage-outside-numbers`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E16-352820-hybe-stage-outside-numbers`
- Cards checked: 01 through 11.
- Initial fail: hook cards 01, 04, 05, 08, 09, 10, and 11 missed headline highlight markers; caption, story brief, review, and loop were broken automatic assembly text.
- Fix: rewrote the story around the plain-language question: is the important issue the headline loss, or whether fan spending repeats outside concerts?
- Direct visual result: cards 01 through 11 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Final visual result: pass.
- Final payoff: 공연 매출이 회복되는지, 팬덤 결제가 공연 밖에서도 이어지는지, 한 번 비용을 빼고 본 이익이 반복되는지.

### E17-012450-hanwha-aerospace-backlog-to-margin

- Render: `python -X utf8 sns\carousels\render.py E17-012450-hanwha-aerospace-backlog-to-margin`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E17-012450-hanwha-aerospace-backlog-to-margin`
- Cards checked: 01 through 11.
- Initial fail: hook cards 01, 02, 05, 08, 09, 10, and 11 missed headline highlight markers; caption, story brief, review, and loop were broken automatic assembly text.
- Fix: rewrote the story around the plain-language question: is the important issue the size of the backlog, or whether backlog becomes delivery, revenue, and profit?
- Direct visual result: cards 01 through 11 opened one by one; headline accent, long company badge, page dots, number cards, and final payoff were readable.
- Final visual result: pass.
- Final payoff: 전차·장갑차 수출 물량이 회복되는지, 수주잔고가 매출로 바뀌는 속도, 한화오션의 남는 이익 비율이 유지되는지.

### E18-271560-orion-localization-margin

- Render: `python -X utf8 sns\carousels\render.py E18-271560-orion-localization-margin`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E18-271560-orion-localization-margin`
- Cards checked: 01 through 09.
- Initial fail: hook cards 01, 02, 04, 06, 07, 08, and 09 missed headline highlight markers; public copy and source notes used OPM/CAPEX/margin/mix wording.
- Fix: rewrote the story around the plain-language question: is Orion just a snack brand, or is the profit story in local factories and country-by-country economics?
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Final visual result: pass.
- Final payoff: 해외 매출이 어느 나라에서 늘어나는지, 지역별 이익 비율이 버티는지, 설비투자 뒤 매출과 현금이 따라오는지.

### E19-042700-hanmi-tc-bonder-hbm4

- Render: `python -X utf8 sns\carousels\render.py E19-042700-hanmi-tc-bonder-hbm4`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E19-042700-hanmi-tc-bonder-hbm4`
- Cards checked: 01 through 09.
- Initial fail: hook cards 01, 02, 03, 05, 07, 08, and 09 missed headline highlight markers; public copy used TC/HBM/DRAM/margin/risk/customer concentration wording.
- Fix: rewrote the story around the plain-language question: does AI memory demand stop at memory companies, or does it call equipment order books first?
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Final visual result: pass.
- Final payoff: AI 메모리 장비 추가 발주, 한 고객 의존이 줄어드는지, 납품 뒤 이익 비율이 회복되는지.

### E20-009540-hd-ksoe-orders-to-margin

- Render: `python -X utf8 sns\carousels\render.py E20-009540-hd-ksoe-orders-to-margin`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\E20-009540-hd-ksoe-orders-to-margin`
- Cards checked: 01 through 09.
- Initial fail: hook cards 01, 02, 03, 06, 07, 08, and 09 missed headline highlight markers; public copy used VLGC, margin, portfolio, and steel-plate jargon.
- Fix: rewrote the story around the plain-language question: shipbuilding contracts arrive before revenue and profit, so readers should watch delivery timing and cost pass-through.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Final visual result: pass.
- Final payoff: 배가 실제 인도되는 시점, 배 가격이 이익 비율로 남는지, 강판 가격과 환율이 흔드는지.

### X01-disclosure-treasury-cancel

- Render: `python -X utf8 sns\carousels\render.py X01-disclosure-treasury-cancel`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\X01-disclosure-treasury-cancel`
- Cards checked: 01 through 09.
- Initial fail: hook cards 01, 02, 03, 04, 06, 07, 08, and 09 missed headline highlight markers; caption/comment/loop had automatic wording such as `자사주 공시을` and `주당 지표을`; card 07 used EPS/BPS abbreviations.
- Fix: added one headline highlight phrase per editorial/editorialBeat card, rewrote public copy around the plain-language distinction between treasury share acquisition and cancellation, and replaced abbreviations with `주당 이익` and `주당 순자산`.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number card, and final payoff were readable.
- Final visual result: pass.
- Final payoff: 소각 여부, 취득 목적, 주당 지표.

### X02-profit-cashflow-conversion

- Render: `python -X utf8 sns\carousels\render.py X02-profit-cashflow-conversion`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\X02-profit-cashflow-conversion`
- Cards checked: 01 through 09.
- Initial fail: hook cards 01, 02, 03, 04, 06, 07, 08, and 09 missed headline highlight markers; caption/review/loop had automatic wording such as `영업현금흐름와`, `재고을`, and `기준를`; public ending leaned on accounting terms like `연결/별도`.
- Fix: added one headline highlight phrase per editorial/editorialBeat card, rewrote public copy around the plain-language question of why profit and cash differ, and changed the final payoff to reader-language checks.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number card, and final payoff were readable.
- Final visual result: pass.
- Final payoff: 본업 현금흐름, 아직 못 받은 돈과 재고, 누적 기간과 회사 기준.

### X03-policy-market-rates

- Render: `python -X utf8 sns\carousels\render.py X03-policy-market-rates`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\X03-policy-market-rates`
- Cards checked: 01 through 09.
- Initial fail: hook cards 01, 02, 03, 04, 06, 07, 08, and 09 missed headline highlight markers; caption/review/loop had automatic wording such as `금리을`, `간격와`, and `금리차을`; public ending used `스프레드` and `위험 프리미엄`.
- Fix: added one headline highlight phrase per editorial/editorialBeat card, rewrote the story around the plain-language distinction between 기준금리 and market-traded rates, and changed the final payoff to additional borrowing-cost checks.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number card, and final payoff were readable.
- 2026-06-20 context recheck: reopened cards 01 and 02 after the borrowing-cost hook repair; no public `X03` classification number is visible.
- Final visual result: pass.
- Final payoff: 기준금리와 시장금리의 간격, 짧은 금리와 긴 금리의 차이, 회사채와 대출의 추가 금리.

### X04-dartlab-compare-grid

- Render: `python -X utf8 sns\carousels\render.py X04-dartlab-compare-grid`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\X04-dartlab-compare-grid`
- Cards checked: 01 through 09.
- Initial fail: hook cards 01 through 09 missed headline highlight markers; public copy used internal `dartlab.compare`, stiff terms such as `결손 라벨` and `연결/별도`, and automatic wording such as `compare을`, `기간 정렬와`, and `비교 대상 수을`; render also failed once because the first cards referenced a missing background image file.
- Fix: added one headline highlight phrase per editorial/editorialBeat card, rewrote the story around the plain-language point that company comparison is not a ranking table, replaced public terms with `기간 맞춤`, `빈칸 표시`, and `비교 대상 수`, and corrected the background asset path to `period-lock-grid.webp`.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, and final payoff were readable.
- Final visual result: pass.
- Final payoff: 기간 맞춤, 빈칸 표시, 비교 대상 수.

### X05-usd-krw-fx-margin

- Render: `python -X utf8 sns\carousels\render.py X05-usd-krw-fx-margin`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\X05-usd-krw-fx-margin`
- Cards checked: 01 through 09.
- Initial fail: hook cards 01, 03, 04, 05, 06, 07, 08, and 09 missed headline highlight markers; public copy and review records used stiff terms such as `레벨`, `헤지`, `마진`, `노출 구조`, and automatic wording such as `비중와` and `통화을`.
- Fix: added one headline highlight phrase per editorial/editorialBeat card, rewrote the story around the plain-language question of whether a weak won is always good for exporters, and replaced the ending with four concrete checks: 해외 매출 비중, 원재료·부품 결제 방식, 외화 빚과 환율 계약, 남는 이익 비율.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number card, and final payoff were readable.
- Final visual result: pass.
- Final payoff: 해외 매출 비중, 원재료·부품 결제 방식, 외화 빚과 환율 계약, 남는 이익 비율.

### X06-ai-power-demand-grid-bottleneck

- Render: `python -X utf8 sns\carousels\render.py X06-ai-power-demand-grid-bottleneck`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\X06-ai-power-demand-grid-bottleneck`
- Cards checked: 01 through 09.
- Initial fail: hook cards 01, 04, 05, 06, 07, 08, and 09 missed headline highlight markers; public copy and review records used unexplained or stiff terms such as `GPU`, `IEA`, `TWh`, `GW`, `계통 접속`, `납기`, `수주`, `마진`, `현금흐름`, and automatic wording such as `납기을`.
- Fix: added one headline highlight phrase per editorial/editorialBeat card, rewrote the story around the plain-language point that AI servers do not run on AI chips alone, converted technical units into reader-facing `약 2배` and `2~3배` cards, and closed on four concrete checks.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable. Card 02's `약 2배 전망` stat structure is readable but should inform a later number-card unit rule.
- Final visual result: pass.
- Final payoff: 데이터센터 전력 사용, 전기 연결과 변압기 대기, 장비 주문이 현금으로 바뀌는지, 효율 개선과 건설 지연.

### X07-disclosure-supply-contract-profit-gap

- Render: `python -X utf8 sns\carousels\render.py X07-disclosure-supply-contract-profit-gap`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\X07-disclosure-supply-contract-profit-gap`
- Cards checked: 01 through 09.
- Initial fail: hook cards 01, 02, 04, 05, 06, 07, 08, and 09 missed headline highlight markers; public copy and review records used stiff or broken wording such as `수주 공시을`, `마진`, `매출 인식`, `납기`, `검수`, `진행률`, and `확정/조건부`.
- Fix: added one headline highlight phrase per editorial/editorialBeat card, rewrote the story around the plain-language point that a supply-contract disclosure amount is contract size rather than profit, and closed on four concrete checks.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number card, and final payoff were readable.
- Visual fix: card 04 initially rendered the awkward headline `언제 끝나는가입니다`; changed it to `끝나는 시점`, rerendered the post, and reopened card 04.
- Final visual result: pass.
- Final payoff: 계약기간과 납품 일정, 확정 금액과 조건 붙은 금액, 매출로 잡히는 시점, 남는 이익을 흔드는 원가.

### X08-capex-depreciation-cash-timing

- Render: `python -X utf8 sns\carousels\render.py X08-capex-depreciation-cash-timing`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\X08-capex-depreciation-cash-timing`
- Cards checked: 01 through 09.
- Initial fail: hook cards 01, 02, 04, 05, 06, 07, 08, and 09 missed headline highlight markers; public copy and review records used unexplained or stiff terms such as `CAPEX`, `FCF`, `OCF`, `유형자산`, `건설중인자산`, `가동률`, `마진`, `현금흐름`, and automatic wording such as `CAPEX을`, `취득와`.
- Fix: added one headline highlight phrase per editorial/editorialBeat card, changed public framing from `CAPEX` to `설비투자`, rewrote the story around cash leaving first and costs entering profit over time, and closed on four concrete checks.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number card, and final payoff were readable.
- 2026-06-20 context recheck: reopened card 01 after the hook repair; no public `X08` classification number is visible.
- Final visual result: pass.
- Final payoff: 설비 구입액, 짓는 중인 설비와 감가상각, 매출과 공장 사용률, 본업 현금이 투자를 버티는지.

### X09-backtest-suspicion-checklist

- Render: `python -X utf8 sns\carousels\render.py X09-backtest-suspicion-checklist`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\X09-backtest-suspicion-checklist`
- Cards checked: 01 through 09.
- Initial fail: hook cards 01, 02, 04, 05, 06, 07, 08, and 09 missed headline highlight markers; public copy used unexplained or stiff terms such as `slippage`, `t+1`, `OFF`, `B&H`, `OOS`, `벤치마크`, `체결`, and `검증 구간`; cards 07 and 09 also referenced a missing Korean background image filename.
- Fix: added one headline highlight phrase per editorial/editorialBeat card, rewrote the story around the plain-language point that a backtest return is a condition-made number rather than an answer, replaced public terms with `사는 날`, `그냥 들고 갔을 때`, and `다른 기간`, and corrected cards 07 and 09 to use the existing shared asset `oos-gate.webp`.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number card, and final payoff were readable.
- Visual fix: cards 04 and 07 initially rendered with stiff kickers `체결` and `검증 구간`; changed them to `사는 날` and `다른 기간`, rerendered the post, and reopened cards 04 and 07.
- Final visual result: pass.
- Final payoff: 사는 날과 데이터 기준, 수수료와 세금 반영, 그냥 보유와 비교, 다른 기간에서도 버티는지.

### X15-macro-lens-evidence-dashboard

- Render: `python -X utf8 sns\carousels\render.py X15-macro-lens-evidence-dashboard`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py sns\carousels\X15-macro-lens-evidence-dashboard`
- Cards checked: 01 through 09.
- Initial fail: hook cards 01, 02, 04, 05, 06, 07, 08, and 09 missed headline highlight markers; public copy and review records leaned on internal framing such as `Macro Lens`, `매크로 신호`, `근거 단계`, `반증 조건`, `손익 경로`, and point-score language; card 07 used an internal asset filename in the card config.
- Fix: added one headline highlight phrase per editorial/editorialBeat card, rewrote the story around the plain-language point that economic news is not a stock answer sheet, changed the final payoff to four reader-facing checks, and added the shared-asset alias `wrong-condition-rail.png` for the former internal asset filename.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number card, and final payoff were readable.
- Final visual result: pass.
- Final payoff: 움직인 경제 변수, 회사 매출·비용·빚, 실제 숫자 근거, 틀렸다고 볼 조건.

### E21-000270-kia-margin-defense

- Render: `python -X utf8 sns\carousels\render.py E21-000270-kia-margin-defense`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py E21-000270-kia-margin-defense`
- Cards checked: 01 through 09.
- Source check: Kia official newsroom/API pages for 2026 Q1 results, May 2026 sales, and 2026 CEO Investor Day.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Final visual result: pass.
- Final payoff: 영업이익률, 하이브리드와 전기차 판매 비중, 미국 관세와 판매 장려금, 보증비 부담.

### E22-006400-samsung-sdi-loss-narrowing

- Render: `python -X utf8 sns\carousels\render.py E22-006400-samsung-sdi-loss-narrowing`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py E22-006400-samsung-sdi-loss-narrowing`
- Cards checked: 01 through 09.
- Source check: Samsung SDI official newsroom Q1 2026 earnings release and official 2026 Q1 IR PDF.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Visual fix: card 05 initially used the stiff phrase `아직 남는 구조`; changed it to `남은 부담은 아직 확인 전입니다`, rerendered the post, and reopened card 05.
- Final visual result: pass.
- Final payoff: 영업손실률, 전력 저장 배터리 주문, 재고가 줄어드는 속도, 공장 가동률 회복.

### E23-042660-hanwha-ocean-order-margin

- Render: `python -X utf8 sns\carousels\render.py E23-042660-hanwha-ocean-order-margin`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py E23-042660-hanwha-ocean-order-margin`
- Cards checked: 01 through 09.
- Source check: Hanwha Ocean official IR page and 2026 Q1 earnings presentation PDF text extraction.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Image source: reused GPT-generated shared assets in `sns/assets/042660` because the three existing scenes cover dock, ship parts, and design/control room without duplicate meaning.
- Final visual result: pass.
- Final payoff: 상선 이익률, 특수선 손익 전환, 수주잔고의 매출 전환, 고정비와 원가 절감.

### E24-068270-celltrion-sales-channel-profit

- Render: `python -X utf8 sns\carousels\render.py E24-068270-celltrion-sales-channel-profit`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py E24-068270-celltrion-sales-channel-profit`
- Batch audit: `python -X utf8 sns\scripts\auditCarouselEditorialBatch.py --since 2026-06-16 --prefix D --prefix E --prefix X`
- Cards checked: 01 through 09.
- Source check: Celltrion official 2026 Q1 press release and official IR pages.
- Image source: reused GPT-generated shared assets in `sns/assets/068270` because the three existing scenes cover product detail, production site, and research lab without duplicate meaning.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Public identity check: top badges show `셀트리온 068270`; no public `E24`, `d01`, `D01`, `X03`, or other internal classification number is visible on cards, caption, thread, or pinned comment.
- Visual fix: card 03 initially used the decimal-style number `1.145조원`; changed it to `1조 1,450억`, rerendered the post, and reopened card 03.
- Final visual result: pass.
- Final payoff: 신규 제품 매출 비중, 유럽 입찰과 처방, 미국 보험 등재 뒤 처방, 연구개발비 뒤 영업이익률.

### E25-034020-doosan-enerbility-turbine-orders

- Render: `python -X utf8 sns\carousels\render.py E25-034020-doosan-enerbility-turbine-orders`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py E25-034020-doosan-enerbility-turbine-orders`
- Batch audit: `python -X utf8 sns\scripts\auditCarouselEditorialBatch.py --since 2026-06-16 --prefix D --prefix E --prefix X`
- Cards checked: 01 through 09.
- Source check: Doosan Enerbility official 2026 Q1 IR page and Korean/English official IR PDFs.
- Image source: reused GPT-generated shared assets in `sns/assets/034020` because the existing scenes cover turbine factory, dark power equipment interior, and power plant exterior without duplicate meaning.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Public identity check: top badges show `두산에너빌리티 034020`; no public `E25`, `d01`, `D01`, `X03`, or other internal classification number is visible on cards, caption, thread, or pinned comment.
- Final visual result: pass.
- Final payoff: 신규 수주, 수주잔고의 매출 전환, 영업이익률, 현금 유입.

### E26-005380-hyundai-profit-mix-tariff

- Render: `python -X utf8 sns\carousels\render.py E26-005380-hyundai-profit-mix-tariff`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py E26-005380-hyundai-profit-mix-tariff`
- Batch audit: `python -X utf8 sns\scripts\auditCarouselEditorialBatch.py --since 2026-06-16 --prefix D --prefix E --prefix X`
- Cards checked: 01 through 09.
- Source check: Hyundai Motor official 2026 Q1 business-results newsroom release.
- Image source: reused GPT-generated shared assets in `sns/assets/005380` because the existing scenes cover assembly line, hybrid vehicle, export ship, and night factory without duplicate meaning.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Public identity check: top badges show `현대차 005380`; no public `E26`, `d01`, `D01`, `X03`, or other internal classification number is visible on cards, caption, thread, or pinned comment.
- Render note: the render command reached the 120-second shell timeout after producing all nine PNGs; direct file inspection and image QA confirmed the card outputs exist and are readable.
- Final visual result: pass.
- Final payoff: 영업이익률, 하이브리드 비중, 미국 관세 영향, 가격과 비용 방어.

### E27-247540-ecopro-bm-inventory-margin

- Render: `python -X utf8 sns\carousels\render.py E27-247540-ecopro-bm-inventory-margin`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py E27-247540-ecopro-bm-inventory-margin`
- Batch audit: `python -X utf8 sns\scripts\auditCarouselEditorialBatch.py --since 2026-06-16 --prefix D --prefix E --prefix X`
- Cards checked: 01 through 09.
- Source check: ECOPRO BM official 2026 Q1 IR page and official 2026 Q1 IR PDF.
- Image source: reused GPT-generated shared assets in `sns/assets/247540` because the existing scenes cover cathode powder, rotary calciner, and battery pack without duplicate meaning.
- Direct visual result: cards 01 through 09 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Public identity check: top badges show `에코프로비엠 247540`; no public `E27`, `d01`, `D01`, `X03`, or other internal classification number is visible on cards, caption, thread, or pinned comment.
- Final visual result: pass.
- Final payoff: 판매 단가, 원재료 가격, 재고자산, 빚 부담.

### E28-003670-posco-futurem-investment-profit-gap

- Render: `python -X utf8 sns\carousels\render.py E28-003670-posco-futurem-investment-profit-gap`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py E28-003670-posco-futurem-investment-profit-gap`
- Batch audit: `python -X utf8 sns\scripts\auditCarouselEditorialBatch.py --since 2026-06-16 --prefix D --prefix E --prefix X`
- Cards checked: 01 through 10.
- Source check: POSCO Future M official IR reference page and official 2026 Q1 Korean/English IR PDFs.
- Image source: generated four GPT images once and saved them as shared assets in `sns/assets/003670`: cathode powder, battery materials factory line, graphite anode material, and plant expansion site.
- Direct visual result: cards 01 through 10 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Public identity check: top badges show `포스코퓨처엠 003670`; no public `E28`, `d01`, `D01`, `X03`, or other internal classification number is visible on cards, caption, thread, or pinned comment.
- Final visual result: pass.
- Final payoff: 에너지소재 손익, 소재 가격, 설비투자 부담, 차입금.

### E29-329180-hd-hhi-margin-engine

- Render: `python -X utf8 sns\carousels\render.py E29-329180-hd-hhi-margin-engine`
- Gate: `python -X utf8 sns\scripts\checkCarouselEditorial.py E29-329180-hd-hhi-margin-engine`
- Batch audit: `python -X utf8 sns\scripts\auditCarouselEditorialBatch.py --since 2026-06-16 --prefix D --prefix E --prefix X`
- Cards checked: 01 through 10.
- Source check: HD Hyundai Heavy Industries official earnings release page and official 2026 Q1 consolidated earnings release.
- Image source: generated four GPT images once and saved them as shared assets in `sns/assets/329180`: shipyard dry dock, marine engine, ship blocks and steel, night shipyard delivery.
- Direct visual result: cards 01 through 10 opened one by one; headline accent, brand, page dots, number cards, and final payoff were readable.
- Public identity check: top badges show `HD현대중공업 329180`; no public `E29`, `d01`, `D01`, `X03`, or other internal classification number is visible on cards, caption, thread, or pinned comment.
- Final visual result: pass.
- Final payoff: 인도되는 배의 가격, 엔진 이익률, 후판가와 인건비, 영업이익률.

## Remaining

- None.
