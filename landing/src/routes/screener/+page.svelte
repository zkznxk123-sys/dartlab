<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import FreshnessBadge from '$lib/components/industry/FreshnessBadge.svelte';
	import { fmtKrw, fmtKrwFromEok, fmtPrice } from '$lib/format/krw';
	import { fmtPct } from '$lib/format/pct';
	import type { Cond, Op, SortKey, MetricKey, MetricDef, ScreenerNode, PriceSnapshot, QueryPayload } from '$lib/screener/types';
	import { loadDartDb, type DartDb } from '$lib/data/duckdb';
	import { PRESETS, PRESETS_BY_ID, PRESET_CATEGORIES, type Preset } from '$lib/screener/presets';
	import PresetCard from '$lib/screener/PresetCard.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// ── DuckDB 통한 KRX 일별 가격 시계열 query (lazy, background) ──
	// PR-3: mount 시 백그라운드에서 DuckDB 로드 + HF parquet 등록 시작.
	// ready 되면 currentVsMA20 / drawdown60d 같은 시계열 derived 메트릭 활성.
	// 미지원 브라우저 (iOS Safari) 또는 미로드 시 메트릭 자동 비활성 — 다른 메트릭 그대로 사용 가능.
	let dartDb: DartDb | null = $state(null);
	let dbState: 'idle' | 'loading' | 'ready' | 'error' | 'unsupported' = $state('idle');
	let dbError = $state('');
	/** stockCode → { currentPrice, ma20, low60, high60 } from DuckDB */
	let priceTimeSeries = $state<Map<string, { currentPrice: number; ma20: number | null; high60: number | null; low60: number | null }>>(new Map());

	// 메트릭 정의 — PR-1 은 25 개 (점-시점 + 이미 박힌 시계열 derived).
	// PR-2 부터 derived/composite/quarterly/timeseries modifier 추가.
	const METRICS: MetricDef[] = [
		// 손익 정량
		{ key: 'revenue', label: '매출 (원)', group: 'income', type: 'number', unit: '원', higherBetter: true },
		{ key: 'roe', label: 'ROE', group: 'income', type: 'number', unit: '%', higherBetter: true },
		{ key: 'opMargin', label: '영업이익률', group: 'income', type: 'number', unit: '%', higherBetter: true },
		{ key: 'revCagr', label: '매출 CAGR 3Y', group: 'income', type: 'number', unit: '%', higherBetter: true },
		{ key: 'revenueYoyPct', label: '매출 YoY', group: 'changes', type: 'number', unit: '%', signed: true, higherBetter: true },
		// Δ 변화
		{ key: 'roeDelta', label: 'ROE Δ', group: 'changes', type: 'number', unit: '%p', signed: true, higherBetter: true },
		{ key: 'opMarginDelta', label: '영업이익률 Δ', group: 'changes', type: 'number', unit: '%p', signed: true, higherBetter: true },
		{ key: 'debtRatioDelta', label: '부채비율 Δ', group: 'changes', type: 'number', unit: '%p', signed: true, higherBetter: false },
		// 재무건전성
		{ key: 'debtRatio', label: '부채비율', group: 'health', type: 'number', unit: '%', higherBetter: false },
		{ key: 'icr', label: 'ICR', group: 'health', type: 'number', unit: '배', higherBetter: true },
		// 인적·점유율
		{ key: 'empCount', label: '직원수', group: 'workforce', type: 'number', unit: '명' },
		{ key: 'marketShare', label: '산업 점유율', group: 'workforce', type: 'number', unit: '%', higherBetter: true },
		{ key: 'industryRank', label: '산업 내 순위', group: 'workforce', type: 'number', higherBetter: false },
		// 거버넌스 (정량)
		{ key: 'holderPct', label: '최대주주 지분', group: 'governance', type: 'number', unit: '%' },
		{ key: 'holderChange', label: '지분 변동', group: 'governance', type: 'number', unit: '%p', signed: true },
		// 가격·시총 (prices-snapshot)
		{ key: 'currentPrice', label: '현재가', group: 'price', type: 'number', unit: '원' },
		{ key: 'marketCap', label: '시가총액', group: 'price', type: 'number', unit: '원', higherBetter: true },
		{ key: 'return1m', label: '1M 수익률', group: 'price', type: 'number', unit: '%', signed: true, higherBetter: true },
		{ key: 'return3m', label: '3M 수익률', group: 'price', type: 'number', unit: '%', signed: true, higherBetter: true },
		{ key: 'return1y', label: '1Y 수익률', group: 'price', type: 'number', unit: '%', signed: true, higherBetter: true },
		{ key: 'volatility1y', label: '1Y 변동성', group: 'price', type: 'number', unit: '%', higherBetter: false },
		// 시계열 derived (DuckDB 가 KRX 일별을 query — PR-3 부터 활성)
		{ key: 'currentVsMA20', label: '현재가 vs MA20', group: 'derived', type: 'number', unit: '%', signed: true, higherBetter: true },
		{ key: 'drawdown60d', label: '60일 고점 대비', group: 'derived', type: 'number', unit: '%', signed: true, higherBetter: true },
		{ key: 'recovery60d', label: '60일 저점 대비', group: 'derived', type: 'number', unit: '%', signed: true, higherBetter: true },
		// 등급 (enum)
		{ key: 'profGrade', label: '수익성 등급', group: 'income', type: 'enum', values: ['우수', '양호', '보통', '저수익', '적자'] },
		{ key: 'debtGrade', label: '부채 등급', group: 'health', type: 'enum', values: ['안전', '관찰', '주의', '고위험'] },
		{ key: 'growthGrade', label: '성장 등급', group: 'income', type: 'enum', values: ['고성장', '성장', '정체', '역성장', '급감'] },
		{ key: 'govGrade', label: '거버넌스 등급', group: 'governance', type: 'enum', values: ['A', 'B', 'C', 'D', 'E'] },
		{ key: 'qualGrade', label: '이익질 등급', group: 'quality', type: 'enum', values: ['우수', '양호', '보통', '주의', '위험'] },
		{ key: 'liqGrade', label: '유동성 등급', group: 'quality', type: 'enum', values: ['우수', '양호', '보통', '주의', '위험'] },
		{ key: 'auditRisk', label: '감사 위험', group: 'quality', type: 'enum', values: ['안전', '관찰', '주의', '고위험'] },
		{ key: 'cfPattern', label: '현금흐름 패턴', group: 'quality', type: 'text' },
		{ key: 'capClass', label: '환원 분류', group: 'governance', type: 'text' },
		{ key: 'stability', label: '지분 안정성', group: 'governance', type: 'enum', values: ['우수', '보통', '주의'] }
	];

	const METRIC_BY_KEY = new Map(METRICS.map((m) => [m.key, m]));

	function metricLabel(key: MetricKey): string {
		const m = METRIC_BY_KEY.get(key);
		return m ? m.label : String(key);
	}

	// State
	let selectedIndustries = $state<Set<string>>(new Set());
	let conds = $state<Cond[]>([{ metric: 'roe', op: '>=', value: 10 }]);
	let sorts = $state<SortKey[]>([{ key: 'revenue', dir: 'desc' }]);
	let activePreset = $state<string | null>(null);
	let displayLimit = $state(500);

	// 데이터 join — ecosystem.nodes + prices-snapshot.data + priceTimeSeries (DuckDB derived)
	const joinedNodes = $derived.by(() => {
		const eco = (data.ecosystem as any)?.nodes ?? [];
		const prices = ((data.pricesSnapshot as any)?.data ?? {}) as Record<string, PriceSnapshot>;
		return eco.map((n: any) => {
			const snap = prices[n.id] ?? {};
			const ts = priceTimeSeries.get(n.id);
			let currentVsMA20: number | null = null;
			let drawdown60d: number | null = null;
			let recovery60d: number | null = null;
			if (ts) {
				if (ts.ma20 && ts.ma20 > 0) {
					currentVsMA20 = ((ts.currentPrice / ts.ma20) - 1) * 100;
				}
				if (ts.high60 && ts.high60 > 0) {
					drawdown60d = ((ts.currentPrice / ts.high60) - 1) * 100;
				}
				if (ts.low60 && ts.low60 > 0) {
					recovery60d = ((ts.currentPrice / ts.low60) - 1) * 100;
				}
			}
			return {
				...n,
				...snap,
				currentVsMA20,
				drawdown60d,
				recovery60d
			};
		}) as ScreenerNode[];
	});

	const industries = $derived(((data.ecosystem as any)?.industries ?? []) as Array<{ id: string; name: string; color: string; count?: number }>);

	function compareValue(a: unknown, b: unknown): number {
		if (a == null && b == null) return 0;
		if (a == null) return 1;
		if (b == null) return -1;
		if (typeof a === 'number' && typeof b === 'number') return a - b;
		return String(a).localeCompare(String(b));
	}

	function evalCond(n: ScreenerNode, c: Cond): boolean {
		const v = (n as any)[c.metric];
		if (v === null || v === undefined) return false;
		// 등급/문자열 enum
		if (typeof v === 'string' || typeof c.value === 'string') {
			if (c.op === '==') return String(v) === String(c.value);
			if (c.op === '!=') return String(v) !== String(c.value);
			return false;
		}
		const num = Number(v);
		if (!Number.isFinite(num)) return false;
		const t = Number(c.value);
		if (!Number.isFinite(t)) return false;
		if (c.op === '>=') return num >= t;
		if (c.op === '<=') return num <= t;
		if (c.op === '==') return num === t;
		if (c.op === '!=') return num !== t;
		if (c.op === 'between') {
			const t2 = c.value2 == null ? Infinity : Number(c.value2);
			if (!Number.isFinite(t2)) return num >= t;
			const lo = Math.min(t, t2);
			const hi = Math.max(t, t2);
			return num >= lo && num <= hi;
		}
		return true;
	}

	const results = $derived.by(() => {
		let out: ScreenerNode[] = joinedNodes;
		if (selectedIndustries.size > 0) {
			out = out.filter((n) => selectedIndustries.has(String(n.industry)));
		}
		for (const c of conds) {
			out = out.filter((n) => evalCond(n, c));
		}
		const sorted = [...out].sort((a, b) => {
			for (const s of sorts) {
				const va = (a as any)[s.key];
				const vb = (b as any)[s.key];
				const cmp = compareValue(va, vb);
				if (cmp !== 0) return s.dir === 'desc' ? -cmp : cmp;
			}
			return 0;
		});
		return sorted;
	});

	// URL 직렬화 — base64(JSON)
	function encodeQuery(): string {
		const payload: QueryPayload = {
			i: [...selectedIndustries],
			c: conds,
			s: sorts,
			...(activePreset ? { p: activePreset } : {})
		};
		return btoa(unescape(encodeURIComponent(JSON.stringify(payload))));
	}

	function decodeQuery(q: string) {
		try {
			const json = decodeURIComponent(escape(atob(q)));
			const p = JSON.parse(json) as Partial<QueryPayload>;
			if (Array.isArray(p.i)) selectedIndustries = new Set(p.i);
			if (Array.isArray(p.c)) conds = p.c;
			if (Array.isArray(p.s)) sorts = p.s;
			if (p.p) activePreset = p.p;
		} catch {
			/* ignore bad query */
		}
	}

	function shareUrl() {
		const q = encodeQuery();
		const url = `${typeof window !== 'undefined' ? window.location.origin : ''}${base}/screener?q=${q}`;
		if (typeof navigator !== 'undefined' && navigator.clipboard) {
			navigator.clipboard.writeText(url);
		}
	}

	function exportCsv() {
		const cols: string[] = [
			'id', 'label', 'industryName', 'stage', 'role', 'stream',
			'revenue', 'roe', 'opMargin', 'debtRatio', 'icr',
			'revCagr', 'revenueYoyPct', 'roeDelta', 'opMarginDelta', 'debtRatioDelta',
			'profGrade', 'debtGrade', 'growthGrade',
			'govGrade', 'qualGrade', 'liqGrade', 'auditRisk', 'cfPattern', 'capClass', 'stability',
			'holderPct', 'holderChange', 'empCount', 'marketShare', 'industryRank', 'industryPeerCount',
			'currentPrice', 'marketCap', 'return1m', 'return3m', 'return1y', 'volatility1y',
			'week52High', 'week52Low', 'volumeAvg30d', 'foreignPct', 'beta'
		];
		const escape = (v: unknown): string => {
			if (v === null || v === undefined) return '';
			if (typeof v === 'string') return `"${v.replace(/"/g, '""')}"`;
			return String(v);
		};
		const header = cols.join(',');
		const rows = results.map((n) => cols.map((c) => escape((n as any)[c])).join(','));
		const csv = '﻿' + header + '\n' + rows.join('\n');
		const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		const today = new Date().toISOString().slice(0, 10);
		a.download = `dartlab-screener-${today}.csv`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}

	onMount(() => {
		const q = page.url.searchParams.get('q');
		if (q) decodeQuery(q);
		const preset = page.url.searchParams.get('preset');
		if (preset) {
			applyPreset(preset);
		}
		// DuckDB lazy 로드 — 백그라운드, 비차단
		void loadPriceTimeSeries();
	});

	/** 프리셋 클릭 → conds + sorts 자동 입력 + activePreset 표시 + 산업 필터 클리어. */
	function applyPreset(presetId: string) {
		const preset = PRESETS_BY_ID.get(presetId);
		if (!preset) return;
		// 깊은 복사 (원본 보존)
		conds = preset.conds.map((c) => ({ ...c }));
		sorts = preset.sorts.map((s) => ({ ...s }));
		selectedIndustries = new Set();
		activePreset = preset.id;
	}

	/** 사용자가 조건을 직접 변경했을 때 active preset 표시 해제. */
	function markPresetDirty() {
		if (activePreset) activePreset = null;
	}

	/** DuckDB 통한 KRX 일별 가격 시계열 derived 메트릭 로드.
	 * 매핑: 종목 → {currentPrice, ma20 (20일 이평), high60/low60 (60일 H/L)}.
	 * 시계열 메트릭 (currentVsMA20, drawdown60d, recovery60d) 가 이 데이터 기반.
	 */
	async function loadPriceTimeSeries() {
		dbState = 'loading';
		try {
			const db = await loadDartDb();
			if (!db) {
				dbState = 'unsupported';
				return;
			}
			dartDb = db;
			const year = new Date().getFullYear();
			// 현재 연도 parquet 한 개만 우선 등록 (1Y 미만이면 last year 도 추후 union)
			await db.registerHfParquet('krxPrices', `krx/prices/raw-${year}.parquet`);
			// 종목별 최근 60거래일 종가에서 MA20, 60일 고점·저점 산출
			const rows = await db.query<{ ISU_CD: string; currentPrice: number; ma20: number | null; high60: number | null; low60: number | null }>(`
				WITH recent AS (
					SELECT
						ISU_CD,
						BAS_DD,
						CAST(TDD_CLSPRC AS DOUBLE) AS close,
						CAST(TDD_HGPRC AS DOUBLE) AS high,
						CAST(TDD_LWPRC AS DOUBLE) AS low,
						ROW_NUMBER() OVER (PARTITION BY ISU_CD ORDER BY BAS_DD DESC) AS rn
					FROM krxPrices
				),
				last60 AS (
					SELECT * FROM recent WHERE rn <= 60
				),
				ma20 AS (
					SELECT ISU_CD, AVG(close) AS ma20 FROM last60 WHERE rn <= 20 GROUP BY ISU_CD
				),
				latest AS (
					SELECT ISU_CD, close AS currentPrice FROM last60 WHERE rn = 1
				),
				bounds AS (
					SELECT ISU_CD, MAX(high) AS high60, MIN(low) AS low60 FROM last60 GROUP BY ISU_CD
				)
				SELECT
					l.ISU_CD,
					l.currentPrice,
					m.ma20,
					b.high60,
					b.low60
				FROM latest l
				LEFT JOIN ma20 m USING (ISU_CD)
				LEFT JOIN bounds b USING (ISU_CD)
			`);
			const map = new Map<string, { currentPrice: number; ma20: number | null; high60: number | null; low60: number | null }>();
			for (const r of rows) {
				map.set(r.ISU_CD, {
					currentPrice: Number(r.currentPrice),
					ma20: r.ma20 != null ? Number(r.ma20) : null,
					high60: r.high60 != null ? Number(r.high60) : null,
					low60: r.low60 != null ? Number(r.low60) : null
				});
			}
			priceTimeSeries = map;
			dbState = 'ready';
		} catch (err) {
			dbState = 'error';
			dbError = err instanceof Error ? err.message : String(err);
			console.warn('[screener] DuckDB 시계열 로드 실패', err);
		}
	}

	function addCond() {
		conds = [...conds, { metric: 'opMargin', op: '>=', value: 10 }];
	}
	function removeCond(i: number) {
		conds = conds.filter((_, idx) => idx !== i);
	}
	function addSort() {
		const used = new Set(sorts.map((s) => s.key));
		const next = (METRICS.find((m) => m.type === 'number' && !used.has(m.key))?.key ?? 'roe') as MetricKey;
		sorts = [...sorts, { key: next, dir: 'desc' }];
	}
	function removeSort(i: number) {
		sorts = sorts.filter((_, idx) => idx !== i);
	}
	function toggleIndustry(id: string) {
		const next = new Set(selectedIndustries);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		selectedIndustries = next;
	}
	function clearIndustries() {
		selectedIndustries = new Set();
	}
	function changeMetric(condIdx: number, newKey: MetricKey) {
		const c = conds[condIdx];
		const oldDef = METRIC_BY_KEY.get(c.metric);
		const newDef = METRIC_BY_KEY.get(newKey);
		const oldType = oldDef?.type ?? 'number';
		const newType = newDef?.type ?? 'number';
		// type 변경 시 값 초기화
		if (oldType !== newType) {
			const initVal = newType === 'number' ? 0 : (newDef?.values?.[0] ?? '');
			conds = conds.map((x, i) => (i === condIdx ? { metric: newKey, op: newType === 'number' ? '>=' : '==', value: initVal } : x));
		} else {
			conds = conds.map((x, i) => (i === condIdx ? { ...x, metric: newKey } : x));
		}
	}

	function fmtMetricValue(key: MetricKey, v: unknown): string {
		if (v === null || v === undefined) return '—';
		const m = METRIC_BY_KEY.get(key);
		if (!m) return String(v);
		if (m.type !== 'number') return String(v);
		const num = Number(v);
		if (!Number.isFinite(num)) return '—';
		if (key === 'revenue' || key === 'marketCap' || key === 'currentPrice') {
			if (key === 'currentPrice') return fmtPrice(num);
			return fmtKrw(num);
		}
		if (key === 'empCount' || key === 'volumeAvg30d') {
			return Math.round(num).toLocaleString('ko-KR');
		}
		if (key === 'industryRank' || key === 'industryPeerCount') {
			return Math.round(num).toLocaleString('ko-KR');
		}
		if (m.signed) {
			const sign = num > 0 ? '+' : '';
			return `${sign}${num.toFixed(1)}${m.unit ?? ''}`;
		}
		const digits = m.unit === '%' ? 1 : m.unit === '배' ? 2 : 1;
		return `${num.toFixed(digits)}${m.unit ?? ''}`;
	}

	function returnTone(v: unknown): 'up' | 'down' | 'flat' {
		const n = typeof v === 'number' ? v : Number(v);
		if (!Number.isFinite(n) || n === 0) return 'flat';
		return n > 0 ? 'up' : 'down';
	}

	// 결과 테이블에 표시할 컬럼 (PR-1 기본 셋. PR-9 에서 컬럼 사전셋 도입 예정)
	const TABLE_COLUMNS: { key: MetricKey | 'label' | 'industryName'; label: string; align?: 'left' | 'right' | 'center' }[] = [
		{ key: 'label', label: '회사', align: 'left' },
		{ key: 'industryName', label: '산업', align: 'left' },
		{ key: 'revenue', label: '매출', align: 'right' },
		{ key: 'roe', label: 'ROE', align: 'right' },
		{ key: 'opMargin', label: 'OPM', align: 'right' },
		{ key: 'debtRatio', label: '부채', align: 'right' },
		{ key: 'revCagr', label: 'CAGR', align: 'right' },
		{ key: 'marketCap', label: '시총', align: 'right' },
		{ key: 'return1y', label: '1Y', align: 'right' },
		{ key: 'profGrade', label: '수익', align: 'center' },
		{ key: 'qualGrade', label: '이익질', align: 'center' },
		{ key: 'govGrade', label: '거버넌스', align: 'center' }
	];

	const dataAsOf = $derived((data.meta as any)?.dataAsOf ?? null);

	/** 결과 요약 — 산업 Top3 + 평균 메트릭 (사용자가 결과 분포·집중을 즉시 인지). */
	const resultSummary = $derived.by(() => {
		if (results.length === 0) return null;
		// 산업별 카운트
		const indCount = new Map<string, number>();
		let roeSum = 0;
		let roeN = 0;
		let opmSum = 0;
		let opmN = 0;
		let debtSum = 0;
		let debtN = 0;
		for (const n of results) {
			const ind = String(n.industryName ?? n.industry ?? '미분류');
			indCount.set(ind, (indCount.get(ind) ?? 0) + 1);
			if (typeof n.roe === 'number') {
				roeSum += n.roe;
				roeN++;
			}
			if (typeof n.opMargin === 'number') {
				opmSum += n.opMargin;
				opmN++;
			}
			if (typeof n.debtRatio === 'number') {
				debtSum += n.debtRatio;
				debtN++;
			}
		}
		const top3 = [...indCount.entries()]
			.sort((a, b) => b[1] - a[1])
			.slice(0, 3)
			.map(([name, n]) => `${name} ${n}`);
		return {
			top3: top3.join(' · '),
			avgRoe: roeN > 0 ? roeSum / roeN : null,
			avgOpm: opmN > 0 ? opmSum / opmN : null,
			avgDebt: debtN > 0 ? debtSum / debtN : null,
			indCount: indCount.size
		};
	});

	/** 등급 색칩 — 등급 메트릭에 한해 단색 칩 토글 */
	const GRADE_COLORS: Record<string, { bg: string; fg: string; border: string }> = {
		// scan 등급 5단계
		'우수': { bg: 'rgba(16, 185, 129, 0.18)', fg: '#34d399', border: 'rgba(16, 185, 129, 0.4)' },
		'양호': { bg: 'rgba(132, 204, 22, 0.16)', fg: '#a3e635', border: 'rgba(132, 204, 22, 0.4)' },
		'보통': { bg: 'rgba(245, 158, 11, 0.14)', fg: '#fbbf24', border: 'rgba(245, 158, 11, 0.4)' },
		'주의': { bg: 'rgba(239, 68, 68, 0.14)', fg: '#fca5a5', border: 'rgba(239, 68, 68, 0.4)' },
		'위험': { bg: 'rgba(239, 68, 68, 0.22)', fg: '#f87171', border: 'rgba(239, 68, 68, 0.6)' },
		// 부채/감사 4단계
		'안전': { bg: 'rgba(16, 185, 129, 0.18)', fg: '#34d399', border: 'rgba(16, 185, 129, 0.4)' },
		'관찰': { bg: 'rgba(132, 204, 22, 0.16)', fg: '#a3e635', border: 'rgba(132, 204, 22, 0.4)' },
		'고위험': { bg: 'rgba(239, 68, 68, 0.22)', fg: '#f87171', border: 'rgba(239, 68, 68, 0.6)' },
		// 거버넌스 A~E
		'A': { bg: 'rgba(16, 185, 129, 0.18)', fg: '#34d399', border: 'rgba(16, 185, 129, 0.4)' },
		'B': { bg: 'rgba(132, 204, 22, 0.16)', fg: '#a3e635', border: 'rgba(132, 204, 22, 0.4)' },
		'C': { bg: 'rgba(245, 158, 11, 0.14)', fg: '#fbbf24', border: 'rgba(245, 158, 11, 0.4)' },
		'D': { bg: 'rgba(239, 68, 68, 0.14)', fg: '#fca5a5', border: 'rgba(239, 68, 68, 0.4)' },
		'E': { bg: 'rgba(239, 68, 68, 0.22)', fg: '#f87171', border: 'rgba(239, 68, 68, 0.6)' },
		// 성장 등급
		'고성장': { bg: 'rgba(16, 185, 129, 0.18)', fg: '#34d399', border: 'rgba(16, 185, 129, 0.4)' },
		'성장': { bg: 'rgba(132, 204, 22, 0.16)', fg: '#a3e635', border: 'rgba(132, 204, 22, 0.4)' },
		'정체': { bg: 'rgba(148, 163, 184, 0.14)', fg: '#94a3b8', border: 'rgba(148, 163, 184, 0.4)' },
		'역성장': { bg: 'rgba(239, 68, 68, 0.14)', fg: '#fca5a5', border: 'rgba(239, 68, 68, 0.4)' },
		'급감': { bg: 'rgba(239, 68, 68, 0.22)', fg: '#f87171', border: 'rgba(239, 68, 68, 0.6)' },
		// 수익성 등급
		'저수익': { bg: 'rgba(245, 158, 11, 0.14)', fg: '#fbbf24', border: 'rgba(245, 158, 11, 0.4)' },
		'적자': { bg: 'rgba(239, 68, 68, 0.22)', fg: '#f87171', border: 'rgba(239, 68, 68, 0.6)' }
	};
	const NEUTRAL_GRADE = { bg: 'rgba(148, 163, 184, 0.1)', fg: '#94a3b8', border: 'rgba(148, 163, 184, 0.3)' };
	function gradeStyle(v: unknown): string {
		const s = GRADE_COLORS[String(v)] ?? NEUTRAL_GRADE;
		return `background:${s.bg};color:${s.fg};border:1px solid ${s.border}`;
	}
