// 리얼타임 기업분석보고서 조립기 — 데이터 작업대 포트(finance/search)만 사용.
// 정적 bake JSON 폐기. 모든 수치는 runtime.finance.bundle(HF parquet 직독) 결과를 조회 시점에 계산.
import type {
	DartLabRuntime,
	TerminalFinanceBundle,
	TerminalFinance,
	IndexRow,
	Num
} from '@dartlab/ui-contracts';
import { loadJson } from '@dartlab/ui-runtime/data/dartlabData';
import type { ReportBlock, ReportModel, ReportResult, ReportSection } from './model';
import { lastNonNull } from './model';
import { findPerspective, type PerspectiveMeta } from './perspectives';
import type { ShareholderReturnYear, CapitalChangesBundle } from '@dartlab/ui-contracts';
import { pYear, fmtPct, fmtPctSigned, fmtMult, fmtAmt1, scaleAmt, fmtScaled, fmtRange, fmtShares, fmtWon } from './format';

// ── 공통 유틸 ──────────────────────────────────────────────
function annualView(fin: TerminalFinanceBundle): TerminalFinance | null {
	return fin.views.annual ?? fin.views[fin.defaultMode] ?? null;
}

function latestFiled(fin: TerminalFinanceBundle): string | null {
	const ds = Object.values(fin.filedDates ?? {})
		.filter((d): d is string => !!d && d.length >= 8)
		.sort();
	const d = ds[ds.length - 1];
	if (!d) return null;
	return `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`;
}

const last = <T,>(arr: T[]): T => arr[arr.length - 1];

// 금액 표(단일 단위 스케일) — 빈 행 자동 제거. 유효 행 0이면 null.
function coverage(values: Num[]): number {
	return values.filter((v) => v != null && Number.isFinite(v)).length;
}

// 일회성 스파이크 탐지 — 한 칸이 본업 추세를 압도(중앙값 4배 초과 & 절대 60 초과)하면 {연도,값}.
// 값은 *건드리지 않고*(정직), 본문에 맥락 각주만 붙인다(NAVER FY21 순이익률 241.7% 등).
function detectOneOff(values: Num[], yearCols: string[]): { year: string; value: number } | null {
	const pairs = values
		.map((v, i) => ({ v, year: yearCols[i] }))
		.filter((p): p is { v: number; year: string } => p.v != null && Number.isFinite(p.v));
	if (pairs.length < 3) return null;
	const absSorted = pairs.map((p) => Math.abs(p.v)).sort((a, b) => a - b);
	const med = absSorted[Math.floor(absSorted.length / 2)] || 1;
	for (const p of pairs) {
		if (Math.abs(p.v) > 60 && Math.abs(p.v) > med * 4) return { year: p.year, value: p.v };
	}
	return null;
}

function amtTable(
	rows: { label: string; values: Num[] }[],
	yearCols: string[],
	labelHeader: string,
	caption: string
): ReportBlock | null {
	// 저커버리지 행 제거 — 떨이 단일값(예: NAVER 매출원가 1개)이 표를 더럽히지 않게.
	const present = rows.filter((r) => coverage(r.values) >= 2);
	if (!present.length) return null;
	const allVals = present.flatMap((r) => r.values);
	const { unit, scale } = scaleAmt(allVals);
	const data = present.map((r) => {
		const rec: Record<string, string> = { [labelHeader]: r.label };
		yearCols.forEach((yc, i) => {
			rec[yc] = fmtScaled(r.values[i] ?? null, scale);
		});
		return rec;
	});
	return { type: 'table', label: `${caption} (단위: ${unit})`, data };
}

// 비율 표(% 또는 배). signed=true 면 +부호 표기(성장률).
function pctTable(
	rows: { label: string; values: Num[]; unit?: '%' | '배' }[],
	yearCols: string[],
	labelHeader: string,
	caption: string,
	signed = false
): ReportBlock | null {
	const present = rows.filter((r) => coverage(r.values) >= 2);
	if (!present.length) return null;
	const data = present.map((r) => {
		const rec: Record<string, string> = { [labelHeader]: r.label };
		yearCols.forEach((yc, i) => {
			const v = r.values[i] ?? null;
			rec[yc] = r.unit === '배' ? fmtMult(v) : signed ? fmtPctSigned(v) : fmtPct(v);
		});
		return rec;
	});
	return { type: 'table', label: caption, data };
}

