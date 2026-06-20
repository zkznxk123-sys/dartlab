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
import type {
	ShareholderReturnYear,
	CapitalChangesBundle,
	Candle,
	ShareholdersView,
	OwnershipYear,
	WorkforceYear,
	ExecBoardYear,
	TopExecPay,
	AuditYear,
	AuditFeeYear,
	InvestmentsBundle
} from '@dartlab/ui-contracts';
import { KR_INDEX_PRESETS } from '@dartlab/ui-contracts';
import { pYear, fmtPct, fmtPctSigned, fmtMult, fmtAmt1, scaleAmt, fmtScaled, fmtRange, fmtShares, fmtWon, fmtPay, fmtNum } from './format';
import { calcBeta, yearEndCloses, priceSummary } from './market';

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

// ── 관점 4: 시장의 평가 (Market & Valuation Context) ──────
// NEVER-CLAIM 위험 최대 — 목표주가·매수/매도·적정주가 환산 절대 금지. 측정값·맥락만.
function buildMarket(
	candles: Candle[] | null,
	marketCandles: Candle[] | null,
	sr: ShareholderReturnYear[] | null,
	ctx: { corpName: string }
): { sections: ReportSection[]; findings: ReportModel['keyFindings']; closing: ReportModel['closing']; kpis: ReportModel['headlineKpis']; conclusion: string } | null {
	const { corpName } = ctx;
	if (!candles || !candles.length) return null;
	const ps = priceSummary(candles);
	if (!ps) return null;
	const beta = marketCandles ? calcBeta(candles, marketCandles) : null;

	const sections: ReportSection[] = [];
	const findings: ReportModel['keyFindings'] = [];

	// S1 주가 궤적
	const won = (v: number) => `${Math.round(v).toLocaleString('en-US')}원`;
	sections.push({
		key: 'priceTrack',
		title: '주가 궤적 -- 시장은 어떻게 움직였나',
		sourceEngine: 'quant',
		blocks: [
			{ type: 'text', text: `${corpName}의 최근 주가 흐름입니다. 아래는 가격 *사실*이며 매수·매도 의견이 아닙니다.` },
			{
				type: 'metrics',
				metrics: [
					{ label: '현재가', value: won(ps.last) },
					{ label: '52주 최고', value: won(ps.hi) },
					{ label: '52주 최저', value: won(ps.lo) },
					{ label: '1년 수익률', value: ps.ret1y != null ? fmtPctSigned(ps.ret1y * 100) : '-' },
					{ label: '최근 거래대금', value: ps.tv != null ? fmtAmt1(ps.tv / 1e12) : '-' }
				]
			}
		],
		emph: true
	});
	findings.push({ key: '주가', finding: `현재가 ${won(ps.last)} · 1년 ${ps.ret1y != null ? fmtPctSigned(ps.ret1y * 100) : '-'} · 52주 ${won(ps.lo)}~${won(ps.hi)}.`, sourceEngine: 'quant' });

	// S2 시장 동행성 (베타) — 코스피 대비 명시
	if (beta) {
		const lowR2 = beta.r2 < 0.2;
		const betaText = `베타는 시장(코스피)이 1% 움직일 때 이 종목이 평균 몇 % 움직였는지를 회귀로 추정한 값입니다. 1보다 크면 시장보다 더 크게, 작으면 덜 움직였다는 *과거 사실*이며 등락 방향을 예측하지 않습니다. (회귀 윈도 ${beta.days}거래일·약 2년 — 위 1년 수익률과 측정 기간이 다릅니다. R² ${beta.r2.toFixed(2)}${lowR2 ? ' — 설명력이 낮아 참고용' : ''})`;
		sections.push({
			key: 'beta',
			title: '시장 동행성 -- 시장과 얼마나 함께 움직이나',
			sourceEngine: 'quant',
			blocks: [
				{ type: 'text', text: betaText },
				{
					type: 'metrics',
					metrics: [
						{ label: '베타 (코스피 대비)', value: beta.beta.toFixed(2) },
						{ label: '설명력 (R²)', value: beta.r2.toFixed(2) },
						{ label: '관측 거래일', value: `${beta.days}일` }
					]
				}
			]
		});
		findings.push({ key: '위험', finding: `베타 ${beta.beta.toFixed(2)}(코스피 대비) · 설명력 R² ${beta.r2.toFixed(2)} · 관측 ${beta.days}일.`, sourceEngine: 'quant' });
	}

	// S3 밸류 맥락 — PER 자기역사(연말가/EPS). 적정주가 환산 금지.
	if (sr && sr.length) {
		const yec = yearEndCloses(candles);
		const ys = sr.slice(-6);
		const perCells = ys.map((y) => {
			const px = yec.get(y.year);
			if (px == null || y.eps == null || !Number.isFinite(y.eps as number) || (y.eps as number) <= 0) return '-';
			return fmtMult(px / (y.eps as number));
		});
		const yieldCells = ys.map((y) => fmtPct(y.yieldPct));
		const perTbl = reportTable(
			ys.map((y) => y.year),
			[
				{ label: 'PER (연말가÷EPS)', cells: perCells },
				{ label: '배당수익률', cells: yieldCells }
			],
			'밸류 지표',
			'밸류에이션 맥락 (자기역사)'
		);
		if (perTbl) {
			const perVals = perCells.map((c) => parseFloat(c)).filter((v) => Number.isFinite(v));
			const perCtx = perVals.length >= 2 ? ` 최근 PER는 자기 ${perVals.length}년 범위 ${Math.min(...perVals).toFixed(1)}~${Math.max(...perVals).toFixed(1)}배 안에서 움직였습니다.` : '';
			sections.push({
				key: 'valuation',
				title: '밸류에이션 맥락 -- 시장은 이익에 얼마를 매겼나',
				sourceEngine: 'quant',
				blocks: [
					{ type: 'text', text: `PER는 주가를 주당순이익(EPS)으로 나눈 배수로, 시장이 1원의 이익에 얼마를 매겼는지 보여줍니다. 여기서는 *적정주가를 환산하지 않고*, 이 회사 자신의 과거 PER 범위와만 비교합니다.${perCtx}` },
					perTbl,
					{ type: 'text', text: `※ 상단 KPI의 'PER(현재)'는 현재가 기준, 위 표는 각 연도의 *연말가* 기준이라 같은 해라도 값이 다를 수 있습니다. 주식 분할이 있던 회사는 연도 간 PER이 불연속으로 보일 수 있습니다(분할 조정은 원천 데이터 책임).` }
				]
			});
			findings.push({ key: '밸류', finding: `PER ${perCells[perCells.length - 1]} · 배당수익률 ${yieldCells[yieldCells.length - 1]}.`, sourceEngine: 'quant' });
		}
	}

	const lastEps = sr ? [...sr].reverse().find((y) => y.eps != null && Number.isFinite(y.eps as number) && (y.eps as number) > 0) : null;
	const curPer = lastEps ? fmtMult(ps.last / (lastEps.eps as number)) : '-';
	const kpis: ReportModel['headlineKpis'] = [
		{ label: '현재가', value: won(ps.last) },
		{ label: '1년 수익률', value: ps.ret1y != null ? fmtPctSigned(ps.ret1y * 100) : '-' },
		{ label: '베타(코스피)', value: beta ? beta.beta.toFixed(2) : '-' },
		{ label: '설명력(R²)', value: beta ? beta.r2.toFixed(2) : '-' },
		{ label: 'PER(현재)', value: curPer },
		{ label: '배당수익률', value: fmtPct(lastEps?.yieldPct ?? (sr ? [...sr].reverse().find((y) => y.yieldPct != null)?.yieldPct ?? null : null)) }
	];
	const conclusion = `${corpName} — 현재가 ${won(ps.last)}, 1년 수익률 ${ps.ret1y != null ? fmtPctSigned(ps.ret1y * 100) : '-'}${beta ? `, 베타 ${beta.beta.toFixed(2)}(코스피 대비)` : ''}. (가격 사실 — 매수·매도 의견 아님)`;
	const closing: ReportModel['closing'] = [
		{ label: '시장', engine: 'quant', line: `${beta ? `베타 ${beta.beta.toFixed(2)} · ` : ''}1년 수익률 ${ps.ret1y != null ? fmtPctSigned(ps.ret1y * 100) : '-'} · PER ${curPer}. 가격·밸류 맥락이며 투자판단 아님.` }
	];
	return { sections, findings, closing, kpis, conclusion };
}

