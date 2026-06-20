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
import { pYear, fmtPct, fmtPctSigned, fmtMult, fmtAmt1, scaleAmt, fmtScaled } from './format';

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

	const built = buildEarningsPower(tf, { corpName, yearCols, pick });
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
		narrativeOverview: `이 보고서는 ${corpName}의 손익·마진·성장·이익품질을 연간 공시 기준으로 정리했습니다. 모든 수치는 데이터 작업대에서 조회 시점에 계산되며, 사전 bake·정적 캐시는 사용하지 않습니다.`,
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
			'연간(사업보고서) 기준 · 분기는 누계 처리 · 표 단위는 자릿수에 따라 조/억 자동 스케일 · 공시 항목이 빈약한 행(예: 일부 기업의 매출원가)은 표에서 자동 생략 · 영업외 일회성 손익이 큰 해는 본문에 각주로 표시. 신용·산업·시장·주주환원 관점은 후속 사이클에서 추가됩니다.',
		qualityLabel: built.sections.length >= 3 ? 'verified' : 'conditional',
		focusQuestions: persp.focusQuestions
	};
}
