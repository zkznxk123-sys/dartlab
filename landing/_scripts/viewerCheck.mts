// 공시뷰어 readWide 포팅 순수단위 검증 (데이터 불필요). Python canonicalChapterExpr / _viewerUrlForFiling 대조.
// 실행: cd landing && npx tsx _scripts/viewerCheck.mts
// (전체 parity = data/dart/panel 로컬 필요, 별도 수동 — 본 스크립트는 결정론 순수함수만.)
import { canonicalChapter, isReportChapter } from '../src/lib/viewer/canonical.ts';
import { edgarSectionStatus } from '../src/lib/viewer/edgarSection.ts';
import { narrativeCore, computePeriodKind } from '../src/lib/viewer/panelWide.ts';
import { userMarkClass } from '../src/lib/viewer/cell.ts';
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

// narrativeCore — 번호·'등' strip + NOTE_TITLE_NORM 정규화 (Python read._narrativeCore 대조). era 변종이 같은 코어로.
eq(narrativeCore('6. 배당에 관한 사항 등'), '배당에관한사항', 'core 배당 등');
eq(narrativeCore('6. 배당에 관한 사항'), '배당에관한사항', 'core 배당');
eq(narrativeCore('6. 기타 재무에 관한 사항'), '기타재무에관한사항', 'core 기타재무 옛번호');
eq(narrativeCore('8. 기타 재무에 관한 사항'), '기타재무에관한사항', 'core 기타재무 현행');
eq(narrativeCore('7-1. 증권의 발행을 통한 자금조달 실적'), '증권의발행을통한자금조달실적', 'core 7-1');

// computePeriodKind — 회사별 결산 보정: 연간보고서 분기(본문 dominant) 검출. 12월결산=Q4, 3월결산=Q1.
const decP = ['2020Q1', '2020Q2', '2020Q3', '2020Q4', '2021Q1', '2021Q2', '2021Q3', '2021Q4'];
const decC = Object.fromEntries(decP.map((p) => [p, p.endsWith('Q4') ? 3000 : 1400]));
eq(computePeriodKind(decP, decC)['2021Q4'], 'annual', 'periodKind Dec Q4=annual');
eq(computePeriodKind(decP, decC)['2021Q2'], 'quarter', 'periodKind Dec Q2=quarter');
const marC = Object.fromEntries(decP.map((p) => [p, p.endsWith('Q1') ? 3000 : 1400])); // 3월 결산: Q1 본문 dominant
eq(computePeriodKind(decP, marC)['2021Q1'], 'annual', 'periodKind March Q1=annual');
eq(computePeriodKind(decP, marC)['2021Q4'], 'quarter', 'periodKind March Q4=quarter');

// userMarkClass — DART USERMARK → 헤딩 구조 class. F-14↑=헤딩, standalone B=볼드, 본문/폰트패밀리=무.
eq(userMarkClass('F-14 B'), 'dm-h', 'um F-14 B 헤딩');
eq(userMarkClass('F-16 B'), 'dm-h', 'um F-16 B 헤딩');
eq(userMarkClass(' B'), 'dm-b', 'um B 볼드');
eq(userMarkClass('F-10'), '', 'um F-10 본문');
eq(userMarkClass('F-BT12'), '', 'um F-BT12 폰트패밀리 오탐X');
eq(userMarkClass('0X0000FF'), '', 'um 색상 무시');

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

console.log(fail === 0 ? 'viewerCheck: ALL OK (40/40)' : `viewerCheck: ${fail} FAIL`);
process.exit(fail === 0 ? 0 : 1);