// ── 관점 5: 누구의 회사 (Ownership, People & Governance) ──
interface OwnershipData {
	shareholders: ShareholdersView | null;
	ownership: OwnershipYear[] | null;
	workforce: WorkforceYear[] | null;
	execBoard: ExecBoardYear[] | null;
	topExecPay: TopExecPay | null;
	auditTrail: AuditYear[] | null;
	auditFees: AuditFeeYear[] | null;
	investments: InvestmentsBundle | null;
}

function buildOwnership(
	d: OwnershipData,
	ctx: { corpName: string }
): { sections: ReportSection[]; findings: ReportModel['keyFindings']; closing: ReportModel['closing']; kpis: ReportModel['headlineKpis']; conclusion: string } | null {
	const { corpName } = ctx;
	const sections: ReportSection[] = [];
	const findings: ReportModel['keyFindings'] = [];

	// S1 소유 구조
	const ow = d.ownership?.slice(-6) ?? [];
	let majorL: number | null = null;
	let minorL: number | null = null;
	if (ow.length) {
		const owTbl = reportTable(
			ow.map((y) => y.year),
			[
				{ label: '최대주주측 지분', cells: ow.map((y) => fmtPct(y.majorPct)) },
				{ label: '소액주주 지분', cells: ow.map((y) => fmtPct(y.minorPct)) },
				{ label: '소액주주 수', cells: ow.map((y) => fmtNum(y.minorCount, '명')) }
			],
			'소유 지표',
			'지분 분포 추이'
		);
		majorL = lastNonNull(ow.map((y) => y.majorPct)) as number | null;
		minorL = lastNonNull(ow.map((y) => y.minorPct)) as number | null;
		const s1: ReportBlock[] = [
			{ type: 'text', text: `${corpName}의 소유 구조입니다. 최대주주측 지분이 높으면 경영권은 안정적이나 소액주주 영향력은 작고, 소액주주 지분·주주 수가 많으면 그 반대입니다.` }
		];
		if (owTbl) s1.push(owTbl);
		// control-shift 정직 플래그
		const first = ow.find((y) => y.majorPct != null)?.majorPct as number | undefined;
		const lastM = majorL;
		if (first != null && lastM != null && Math.abs(lastM - first) >= 5)
			s1.push({ type: 'text', text: `※ 최대주주측 지분이 ${fmtPct(first)} → ${fmtPct(lastM)}로 ${Math.abs(lastM - first).toFixed(1)}%p 변동했습니다 — 지배구조 변화 신호로 함께 보십시오.` });
		// 최대주주 개별(현재) — 방어 가드: person 분류 행은 실명 미노출(익명집계로만). 개인정보 레드라인.
		if (d.shareholders?.named?.length) {
			const top = d.shareholders.named.filter((r) => r.kind !== 'person').slice(0, 6);
			if (top.length)
				s1.push({
					type: 'table',
					label: `주요 주주 (${d.shareholders.year} 기준)`,
					data: top.map((r) => ({ 주주: r.name, 관계: r.relate || '-', 지분율: fmtPct(r.ratio) }))
				});
			if (d.shareholders.person) s1.push({ type: 'text', text: `특수관계 개인 ${d.shareholders.person.count}인은 개인정보 보호로 익명 집계(합산 지분 ${fmtPct(d.shareholders.person.ratio)})했습니다.` });
		}
		sections.push({ key: 'ownershipStruct', title: '소유 구조 -- 누가 이 회사를 가졌나', sourceEngine: 'analysis', blocks: s1, emph: true });
		findings.push({ key: '소유', finding: `최대주주측 ${fmtPct(majorL)} · 소액주주 ${fmtPct(minorL)}.`, sourceEngine: 'analysis' });
	}

	// S2 인력
	const wf = d.workforce?.slice(-6) ?? [];
	if (wf.length) {
		const wfTbl = reportTable(
			wf.map((y) => y.year),
			[
				{ label: '총원', cells: wf.map((y) => fmtNum(y.total, '명')) },
				{ label: '정규직', cells: wf.map((y) => fmtNum(y.regular, '명')) },
				{ label: '평균 급여', cells: wf.map((y) => fmtPay(y.avgSalary)) },
				{ label: '평균 근속', cells: wf.map((y) => (y.tenure != null ? `${(y.tenure as number).toFixed(1)}년` : '-')) }
			],
			'인력 지표',
			'인력·보상 추이'
		);
		const last = wf[wf.length - 1];
		if (wfTbl)
			sections.push({
				key: 'workforce',
				title: '인력 -- 누가 일하고 얼마를 받나',
				sourceEngine: 'analysis',
				blocks: [{ type: 'text', text: `직원 규모와 보상입니다. 평균 급여는 급여총액을 인원으로 나눈 값으로 직군 구성에 따라 회사 간 단순 비교는 주의가 필요합니다.` }, wfTbl]
			});
		if (wfTbl) findings.push({ key: '인력', finding: `총원 ${fmtNum(last.total, '명')} · 평균급여 ${fmtPay(last.avgSalary)} · 근속 ${last.tenure != null ? (last.tenure as number).toFixed(1) + '년' : '-'}.`, sourceEngine: 'analysis' });
	}

	// S3 이사회·보수
	const eb = d.execBoard?.slice(-6) ?? [];
	if (eb.length) {
		const ebTbl = reportTable(
			eb.map((y) => y.year),
			[
				{ label: '이사회 인원', cells: eb.map((y) => fmtNum(y.directors, '명')) },
				{ label: '사외이사', cells: eb.map((y) => fmtNum(y.outsideDirectors, '명')) },
				{ label: '사외이사 비율', cells: eb.map((y) => (y.directors != null && (y.directors as number) > 0 && y.outsideDirectors != null ? fmtPct(((y.outsideDirectors as number) / (y.directors as number)) * 100) : '-')) },
				{ label: '이사·감사 1인 평균보수', cells: eb.map((y) => fmtPay(y.execAvgPay)) }
			],
			'이사회 지표',
			'이사회 구성·보수 추이'
		);
		const s3: ReportBlock[] = [{ type: 'text', text: `이사회 구성과 보수입니다. 사외이사 비율이 높을수록 경영진 견제 장치가 두텁다고 봅니다(과반이 권고 기준).` }];
		if (ebTbl) s3.push(ebTbl);
		// 상위 임원 보수(현재)
		if (d.topExecPay?.rows?.length) {
			const rows = d.topExecPay.rows.slice(0, 6);
			s3.push({ type: 'table', label: `상위 임원 보수 (${d.topExecPay.year} 기준)`, data: rows.map((r) => ({ 임원: r.name, 직위: r.title || '-', 보수: fmtPay(r.pay) })) });
			if (d.topExecPay.avgPay != null) s3.push({ type: 'text', text: `같은 해 이사·감사 1인 평균보수는 ${fmtPay(d.topExecPay.avgPay)}입니다 — 상위 임원과의 격차를 함께 보십시오.` });
		}
		if (ebTbl) {
			sections.push({ key: 'board', title: '이사회·보수 -- 누가 견제하고 얼마를 받나', sourceEngine: 'analysis', blocks: s3 });
			const lastEb = eb[eb.length - 1];
			findings.push({ key: '이사회', finding: `이사회 ${fmtNum(lastEb.directors, '명')} · 사외이사 ${fmtNum(lastEb.outsideDirectors, '명')}.`, sourceEngine: 'analysis' });
		}
	}

	// S4 감사·외부출자
	const at = d.auditTrail?.slice(-6) ?? [];
	const af = d.auditFees?.slice(-1)?.[0] ?? null;
	if (at.length || af) {
		const s4: ReportBlock[] = [];
		if (at.length) {
			s4.push({ type: 'text', text: `감사 이력입니다. 감사의견이 '적정'이 아니거나 자주 바뀌면 회계 신뢰성을 따져봐야 합니다.` });
			s4.push({ type: 'table', label: '감사 의견 이력', data: at.map((y) => ({ 사업연도: String(y.year), 감사인: y.auditor || '-', 감사의견: y.opinion || '-' })) });
			const nonClean = at.filter((y) => y.opinion && y.opinion !== '적정');
			if (nonClean.length) s4.push({ type: 'text', text: `※ 적정이 아닌 감사의견(${nonClean.map((y) => `${y.year} ${y.opinion}`).join(', ')})이 있습니다 — 회계 신뢰성을 별도로 확인하십시오.` });
			// 감사인 변경은 중립 사실로만 마킹(한국 주기적 지정감사=의무 로테이션이라 경보 아님).
			const auditors = [...new Set(at.map((y) => y.auditor).filter(Boolean))];
			if (auditors.length > 1) s4.push({ type: 'text', text: `감사인 변경: ${auditors.join(' → ')}. 한국은 주기적 지정감사 제도로 감사인 교체가 의무인 경우가 많아, 변경 자체가 부정 신호는 아닙니다.` });
		}
		const metrics: { label: string; value: string }[] = [];
		if (af) {
			metrics.push({ label: `감사보수 (${af.year})`, value: fmtPay(af.auditFee) });
			if (af.nonAuditFee != null) metrics.push({ label: '비감사보수', value: fmtPay(af.nonAuditFee) });
		}
		if (d.investments?.latest) {
			metrics.push({ label: `타법인 출자사 (${d.investments.latest.year})`, value: fmtNum(d.investments.latest.rows.length, '개사') });
			const book = d.investments.latest.rows.reduce((s, r) => s + ((r.bookValue as number) || 0), 0);
			if (book > 0) metrics.push({ label: '출자 장부가 합계', value: fmtPay(book) });
		}
		if (metrics.length) s4.push({ type: 'metrics', metrics });
		if (s4.length) {
			sections.push({ key: 'audit', title: '감사·외부출자 -- 회계는 믿을 만한가', sourceEngine: 'analysis', blocks: s4 });
			const lastAt = at[at.length - 1];
			if (lastAt) findings.push({ key: '감사', finding: `${lastAt.year} 감사의견 ${lastAt.opinion || '-'} (${lastAt.auditor || '-'}).`, sourceEngine: 'analysis' });
		}
	}

	if (!sections.length) return null;

	const lastAt = at[at.length - 1];
	const wfTotalL = lastNonNull(wf.map((y) => y.total));
	const wfSalaryL = lastNonNull(wf.map((y) => y.avgSalary));
	const odL = lastNonNull(eb.map((y) => y.outsideDirectors));
	const totalStr = wf.length ? fmtNum(wfTotalL, '명') : '-';
	const odStr = eb.length ? fmtNum(odL, '명') : '-';
	const kpis: ReportModel['headlineKpis'] = [
		{ label: '최대주주측 지분', value: fmtPct(majorL) },
		{ label: '소액주주 지분', value: fmtPct(minorL) },
		{ label: '총원', value: totalStr },
		{ label: '평균 급여', value: wf.length ? fmtPay(wfSalaryL) : '-' },
		{ label: '사외이사', value: odStr },
		{ label: '감사의견', value: lastAt?.opinion || '-' }
	];
	const conclusion = `${corpName} — 최대주주측 지분 ${fmtPct(majorL)}, 총원 ${totalStr}${lastAt ? `, ${lastAt.year} 감사의견 ${lastAt.opinion || '-'}` : ''}.`;
	const closing: ReportModel['closing'] = [
		{ label: '재무', engine: 'analysis', line: `최대주주측 ${fmtPct(majorL)} · 총원 ${totalStr} · 사외이사 ${odStr}${lastAt ? ` · 감사의견 ${lastAt.opinion || '-'}` : ''}.` }
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
	} else if (persp.key === 'market') {
		const kospi = KR_INDEX_PRESETS[0]; // 코스피 (시장 메타 부재 → 명시 라벨로 정직)
		const [candles, marketCandles, sr] = await Promise.all([
			rt.price.govCandles(code).catch(() => null),
			rt.index.series(kospi).catch(() => null),
			rt.report.shareholderReturn(code).catch(() => null)
		]);
		built = buildMarket(candles, marketCandles, sr, { corpName });
	} else if (persp.key === 'ownership') {
		const [shareholders, ownership, workforce, execBoard, topExecPay, auditTrail, auditFees, investments] = await Promise.all([
			rt.report.shareholders(code).catch(() => null),
			rt.report.ownership(code).catch(() => null),
			rt.report.workforce(code).catch(() => null),
			rt.report.execBoard(code).catch(() => null),
			rt.report.topExecPay(code).catch(() => null),
			rt.report.auditTrail(code).catch(() => null),
			rt.report.auditFees(code).catch(() => null),
			rt.report.investments(code).catch(() => null)
		]);
		built = buildOwnership({ shareholders, ownership, workforce, execBoard, topExecPay, auditTrail, auditFees, investments }, { corpName });
	} else {
		built = buildEarningsPower(tf, ctx);
	}
	if (!built || !built.sections.length)
		return { skipped: true, stockCode: code, reason: '이 관점에 채울 데이터가 부족합니다(예: 무배당 기업).' };

	// 출처 = 섹션 sourceEngine 별 정직 집계(재무/시장 혼재 시 각각).
	const ENG_LABEL: Record<string, string> = {
		analysis: '재무분석 (브라우저 리얼타임)',
		quant: '시장·기술 (브라우저 리얼타임)',
		credit: '신용평가',
		industry: '산업비교',
		macro: '거시',
		story: '종합서사'
	};
	const engAgg: Record<string, { label: string; sections: number; blocks: number }> = {};
	for (const s of built.sections) {
		const e = s.sourceEngine;
		if (!engAgg[e]) engAgg[e] = { label: ENG_LABEL[e] ?? e, sections: 0, blocks: 0 };
		engAgg[e].sections++;
		engAgg[e].blocks += s.blocks.length;
	}

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
			engines: engAgg,
			note: '모든 수치는 HuggingFace parquet(재무·주가·정기보고)을 브라우저가 직접 읽어 계산했습니다. 정적 캐시·사전 bake 없음 — 조회 시점 리얼타임.'
		},
		assumptionsNote:
			'연간(사업보고서) 기준 · 분기는 누계 처리 · 표 단위는 자릿수에 따라 조/억 자동 스케일 · 공시 항목이 빈약한 행은 표에서 자동 생략 · 영업외 일회성 손익이 큰 해는 본문에 각주로 표시 · 재무건전성 점검은 브라우저 재무비율 계산(Python 신용등급 dCR 아님). 주주환원·시장의 평가·누구의 회사 관점은 후속 사이클에서 추가됩니다.',
		qualityLabel: built.sections.length >= 3 ? 'verified' : 'conditional',
		focusQuestions: persp.focusQuestions
	};
}
