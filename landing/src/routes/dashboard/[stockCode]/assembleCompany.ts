// @ts-nocheck
/**
 * 대시보드 v16 — 클라이언트 사이드 회사 데이터 조립.
 *
 * 입력: ecosystem.json + finance.json + valuation.json + meta.json + stockCode
 * 출력: sections/*.svelte 가 소비하는 `company` 객체 (Hero/Health/Past/Financials/Value/Future/Health_fin/Supply/Thesis/Blog/Engines)
 *
 * 런타임 계산:
 *  - radar: ecosystem grades (A-F) → 1-5
 *  - Altman Z: finance.bs.totals 로부터 공식 적용
 *  - Supply: ecosystem.links 필터링 (target=code | source=code)
 */

// ── 유틸 ──
// ecosystem 의 grade 필드는 한국어/영문 혼합. 필드별 값 분포:
//   profGrade: 우수/양호/보통/저수익/적자
//   growthGrade: 고성장/성장/정체/급감/역성장
//   debtGrade: 안전/관찰/주의/고위험
//   qualGrade: 우수/양호/보통/주의/위험
//   govGrade: A/B/C/D/E (영문)
//   liqGrade: 우수/양호/보통/주의/위험
//   stability: 안정/보통/경고/위험/취약
const GRADE_SCORE: Record<string, number> = {
	// 영문 (govGrade 등)
	A: 5, B: 4, C: 3, D: 2, E: 1, F: 1,
	// 수익성
	'우수': 5, '양호': 4, '보통': 3, '저수익': 2, '적자': 1,
	// 성장
	'고성장': 5, '성장': 4, '정체': 3, '급감': 2, '역성장': 1,
	// 안정성/부채
	'안전': 5, '관찰': 3, '주의': 2, '고위험': 1,
	// 품질/유동성
	'위험': 1,
	// 공통 사용
	'안정': 5, '경고': 2, '취약': 1
};

const gradeToScore = (g?: string | null) => {
	if (!g) return 3;
	return GRADE_SCORE[g] ?? 3;
};

const gradeToStatus = (g?: string | null): 'pass' | 'warn' | 'fail' => {
	const s = gradeToScore(g);
	if (s >= 4) return 'pass';
	if (s >= 3) return 'warn';
	return 'fail';
};

// grade letter for display: 원본 한국어 그대로 리턴 (영문 A~E 는 그대로)
const gradeLetter = (g?: string | null): string => {
	if (!g) return '—';
	// 영문 A~E 는 단일문자로
	if (/^[A-F]$/.test(g)) return g;
	return g;
};

const pct = (v?: number | null) => (typeof v === 'number' ? v : 0);
const fmt1 = (v?: number | null) => (typeof v === 'number' ? v.toFixed(1) : '—');

// 배열의 null/undefined 을 0 으로. 컴포넌트의 Math.max/.../reduce 가 NaN 내지 않도록.
const safeArr = (arr: (number | null | undefined)[] | undefined, len = 5): number[] => {
	const base = arr && arr.length ? arr : new Array(len).fill(0);
	return base.map((v) => (typeof v === 'number' && Number.isFinite(v) ? v : 0));
};

// ── Altman Z (Public Manufacturing) ──
// Z = 1.2·(WC/TA) + 1.4·(RE/TA) + 3.3·(EBIT/TA) + 0.6·(MVE/TL) + 1.0·(S/TA)
function calcAltmanZ(fin: any, mve: number | null): number | null {
	const bs = fin?.bs?.totals;
	const is_ = fin?.is;
	const bsE = fin?.bs?.equity;
	if (!bs || !is_) return null;
	const lastIdx = 4; // 2025 (last year)
	const ta = bs.totalAsset?.[lastIdx];
	const tl = bs.totalLiab?.[lastIdx];
	const ca = bs.currAsset?.[lastIdx];
	const cl = bs.currLiab?.[lastIdx];
	const re = bsE?.retained?.[lastIdx];
	const ebit = is_.op?.[lastIdx];
	const sales = is_.sales?.[lastIdx];
	if (!ta || ta <= 0) return null;
	const wc = (ca ?? 0) - (cl ?? 0);
	const A = wc / ta;
	const B = (re ?? 0) / ta;
	const C = (ebit ?? 0) / ta;
	const D = mve && tl ? mve / tl : 0.6; // fallback average
	const E = (sales ?? 0) / ta;
	const z = 1.2 * A + 1.4 * B + 3.3 * C + 0.6 * D + 1.0 * E;
	return Math.round(z * 100) / 100;
}

