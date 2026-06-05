// 공시뷰어 readWide 포팅 순수단위 검증 (데이터 불필요). Python canonicalChapterExpr / _viewerUrlForFiling 대조.
// 실행: cd landing && npx tsx _scripts/viewerCheck.mts
// (전체 parity = data/dart/panel 로컬 필요, 별도 수동 — 본 스크립트는 결정론 순수함수만.)
import { canonicalChapter, isReportChapter } from '../src/lib/viewer/canonical.ts';
import { edgarSectionStatus } from '../src/lib/viewer/edgarSection.ts';
import { narrativeCore } from '../src/lib/viewer/pipeline/narrativeSpine.ts';
import { computePeriodKind } from '../src/lib/viewer/periodKind.ts';
import { userMarkClass } from '../src/lib/viewer/cell.ts';
import { mergeDriftVariants, accountDepth, sceComponent, buildSceMatrix, buildSql } from '../src/lib/viewer/finance/financePivot.ts';
import { toCsv, cellText, financeToExcel } from '../src/lib/viewer/dataExport.ts';
import { viewerUrl, marketForCode } from '../src/lib/viewer/dartUrl.ts';
import { buildCompareBoard, compareRows, detectFinanceUnit, normalizeCompareTargets } from '../src/lib/viewer/compare/index.ts';
import type { PanelBundle, PanelRow } from '../src/lib/viewer/types.ts';

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

// mergeDriftVariants — 같은 label·기간 비충돌(era-drift 태그 변종) 병합, 공존 동명(기간 겹침)은 분리.
const drift = mergeDriftVariants([
	{ accountId: 'A', label: '수익(매출액)', ord: 0, depth: 2, values: { '2016': 100, '2017': 110 } }, // 옛 태그
	{ accountId: 'B', label: '수익(매출액)', ord: 0, depth: 2, values: { '2024': 300, '2025': 333 } }, // 현 태그 (기간 비충돌)
	{ accountId: 'C', label: '기타', ord: 5, depth: 2, values: { '2024': 10 } }, // 공존 기타
	{ accountId: 'D', label: '기타', ord: 6, depth: 2, values: { '2024': 20 } } // 같은해 기타 (충돌 → 분리)
]);
eq(drift.filter((r) => r.label === '수익(매출액)').length, 1, 'drift 동의어 병합 1행');
eq(drift.find((r) => r.label === '수익(매출액)')?.values['2016'], 100, 'drift 병합 옛값 보존');
eq(drift.find((r) => r.label === '수익(매출액)')?.values['2025'], 333, 'drift 병합 현값 보존');
eq(drift.filter((r) => r.label === '기타').length, 2, '공존 동명 분리 유지');

// accountDepth — account_id XBRL 구조: 총계 0·소계 1·리프 2.
eq(accountDepth('ifrs-full_Assets'), 0, 'depth 자산총계=0');
eq(accountDepth('ifrs-full_ProfitLoss'), 0, 'depth 당기순이익=0');
eq(accountDepth('ifrs-full_CurrentAssets'), 1, 'depth 유동자산=1');
eq(accountDepth('dart_OperatingIncomeLoss'), 1, 'depth 영업이익=1');
eq(accountDepth('ifrs-full_CashAndCashEquivalents'), 2, 'depth 현금=2(리프)');
eq(accountDepth('dart_ShortTermOtherReceivables'), 2, 'depth 미수금=2(리프)');

// sceComponent — account_detail 경로 끝 = 자본구성요소, 연결재무제표/재무제표 [member] = 자본총계.
eq(sceComponent('자본 [구성요소]|지배기업의 소유주에게 귀속되는 지분 [구성요소]|자본금 [구성요소]'), '자본금', 'sceComp 자본금');
eq(sceComponent('연결재무제표 [member]'), '자본총계', 'sceComp 연결총계');
eq(sceComponent(null), '기타', 'sceComp null');

// buildSceMatrix — 기간 desc, 자본총계 열 마지막, 변동유형 ord 정렬.
const sce = buildSceMatrix(
	[
		{ period: '2024', label: '당기순이익', comp: '이익잉여금', val: 100, ord: 5 },
		{ period: '2024', label: '당기순이익', comp: '자본총계', val: 100, ord: 5 },
		{ period: '2024', label: '기초자본', comp: '자본금', val: 50, ord: 1 },
		{ period: '2023', label: '배당', comp: '자본총계', val: -20, ord: 6 }
	],
	'CFS'
);
eq(sce.periods, ['2024', '2023'], 'sceMatrix 기간 desc');
eq(sce.components[sce.components.length - 1], '자본총계', 'sceMatrix 자본총계 마지막 열');
eq(sce.byPeriod['2024'][0].label, '기초자본', 'sceMatrix ord 정렬(기초자본 먼저)');
eq(sce.byPeriod['2024'][1].values['자본총계'], 100, 'sceMatrix 당기순이익 자본총계 셀');

// buildSql 분기 단독 — Q4 = 연간−Q3누적 포함.
const qsql = buildSql('005930', 'IS', 'quarter', 'CFS');
eq(/'Q4'/.test(qsql) && /yr_amt - q3cum/.test(qsql), true, 'buildSql 분기 Q4(연간−Q3누적) 포함');