// ── 관점 1: 수익체력 (Earnings Power) ─────────────────────
function buildEarningsPower(
	tf: TerminalFinance,
	ctx: { corpName: string; yearCols: string[]; pick: (v: Num[]) => Num[] }
): { sections: ReportSection[]; findings: ReportModel['keyFindings']; closing: ReportModel['closing']; kpis: ReportModel['headlineKpis']; conclusion: string } {
	const { corpName, yearCols, pick } = ctx;
	const isRow = (k: string): Num[] => tf.statements.IS.find((r) => r.key === k)?.values ?? [];
	const cfRow = (k: string): Num[] => tf.statements.CF.find((r) => r.key === k)?.values ?? [];
	const rRow = (k: string): Num[] => tf.ratios.find((r) => r.key === k)?.values ?? [];

	const revL = lastNonNull(isRow('revenue'));
	const opmL = lastNonNull(rRow('opm'));
	const npmL = lastNonNull(rRow('npm'));
	const roeL = lastNonNull(rRow('roe'));
	const yoyL = lastNonNull(tf.revYoy);
	const eqL = lastNonNull(rRow('earningsQuality'));
	const niL = lastNonNull(isRow('netIncome'));
	const yearL = pYear(last(tf.periods));

	const sections: ReportSection[] = [];
	const findings: ReportModel['keyFindings'] = [];

	// S1 손익 구조
	const s1: ReportBlock[] = [
		{
			type: 'text',
			text: `${corpName}의 최근 회계연도(FY${yearL.slice(2)}) 매출은 ${fmtAmt1(revL)}, 영업이익률 ${fmtPct(opmL)}, 순이익률 ${fmtPct(npmL)} 입니다. 아래 표는 매출에서 영업이익·순이익으로 이어지는 손익 구조를 연도별로 보여줍니다.`
		}
	];
	const isTbl = amtTable(
		[
			{ label: '매출액', values: pick(isRow('revenue')) },
			{ label: '매출원가', values: pick(isRow('costOfSales')) },
			{ label: '매출총이익', values: pick(isRow('grossProfit')) },
			{ label: '판매관리비', values: pick(isRow('sga')) },
			{ label: '영업이익', values: pick(isRow('operatingIncome')) },
			{ label: '당기순이익', values: pick(isRow('netIncome')) }
		],
		yearCols,
		'손익 항목',
		'손익계산서 (요약)'
	);
	if (isTbl) s1.push(isTbl);
	sections.push({ key: 'incomeStructure', title: '손익 구조 -- 무엇으로 얼마를 버는가', sourceEngine: 'analysis', blocks: s1, emph: true });
	findings.push({ key: '손익구조', finding: `FY${yearL.slice(2)} 매출 ${fmtAmt1(revL)} · 영업이익률 ${fmtPct(opmL)}.`, sourceEngine: 'analysis' });

	// S2 마진 궤적 — 추세는 *직전 연도 대비* 방향(양끝 비교는 V자 회복을 '둔화'로 오표기).
	const opmSeries = (pick(rRow('opm')).filter((v) => v != null && Number.isFinite(v)) as number[]);
	const sn = opmSeries.length;
	const trend =
		sn >= 2
			? opmSeries[sn - 1] > opmSeries[sn - 2] * 1.02
				? '개선'
				: opmSeries[sn - 1] < opmSeries[sn - 2] * 0.98
					? '둔화'
					: '횡보'
			: null;
	const opmLo = sn ? Math.min(...opmSeries) : null;
	const opmHi = sn ? Math.max(...opmSeries) : null;
	const s2text =
		sn >= 2
			? `영업이익률은 직전 회계연도 ${fmtPct(opmSeries[sn - 2])} → ${fmtPct(opmSeries[sn - 1])}로 ${trend}했습니다 (최근 ${sn}년 범위 ${fmtPct(opmLo)}~${fmtPct(opmHi)}). 매출총이익률·순이익률과 함께 보면 비용 구조의 변화 방향을 읽을 수 있습니다.`
			: `영업이익률은 ${fmtPct(opmL)} 수준입니다.`;
	const marginTbl = pctTable(
		[
			{ label: '매출총이익률', values: pick(rRow('gpm')) },
			{ label: '영업이익률', values: pick(rRow('opm')) },
			{ label: '순이익률', values: pick(rRow('npm')) }
		],
		yearCols,
		'수익성 지표',
		'수익성 비율 추이'
	);
	const s2: ReportBlock[] = [{ type: 'text', text: s2text }];
	if (marginTbl) s2.push(marginTbl);
	// 순이익률 일회성 각주 — 값 보존 + 맥락(영업외 일회성)으로 표 오독 방지.
	const npmOneOff = detectOneOff(pick(rRow('npm')), yearCols);
	if (marginTbl && npmOneOff)
		s2.push({
			type: 'text',
			text: `※ 순이익률 ${npmOneOff.year}년 ${fmtPct(npmOneOff.value)} 는 영업외 일회성 손익(자산 매각·평가이익 등)이 반영된 값으로, 본업 마진 추세와 분리해 읽으십시오.`
		});
	if (marginTbl) {
		sections.push({ key: 'marginTrajectory', title: '마진 궤적 -- 남는 돈은 늘고 있는가', sourceEngine: 'analysis', blocks: s2 });
		findings.push({ key: '수익성', finding: trend ? `영업이익률 ${fmtPct(opmL)} (직전 연도 대비 ${trend}) · 최근 ${sn}년 ${fmtPct(opmLo)}~${fmtPct(opmHi)}.` : `영업이익률 ${fmtPct(opmL)}.`, sourceEngine: 'analysis' });
	}

	// S3 성장 모멘텀 (≥2 기간 YoY 있을 때만)
	const growthTbl = pctTable(
		[
			{ label: '매출 (YoY)', values: pick(tf.revYoy) },
			{ label: '영업이익 (YoY)', values: pick(tf.opYoy) }
		],
		yearCols,
		'성장률',
		'성장률 (전년 대비)',
		true
	);
	if (growthTbl) {
		const s3text =
			yoyL != null
				? `직전 회계연도 매출은 전년 대비 ${fmtPctSigned(yoyL)} 변화했습니다. 성장은 마진과 함께 봐야 — 매출이 늘어도 마진이 꺾이면 이익 체력은 약해집니다.`
				: '성장률 시계열을 표로 정리했습니다.';
		const s3blocks: ReportBlock[] = [{ type: 'text', text: s3text }, growthTbl];
		// 영업이익 YoY 극단 변동(기저효과) 각주 — 인과 단정 없이 분리 읽기 안내.
		const opYoyOneOff = detectOneOff(pick(tf.opYoy), yearCols);
		if (opYoyOneOff)
			s3blocks.push({
				type: 'text',
				text: `※ 영업이익 YoY ${opYoyOneOff.year}년 ${fmtPctSigned(opYoyOneOff.value)} 는 전년도 실적이 낮아 생긴 기저효과가 큰 값입니다 — 매출 YoY와 분리해 읽으십시오.`
			});
		sections.push({ key: 'growthMomentum', title: '성장 모멘텀 -- 외형은 커지고 있는가', sourceEngine: 'analysis', blocks: s3blocks });
		findings.push({ key: '성장성', finding: yoyL != null ? `매출 ${fmtPctSigned(yoyL)} YoY.` : '성장률 시계열 제공.', sourceEngine: 'analysis' });
	}

	// S4 이익의 진정성 (현금화)
	const eqTbl = amtTable(
		[
			{ label: '당기순이익', values: pick(isRow('netIncome')) },
			{ label: '영업활동현금흐름', values: pick(cfRow('cfOperating')) }
		],
		yearCols,
		'항목',
		'이익의 현금화 (순이익 대비 영업현금)'
	);
	if (eqTbl) {
		const healthy = eqL != null && niL != null && niL > 0;
		const s4text = healthy
			? `영업활동현금흐름이 당기순이익의 ${fmtMult(eqL)} 수준입니다 — 회계이익이 현금으로 ${(eqL as number) >= 1 ? '충분히' : '부분적으로'} 뒷받침됩니다. 배율이 1배를 밑돌면 운전자본·일회성 항목을 점검할 신호입니다.`
			: '당기순이익이 적자이거나 데이터가 부족해 현금화 배율은 산출하지 않았습니다(억지 채움 없음).';
		const s4: ReportBlock[] = [{ type: 'text', text: s4text }, eqTbl];
		if (healthy)
			s4.push({ type: 'metrics', metrics: [{ label: '이익품질 (영업CF / 순이익)', value: fmtMult(eqL) }] });
		sections.push({ key: 'earningsQuality', title: '이익의 진정성 -- 번 돈이 현금으로 돌아오나', sourceEngine: 'analysis', blocks: s4 });
		findings.push({ key: '이익품질', finding: healthy ? `영업CF/순이익 ${fmtMult(eqL)}.` : '현금화 배율 산출 불가(적자/결측).', sourceEngine: 'analysis' });
	}

	const kpis: ReportModel['headlineKpis'] = [
		{ label: '매출', value: fmtAmt1(revL) },
		{ label: '영업이익률', value: fmtPct(opmL) },
		{ label: '순이익률', value: fmtPct(npmL) },
		{ label: '매출 성장(YoY)', value: fmtPctSigned(yoyL) },
		{ label: 'ROE', value: fmtPct(roeL) },
		{ label: '이익품질', value: fmtMult(eqL) }
	];
	const conclusion = `${corpName} — FY${yearL.slice(2)} 매출 ${fmtAmt1(revL)}, 영업이익률 ${fmtPct(opmL)} · 순이익률 ${fmtPct(npmL)}${yoyL != null ? ` · 매출 ${fmtPctSigned(yoyL)} YoY` : ''}.`;
	const closing: ReportModel['closing'] = [
		{
			label: '재무',
			engine: 'analysis',
			line: `FY${yearL.slice(2)} 매출 ${fmtAmt1(revL)} · 영업이익률 ${fmtPct(opmL)}${trend ? ` (직전 연도 대비 ${trend})` : ''} · 이익품질 ${fmtMult(eqL)}.`
		}
	];
	return { sections, findings, closing, kpis, conclusion };
}

