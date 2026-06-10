// 재무 전체화면 탭 레지스트리 — finance 심화 카드(terminalFinance.tabCards, 모드 토글 동작)
// + report·교차 카드(연 축 고정, 카드 제목에 '· 연' 표기). 데이터 규칙은 전부 reportSeries.ts
// 로더가 보장 — 본 모듈은 로더 출력 → FinCard 매핑만 한다 (집계·재계산 없음).
// 교차 카드(배당여력·생산성·인건비)는 finBundle.views.annual.statements 의 조 단위 값을
// report 연도와 union 축으로 정렬한다 (결측 = null → MiniFinChart pen-up).
import type { FinCard, Num, TerminalFinanceBundle } from './terminalFinance';
import {
	loadWorkforce,
	loadShareholderReturn,
	loadInvestments,
	loadOwnership,
	loadExecBoard,
	loadDebtProfile
} from './reportSeries';

export interface TabCard {
	card: FinCard;
	periods: string[];
}
export interface FsTab {
	key: string;
	label: { kr: string; en: string };
	finKey?: 'profitability' | 'cashflow' | 'debt'; // terminalFinance.tabCards 키 (모드 토글 동작)
	load?: (code: string, bundle: TerminalFinanceBundle) => Promise<TabCard[]>; // report·교차 (연 축)
	note?: string; // 탭 하단 정직성 캡션
}

const C = { rev: '#5b9bf0', op: '#fb923c', net: '#34d399', good: '#34d399', warn: '#fbbf24', purple: '#a78bfa', red: '#f0616f', blue: '#60a5fa', cyan: '#22d3ee', dim: '#64748b' };

const fyLabel = (year: string) => 'FY' + year.slice(2);
// 시리즈 전부 null 인 카드는 버린다 (빈 카드 노출 금지 — 신규 탭 공통 규칙)
const alive = (tc: TabCard): boolean => tc.card.series.some((s) => s.data.some((v) => v != null));

// finance annual statements 에서 계정 1행을 연도('2024') → 조 값 Map 으로
function annualMap(bundle: TerminalFinanceBundle, stmt: 'IS' | 'CF', key: string): Map<string, number> {
	const out = new Map<string, number>();
	const av = bundle.views.annual;
	if (!av) return out;
	const row = av.statements[stmt].find((r) => r.key === key);
	if (!row) return out;
	av.periods.forEach((p, i) => {
		const m = p.match(/^FY(\d{2})$/);
		const v = row.values[i];
		if (m && v != null) out.set('20' + m[1], v);
	});
	return out;
}

async function cashflowReport(code: string): Promise<TabCard[]> {
	const inv = await loadInvestments(code);
	if (!inv || inv.trend.length < 2) return [];
	const years = inv.trend.map((t) => t.year);
	const tc: TabCard = {
		periods: years.map(fyLabel),
		card: {
			key: 'investedBook', title: '타법인출자 추이 · 연', unit: '조', series: [
				{ name: '출자 장부가', data: inv.trend.map((t) => (t.bookTotal != null ? +(t.bookTotal / 1e12).toFixed(3) : null)), color: C.blue, type: 'bar' },
				{ name: '출자사 수(개)', data: inv.trend.map((t) => t.count), color: C.warn, type: 'line', axis: 'r' }
			]
		}
	};
	return [tc].filter(alive);
}