// ── Beneish M-Score (simplified 5-var) ──
// M = -6.065 + 0.823·DSRI + 0.906·GMI + 0.593·AQI (간이)
function calcBeneishM(fin: any): number | null {
	const is_ = fin?.is;
	const bs = fin?.bs?.totals;
	const assets = fin?.bs?.assets;
	if (!is_ || !bs || !assets) return null;
	const i = 4; // 2025
	const p = 3; // 2024
	const salesNow = is_.sales?.[i];
	const salesPrev = is_.sales?.[p];
	if (!salesNow || !salesPrev || salesPrev <= 0) return null;

	const recvNow = assets.recv?.[i] ?? 0;
	const recvPrev = assets.recv?.[p] ?? 0;
	const dsri = recvPrev > 0 && salesNow > 0 ? (recvNow / salesNow) / (recvPrev / salesPrev) : 1;

	const costPrev = (salesPrev ?? 0) - (is_.op?.[p] ?? 0);
	const costNow = (salesNow ?? 0) - (is_.op?.[i] ?? 0);
	const gmPrev = salesPrev > 0 ? (salesPrev - costPrev) / salesPrev : 0;
	const gmNow = salesNow > 0 ? (salesNow - costNow) / salesNow : 0;
	const gmi = gmNow > 0 ? gmPrev / gmNow : 1;

	const taNow = bs.totalAsset?.[i] ?? 1;
	const taPrev = bs.totalAsset?.[p] ?? 1;
	const aqiNow = taNow > 0 ? 1 - (assets.cash?.[i] ?? 0) / taNow : 0;
	const aqiPrev = taPrev > 0 ? 1 - (assets.cash?.[p] ?? 0) / taPrev : 0;
	const aqi = aqiPrev > 0 ? aqiNow / aqiPrev : 1;

	const m = -6.065 + 0.823 * dsri + 0.906 * gmi + 0.593 * aqi;
	return Math.round(m * 100) / 100;
}

// ── Supply chain 추출 ──
function extractSupply(code: string, nodes: any[], links: any[]) {
	const nodeMap = new Map(nodes.map((n) => [n.id, n]));
	const suppliers: any[] = [];
	const customers: any[] = [];

	for (const link of links) {
		if (link.type !== 'supplier') continue;
		if (link.target === code) {
			const n = nodeMap.get(link.source);
			suppliers.push({
				name: n?.label ?? link.source,
				role: link.product || '—',
				share: Math.round((link.ratio ?? 0) * 10) / 10
			});
		} else if (link.source === code) {
			const n = nodeMap.get(link.target);
			customers.push({
				name: n?.label ?? link.target,
				role: link.product || '—',
				share: Math.round((link.ratio ?? 0) * 10) / 10
			});
		}
	}

	suppliers.sort((a, b) => b.share - a.share);
	customers.sort((a, b) => b.share - a.share);
	const top5s = suppliers.slice(0, 5);
	const top5c = customers.slice(0, 5);

	const shares = [...top5s.map((s) => s.share), ...top5c.map((s) => s.share)];
	const hhi = Math.round(shares.reduce((sum, s) => sum + s * s, 0));
	const hhiLabel = hhi > 2500 ? '높은 집중' : hhi > 1500 ? '중간 집중' : '낮은 집중';

	return { hhi, hhiLabel, suppliers: top5s, customers: top5c };
}

// ── Thesis (grade 기반 derive) ──
function deriveThesis(grades: Record<string, string>, templates: any) {
	const strengths: string[] = [];
	const weaknesses: string[] = [];
	for (const [key, g] of Object.entries(grades)) {
		if (g === 'A' || g === 'B') {
			const tkey = `A_${key}`;
			if (templates?.strengths?.[tkey]) strengths.push(templates.strengths[tkey]);
		} else if (g === 'F' || g === 'D') {
			const tkey = `F_${key}`;
			if (templates?.weaknesses?.[tkey]) weaknesses.push(templates.weaknesses[tkey]);
		}
	}
	if (strengths.length === 0) strengths.push('주요 등급은 평균 수준');
	if (weaknesses.length === 0) weaknesses.push('중대한 리스크 플래그 없음');
	const summary = `업종 대비 등급 — 수익성 ${grades.profit ?? '—'}, 성장 ${grades.growth ?? '—'}, 안정성 ${grades.stable ?? '—'}, 품질 ${grades.quality ?? '—'}`;
	return { summary, strengths: strengths.slice(0, 4), weaknesses: weaknesses.slice(0, 4) };
}