// 재무건전성 점검(브라우저 — Python dCR 7축 아님). 측정값 *나란히*, 종합점수·등급 금지.
// 판정에 자기이력 편입(과거 미달 연수) + 전구간 결측 축은 honest-skip 행으로 명시.
function healthTable(
	axes: { name: string; series: Num[]; unit: '%' | '배' | '조'; good: 'high' | 'low'; threshold: number; thLabel: string }[]
): ReportBlock | null {
	const fmtOf = (u: '%' | '배' | '조') => (u === '%' ? fmtPct : u === '배' ? fmtMult : fmtAmt1);
	const rows = axes.map((a) => {
		const vals = a.series.filter((v): v is number => v != null && Number.isFinite(v));
		const fmt = fmtOf(a.unit);
		if (!vals.length) {
			// honest-skip — 축이 조용히 사라지지 않게 '산출 불가' 행 명시(예: 무차입사 이자보상배율).
			return { 지표: a.name, 최근값: '-', '최근 범위': '-', 기준: a.thLabel, 판정: '산출 불가' } as Record<string, string>;
		}
		const latest = vals[vals.length - 1];
		const lo = Math.min(...vals);
		const hi = Math.max(...vals);
		const isPass = (v: number) => (a.good === 'high' ? v >= a.threshold : v <= a.threshold);
		const breaches = vals.filter((v) => !isPass(v)).length;
		let verdict: string;
		if (!isPass(latest)) verdict = '주의';
		else if (breaches > 0) verdict = `양호 (과거 ${breaches}년 미달)`;
		else verdict = '양호';
		return {
			지표: a.name,
			최근값: fmt(latest),
			'최근 범위': fmtRange(lo, hi, a.unit),
			기준: a.thLabel,
			판정: verdict
		} as Record<string, string>;
	});
	if (!rows.length) return null;
	return { type: 'table', label: '재무건전성 점검 · 4축 측정값 (각 축 독립 — 종합점수 없음, Python 신용등급 아님)', data: rows };
}

