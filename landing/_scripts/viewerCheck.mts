// 공시뷰어 readWide 포팅 순수단위 검증 (데이터 불필요). Python canonicalChapterExpr / _viewerUrlForFiling 대조.
// 실행: cd landing && npx tsx _scripts/viewerCheck.mts
// (전체 parity = data/dart/panel 로컬 필요, 별도 수동 — 본 스크립트는 결정론 순수함수만.)
import { canonicalChapter, isReportChapter } from '../src/lib/viewer/canonical.ts';
import { edgarSectionStatus } from '../src/lib/viewer/edgarSection.ts';
import { viewerUrl, marketForCode } from '../src/lib/viewer/dartUrl.ts';

let fail = 0;
const eq = (got: unknown, exp: unknown, label: string) => {
	if (JSON.stringify(got) !== JSON.stringify(exp)) { fail++; console.log('FAIL', label, '\n  got', JSON.stringify(got), '\n  exp', JSON.stringify(exp)); }
};

// canonicalChapter — 붕괴 II→III 복원·(첨부)→III·배당/증권발행→III·depth V·honest fallback (Python 대조값).
eq(canonicalChapter('II. 사업의 내용', 'II. 사업의 내용␟III. 재무에 관한 사항'), 'III. 재무에 관한 사항', 'collapse II→III');
eq(canonicalChapter('II. 사업의 내용', 'II. 사업의 내용'), 'II. 사업의 내용', 'no-collapse II');
eq(canonicalChapter('III. 재무에 관한 사항', '(첨부)재무제표'), 'III. 재무에 관한 사항', '(첨부)→III');
eq(canonicalChapter('6. 배당에 관한 사항', '6. 배당에 관한 사항'), 'III. 재무에 관한 사항', '배당→III');
eq(canonicalChapter('7. 증권의 발행을 통한 자금조달에 관한 사항', '7. 증권의 발행을 통한 자금조달에 관한 사항'), 'III. 재무에 관한 사항', '증권발행→III');
eq(canonicalChapter('별난 챕터', '별난 챕터'), '별난 챕터', 'honest fallback');
eq(canonicalChapter('II. 사업의 내용', 'II. 사업의 내용␟V. 회계감사인의 감사의견 등␟외부감사'), 'V. 회계감사인의 감사의견 등', 'depth V');

// isReportChapter — navigable 보고서 챕터(I~XII)만, cert(cover/expert)·EDGAR form·stray 제외 (Python REPORT_CHAPTER_LABELS).
eq(isReportChapter('III. 재무에 관한 사항'), true, 'isReport III');
eq(isReportChapter('VII. 주주에 관한 사항'), true, 'isReport VII');
eq(isReportChapter('【 대표이사 등의 확인 】'), false, 'isReport cover=false');
eq(isReportChapter('【 전문가의 확인 】'), false, 'isReport expert=false');
eq(isReportChapter('10-K'), false, 'isReport form=false');
eq(isReportChapter('6. 배당에 관한 사항'), false, 'isReport stray=false');

// edgarSectionStatus — 카탈로그 표준명 정확일치 게이트 (Python mapper.edgarSectionStatus 대조).
eq(edgarSectionStatus('10-K', 'Item 1. Business'), 'navi', 'edgar navi item1');
eq(edgarSectionStatus('10-K', 'Item 1A. Risk Factors'), 'navi', 'edgar navi 1A');
eq(edgarSectionStatus('10-K', "Item 5. Market for Registrant's Common Equity"), 'navi', 'edgar navi 5 apostrophe');
eq(edgarSectionStatus('10-K', 'BS'), 'stmt', 'edgar stmt BS');
eq(edgarSectionStatus('10-K', '10-K'), 'junk', 'edgar junk cover');
eq(edgarSectionStatus('10-K', 'Item 405. Of Regulation S-K (§229'), 'junk', 'edgar junk 405');
eq(edgarSectionStatus('10-Q', 'Item 8. Of Our Annual Report On Form'), 'junk', 'edgar junk 10Q item8');
eq(edgarSectionStatus('10-K', 'Item 1A. Risk Factors You Should Carefully Consider'), 'junk', 'edgar junk prose tail');
eq(edgarSectionStatus('20-F', 'Item 16A. Audit Committee Financial Expert'), 'navi', 'edgar 20-F keep-all');

// viewerUrl — KR DART(rcpNo) / US SEC(filing index, cik=accession 앞10자리).
eq(viewerUrl(marketForCode('005930'), '20260515002181'), 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260515002181', 'KR DART');
eq(viewerUrl(marketForCode('AAPL'), '0000320193-25-000079'), 'https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/0000320193-25-000079-index.htm', 'US SEC');
eq(viewerUrl('US', null), null, 'US null');

console.log(fail === 0 ? 'viewerCheck: ALL OK (25/25)' : `viewerCheck: ${fail} FAIL`);
process.exit(fail === 0 ? 0 : 1);