async function shareholderReport(code: string, bundle: TerminalFinanceBundle): Promise<TabCard[]> {
	const [sr, own] = await Promise.all([loadShareholderReturn(code), loadOwnership(code)]);
	const cards: TabCard[] = [];
	if (sr && sr.length) {
		const srYears = sr.map((s) => s.year);
		cards.push({
			periods: srYears.map(fyLabel),
			card: {
				key: 'dpsYield', title: '주당배당·수익률 · 연', unit: '원', series: [
					{ name: 'DPS', data: sr.map((s) => s.dps), color: C.blue, type: 'bar' },
					{ name: '시가배당수익률%', data: sr.map((s) => s.yieldPct), color: C.good, type: 'line', axis: 'r' }
				]
			}
		});
		// 배당여력 — report 연도 ∪ finance annual 연도 union 축 (비12월 결산은 사업연도 기준 정렬)
		const niBy = annualMap(bundle, 'IS', 'netIncome');
		const cfoBy = annualMap(bundle, 'CF', 'cfOperating');
		const capexBy = annualMap(bundle, 'CF', 'capex');
		const years = [...new Set([...srYears, ...niBy.keys()])].sort();
		const srBy = new Map(sr.map((s) => [s.year, s]));
		cards.push({
			periods: years.map(fyLabel),
			card: {
				key: 'payoutCoverage', title: '배당여력 (배당 vs FCF vs 순이익) · 연', unit: '조', series: [
					{ name: '배당총액', data: years.map((y) => { const v = srBy.get(y)?.totalDividend; return v != null ? +(v / 1e12).toFixed(3) : null; }), color: C.blue, type: 'bar' },
					{ name: 'FCF', data: years.map((y) => { const op = cfoBy.get(y); return op != null ? +(op - (capexBy.get(y) ?? 0)).toFixed(3) : null; }), color: C.warn, type: 'bar' },
					{ name: '순이익', data: years.map((y) => niBy.get(y) ?? null), color: C.net, type: 'bar' },
					{ name: '배당성향%', data: years.map((y) => srBy.get(y)?.payoutPct ?? null), color: C.purple, type: 'line', axis: 'r' }
				]
			}
		});
		cards.push({
			periods: srYears.map(fyLabel),
			card: {
				key: 'buybackFlow', title: '자사주 (보통주) · 연', unit: '만주', signed: true, series: [
					{ name: '취득', data: sr.map((s) => (s.buybackQty != null ? +(s.buybackQty / 1e4).toFixed(1) : null)), color: C.good, type: 'bar' },
					{ name: '처분(−)', data: sr.map((s) => (s.disposalQty != null ? +(-s.disposalQty / 1e4).toFixed(1) : null)), color: C.warn, type: 'bar' },
					{ name: '소각(−)', data: sr.map((s) => (s.buybackCancel != null ? +(-s.buybackCancel / 1e4).toFixed(1) : null)), color: C.red, type: 'bar' },
					{ name: '기말보유', data: sr.map((s) => (s.treasuryEnd != null ? +(s.treasuryEnd / 1e4).toFixed(1) : null)), color: C.cyan, type: 'line', axis: 'r' }
				]
			}
		});
	}
	if (own && own.length) {
		cards.push({
			periods: own.map((o) => fyLabel(o.year)),
			card: {
				key: 'ownership', title: '소유구조 · 연', unit: '%', series: [
					{ name: '최대주주측', data: own.map((o) => o.majorPct), color: C.red, type: 'line' },
					{ name: '소액주주', data: own.map((o) => o.minorPct), color: C.blue, type: 'line' },
					{ name: '소액주주수(만명)', data: own.map((o) => (o.minorCount != null ? +(o.minorCount / 1e4).toFixed(2) : null)), color: C.dim, type: 'line', axis: 'r' }
				]
			}
		});
	}
	return cards.filter(alive);
}

async function peopleReport(code: string, bundle: TerminalFinanceBundle): Promise<TabCard[]> {
	const [wf, eb] = await Promise.all([loadWorkforce(code), loadExecBoard(code)]);
	const cards: TabCard[] = [];
	if (wf && wf.length) {
		const wfYears = wf.map((w) => w.year);
		const wfP = wfYears.map(fyLabel);
		cards.push({
			periods: wfP,
			card: {
				key: 'headcount', title: '인원 구성 · 연', unit: '명', stacked: true, series: [
					{ name: '정규직', data: wf.map((w) => w.regular), color: C.blue, type: 'bar' },
					{ name: '계약직', data: wf.map((w) => w.contract), color: C.warn, type: 'bar' },
					{ name: '계약직 비중%', data: wf.map((w) => (w.regular != null && w.contract != null && w.regular + w.contract > 0 ? +((w.contract / (w.regular + w.contract)) * 100).toFixed(1) : null)), color: C.red, type: 'line', axis: 'r' }
				]
			}
		});
		cards.push({
			periods: wfP,
			card: {
				key: 'payTenure', title: '급여·근속 · 연', unit: '백만원', series: [
					{ name: '1인평균급여', data: wf.map((w) => (w.avgSalary != null ? +(w.avgSalary / 1e6).toFixed(0) : null)), color: C.good, type: 'bar' },
					{ name: '근속연수(년)', data: wf.map((w) => w.tenure), color: C.purple, type: 'line', axis: 'r' }
				]
			}
		});
		// 생산성·인건비 — finance annual 교차 (조 → 억: ×1e4)
		const revBy = annualMap(bundle, 'IS', 'revenue');
		const opBy = annualMap(bundle, 'IS', 'operatingIncome');
		const wfBy = new Map(wf.map((w) => [w.year, w]));
		const years = [...new Set([...wfYears, ...revBy.keys()])].sort();
		const perEmp = (y: string, v: number | undefined): Num => {
			const t = wfBy.get(y)?.total;
			return v != null && t != null && t > 0 ? +((v * 1e4) / t).toFixed(1) : null;
		};
		cards.push({
			periods: years.map(fyLabel),
			card: {
				key: 'laborProductivity', title: '1인당 생산성 · 연', unit: '억', series: [
					{ name: '1인당 매출', data: years.map((y) => perEmp(y, revBy.get(y))), color: C.rev, type: 'bar' },
					{ name: '1인당 영업이익', data: years.map((y) => perEmp(y, opBy.get(y))), color: C.op, type: 'line' }
				]
			}
		});
		cards.push({
			periods: years.map(fyLabel),
			card: {
				key: 'laborShare', title: '인건비 부담 (직원 급여) · 연', unit: '조', series: [
					{ name: '급여총액', data: years.map((y) => { const v = wfBy.get(y)?.totalSalary; return v != null ? +(v / 1e12).toFixed(3) : null; }), color: C.blue, type: 'bar' },
					{ name: '급여/매출%', data: years.map((y) => { const v = wfBy.get(y)?.totalSalary; const r = revBy.get(y); return v != null && r != null && r > 0 ? +((v / 1e12 / r) * 100).toFixed(1) : null; }), color: C.warn, type: 'line', axis: 'r' },
					{ name: '급여/영업이익%', data: years.map((y) => { const v = wfBy.get(y)?.totalSalary; const o = opBy.get(y); return v != null && o != null && o > 0 ? +((v / 1e12 / o) * 100).toFixed(1) : null; }), color: C.red, type: 'line', axis: 'r' }
				]
			}
		});
		if (eb && eb.length) {
			cards.push({
				periods: eb.map((e) => fyLabel(e.year)),
				card: {
					key: 'execPay', title: '이사·감사 보수 · 연', unit: '억', series: [
						{ name: '1인평균 보수', data: eb.map((e) => (e.execAvgPay != null ? +(e.execAvgPay / 1e8).toFixed(2) : null)), color: C.op, type: 'bar' },
						{ name: '임원/직원 배율(배)', data: eb.map((e) => { const w = wfBy.get(e.year)?.avgSalary; return e.execAvgPay != null && w != null && w > 0 ? +(e.execAvgPay / w).toFixed(1) : null; }), color: C.purple, type: 'line', axis: 'r' }
					]
				}
			});
		}
	}
	if (eb && eb.length) {
		cards.push({
			periods: eb.map((e) => fyLabel(e.year)),
			card: {
				key: 'board', title: '이사회 구성 · 연', unit: '명', stacked: true, series: [
					{ name: '사외이사', data: eb.map((e) => e.outsideDirectors), color: C.good, type: 'bar' },
					{ name: '사내이사', data: eb.map((e) => (e.directors != null && e.outsideDirectors != null ? e.directors - e.outsideDirectors : null)), color: C.dim, type: 'bar' },
					{ name: '사외이사 비율%', data: eb.map((e) => (e.directors != null && e.directors > 0 && e.outsideDirectors != null ? +((e.outsideDirectors / e.directors) * 100).toFixed(0) : null)), color: C.cyan, type: 'line', axis: 'r' }
				]
			}
		});
	}
	return cards.filter(alive);
}