// ── 관점 2: 곳간과 빚 (Liquidity & Solvency) ───────────────
function buildLiquidity(
	tf: TerminalFinance,
	ctx: { corpName: string; yearCols: string[]; pick: (v: Num[]) => Num[] },
	debt: { ladder: { buckets: Num[]; shortTerm: Num; year: string } | null } | null
): { sections: ReportSection[]; findings: ReportModel['keyFindings']; closing: ReportModel['closing']; kpis: ReportModel['headlineKpis']; conclusion: string } {
	const { corpName, yearCols, pick } = ctx;
	const isRow = (k: string): Num[] => tf.statements.IS.find((r) => r.key === k)?.values ?? [];
	const cfRow = (k: string): Num[] => tf.statements.CF.find((r) => r.key === k)?.values ?? [];
	const rRow = (k: string): Num[] => tf.ratios.find((r) => r.key === k)?.values ?? [];
	const cardSeries = (k: string): Num[] => tf.cards.find((c) => c.key === k)?.series?.[0]?.data ?? [];

	// 파생 시계열
	const oiAll = pick(isRow('operatingIncome'));
	const fcAll = pick(isRow('financeCosts'));
	const icr = oiAll.map((v, i) => (v != null && fcAll[i] != null && (fcAll[i] as number) !== 0 ? (v as number) / (fcAll[i] as number) : null));
	const fcf = pick(cardSeries('fcfTrend'));

	const drL = lastNonNull(rRow('debtRatio'));
	const crL = lastNonNull(rRow('currentRatio'));
	const erL = lastNonNull(rRow('equityRatio'));
	const icrL = lastNonNull(icr);
	const fcfL = lastNonNull(fcf);
	const cfoL = lastNonNull(pick(cfRow('cfOperating')));

	const sections: ReportSection[] = [];
	const findings: ReportModel['keyFindings'] = [];

	// S1 현금 창출·배분
	const cfTbl = amtTable(
		[
			{ label: '영업활동현금흐름', values: pick(cfRow('cfOperating')) },
			{ label: '투자활동현금흐름', values: pick(cfRow('cfInvesting')) },
			{ label: '재무활동현금흐름', values: pick(cfRow('cfFinancing')) },
			{ label: '잉여현금흐름(FCF)', values: fcf }
		],
		yearCols,
		'현금흐름',
		'현금 창출·배분'
	);
	const s1: ReportBlock[] = [
		{
			type: 'text',
			text: `${corpName}의 현금은 영업에서 벌어 투자·재무로 흘러갑니다. 영업현금흐름이 꾸준히 (+)이고 잉여현금흐름(FCF = 영업현금 − 설비투자)이 (+)이면, 외부 차입 없이 자체 현금으로 굴러간다는 뜻입니다. 투자활동현금흐름이 (−)인 것은 설비·지분 투자 집행을 뜻하며 통상적인 모습입니다(붉은색은 음수 부호 표기일 뿐 부정적 신호가 아닙니다).`
		}
	];
	if (cfTbl) s1.push(cfTbl);
	if (cfTbl) {
		sections.push({ key: 'cashFlow', title: '현금 창출·배분 -- 현금은 어떻게 도는가', sourceEngine: 'analysis', blocks: s1, emph: true });
		findings.push({ key: '현금흐름', finding: `최근 영업CF ${fmtAmt1(cfoL)} · FCF ${fmtAmt1(fcfL)}.`, sourceEngine: 'analysis' });
	}

	// S2 레버리지·유동성
	const levTbl = pctTable(
		[
			{ label: '부채비율', values: pick(rRow('debtRatio')) },
			{ label: '자기자본비율', values: pick(rRow('equityRatio')) },
			{ label: '유동비율', values: pick(rRow('currentRatio')) }
		],
		yearCols,
		'안정성 지표',
		'레버리지·유동성 비율'
	);
	if (levTbl) {
		const s2text = `부채비율 ${fmtPct(drL)} · 유동비율 ${fmtPct(crL)} 입니다. 부채비율은 자본 대비 부채(낮을수록 안정), 유동비율은 1년 내 갚을 빚 대비 1년 내 현금화 자산(100% 이상이면 단기 상환 여력)입니다.`;
		sections.push({ key: 'leverage', title: '레버리지·유동성 -- 빚은 감당 가능한가', sourceEngine: 'analysis', blocks: [{ type: 'text', text: s2text }, levTbl] });
		findings.push({ key: '안정성', finding: `부채비율 ${fmtPct(drL)} · 유동비율 ${fmtPct(crL)} · 자기자본비율 ${fmtPct(erL)}.`, sourceEngine: 'analysis' });
	}

	// S3 재무건전성 점검 (브라우저 측정 — dCR 아님). 부채비율↔자기자본비율 항등 중복이라
	// 자기자본비율은 제외(레버리지 표에 이미 있음). 레버리지·유동성·이자감당·현금창출 4축.
	const hTbl = healthTable([
		{ name: '부채비율', series: pick(rRow('debtRatio')), unit: '%', good: 'low', threshold: 200, thLabel: '200% 이하' },
		{ name: '유동비율', series: pick(rRow('currentRatio')), unit: '%', good: 'high', threshold: 100, thLabel: '100% 이상' },
		{ name: '이자보상배율', series: icr, unit: '배', good: 'high', threshold: 1, thLabel: '1배 이상' },
		{ name: '잉여현금흐름(FCF)', series: fcf, unit: '조', good: 'high', threshold: 0, thLabel: '0 이상' }
	]);
	if (hTbl) {
		const s3: ReportBlock[] = [
			{
				type: 'text',
				text: `아래는 재무 안정성을 레버리지·유동성·이자감당·현금창출 4개 축으로 *나란히* 본 것입니다. 각 축은 독립이며 하나의 종합점수로 합치지 않습니다 — 이 표는 dartlab 의 정밀 신용등급(Python 7축 dCR)이 아니라 브라우저에서 재무비율로 계산한 점검표입니다. 판정은 최신값 기준이며, 과거 미달 이력이 있으면 함께 표기합니다.`
			},
			hTbl
		];
		sections.push({ key: 'financialHealth', title: '재무건전성 점검 -- 어느 축이 견고하고 어느 축이 약한가', sourceEngine: 'analysis', blocks: s3 });
		findings.push({ key: '재무건전성', finding: `이자보상배율 ${fmtMult(icrL)} · 부채비율 ${fmtPct(drL)} · FCF ${fmtAmt1(fcfL)}.`, sourceEngine: 'analysis' });
	}

	// S4 채무 만기 사다리 (report.debtProfile — 데이터 있을 때만)
	const ladder = debt?.ladder ?? null;
	if (ladder && ladder.buckets.some((v) => v != null && (v as number) > 0)) {
		const W = 1e12; // 원 → 조
		const names = ['1년 이하', '1~2년', '2~3년', '3~4년', '4~5년', '5~10년', '10년 초과'];
		// 꼬리 빈 구간 절단 — 마지막 유효 만기 이후 연속 빈 행 제거(삼성처럼 단기 2칸만인 경우 휑한 표 방지).
		let lastFilled = 0;
		ladder.buckets.forEach((v, i) => { if (v != null && (v as number) > 0) lastFilled = i; });
		const rows: Record<string, string>[] = ladder.buckets.slice(0, lastFilled + 1).map((v, i) => ({
			만기구간: names[i] ?? `구간${i + 1}`,
			금액: v != null ? fmtAmt1((v as number) / W) : '-'
		}));
		const stb = ladder.shortTerm != null ? fmtAmt1((ladder.shortTerm as number) / W) : '-';
		sections.push({
			key: 'debtLadder',
			title: '채무 만기 사다리 -- 언제 얼마를 갚아야 하나',
			sourceEngine: 'analysis',
			blocks: [
				{ type: 'text', text: `사채 만기를 잔존기간별로 나눈 것입니다(${ladder.year} 기준). 단기(1년 이하)에 몰려 있으면 차환 부담이 큽니다. 전자단기사채·CP 등 단기성 채무 합계는 ${stb} 입니다.` },
				{ type: 'table', label: '사채 잔존만기 분포', data: rows }
			]
		});
		findings.push({ key: '채무만기', finding: `단기성 채무 ${stb} · 1년 이하 만기 ${fmtAmt1((ladder.buckets[0] as number) / W)}.`, sourceEngine: 'analysis' });
	}

	const kpis: ReportModel['headlineKpis'] = [
		{ label: '부채비율', value: fmtPct(drL) },
		{ label: '자기자본비율', value: fmtPct(erL) },
		{ label: '유동비율', value: fmtPct(crL) },
		{ label: '이자보상배율', value: fmtMult(icrL) },
		{ label: '잉여현금흐름', value: fmtAmt1(fcfL) },
		{ label: '영업현금흐름', value: fmtAmt1(cfoL) }
	];
	const conclusion = `${corpName} — 부채비율 ${fmtPct(drL)}, 유동비율 ${fmtPct(crL)}, 이자보상배율 ${fmtMult(icrL)}${fcfL != null ? ` · FCF ${fmtAmt1(fcfL)}` : ''}.`;
	const closing: ReportModel['closing'] = [
		{ label: '재무', engine: 'analysis', line: `부채비율 ${fmtPct(drL)} · 유동비율 ${fmtPct(crL)} · 이자보상배율 ${fmtMult(icrL)} · FCF ${fmtAmt1(fcfL)}.` }
	];
	return { sections, findings, closing, kpis, conclusion };
}