// ── 메인 조립 ──
export function assembleCompany(payload: {
	stockCode: string;
	ecosystem: any;
	finance: any;
	valuation?: any;
	meta: any;
	quarters?: any;
	macro?: any;
	companyMeta?: any;
	industryMeta?: any;
	industryId?: string | null;
}) {
	const {
		stockCode,
		ecosystem,
		finance,
		valuation,
		meta,
		quarters,
		macro,
		companyMeta,
		industryMeta,
		industryId
	} = payload;
	// node lookup: ecosystem 우선, 없으면 companyMeta.ego 활용 (HF 폴백 시)
	let node = ecosystem?.nodes?.find((n: any) => n.id === stockCode);
	if (!node && companyMeta?.ego) {
		node = {
			id: companyMeta.ego.stockCode,
			label: companyMeta.ego.corpName,
			industry: companyMeta.ego.industry,
			industryName: companyMeta.ego.industry,
			stageName: companyMeta.ego.stage,
			role: companyMeta.ego.role,
			revenue: companyMeta.ego.revenue
		};
	}
	if (!node) return null;

	const fin = finance?.companies?.[stockCode] ?? null;
	const val = valuation?.companies?.[stockCode] ?? null;
	const q = quarters?.companies?.[stockCode] ?? null;
	const years: string[] = finance?.years ?? ['2021', '2022', '2023', '2024', '2025'];

	// ── 1. Identity ──
	const sectorKR = node.industryName || node.industry || '기타';
	const identity = {
		code: stockCode,
		name: node.label,
		market: 'KOSPI',
		sector: sectorKR,
		subsector: node.industryName ?? sectorKR,
		lifecycle: node.stageName ?? '성숙기',
		type: node.role ?? '일반',
		ceo: '—',
		listed: '—'
	};

	// ── 2. Price ──
	const revenue = node.revenue ?? 0;
	const marketCapStr = revenue >= 10000 ? `${(revenue / 10000).toFixed(1)}조` : `${Math.round(revenue)}억`;
	const price = {
		price: val?.current || 0,
		priceChange: 0,
		marketCap: marketCapStr,
		per: 0,
		pbr: 0,
		dy: 0
	};

	// ── 3. Radar 5축 ──
	const grades = {
		profit: node.profGrade,
		growth: node.growthGrade,
		stable: node.debtGrade,
		quality: node.qualGrade,
		gov: node.govGrade
	};
	const radar = {
		axes: ['수익성', '성장', '안정성', '품질', '지배구조'],
		company: [
			gradeToScore(grades.profit),
			gradeToScore(grades.growth),
			gradeToScore(grades.stable),
			gradeToScore(grades.quality),
			gradeToScore(grades.gov)
		],
		sector: [3, 3, 3, 3, 3]
	};

	// ── 4. Verdict — 실제 grade 있을 때만 생성 (없으면 null → Hero 에서 배지 숨김) ──
	const gradeValues = [grades.profit, grades.growth, grades.stable, grades.quality, grades.gov];
	const haveGrades = gradeValues.filter(Boolean).length >= 3;
	let verdict: any = null;
	if (haveGrades) {
		const scores = gradeValues.map((g) => (g ? gradeToScore(g) : null)).filter((v) => v != null);
		const avgGrade = scores.reduce((s, v) => s + (v as number), 0) / scores.length;
		let call: 'BUY' | 'HOLD' | 'SELL';
		let confidence: number;
		if (val?.mos && val.mos > 20) {
			call = 'BUY';
			confidence = 72;
		} else if (val?.mos && val.mos < -15) {
			call = 'SELL';
			confidence = 68;
		} else if (avgGrade >= 4) {
			call = 'BUY';
			confidence = 64;
		} else if (avgGrade <= 2) {
			call = 'SELL';
			confidence = 62;
		} else {
			call = 'HOLD';
			confidence = 60;
		}
		const verdictLine =
			call === 'BUY'
				? meta?.thesisTemplates?.default?.call_buy
				: call === 'SELL'
					? meta?.thesisTemplates?.default?.call_sell
					: meta?.thesisTemplates?.default?.call_hold;
		verdict = {
			call,
			confidence,
			oneLiner: verdictLine ?? `종합 스코어 ${avgGrade.toFixed(1)}/5. 재무·공급망·매크로 통합 분석.`
		};
	}

	// ── 5. Health 6축 ──
	const health = [
		{
			key: 'profit',
			label: '수익성',
			status: gradeToStatus(grades.profit),
			note: `영업이익률 ${fmt1(node.opMargin)}%, 등급 ${grades.profit ?? '—'}`
		},
		{
			key: 'growth',
			label: '성장',
			status: gradeToStatus(grades.growth),
			note: `매출 YoY ${fmt1(node.revenueYoyPct)}%, 등급 ${grades.growth ?? '—'}`
		},
		{
			key: 'stable',
			label: '안정성',
			status: gradeToStatus(grades.stable),
			note: `부채비율 ${fmt1(node.debtRatio)}%, 등급 ${grades.stable ?? '—'}`
		},
		{
			key: 'quality',
			label: '품질',
			status: gradeToStatus(grades.quality),
			note: `ROE ${fmt1(node.roe)}%, 품질등급 ${grades.quality ?? '—'}`
		},
		{
			key: 'gov',
			label: '지배구조',
			status: gradeToStatus(grades.gov),
			note: `지분 ${fmt1(node.holderPct)}%, 감사 ${node.auditRisk ?? '—'}`
		},
		{
			key: 'macro',
			label: '매크로',
			status: 'pass' as const,
			note: '현재 사이클 국면 기준 중립~우호.'
		}
	];

	// ── 6. Past 5Y (annual → 분기 근사) ──
	const past = {
		periods: years,
		revenue: safeArr(fin?.is?.sales, years.length),
		opIncome: safeArr(fin?.is?.op, years.length),
		roe: safeArr(fin?.ratios?.roe, years.length),
		debtRatio: safeArr(fin?.ratios?.debtRatio, years.length),
		revenueCAGR: Number.isFinite(node.revCagr) ? node.revCagr : 0,
		opIncomeCAGR: 0
	};

	// ── 7. IS/BS/CF ──
	const is_ = {
		years,
		revenue: safeArr(fin?.is?.sales, years.length),
		opIncome: safeArr(fin?.is?.op, years.length),
		netIncome: safeArr(fin?.is?.net, years.length),
		opMargin: safeArr(fin?.is?.opMargin, years.length)
	};
	const bs = {
		years,
		assets: {
			cash: safeArr(fin?.bs?.assets?.cash, years.length),
			receivables: safeArr(fin?.bs?.assets?.recv, years.length),
			inventory: safeArr(fin?.bs?.assets?.inv, years.length),
			tangible: safeArr(fin?.bs?.assets?.tang, years.length),
			intangible: safeArr(fin?.bs?.assets?.intan, years.length),
			other: new Array(years.length).fill(0)
		},
		liabilities: {
			payables: safeArr(fin?.bs?.liab?.pay, years.length),
			shortDebt: safeArr(fin?.bs?.liab?.shortDebt, years.length),
			longDebt: safeArr(fin?.bs?.liab?.longDebt, years.length),
			bonds: safeArr(fin?.bs?.liab?.bonds, years.length),
			provisions: safeArr(fin?.bs?.liab?.prov, years.length),
			other: new Array(years.length).fill(0)
		},
		equity: {
			paidIn: safeArr(fin?.bs?.equity?.paidIn, years.length),
			capitalSurplus: safeArr(fin?.bs?.equity?.surplus, years.length),
			retained: safeArr(fin?.bs?.equity?.retained, years.length),
			otherComp: safeArr(fin?.bs?.equity?.otherComp, years.length),
			treasury: new Array(years.length).fill(0)
		}
	};
	const cfRaw = fin?.cf ?? {};
	const finite = (v: any) => (typeof v === 'number' && Number.isFinite(v) ? v : 0);
	const cf = {
		year: years[years.length - 1],
		opening: finite(cfRaw.opening),
		operating: finite(cfRaw.op),
		investing: finite(cfRaw.inv),
		financing: finite(cfRaw.fin),
		fxEffect: finite(cfRaw.fx),
		closing: finite(cfRaw.closing)
	};

	// ── 8. Value ──
	const value = val
		? {
				methods: val.methods ?? [],
				blended: val.blended ?? 0,
				mos: val.mos ?? 0,
				scenarios: {
					bull: { target: Math.round((val.blended ?? 0) * 1.4), prob: 22 },
					base: { target: val.blended ?? 0, prob: 56 },
					bear: { target: Math.round((val.blended ?? 0) * 0.7), prob: 22 }
				}
			}
		: null; // skeleton 처리는 +page 에서

	// fairValue/fairRange for Hero
	const fairValue = val?.blended ?? 0;
	const fairRange = fairValue > 0 ? [Math.round(fairValue * 0.85), Math.round(fairValue * 1.15)] : [0, 0];

	// ── 9. Future — 합성 curve 제거. quant prebuild 없으면 null (섹션 숨김) ──
	// 현재 quant forecast prebuild 가 없으므로 항상 null.
	// TODO: c.future = quant?.forecast?.companies?.[stockCode] 같이 실데이터 연결 시 복원.
	const future = null;

	// ── 10. Health_fin — Altman/Beneish 계산 실패 시 null → 섹션 숨김 ──
	const altmanZ = calcAltmanZ(fin, null);
	const beneishM = calcBeneishM(fin);
	const flags: { level: string; text: string }[] = [];
	if (node.debtRatio && node.debtRatio > 200) {
		flags.push({ level: 'warn', text: `부채비율 ${fmt1(node.debtRatio)}% — 업종 대비 높음` });
	}
	if (node.opMargin !== null && node.opMargin !== undefined && node.opMargin < 0) {
		flags.push({ level: 'warn', text: '영업손실 — 수익성 회복 필요' });
	}
	if (node.icr && node.icr > 5) {
		flags.push({ level: 'info', text: `이자보상배율 ${fmt1(node.icr)}x (안전)` });
	}

	// Altman/Beneish 둘 다 null + flags 도 비어있으면 health_fin 자체 null
	const hasHealthData = altmanZ != null || beneishM != null || flags.length > 0;
	const health_fin = hasHealthData
		? {
				altmanZ:
					altmanZ != null
						? {
								value: altmanZ,
								zones: [
									{ max: 1.81, l: 'Distress' },
									{ max: 2.99, l: 'Grey' },
									{ max: 6, l: 'Safe' }
								]
							}
						: null,
				beneishM:
					beneishM != null
						? {
								value: beneishM,
								flag: beneishM > -1.78 ? 'Manipulation risk — review' : 'Low manipulation risk'
							}
						: null,
				flags: flags.length ? flags : [{ level: 'info', text: '주요 재무 flag 없음' }]
			}
		: null;

	// ── 11. Supply ──
	const supply = extractSupply(stockCode, ecosystem.nodes ?? [], ecosystem.links ?? []);

	// ── 12. Thesis ──
	const thesis = deriveThesis(grades, meta?.thesisTemplates);

	// ── 13. Blog ──
	const blog = meta?.blog?.[stockCode] ?? {
		slug: '',
		title: `${identity.name} — 블로그 준비 중`,
		date: '',
		excerpt: '심층분석 글은 아직 작성되지 않았습니다.',
		readTime: '—'
	};

	// ── 14. Engines ──
	const engines = meta?.engines ?? [];

	// ── 15. Quarters (v19) — 20분기 시계열 ──
	const quartersOut = q
		? {
				periods: quarters?.periods ?? [],
				is: q.is ?? {},
				cf: q.cf ?? {},
				bs: q.bs ?? {}
			}
		: null;

	// ── 16. Macro (v19) — 시장 국면 + 섹터 가중 ──
	const macroOut = macro
		? {
				asOf: macro.asOf,
				kr: macro.kr,
				us: macro.us,
				sectorTailwind: macro.sectorTailwind?.[node.industry] ?? null,
				industry: node.industry
			}
		: null;

	// ── 17. Ego (v22) — companies/{code}.json 11 필드 ──
	const egoOut = companyMeta
		? {
				ego: companyMeta.ego ?? null,
				aiInsight: companyMeta.aiInsight ?? null,
				blogPosts: companyMeta.blogPosts ?? [],
				financials5y: companyMeta.financials5y ?? [],
				supplyInsights: companyMeta.supplyInsights ?? null,
				peers: companyMeta.peers ?? [],
				suppliersTop10: companyMeta.suppliers ?? [],
				customersTop10: companyMeta.customers ?? [],
				neighborsCount: Array.isArray(companyMeta.neighbors) ? companyMeta.neighbors.length : 0,
				edgesCount: Array.isArray(companyMeta.edges) ? companyMeta.edges.length : 0,
				hop2Count: companyMeta.hop2?.hop2Neighbors?.length ?? 0
			}
		: null;

	// ── 18. Industry Context (v23) — industries/{id}.json 에서 derive ──
	let industryContext: any = null;
	let peersFromIndustry: any = null;
	if (industryMeta && Array.isArray(industryMeta.stages)) {
		// 전체 회사 flat + 이 회사의 stage
		const allNodes: any[] = [];
		let myStage: string | null = null;
		let myStageName: string | null = null;
		for (const stg of industryMeta.stages) {
			for (const nd of stg.nodes ?? []) {
				allNodes.push({ ...nd, _stageKey: stg.key, _stageName: stg.name });
				if (nd.stockCode === stockCode) {
					myStage = stg.key;
					myStageName = stg.name;
				}
			}
		}

		// stage 분포
		const stagesSummary = (industryMeta.stages ?? []).map((stg: any) => ({
			key: stg.key,
			name: stg.name,
			count: (stg.nodes ?? []).length,
			totalRevenue: (stg.nodes ?? []).reduce((s: number, n: any) => s + (Number(n.revenue) || 0), 0)
		}));

		// 전체 순위 (revenue 기준)
		const sortedByRev = [...allNodes].sort((a, b) => (b.revenue ?? 0) - (a.revenue ?? 0));
		const myRankOverall = sortedByRev.findIndex((n) => n.stockCode === stockCode) + 1 || null;

		industryContext = {
			industryId,
			name: industryMeta.name ?? industryId,
			totalRevenue: industryMeta.totalRevenue ?? 0,
			nodeCount: industryMeta.nodeCount ?? allNodes.length,
			stagesSummary,
			myStage,
			myStageName,
			myRank: myRankOverall,
			totalInIndustry: allNodes.length,
			edgesCount: Array.isArray(industryMeta.edges) ? industryMeta.edges.length : 0
		};

		// Peer 선정: 같은 stage top 10 by revenue (없으면 업종 전체 top 10). 본인 포함.
		const sameStage = myStage ? allNodes.filter((n) => n._stageKey === myStage) : allNodes;
		const peerPool = sameStage.length >= 3 ? sameStage : allNodes;
		const peersSorted = [...peerPool].sort((a, b) => (b.revenue ?? 0) - (a.revenue ?? 0)).slice(0, 10);
		peersFromIndustry = {
			stageKey: myStage,
			stageName: myStageName,
			stageFallback: sameStage.length < 3, // peer 부족해서 업종 전체 기준으로 대체했는지
			rows: peersSorted.map((n) => ({
				stockCode: n.stockCode,
				corpName: n.corpName,
				revenue: n.revenue ?? null,
				roe: n.roe ?? null,
				opMargin: n.opMargin ?? null,
				debtRatio: n.debtRatio ?? null,
				revCagr: n.revCagr ?? null,
				profGrade: n.profGrade ?? null,
				isSelf: n.stockCode === stockCode
			}))
		};
	}

	return {
		...identity,
		...price,
		fairValue,
		fairRange,
		verdict,
		radar,
		health,
		past,
		is: is_,
		bs,
		cf,
		value,
		future,
		health_fin,
		supply,
		thesis,
		blog,
		engines,
		// v19 신규
		quarters: quartersOut,
		macro: macroOut,
		// v22 신규
		egoData: egoOut,
		// v23 신규
		industryContext,
		peersFromIndustry
	};
}