</script>

<svelte:head>
	<title>스크리너 — 한국 상장사 재무·가격 조건 검색 | dartlab 전자공시</title>
	<meta
		name="description"
		content="한국 상장사 약 2,664사를 ROE·영업이익률·부채·성장률·등급·가격 등 약 30 가지 조건으로 자유롭게 조합 검색. URL 공유 + CSV 전체 다운로드."
	/>
	<meta property="og:type" content="website" />
	<meta property="og:title" content="dartlab 스크리너 — 한국 상장사 조건 검색" />
	<meta
		property="og:description"
		content="재무·등급·가격 30+ 조건 자유 조합. AND 다중 필터 + 다중 정렬 + URL 공유 + CSV 전체."
	/>
</svelte:head>

<div class="page">
	<header class="head">
		<div class="head-left">
			<a class="back" href="{base}/map">← 산업지도</a>
			<h1>스크리너</h1>
			<p class="lead">
				한국 상장사 <strong>{joinedNodes.length.toLocaleString()}사</strong>를
				재무 · 등급 · 가격 조건으로 자유롭게 조합 검색.
			</p>
		</div>
		<div class="head-right">
			<span class="db-badge db-{dbState}" title={dbError || ''}>
				<span class="db-dot"></span>
				{#if dbState === 'idle'}대기
				{:else if dbState === 'loading'}DuckDB 로드 중…
				{:else if dbState === 'ready'}시계열 ON · {priceTimeSeries.size.toLocaleString()}사
				{:else if dbState === 'unsupported'}시계열 OFF (iOS Safari)
				{:else if dbState === 'error'}시계열 오류
				{/if}
			</span>
			{#if dataAsOf}
				<FreshnessBadge dataAsOf={dataAsOf} variant="compact" />
			{/if}
		</div>
	</header>

	<!-- 프리셋 라이브러리 — 한 클릭 입력 -->
	<section class="presets">
		<div class="presets-head">
			<span class="presets-title">프리셋</span>
			<span class="presets-hint">한 클릭으로 조건 자동 입력 · {PRESETS.length} 가지</span>
			{#if activePreset}
				<button class="link" onclick={() => (activePreset = null)}>활성 해제</button>
			{/if}
		</div>
		{#each PRESET_CATEGORIES as cat (cat.key)}
			{@const items = PRESETS.filter((p) => p.category === cat.key)}
			{#if items.length > 0}
				<div class="preset-group">
					<div class="preset-group-label">{cat.label}</div>
					<div class="preset-grid">
						{#each items as p (p.id)}
							<PresetCard preset={p} active={activePreset === p.id} onClick={applyPreset} />
						{/each}
					</div>
				</div>
			{/if}
		{/each}
	</section>

	<section class="builder">
		<!-- 산업 다중선택 -->
		<div class="block">
			<div class="block-head">
				<span class="block-title">산업</span>
				<span class="hint">다중선택 OR · 비워두면 전체</span>
				{#if selectedIndustries.size > 0}
					<button class="link" onclick={clearIndustries}>모두 해제</button>
				{/if}
			</div>
			<div class="inds">
				{#each industries as ind (ind.id)}
					<button
						type="button"
						class="ind-chip"
						class:on={selectedIndustries.has(ind.id)}
						onclick={() => toggleIndustry(ind.id)}
					>
						<span class="dot" style:background={ind.color}></span>
						<span class="ind-name">{ind.name}</span>
						{#if ind.count != null}<span class="ind-count">{ind.count}</span>{/if}
					</button>
				{/each}
			</div>
		</div>

		<!-- 조건 (AND) -->
		<div class="block">
			<div class="block-head">
				<span class="block-title">조건 (모두 만족)</span>
				<span class="hint">AND 다중 필터</span>
			</div>
			<div class="conds">
				{#each conds as c, i (i)}
					{@const m = METRIC_BY_KEY.get(c.metric)}
					<div class="cond-row">
						<select
							class="cond-metric"
							value={c.metric}
							onchange={(e) => changeMetric(i, (e.currentTarget as HTMLSelectElement).value as MetricKey)}
						>
							<optgroup label="손익">
								{#each METRICS.filter((m) => m.group === 'income') as opt}
									<option value={opt.key}>{opt.label}</option>
								{/each}
							</optgroup>
							<optgroup label="변화">
								{#each METRICS.filter((m) => m.group === 'changes') as opt}
									<option value={opt.key}>{opt.label}</option>
								{/each}
							</optgroup>
							<optgroup label="재무건전성">
								{#each METRICS.filter((m) => m.group === 'health') as opt}
									<option value={opt.key}>{opt.label}</option>
								{/each}
							</optgroup>
							<optgroup label="가격·시총">
								{#each METRICS.filter((m) => m.group === 'price') as opt}
									<option value={opt.key}>{opt.label}</option>
								{/each}
							</optgroup>
							<optgroup label="가격 시계열 (DuckDB)">
								{#each METRICS.filter((m) => m.group === 'derived') as opt}
									<option value={opt.key}>{opt.label}</option>
								{/each}
							</optgroup>
							<optgroup label="이익질·현금흐름">
								{#each METRICS.filter((m) => m.group === 'quality') as opt}
									<option value={opt.key}>{opt.label}</option>
								{/each}
							</optgroup>
							<optgroup label="거버넌스">
								{#each METRICS.filter((m) => m.group === 'governance') as opt}
									<option value={opt.key}>{opt.label}</option>
								{/each}
							</optgroup>
							<optgroup label="인적·점유율">
								{#each METRICS.filter((m) => m.group === 'workforce') as opt}
									<option value={opt.key}>{opt.label}</option>
								{/each}
							</optgroup>
						</select>

						{#if m?.type === 'number'}
							<select class="cond-op" bind:value={c.op}>
								<option value=">=">≥ 이상</option>
								<option value="<=">≤ 이하</option>
								<option value="between">사이</option>
								<option value="==">= 같음</option>
								<option value="!=">≠ 다름</option>
							</select>
							<input
								class="cond-val"
								type="number"
								bind:value={c.value}
								step={m.unit === '원' ? 1e8 : 1}
							/>
							{#if c.op === 'between'}
								<span class="tilde">~</span>
								<input class="cond-val" type="number" bind:value={c.value2} placeholder="상한" />
							{/if}
							{#if m.unit}
								<span class="unit">{m.unit}</span>
							{/if}
						{:else}
							<select class="cond-op" bind:value={c.op}>
								<option value="==">= 같음</option>
								<option value="!=">≠ 다름</option>
							</select>
							{#if m?.values}
								<select class="cond-val cond-val-enum" bind:value={c.value}>
									{#each m.values as v}
										<option value={v}>{v}</option>
									{/each}
								</select>
							{:else}
								<input class="cond-val" type="text" bind:value={c.value} />
							{/if}
						{/if}

						<button class="del" type="button" onclick={() => removeCond(i)} aria-label="조건 삭제">×</button>
					</div>
				{/each}
				<button class="add" type="button" onclick={addCond}>+ 조건 추가</button>
			</div>
		</div>

		<!-- 정렬 (다중) -->
		<div class="block">
			<div class="block-head">
				<span class="block-title">정렬</span>
				<span class="hint">동률 시 다음 정렬 적용</span>
			</div>
			<div class="sorts">
				{#each sorts as s, i (i)}
					<div class="sort-row">
						<span class="sort-label">{i === 0 ? '1차' : `${i + 1}차`}</span>
						<select bind:value={s.key} class="sort-key">
							{#each METRICS as m}
								<option value={m.key}>{m.label}</option>
							{/each}
						</select>
						<select bind:value={s.dir} class="sort-dir">
							<option value="desc">↓ 내림</option>
							<option value="asc">↑ 오름</option>
						</select>
						{#if i > 0}
							<button class="del" type="button" onclick={() => removeSort(i)} aria-label="정렬 삭제">×</button>
						{/if}
					</div>
				{/each}
				<button class="add" type="button" onclick={addSort}>+ 정렬 추가</button>
			</div>
		</div>
	</section>

	<!-- 결과 요약 한 줄 (자동 생성) -->
	{#if resultSummary}
		<section class="summary">
			<span class="sum-icon" aria-hidden="true">✦</span>
			<span class="sum-text">
				{results.length.toLocaleString()}사 통과
				{#if resultSummary.indCount > 0}
					· <strong>{resultSummary.indCount}</strong>개 산업
				{/if}
				{#if resultSummary.top3}
					· 다수: <strong>{resultSummary.top3}</strong>
				{/if}
			</span>
			<span class="sum-stats">
				{#if resultSummary.avgRoe != null}
					평균 ROE <strong>{resultSummary.avgRoe.toFixed(1)}%</strong>
				{/if}
				{#if resultSummary.avgOpm != null}
					· OPM <strong>{resultSummary.avgOpm.toFixed(1)}%</strong>
				{/if}
				{#if resultSummary.avgDebt != null}
					· 부채 <strong>{resultSummary.avgDebt.toFixed(0)}%</strong>
				{/if}
			</span>
		</section>
	{/if}

	<!-- 결과 액션 바 -->
	<section class="actions">
		<div class="result-meta">
			<strong class="count">{results.length.toLocaleString()}</strong>
			<span class="count-sub">사 통과 / {joinedNodes.length.toLocaleString()} 사 중</span>
		</div>
		<div class="action-btns">
			<button type="button" class="btn ghost" onclick={shareUrl}>URL 복사</button>
			<button type="button" class="btn primary" onclick={exportCsv}>CSV 다운로드 (전체)</button>
		</div>
	</section>

	<!-- 결과 테이블 -->
	<section class="result">
		<div class="table-wrap">
			<table>
				<thead>
					<tr>
						{#each TABLE_COLUMNS as col}
							<th class:right={col.align === 'right'} class:center={col.align === 'center'}>{col.label}</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each results.slice(0, displayLimit) as n (n.id)}
						<tr>
							<td class="company">
								<a href="{base}/map?focus={n.id}" target="_blank" rel="noopener">{n.label}</a>
								<span class="code">{n.id}</span>
							</td>
							<td class="industry">{n.industryName ?? '—'}</td>
							<td class="num">{fmtMetricValue('revenue', n.revenue)}</td>
							<td class="num" class:up={typeof n.roe === 'number' && n.roe >= 10} class:down={typeof n.roe === 'number' && n.roe < 0}>
								{fmtMetricValue('roe', n.roe)}
							</td>
							<td class="num" class:up={typeof n.opMargin === 'number' && n.opMargin >= 10} class:down={typeof n.opMargin === 'number' && n.opMargin < 0}>
								{fmtMetricValue('opMargin', n.opMargin)}
							</td>
							<td class="num" class:down={typeof n.debtRatio === 'number' && n.debtRatio >= 200} class:up={typeof n.debtRatio === 'number' && n.debtRatio <= 50}>
								{fmtMetricValue('debtRatio', n.debtRatio)}
							</td>
							<td class="num" class:up={typeof n.revCagr === 'number' && n.revCagr > 10} class:down={typeof n.revCagr === 'number' && n.revCagr < 0}>
								{fmtMetricValue('revCagr', n.revCagr)}
							</td>
							<td class="num">{fmtMetricValue('marketCap', n.marketCap)}</td>
							<td class="num {returnTone(n.return1y)}">{fmtMetricValue('return1y', n.return1y)}</td>
							<td class="grade-cell">
								{#if n.profGrade}
									<span class="grade-chip" style={gradeStyle(n.profGrade)}>{n.profGrade}</span>
								{:else}
									<span class="dim">—</span>
								{/if}
							</td>
							<td class="grade-cell">
								{#if n.qualGrade}
									<span class="grade-chip" style={gradeStyle(n.qualGrade)}>{n.qualGrade}</span>
								{:else}
									<span class="dim">—</span>
								{/if}
							</td>
							<td class="grade-cell">
								{#if n.govGrade}
									<span class="grade-chip" style={gradeStyle(n.govGrade)}>{n.govGrade}</span>
								{:else}
									<span class="dim">—</span>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		{#if results.length > displayLimit}
			<div class="trunc">
				<span>상위 {displayLimit.toLocaleString()} 사 표시 / 전체 {results.length.toLocaleString()} 사</span>
				<button class="link" onclick={() => (displayLimit = results.length)}>모두 표시</button>
				<span class="hint">— 전체는 CSV 다운로드 권장</span>
			</div>
		{/if}
		{#if results.length === 0}
			<div class="empty">조건에 부합하는 회사가 없습니다. 조건을 완화해 보세요.</div>
		{/if}
	</section>

	<footer class="foot">
		<p class="note">
			scan 등급은 <a href="{base}/docs/scan">scan 엔진</a> 산출. 가격은 KRX 일별 종가 기준
			(매일 18:00 갱신). 데이터: <a href="{base}/map">산업지도</a> · <a href="{base}/docs">문서</a>.
		</p>
	</footer>
</div>

<style>
	.page {
		max-width: 1400px;
		margin: 0 auto;
		padding: 24px 24px 64px;
		color: #f1f5f9;
	}

	.head {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 16px;
		margin-bottom: 28px;
		flex-wrap: wrap;
	}
	.head-left {
		flex: 1;
		min-width: 260px;
	}
	.back {
		display: inline-block;
		font-size: 13px;
		color: #94a3b8;
		text-decoration: none;
		margin-bottom: 8px;
	}
	.back:hover { color: #f1f5f9; }
	h1 {
		margin: 0 0 4px;
		font-size: 28px;
		font-weight: 800;
		letter-spacing: -0.02em;
	}
	.lead {
		margin: 0;
		font-size: 14px;
		color: #94a3b8;
		line-height: 1.5;
	}
	.lead strong { color: #f1f5f9; }

	.head-right {
		display: flex;
		flex-direction: column;
		gap: 6px;
		align-items: flex-end;
	}
	.db-badge {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 4px 10px;
		font-size: 11px;
		border-radius: 999px;
		border: 1px solid #1e2433;
		background: #0b1120;
		color: #94a3b8;
		font-family: monospace;
		white-space: nowrap;
	}
	.db-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: #64748b;
		flex-shrink: 0;
	}
	.db-badge.db-loading { color: #fbbf24; border-color: rgba(251, 191, 36, 0.4); }
	.db-badge.db-loading .db-dot { background: #fbbf24; animation: pulse 1.4s ease-in-out infinite; }
	.db-badge.db-ready { color: #34d399; border-color: rgba(52, 211, 153, 0.4); }
	.db-badge.db-ready .db-dot { background: #34d399; }
	.db-badge.db-unsupported { color: #94a3b8; }
	.db-badge.db-error { color: #f87171; border-color: rgba(239, 68, 68, 0.4); }
	.db-badge.db-error .db-dot { background: #f87171; }
	@keyframes pulse {
		0%, 100% { opacity: 0.4; }
		50% { opacity: 1; }
	}

	.presets {
		margin-bottom: 24px;
		padding: 16px 18px;
		background: linear-gradient(180deg, rgba(96, 165, 250, 0.04), transparent 60%);
		border: 1px solid rgba(96, 165, 250, 0.14);
		border-radius: 12px;
	}
	.presets-head {
		display: flex;
		align-items: baseline;
		gap: 12px;
		margin-bottom: 14px;
	}
	.presets-title {
		font-size: 13px;
		font-weight: 700;
		color: #f1f5f9;
		letter-spacing: -0.01em;
	}
	.presets-hint {
		font-size: 11px;
		color: #64748b;
	}
	.preset-group {
		margin-top: 12px;
	}
	.preset-group:first-child {
		margin-top: 0;
	}
	.preset-group-label {
		font-size: 10px;
		font-weight: 700;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		margin-bottom: 8px;
	}
	.preset-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 10px;
	}

	.builder {
		display: flex;
		flex-direction: column;
		gap: 18px;
		margin-bottom: 24px;
	}
	.block {
		background: #0b1120;
		border: 1px solid #1e2433;
		border-radius: 10px;
		padding: 14px 16px;
	}
	.block-head {
		display: flex;
		align-items: baseline;
		gap: 12px;
		margin-bottom: 10px;
	}
	.block-title {
		font-size: 12px;
		font-weight: 700;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.hint { font-size: 11px; color: #475569; }
	.link {
		background: none;
		border: none;
		color: #60a5fa;
		font-size: 11px;
		cursor: pointer;
		padding: 0;
		margin-left: auto;
	}
	.link:hover { text-decoration: underline; }

	/* 산업 칩 */
	.inds {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.ind-chip {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 5px 10px;
		font-size: 12px;
		background: transparent;
		border: 1px solid #1e2433;
		border-radius: 6px;
		color: #cbd5e1;
		cursor: pointer;
		transition: background 0.12s, border-color 0.12s, color 0.12s;
	}
	.ind-chip:hover {
		background: rgba(96, 165, 250, 0.08);
		border-color: #334155;
		color: #f1f5f9;
	}
	.ind-chip.on {
		background: rgba(96, 165, 250, 0.15);
		border-color: #60a5fa;
		color: #f1f5f9;
	}
	.dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.ind-name { white-space: nowrap; }
	.ind-count {
		color: #64748b;
		font-family: monospace;
		font-size: 11px;
	}

	/* 조건 */
	.conds {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.cond-row {
		display: flex;
		align-items: center;
		gap: 6px;
		flex-wrap: wrap;
	}
	.cond-metric, .cond-op, .cond-val, .sort-key, .sort-dir {
		padding: 6px 10px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 6px;
		color: #f1f5f9;
		font-size: 12px;
		cursor: pointer;
	}
	.cond-metric { min-width: 160px; }
	.cond-op { min-width: 90px; }
	.cond-val { width: 110px; }
	.cond-val-enum { width: 110px; cursor: pointer; }
	.cond-metric:focus, .cond-op:focus, .cond-val:focus, .sort-key:focus, .sort-dir:focus {
		outline: none;
		border-color: #60a5fa;
	}
	.unit {
		color: #64748b;
		font-size: 11px;
		font-family: monospace;
	}
	.tilde { color: #64748b; }
	.del {
		width: 24px;
		height: 24px;
		background: transparent;
		border: 1px solid transparent;
		border-radius: 4px;
		color: #64748b;
		font-size: 14px;
		cursor: pointer;
	}
	.del:hover {
		background: rgba(239, 68, 68, 0.12);
		color: #f87171;
	}
	.add {
		align-self: flex-start;
		padding: 6px 12px;
		background: transparent;
		border: 1px dashed #334155;
		border-radius: 6px;
		color: #94a3b8;
		font-size: 12px;
		cursor: pointer;
	}
	.add:hover {
		border-color: #60a5fa;
		color: #60a5fa;
	}

	/* 정렬 */
	.sorts {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.sort-row {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.sort-label {
		display: inline-block;
		min-width: 32px;
		font-size: 11px;
		color: #64748b;
		font-family: monospace;
	}
	.sort-key { min-width: 160px; }
	.sort-dir { min-width: 90px; }

	/* 결과 요약 한 줄 */
	.summary {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 14px;
		background: linear-gradient(90deg, rgba(96, 165, 250, 0.08), rgba(96, 165, 250, 0.02));
		border: 1px solid rgba(96, 165, 250, 0.2);
		border-radius: 10px;
		margin-bottom: 8px;
		font-size: 12px;
		color: #cbd5e1;
		flex-wrap: wrap;
	}
	.sum-icon {
		color: #60a5fa;
		font-size: 13px;
	}
	.sum-text { flex: 1; min-width: 0; }
	.sum-text strong { color: #f1f5f9; font-weight: 600; }
	.sum-stats {
		font-family: monospace;
		color: #94a3b8;
		font-size: 11px;
	}
	.sum-stats strong { color: #f1f5f9; }

	/* 등급 색칩 */
	.grade-chip {
		display: inline-block;
		padding: 2px 8px;
		font-size: 10px;
		font-weight: 700;
		border-radius: 4px;
		font-family: monospace;
		letter-spacing: 0.02em;
	}

	/* 액션 */
	.actions {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
		padding: 12px 16px;
		background: #0b1120;
		border: 1px solid #1e2433;
		border-radius: 10px;
		margin-bottom: 12px;
	}
	.result-meta { font-size: 14px; }
	.count {
		font-size: 22px;
		font-weight: 700;
		color: #60a5fa;
		font-family: monospace;
	}
	.count-sub {
		color: #64748b;
		margin-left: 6px;
	}
	.action-btns { display: flex; gap: 8px; }
	.btn {
		padding: 8px 14px;
		border-radius: 6px;
		font-size: 12px;
		font-weight: 600;
		cursor: pointer;
		border: 1px solid transparent;
	}
	.btn.ghost {
		background: transparent;
		border-color: #1e2433;
		color: #94a3b8;
	}
	.btn.ghost:hover {
		background: rgba(96, 165, 250, 0.08);
		color: #f1f5f9;
		border-color: #334155;
	}
	.btn.primary {
		background: #60a5fa;
		color: #050811;
		border-color: #60a5fa;
	}
	.btn.primary:hover {
		background: #93c5fd;
	}

	/* 결과 테이블 */
	.result {
		background: #0b1120;
		border: 1px solid #1e2433;
		border-radius: 10px;
		overflow: hidden;
	}
	.table-wrap {
		overflow-x: auto;
		max-height: 70vh;
		overflow-y: auto;
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 12px;
	}
	thead {
		position: sticky;
		top: 0;
		background: #0f1219;
		z-index: 1;
	}
	th {
		text-align: left;
		padding: 10px 12px;
		font-size: 11px;
		font-weight: 700;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		border-bottom: 1px solid #1e2433;
	}
	th.right { text-align: right; }
	th.center { text-align: center; }
	td.grade-cell { text-align: center; }
	td.grade-cell .dim { color: #475569; font-size: 11px; }
	td {
		padding: 8px 12px;
		border-bottom: 1px solid rgba(30, 36, 51, 0.5);
		color: #cbd5e1;
	}
	tr:hover td { background: rgba(96, 165, 250, 0.04); }
	td.num {
		text-align: right;
		font-family: monospace;
	}
	td.up { color: #34d399; }
	td.down { color: #f87171; }
	td.flat { color: #94a3b8; }
	.company {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.company a {
		color: #60a5fa;
		text-decoration: none;
		font-weight: 500;
	}
	.company a:hover { text-decoration: underline; }
	.code {
		font-family: monospace;
		font-size: 10px;
		color: #64748b;
	}
	.industry {
		color: #94a3b8;
		font-size: 11px;
	}

	.trunc {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 12px 16px;
		font-size: 12px;
		color: #94a3b8;
		border-top: 1px solid #1e2433;
		flex-wrap: wrap;
	}
	.empty {
		padding: 36px 16px;
		text-align: center;
		font-size: 13px;
		color: #64748b;
	}

	.foot {
		margin-top: 24px;
		padding-top: 16px;
		border-top: 1px dashed #1e2433;
	}
	.note {
		font-size: 11px;
		color: #64748b;
		line-height: 1.6;
	}
	.note a { color: #60a5fa; text-decoration: none; }
	.note a:hover { text-decoration: underline; }
</style>