// 연도 키 보고 데이터용 범용 표 — 행마다 이미 포맷된 문자열 셀.
function reportTable(years: string[], rows: { label: string; cells: string[] }[], labelHeader: string, caption: string): ReportBlock | null {
	const present = rows.filter((r) => r.cells.some((c) => c && c !== '-'));
	if (!present.length) return null;
	const data = present.map((r) => {
		const rec: Record<string, string> = { [labelHeader]: r.label };
		years.forEach((y, i) => {
			rec[y] = r.cells[i] ?? '-';
		});
		return rec;
	});
	return { type: 'table', label: caption, data };
}

// ── 관점 3: 주주와의 약속 (Capital Return & Dilution) ──────
function buildCapitalReturn(
	sr: ShareholderReturnYear[] | null,
	cc: CapitalChangesBundle | null,
	ctx: { corpName: string }
): { sections: ReportSection[]; findings: ReportModel['keyFindings']; closing: ReportModel['closing']; kpis: ReportModel['headlineKpis']; conclusion: string } | null {
	const { corpName } = ctx;
	if (!sr || !sr.length) return null;
	const ys = sr.slice(-6);
	const yc = ys.map((y) => y.year);
	const latest = ys[ys.length - 1];
	// 배당은 주총 확정이 늦어 최신 연도가 비는 경우가 많다 → 배당 데이터가 있는 최근 연도 기준.
	const divYear = [...ys].reverse().find((y) => y.dps != null && Number.isFinite(y.dps as number)) ?? null;
	const divAsOf = divYear && divYear.year !== latest.year ? ` (${divYear.year} 기준)` : '';

	const sections: ReportSection[] = [];
	const findings: ReportModel['keyFindings'] = [];

	// S1 배당 정책
	const divTbl = reportTable(
		yc,
		[
			{ label: '주당배당금(DPS)', cells: ys.map((y) => fmtWon(y.dps)) },
			{ label: '배당성향', cells: ys.map((y) => fmtPct(y.payoutPct)) },
			{ label: '배당수익률', cells: ys.map((y) => fmtPct(y.yieldPct)) },
			{ label: '총배당금', cells: ys.map((y) => fmtWon(y.totalDividend)) }
		],
		'배당 지표',
		'배당 정책'
	);
	if (divTbl) {
		sections.push({
			key: 'dividend',
			title: '배당 정책 -- 주주에게 얼마를 돌려주나',
			sourceEngine: 'analysis',
			blocks: [
				{ type: 'text', text: `${corpName}의 배당입니다. 배당성향은 순이익 중 배당으로 나간 비율, 배당수익률은 주가 대비 배당입니다.${divYear ? ` 가장 최근 확정 배당은 주당 ${fmtWon(divYear.dps)}, 배당성향 ${fmtPct(divYear.payoutPct)}${divAsOf} 입니다.` : ''} 배당성향은 순이익이 급감한 해(분모 효과)나 특별배당이 있던 해에 일시적으로 치솟을 수 있어, 한 해 값보다 추세로 보는 것이 좋습니다.${divAsOf ? ' 최신 회계연도 배당은 주주총회 확정 전이라 표에서 비어 있습니다.' : ''}` },
				divTbl
			],
			emph: true
		});
		if (divYear) findings.push({ key: '배당', finding: `DPS ${fmtWon(divYear.dps)} · 배당성향 ${fmtPct(divYear.payoutPct)} · 배당수익률 ${fmtPct(divYear.yieldPct)}${divAsOf}.`, sourceEngine: 'analysis' });
	}

	// S2 자사주 행동 — ★소각(영구) vs 기말 보유(금고주) 구분.
	// 자사주 수치는 공시상 양수 카운트(finTabs 계약) — 정정공시 합산으로 음수가 나오면 신뢰불가 → 보류.
	let suppressed = false;
	const cnt = (v: Num): string => {
		if (v != null && Number.isFinite(v) && (v as number) < 0) {
			suppressed = true;
			return '-';
		}
		return fmtShares(v);
	};
	const buyTbl = reportTable(
		yc,
		[
			{ label: '자사주 매입', cells: ys.map((y) => cnt(y.buybackQty)) },
			{ label: '자사주 처분', cells: ys.map((y) => cnt(y.disposalQty)) },
			{ label: '자사주 소각', cells: ys.map((y) => cnt(y.buybackCancel)) },
			{ label: '기말 보유(금고주)', cells: ys.map((y) => cnt(y.treasuryEnd)) }
		],
		'자사주(보통주)',
		'자사주 매입·소각·보유'
	);
	if (buyTbl) {
		const buyBlocks: ReportBlock[] = [
			{ type: 'text', text: `자사주 매입이 곧 주주환원은 아닙니다. 매입 후 *소각*하면 주식수가 영구히 줄어 주당 가치가 오르지만, *기말 보유(금고주)*로 쌓아 두면 나중에 다시 팔려 희석될 수 있습니다 — 둘을 구분해 봐야 합니다.` },
			buyTbl
		];
		if (suppressed)
			buyBlocks.push({ type: 'text', text: `※ 자사주 수치는 공시상 양수(주식 수)여야 하나, 정정공시 합산 등으로 순변동이 음수가 된 칸은 신뢰할 수 없어 표면화를 보류(−)했습니다.` });
		sections.push({ key: 'buyback', title: '자사주 행동 -- 사서 태우나, 쌓아 두나', sourceEngine: 'analysis', blocks: buyBlocks });
		findings.push({ key: '자사주', finding: `최근 소각 ${cnt(latest.buybackCancel)} · 기말 보유 ${cnt(latest.treasuryEnd)}.`, sourceEngine: 'analysis' });
	}

	// S3 자본 변동·희석
	if (cc && cc.years.length) {
		const cy = cc.years.slice(-6);
		const cyc = cy.map((y) => String(y.year));
		const dilTbl = reportTable(
			cyc,
			[
				{ label: '유상증자', cells: cy.map((y) => fmtShares(y.paidIn)) },
				{ label: '전환권 행사', cells: cy.map((y) => fmtShares(y.conversion)) },
				{ label: '감자·소각', cells: cy.map((y) => fmtShares(y.reduction)) }
			],
			'자본 변동(주)',
			'발행주식 변동 (희석 ↔ 환원)'
		);
		if (dilTbl)
			sections.push({
				key: 'dilution',
				title: '자본 변동·희석 -- 주식 수는 늘었나 줄었나',
				sourceEngine: 'analysis',
				blocks: [
					{ type: 'text', text: `유상증자·전환권 행사는 주식 수를 늘려(희석), 감자·소각은 줄입니다(환원). 아래는 연도별 발행주식 변동입니다(주식 수 기준).` },
					dilTbl
				]
			});
		if (dilTbl) findings.push({ key: '희석', finding: '발행주식 변동(증자/전환/감자) 시계열 제공.', sourceEngine: 'analysis' });
	}

	const kpis: ReportModel['headlineKpis'] = [
		{ label: divYear ? `주당배당금${divAsOf}` : '주당배당금', value: fmtWon(divYear?.dps ?? null) },
		{ label: '배당성향', value: fmtPct(divYear?.payoutPct ?? null) },
		{ label: '배당수익률', value: fmtPct(divYear?.yieldPct ?? null) },
		{ label: '총배당금', value: fmtWon(divYear?.totalDividend ?? null) },
		{ label: `최근 소각 (${latest.year})`, value: cnt(latest.buybackCancel) },
		{ label: `기말 자사주 (${latest.year})`, value: cnt(latest.treasuryEnd) }
	];
	const conclusion = divYear
		? `${corpName} — 주당배당금 ${fmtWon(divYear.dps)}, 배당성향 ${fmtPct(divYear.payoutPct)}, 배당수익률 ${fmtPct(divYear.yieldPct)}${divAsOf}.`
		: `${corpName} — 최근 확정 배당 이력이 없습니다(무배당 또는 미확정). 자사주 정책 중심으로 정리했습니다.`;
	const closing: ReportModel['closing'] = [
		{ label: '재무', engine: 'analysis', line: divYear ? `배당성향 ${fmtPct(divYear.payoutPct)} · DPS ${fmtWon(divYear.dps)}${divAsOf} · 최근 자사주 소각 ${fmtShares(latest.buybackCancel)}.` : `배당 없음 · 최근 자사주 소각 ${fmtShares(latest.buybackCancel)}.` }
	];
	return { sections, findings, closing, kpis, conclusion };
}