// dataExport — CSV(BOM·인용 escaping)·cellText(태그·엔티티 제거)·financeToExcel(SpreadsheetML 멀티시트).
eq(toCsv([['a']]).charCodeAt(0), 0xfeff, 'csv UTF-8 BOM');
eq(toCsv([['a,b', 'c']]).includes('"a,b"'), true, 'csv 콤마 인용');
eq(toCsv([['he"llo']]).includes('"he""llo"'), true, 'csv 따옴표 이스케이프');
eq(cellText('<p>가<br>나</p>'), '가 나', 'cellText 태그 제거');
eq(cellText('a&amp;b&nbsp;c'), 'a&b c', 'cellText 엔티티 디코드');
eq(cellText(undefined), '', 'cellText undefined');
const xls = financeToExcel([
	{
		name: '손익계산서',
		statement: { kind: 'IS', scope: 'CFS', freq: 'annual', periods: ['2024'], unit: 'KRW', rows: [{ accountId: 'A', label: '매출액', ord: 0, depth: 2, values: { '2024': 100 } }] }
	}
]);
eq(/ss:Name="손익계산서"/.test(xls), true, 'xls 시트명');
eq(/ss:Type="Number">100</.test(xls), true, 'xls 숫자셀');
eq(xls.includes('progid="Excel.Sheet"'), true, 'xls Excel 헤더');

const cmpRow = (patch: Partial<PanelRow>): PanelRow => ({
	chapter: 'III. 재무에 관한 사항',
	sectionLeaf: '2. 연결재무제표',
	blockLeaf: '',
	leafType: 'body',
	disclosureKey: null,
	scope: null,
	blockType: 'text',
	cells: { '2026Q1': '본문' },
	...patch
});
const cmpBundle = (stockCode: string, rows: PanelRow[]): PanelBundle => ({
	stockCode,
	corpName: stockCode,
	toc: { stockCode, corpName: stockCode, chapters: [], periods: ['2026Q1'] },
	periods: ['2026Q1'],
	gridBySection: new Map([['III. 재무에 관한 사항␟2. 연결재무제표', rows]]),
	dartUrlByPeriod: {},
	periodKind: { '2026Q1': 'quarter' }
});

const narrCmp = compareRows(
	[
		cmpBundle('005930', [cmpRow({ cells: { '2026Q1': '삼성 서술 1' } })]),
		cmpBundle('000660', [cmpRow({ cells: { '2026Q1': 'SK 서술 1' } })])
	],
	'III. 재무에 관한 사항␟2. 연결재무제표',
	'2026Q1'
).rows;
eq(narrCmp.length, 2, 'compare narrative 회사행 분리');
eq(narrCmp.every((r) => r.cells.filter((c) => c != null).length === 1), true, 'compare narrative false-merge 금지');
eq(
	buildCompareBoard(
		[
			cmpBundle('005930', [cmpRow({ cells: { '2026Q1': '삼성 서술 1' } })]),
			cmpBundle('000660', [cmpRow({ cells: { '2026Q1': 'SK 서술 1' } })])
		],
		{ sectionKey: 'III. 재무에 관한 사항␟2. 연결재무제표', period: '2026Q1' }
	).diagnostics.mode,
	'row',
	'compare board row entrypoint'
);

const leafCmp = compareRows(
	[
		cmpBundle('005930', [
			cmpRow({ disclosureKey: 'NT_X', scope: 'consolidated', leafType: 'table-a', blockType: 'table', cells: { '2026Q1': 'A' } }),
			cmpRow({ disclosureKey: 'NT_X', scope: 'consolidated', leafType: 'table-b', blockType: 'table', cells: { '2026Q1': 'B' } })
		]),
		cmpBundle('000660', [])
	],
	'III. 재무에 관한 사항␟2. 연결재무제표',
	'2026Q1'
).rows;
eq(leafCmp.length, 2, 'compare key leafType 분리');

const unitRows = [
	cmpRow({
		blockType: 'table',
		cells: {
			'2026Q1':
				'<P>(단위:백만원)</P><TABLE><TR><TE ACODE="ifrs-full_Revenue" ACONTEXT="CFY2026dFQ_ifrs-full_ConsolidatedMember">1,234</TE></TR><TR><TE>기본주당이익(손실)(단위:원)</TE><TE ACODE="ifrs-full_BasicEarningsLossPerShare" ACONTEXT="CFY2026dFQ_ifrs-full_ConsolidatedMember">10</TE></TR></TABLE>'
		}
	})
];
eq(detectFinanceUnit(unitRows, '2026Q1').label, '백만원', 'finance unit 캡션이 EPS 원보다 우선');
eq(detectFinanceUnit([cmpRow({ cells: { '2026Q1': '<TE ACODE="ifrs-full_Assets">2,000,000,000,000</TE>' } })], '2026Q1').label, '원', 'finance unit 캡션부재 magnitude 원');
eq(normalizeCompareTargets('005930', '000660,005930,AAPL,000660').vs, ['000660'], 'compare targets self/dup/cross-market 제거');
eq(normalizeCompareTargets('005930', '000001,000002,000003,000004,000005,000006').vs.length, 5, 'compare targets 총 6사 제한');
eq(normalizeCompareTargets('AAPL', 'msft,aapl').vs, ['MSFT'], 'compare targets US ticker 대문자 정규화');

console.log(fail === 0 ? 'viewerCheck: ALL OK (75/75)' : `viewerCheck: ${fail} FAIL`);
process.exit(fail === 0 ? 0 : 1);