async function debtReport(code: string): Promise<TabCard[]> {
	const dpr = await loadDebtProfile(code);
	if (!dpr || !dpr.length) return [];
	const series: FinCard['series'] = [
		{ name: '1년이하', data: dpr.map((d) => (d.bond1y != null ? +(d.bond1y / 1e12).toFixed(3) : null)), color: C.red, type: 'bar' },
		{ name: '1~5년', data: dpr.map((d) => (d.bond1to5 != null ? +(d.bond1to5 / 1e12).toFixed(3) : null)), color: C.op, type: 'bar' },
		{ name: '5~10년', data: dpr.map((d) => (d.bond5to10 != null ? +(d.bond5to10 / 1e12).toFixed(3) : null)), color: C.blue, type: 'bar' },
		{ name: '10년초과', data: dpr.map((d) => (d.bond10plus != null ? +(d.bond10plus / 1e12).toFixed(3) : null)), color: C.purple, type: 'bar' }
	];
	// 초단기물(전단채+CP) — 보유율 ~5% 라 단독 카드 금지, 유효 연도가 있을 때만 조건부 시리즈
	if (dpr.some((d) => d.stb != null || d.cp != null)) {
		series.push({ name: '초단기물(전단채+CP)', data: dpr.map((d) => (d.stb != null || d.cp != null ? +(((d.stb ?? 0) + (d.cp ?? 0)) / 1e12).toFixed(3) : null)), color: C.cyan, type: 'line' });
	}
	const tc: TabCard = {
		periods: dpr.map((d) => fyLabel(d.year)),
		card: { key: 'bondMaturity', title: '사채 만기 사다리 · 연', unit: '조', stacked: true, series }
	};
	return [tc].filter(alive);
}

export const FS_TABS: FsTab[] = [
	{ key: 'profitability', label: { kr: '수익성', en: 'PROFIT' }, finKey: 'profitability' },
	{ key: 'cashflow', label: { kr: '현금·투자', en: 'CASH' }, finKey: 'cashflow', load: cashflowReport },
	{
		key: 'shareholder', label: { kr: '주주환원·소유', en: 'RETURN' }, load: shareholderReport,
		note: '배당·자사주 = 보통주 기준 공시값 · report. 배당여력의 FCF·순이익 = 연간 재무제표 교차.'
	},
	{
		key: 'people', label: { kr: '인력·보수', en: 'PEOPLE' }, load: peopleReport,
		note: '급여 = 직원 급여만(임원·복리후생 제외), 사업보고서 연간 확정값. 보수 = 이사·감사 전체(등기 구분 미공시).'
	},
	{
		key: 'debt', label: { kr: '부채·만기', en: 'DEBT' }, finKey: 'debt', load: debtReport,
		note: '만기 사다리 = 액면 기준 미상환 잔액(report) — 장부가와 소폭 차이. 무사채 회사는 카드 비표시.'
	}
];