// ── 미구현 관점 — 정직 '준비 중' ───────────────────────────
function pendingModel(
	code: string,
	corpName: string,
	industry: string | undefined,
	persp: PerspectiveMeta,
	asOf: string,
	dataBasis: string
): ReportModel {
	return {
		stockCode: code,
		corpName,
		asOf,
		dataBasis,
		industry,
		perspectiveKey: persp.key,
		perspectiveLabel: persp.label,
		conclusion: `「${persp.label}」 관점은 다음 사이클에서 데이터 작업대 리얼타임으로 구현됩니다.`,
		headlineKpis: [],
		narrativeOverview: '',
		keyFindings: [],
		sections: [],
		closing: [],
		provenance: { engines: {}, note: '' },
		assumptionsNote: '',
		qualityLabel: 'conditional',
		focusQuestions: persp.focusQuestions,
		pending: true
	};
}

// ── 진입점 ─────────────────────────────────────────────────
export async function buildReport(
	rt: DartLabRuntime,
	code: string,
	perspectiveKey: string
): Promise<ReportResult> {
	const persp = findPerspective(perspectiveKey);
	// 회사명·업종 = map/search-index.json (데이터 작업대 loadJson 직독). public search.universe 미배선.
	const [fin, universe] = await Promise.all([
		rt.finance.bundle(code),
		loadJson<IndexRow[]>('map/search-index.json', { fetchFn: fetch, preferLocal: true }).catch(() => null)
	]);
	const meta = (universe ?? []).find((r) => r.stockCode === code);
	const corpName = meta?.corpName ?? code;
	const industry = meta?.industry || undefined;

	if (!fin) return { skipped: true, stockCode: code, reason: '재무 데이터셋이 없습니다(미상장·미공시).' };
	const tf = annualView(fin);
	if (!tf || !tf.periods.length)
		return { skipped: true, stockCode: code, reason: '연간 재무 데이터가 없습니다.' };

	const asOf = latestFiled(fin) ?? pYear(last(tf.periods));
	const dataBasis = `FY${pYear(last(tf.periods)).slice(2)} (연간)`;

	if (!persp.built) return pendingModel(code, corpName, industry, persp, asOf, dataBasis);

	// 최근 N 기간 슬라이스
	const n = Math.min(6, tf.periods.length);
	const idx = Array.from({ length: n }, (_, k) => tf.periods.length - n + k);
	const yearCols = idx.map((i) => pYear(tf.periods[i]));
	const pick = (values: Num[]): Num[] => idx.map((i) => values[i] ?? null);

	const ctx = { corpName, yearCols, pick };
	let built;
	if (persp.key === 'liquidity') {
		const debt = await rt.report.debtProfile(code).catch(() => null);
		built = buildLiquidity(tf, ctx, debt);
	} else if (persp.key === 'capitalReturn') {
		const [sr, cc] = await Promise.all([
			rt.report.shareholderReturn(code).catch(() => null),
			rt.report.capitalChanges(code).catch(() => null)
		]);
		built = buildCapitalReturn(sr, cc, { corpName });
	} else {
		built = buildEarningsPower(tf, ctx);
	}
	if (!built || !built.sections.length)
		return { skipped: true, stockCode: code, reason: '이 관점에 채울 데이터가 부족합니다(예: 무배당 기업).' };
	const blockCount = built.sections.reduce((acc, s) => acc + s.blocks.length, 0);

	return {
		stockCode: code,
		corpName,
		asOf,
		dataBasis,
		industry,
		perspectiveKey: persp.key,
		perspectiveLabel: persp.label,
		conclusion: built.conclusion,
		headlineKpis: built.kpis,
		narrativeOverview: `이 보고서는 ${corpName}의 ${persp.label} — ${persp.question} — 를 연간 공시 기준으로 정리했습니다. 모든 수치는 데이터 작업대에서 조회 시점에 계산되며, 사전 bake·정적 캐시는 사용하지 않습니다.`,
		keyFindings: built.findings,
		sections: built.sections,
		closing: built.closing,
		provenance: {
			engines: {
				analysis: { label: '재무분석 (브라우저 리얼타임)', sections: built.sections.length, blocks: blockCount }
			},
			note: '모든 수치는 HuggingFace dart/finance parquet 을 브라우저가 직접 읽어 계산했습니다. 정적 캐시·사전 bake 없음 — 조회 시점 리얼타임.'
		},
		assumptionsNote:
			'연간(사업보고서) 기준 · 분기는 누계 처리 · 표 단위는 자릿수에 따라 조/억 자동 스케일 · 공시 항목이 빈약한 행은 표에서 자동 생략 · 영업외 일회성 손익이 큰 해는 본문에 각주로 표시 · 재무건전성 점검은 브라우저 재무비율 계산(Python 신용등급 dCR 아님). 주주환원·시장의 평가·누구의 회사 관점은 후속 사이클에서 추가됩니다.',
		qualityLabel: built.sections.length >= 3 ? 'verified' : 'conditional',
		focusQuestions: persp.focusQuestions
	};
}
