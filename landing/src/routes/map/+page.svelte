<script lang="ts">
	import EcosystemMap from '$lib/components/industry/EcosystemMap.svelte';
	import IndustryAtlas from '$lib/components/industry/IndustryAtlas.svelte';
	import IndustryDrilldown from '$lib/components/industry/IndustryDrilldown.svelte';
	import CompanyCard from '$lib/components/industry/CompanyCard.svelte';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import type { PageData } from './$types';
	import { base } from '$app/paths';

	let { data }: { data: PageData } = $props();

	// ── 뷰 모드 ──
	// atlas: 34개 산업 노드 + 산업간 supplier flow (default)
	// companies: 기존 ecosystem 전체 2,664사
	// industry: 한 산업 내부 drill-down
	type ViewMode = 'atlas' | 'companies' | 'industry';
	let viewMode: ViewMode = $state('atlas');
	let drillIndustry: string | null = $state(null);
	let industryDetail: any = $state(null);
	let industryLoading = $state(false);

	// ── 색상 기준 ──
	// industry: 산업 팔레트 / roe / opMargin / debtRatio / revCagr / revenue
	type ColorMetric = 'industry' | 'roe' | 'opMargin' | 'debtRatio' | 'revCagr' | 'revenue';
	let colorMetric: ColorMetric = $state('roe');

	const GRAY = '#475569';
	// 재무 스코어 팔레트 (저→고)
	function _lerp(c1: [number, number, number], c2: [number, number, number], t: number): string {
		const r = Math.round(c1[0] + (c2[0] - c1[0]) * t);
		const g = Math.round(c1[1] + (c2[1] - c1[1]) * t);
		const b = Math.round(c1[2] + (c2[2] - c1[2]) * t);
		return `rgb(${r},${g},${b})`;
	}
	function _scale(v: number, stops: Array<[number, [number, number, number]]>): string {
		if (v <= stops[0][0]) return `rgb(${stops[0][1].join(',')})`;
		const last = stops[stops.length - 1];
		if (v >= last[0]) return `rgb(${last[1].join(',')})`;
		for (let i = 0; i < stops.length - 1; i++) {
			const [a, ca] = stops[i];
			const [b, cb] = stops[i + 1];
			if (v >= a && v <= b) return _lerp(ca, cb, (v - a) / (b - a));
		}
		return GRAY;
	}

	function colorFor(n: any, metric: ColorMetric): string {
		if (metric === 'industry' || n.isIndustry) return n.color;
		const v = n[metric];
		if (v === null || v === undefined || Number.isNaN(v)) return GRAY;
		if (metric === 'roe') {
			return _scale(v, [
				[-10, [239, 68, 68]],
				[0, [245, 158, 11]],
				[10, [132, 204, 22]],
				[20, [16, 185, 129]]
			]);
		}
		if (metric === 'opMargin') {
			return _scale(v, [
				[-5, [239, 68, 68]],
				[0, [245, 158, 11]],
				[10, [132, 204, 22]],
				[20, [16, 185, 129]]
			]);
		}
		if (metric === 'debtRatio') {
			// 역방향 (낮을수록 좋음)
			return _scale(v, [
				[50, [16, 185, 129]],
				[100, [132, 204, 22]],
				[200, [245, 158, 11]],
				[400, [239, 68, 68]]
			]);
		}
		if (metric === 'revCagr') {
			return _scale(v, [
				[-10, [239, 68, 68]],
				[0, [245, 158, 11]],
				[15, [132, 204, 22]],
				[30, [16, 185, 129]]
			]);
		}
		if (metric === 'revenue') {
			// 매출 (원단위) 로그 스케일 파란계열
			const eok = v / 1e8;
			const t = Math.max(0, Math.min(1, Math.log10(Math.max(1, eok)) / 6));
			return _scale(t, [
				[0, [30, 58, 138]],
				[0.5, [59, 130, 246]],
				[1, [147, 197, 253]]
			]);
		}
		return GRAY;
	}

	const STREAM_STROKE: Record<string, string> = {
		upstream: '#8b5cf6',
		midstream: '#f8fafc',
		downstream: '#f97316'
	};

	let allNodes = $derived(data.ecosystem.nodes);
	let allLinks = $derived(data.ecosystem.links);
	let industries = $derived(data.ecosystem.industries);

	let indColorMap = $derived(new Map(industries.map((i: any) => [i.id, i.color])));

	// ── 필터 상태 (companies 뷰) ──
	let enabledIndustries = $state<Set<string>>(new Set());
	let initialized = $state(false);
	$effect(() => {
		if (!initialized && data?.ecosystem?.industries) {
			enabledIndustries = new Set(data.ecosystem.industries.map((i: any) => i.id));
			initialized = true;
		}
	});
	let showSupplier = $state(true);
	let showAffiliate = $state(false);
	let showInvestor = $state(false);
	let minConfidence = $state(0.6);
	let onlyWithAmount = $state(false);
	let searchQuery = $state('');

	let selectedNode: any = $state(null);
	let mapRef: any = $state(null);

	// ── 회사 상세 (companies/{code}.json fetch) ──
	let selectedDetail: any = $state(null);
	let selectedDetailLoading = $state(false);
	let selectedDetailCode: string | null = $state(null);

	async function loadCompanyDetail(stockCode: string) {
		if (selectedDetailCode === stockCode && selectedDetail) return;
		selectedDetailLoading = true;
		selectedDetailCode = stockCode;
		try {
			const r = await fetch(`${base}/map/companies/${stockCode}.json`);
			selectedDetail = r.ok ? await r.json() : null;
		} catch {
			selectedDetail = null;
		} finally {
			selectedDetailLoading = false;
		}
	}

	// ── 비교 슬롯 ──
	let compareB: any = $state(null);
	let compareBDetail: any = $state(null);
	let comparing = $derived(!!compareB);

	async function addToCompare(stockCode: string) {
		// 첫 번째 슬롯 = 현재 selectedNode. 다음 클릭하는 회사가 두 번째 슬롯
		// 여기선 단순화: 첫 번째 = 현재 카드, 두 번째 = "+비교에 추가" 클릭한 회사를 펜딩으로 두고
		// 다음 노드 클릭 시 두 번째에 set
		// 더 직관적으로: 클릭한 회사를 직접 비교 슬롯 B 로
		if (!selectedNode || selectedNode.id === stockCode) return;
		compareB = nodeFinderById(stockCode);
		if (compareB) {
			try {
				const r = await fetch(`${base}/map/companies/${stockCode}.json`);
				compareBDetail = r.ok ? await r.json() : null;
			} catch {
				compareBDetail = null;
			}
		}
	}

	function nodeFinderById(stockCode: string): any {
		for (const n of allNodes) if (n.id === stockCode) return { ...n, color: colorFor(n, colorMetric) };
		return null;
	}

	function clearCompare() {
		compareB = null;
		compareBDetail = null;
	}

	// ── companies 뷰 데이터 ──
	let filteredNodes = $derived(
		allNodes
			.filter((n: any) => enabledIndustries.has(n.industry))
			.map((n: any) => ({ ...n, color: colorFor(n, colorMetric) }))
	);

	let filteredLinks = $derived(
		allLinks.filter((l: any) => {
			if (l.type === 'supplier' && !showSupplier) return false;
			if (l.type === 'affiliate' && !showAffiliate) return false;
			if (l.type === 'investor' && !showInvestor) return false;
			if (l.type === 'customer' && !showSupplier) return false;
			if (l.confidence < minConfidence) return false;
			if (onlyWithAmount && !l.amount) return false;
			return true;
		})
	);

	// ── atlas 뷰 데이터 ──
	let atlasNodes = $derived(
		data.atlas.industries.map((ind: any) => ({
			id: `ind:${ind.id}`,
			label: ind.name,
			industry: ind.id,
			industryName: ind.name,
			stage: '',
			stageName: '',
			role: '',
			stream: '',
			revenue: (ind.revenue || 0) * 1e8, // 억 → 원
			size: Math.max(8, Math.min(32, 6 + Math.log2((ind.nodeCount || 1) + 1) * 2.8)),
			color: indColorMap.get(ind.id) ?? '#9ca3af',
			isIndustry: true,
			nodeCount: ind.nodeCount,
			stageMix: ind.stageMix,
			stages: ind.stages
		}))
	);

	let atlasLinks = $derived(
		data.atlas.flows.map((f: any) => ({
			source: `ind:${f.fromIndustry}`,
			target: `ind:${f.toIndustry}`,
			type: 'supplier',
			amount: f.amount,
			ratio: null,
			product: '',
			confidence: 1,
			source_tag: 'aggregate',
			edgeCount: f.edgeCount
		}))
	);

	// ── industry(drill-down) 뷰 데이터 ──
	let stageFilter = $state<Set<string>>(new Set());
	let stageInitialized = $state<string | null>(null);

	$effect(() => {
		if (industryDetail && stageInitialized !== industryDetail.industryId) {
			stageFilter = new Set((industryDetail.stages || []).map((s: any) => s.key));
			stageInitialized = industryDetail.industryId;
		}
	});

	let industryNodes = $derived.by(() => {
		if (!industryDetail) return [];
		const out: any[] = [];
		for (const s of industryDetail.stages || []) {
			if (!stageFilter.has(s.key)) continue;
			for (const n of s.nodes || []) {
				// industries/*.json 의 revenue 는 "억" 단위 (원 단위로 변환)
				const revWon = (n.revenue || 0) * 1e8;
				const base: any = {
					id: n.stockCode,
					label: n.corpName,
					industry: industryDetail.industryId,
					industryName: industryDetail.name,
					stage: n.stage,
					stageName: s.name,
					role: n.role || s.role,
					stream: n.stream || s.stream,
					confidence: n.confidence,
					source: n.source,
					revenue: revWon,
					// scan 지표
					roe: n.roe,
					opMargin: n.opMargin,
					debtRatio: n.debtRatio,
					revCagr: n.revCagr,
					profGrade: n.profGrade,
					debtGrade: n.debtGrade,
					growthGrade: n.growthGrade,
					size: Math.max(4, Math.min(20, 3 + Math.log2((n.revenue || 0) / 100 + 1)))
				};
				base.color = colorFor(base, colorMetric);
				out.push(base);
			}
		}
		return out;
	});

	let industryLinks = $derived.by(() => {
		if (!industryDetail) return [];
		const nodeIds = new Set(industryNodes.map((n: any) => n.id));
		return (industryDetail.edges || [])
			.filter((e: any) => nodeIds.has(e.from) && nodeIds.has(e.to))
			.map((e: any) => ({
				source: e.from,
				target: e.to,
				type: e.type,
				amount: e.amount,
				ratio: e.ratio,
				product: e.product,
				confidence: e.confidence,
				source_tag: e.source
			}));
	});

	// ── 활성 뷰 데이터 ──
	let activeNodes = $derived(
		viewMode === 'atlas' ? atlasNodes : viewMode === 'industry' ? industryNodes : filteredNodes
	);
	let activeLinks = $derived(
		viewMode === 'atlas' ? atlasLinks : viewMode === 'industry' ? industryLinks : filteredLinks
	);

	// ── 뷰 전환 ──
	let loadError = $state<string | null>(null);

	async function enterIndustry(industryId: string) {
		console.log('[map] enterIndustry', industryId);
		industryLoading = true;
		drillIndustry = industryId;
		viewMode = 'industry';
		selectedNode = null;
		loadError = null;
		const url = `${base}/map/industries/${industryId}.json`;
		try {
			const res = await fetch(url);
			console.log('[map] fetch', url, 'status', res.status);
			if (!res.ok) {
				loadError = `HTTP ${res.status} — ${url}`;
				industryDetail = null;
				return;
			}
			industryDetail = await res.json();
			console.log(
				'[map] industryDetail loaded',
				industryDetail?.industryId,
				'stages',
				industryDetail?.stages?.length
			);
		} catch (e: any) {
			console.error('[map] fetch failed', e);
			loadError = e?.message || String(e);
			industryDetail = null;
		} finally {
			industryLoading = false;
			console.log('[map] industryLoading=false');
		}
	}

	function exitToAtlas() {
		viewMode = 'atlas';
		drillIndustry = null;
		industryDetail = null;
		selectedNode = null;
	}

	function switchView(mode: ViewMode) {
		if (mode === 'industry') return; // industry 는 enterIndustry 로만
		viewMode = mode;
		selectedNode = null;
	}

	// ── 노드 클릭 ──
	function handleNodeClick(node: any) {
		if (!node) {
			selectedNode = null;
			selectedDetail = null;
			selectedDetailCode = null;
			return;
		}
		if (node.isIndustry) {
			enterIndustry(node.industry);
			return;
		}
		selectedNode = node;
		loadCompanyDetail(node.id);
	}

	// ── URL 쿼리 처리 (외부 진입: /map?focus=005930) ──
	let urlHandled = $state(false);
	onMount(() => {
		if (urlHandled) return;
		const focus = page.url.searchParams.get('focus');
		const cmp = page.url.searchParams.get('compare');
		if (focus) {
			const n = nodeFinderById(focus);
			if (n) {
				selectedNode = n;
				loadCompanyDetail(focus);
			}
		}
		if (cmp) {
			const [a, b] = cmp.split(',');
			if (a) {
				const na = nodeFinderById(a);
				if (na) {
					selectedNode = na;
					loadCompanyDetail(a);
				}
			}
			if (b) addToCompare(b);
		}
		urlHandled = true;
	});

	// ── 선택 회사의 공급/고객 관계 (companies/industry 뷰 공통) ──
	let selectedRelations = $derived.by(() => {
		if (!selectedNode || selectedNode.isIndustry) return { suppliers: [], customers: [] };
		const id = selectedNode.id;
		const pool = viewMode === 'industry' ? industryNodes : allNodes;
		const linkPool = viewMode === 'industry' ? industryLinks : allLinks;
		const nodeById = new Map(pool.map((n: any) => [n.id, n]));
		const suppliers: any[] = [];
		const customers: any[] = [];
		for (const l of linkPool) {
			if (l.target === id && l.type === 'supplier') {
				const from = nodeById.get(l.source);
				if (from) suppliers.push({ ...l, partner: from });
			}
			if (l.source === id && (l.type === 'customer' || l.type === 'supplier')) {
				const to = nodeById.get(l.target);
				if (to) customers.push({ ...l, partner: to });
			}
		}
		return { suppliers, customers };
	});

	// ── 필터 통계 (companies 뷰) ──
	let filterInsights = $derived.by(() => {
		if (viewMode !== 'companies') return null;
		const nodes = filteredNodes;
		if (nodes.length === 0) return null;
		const totalRev = nodes.reduce((s: number, n: any) => s + (n.revenue || 0), 0);
		const sorted = [...nodes].sort((a: any, b: any) => (b.revenue || 0) - (a.revenue || 0));
		const top1 = sorted[0]?.revenue || 0;
		const top3 = sorted.slice(0, 3).reduce((s: number, n: any) => s + (n.revenue || 0), 0);
		const top1Ratio = totalRev > 0 ? (top1 / totalRev) * 100 : 0;
		const top3Ratio = totalRev > 0 ? (top3 / totalRev) * 100 : 0;
		const preciseEdges = filteredLinks.filter((l: any) => l.amount).length;
		const singleIndustry = enabledIndustries.size === 1;
		let singleIndId: string | null = null;
		if (singleIndustry) {
			const iter = enabledIndustries.values().next();
			singleIndId = iter.value ?? null;
		}
		return {
			count: nodes.length,
			totalRev,
			top1Name: sorted[0]?.label || '',
			top1Ratio,
			top3Ratio,
			preciseEdges,
			singleIndId
		};
	});

	function toggleIndustry(id: string) {
		const next = new Set(enabledIndustries);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		enabledIndustries = next;
	}
	function toggleAllIndustries(on: boolean) {
		enabledIndustries = on ? new Set(industries.map((i: any) => i.id)) : new Set();
	}
	function toggleStage(key: string) {
		const next = new Set(stageFilter);
		if (next.has(key)) next.delete(key);
		else next.add(key);
		stageFilter = next;
	}

	function formatRev(rev: number): string {
		if (rev >= 1e12) return `${(rev / 1e12).toFixed(1)}조원`;
		return `${Math.round(rev / 1e8).toLocaleString()}억원`;
	}

	function handleSearch() {
		if (!searchQuery.trim()) return;
		const q = searchQuery.toLowerCase();
		const pool = activeNodes;
		const match = pool.find(
			(n: any) =>
				n.label.includes(searchQuery) ||
				n.id === searchQuery ||
				n.label.toLowerCase().includes(q)
		);
		if (match && mapRef) {
			mapRef.zoomToNode(match.id);
			selectedNode = match;
		}
	}
</script>

<svelte:head>
	<title>산업지도 | dartlab 전자공시</title>
	<meta
		name="description"
		content="한국 상장사 2,664사 산업 생태계 지도. 34개 산업 → 공급망 드릴다운."
	/>
</svelte:head>

<div class="map-page">
	<!-- 왼쪽 사이드바 -->
	<aside class="sidebar">
		<div class="header">
			<h1>산업 생태계</h1>
			{#if viewMode === 'atlas'}
				<p class="sub">{data.atlas.industries.length}개 산업 · {data.atlas.flows.length}개 플로우</p>
			{:else if viewMode === 'industry' && industryDetail}
				<p class="sub">
					<button class="crumb" onclick={exitToAtlas} title="전체 산업으로">← 산업</button>
					· {industryDetail.name} · {industryDetail.nodeCount}사
				</p>
			{:else}
				<p class="sub">
					{filteredNodes.length.toLocaleString()}사 · {filteredLinks.length.toLocaleString()}관계
				</p>
			{/if}
			<div class="nav-links">
				<a href="{base}/insights">인사이트 랭킹</a>
				<a href="{base}/compare">기업 비교</a>
			</div>
		</div>

		<!-- 색상 기준 셀렉터 -->
		<div class="section color-switch">
			<h3>색상 기준</h3>
			<select class="metric-select" bind:value={colorMetric}>
				<option value="industry">산업 팔레트</option>
				<option value="roe">ROE (자기자본수익률)</option>
				<option value="opMargin">영업이익률</option>
				<option value="debtRatio">부채비율</option>
				<option value="revCagr">매출 CAGR</option>
				<option value="revenue">매출 규모</option>
			</select>
			{#if colorMetric !== 'industry'}
				<div class="color-legend">
					{#if colorMetric === 'debtRatio'}
						<span class="lg-swatch" style="background:#10b981"></span>
						<span class="lg-label">낮음(건전)</span>
						<span class="lg-swatch" style="background:#f59e0b"></span>
						<span class="lg-swatch" style="background:#ef4444"></span>
						<span class="lg-label">높음(위험)</span>
					{:else if colorMetric === 'revenue'}
						<span class="lg-swatch" style="background:#1e3a8a"></span>
						<span class="lg-swatch" style="background:#3b82f6"></span>
						<span class="lg-swatch" style="background:#93c5fd"></span>
						<span class="lg-label">소 → 대</span>
					{:else}
						<span class="lg-swatch" style="background:#ef4444"></span>
						<span class="lg-swatch" style="background:#f59e0b"></span>
						<span class="lg-swatch" style="background:#84cc16"></span>
						<span class="lg-swatch" style="background:#10b981"></span>
						<span class="lg-label">저 → 고</span>
					{/if}
				</div>
			{/if}
		</div>

		<!-- 관점(view) 셀렉터 -->
		<div class="section view-switch">
			<h3>관점</h3>
			<div class="view-tabs">
				<button
					class="view-tab"
					class:active={viewMode === 'atlas'}
					onclick={() => switchView('atlas')}
				>
					🗺️ 산업지도
					<span class="hint">34개 산업 + 공급 플로우</span>
				</button>
				<button
					class="view-tab"
					class:active={viewMode === 'companies'}
					onclick={() => switchView('companies')}
				>
					🏢 전 회사
					<span class="hint">2,664사 전체 그래프</span>
				</button>
				<button
					class="view-tab"
					class:active={viewMode === 'industry'}
					disabled={!drillIndustry}
					onclick={() => drillIndustry && enterIndustry(drillIndustry)}
				>
					🔍 산업 내부
					<span class="hint">
						{drillIndustry
							? `${industryDetail?.name || drillIndustry} 드릴다운`
							: '산업 클릭하여 진입'}
					</span>
				</button>
			</div>
		</div>

		<!-- 검색 -->
		<div class="section">
			<input
				type="text"
				bind:value={searchQuery}
				onkeydown={(e) => e.key === 'Enter' && handleSearch()}
				placeholder={viewMode === 'atlas' ? '산업명 검색...' : '회사명/종목코드 검색...'}
				class="search"
			/>
		</div>

		<!-- atlas 뷰 전용: 산업 목록 (클릭=드릴다운) -->
		{#if viewMode === 'atlas'}
			<div class="section industries">
				<h3>산업 (클릭 → 내부 보기)</h3>
				<ul>
					{#each [...data.atlas.industries].sort((a: any, b: any) => b.nodeCount - a.nodeCount) as ind (ind.id)}
						<li>
							<button class="atlas-item" onclick={() => enterIndustry(ind.id)}>
								<span class="swatch" style="background:{indColorMap.get(ind.id) || '#9ca3af'}"
								></span>
								<span class="name">{ind.name}</span>
								<span class="count">{ind.nodeCount}사</span>
							</button>
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		<!-- industry 뷰 전용: stage 필터 + 진입 회사 -->
		{#if viewMode === 'industry' && industryDetail}
			<div class="section">
				<h3>공정 필터</h3>
				<ul class="stage-list">
					{#each industryDetail.stages || [] as s (s.key)}
						<li>
							<label class="check">
								<input
									type="checkbox"
									checked={stageFilter.has(s.key)}
									onchange={() => toggleStage(s.key)}
								/>
								<span
									class="swatch"
									style="background:{s.stream === 'upstream'
										? '#8b5cf6'
										: s.stream === 'downstream'
											? '#f97316'
											: '#f8fafc'}"
								></span>
								<span class="name">{s.name}</span>
								<span class="count">{(s.nodes || []).length}</span>
							</label>
						</li>
					{/each}
				</ul>
			</div>
			<div class="section">
				<h3>총 매출 · 진입 회사</h3>
				<div class="ins-grid">
					<div class="ins-cell">
						<div class="ins-label">총 매출</div>
						<div class="ins-value">
							{formatRev((industryDetail.totalRevenue || 0) * 1e8)}
						</div>
					</div>
					<div class="ins-cell">
						<div class="ins-label">회사 수</div>
						<div class="ins-value">{industryDetail.nodeCount}사</div>
					</div>
				</div>
				<a href="{base}/industry/{industryDetail.industryId}" class="ins-link">
					산업 상세 페이지 →
				</a>
			</div>
		{/if}

		<!-- companies 뷰: 기존 엣지 타입 + 품질 필터 + 산업 토글 -->
		{#if viewMode === 'companies'}
			<div class="section">
				<h3>관계 유형</h3>
				<label class="check"
					><input type="checkbox" bind:checked={showSupplier} />
					<span class="dot supplier"></span>공급</label
				>
				<label class="check"
					><input type="checkbox" bind:checked={showAffiliate} />
					<span class="dot affiliate"></span>계열</label
				>
				<label class="check"
					><input type="checkbox" bind:checked={showInvestor} />
					<span class="dot investor"></span>투자</label
				>
			</div>
			<div class="section">
				<h3>품질 필터</h3>
				<label class="range">
					신뢰도 ≥ {minConfidence.toFixed(1)}
					<input type="range" bind:value={minConfidence} min="0" max="1" step="0.1" />
				</label>
				<label class="check">
					<input type="checkbox" bind:checked={onlyWithAmount} />
					금액 공개 엣지만
				</label>
			</div>
			{#if filterInsights}
				<div class="section insight-box">
					<h3>
						현재 선택
						<span class="info-tip" title="1억원 = 100,000,000 KRW (~$75K) / 1조원 = 10,000억원">ⓘ</span>
					</h3>
					<div class="ins-grid">
						<div class="ins-cell">
							<div class="ins-label">기업</div>
							<div class="ins-value">{filterInsights.count.toLocaleString()}사</div>
						</div>
						<div class="ins-cell">
							<div class="ins-label">총 매출</div>
							<div class="ins-value">{formatRev(filterInsights.totalRev)}</div>
						</div>
						<div class="ins-cell">
							<div class="ins-label">Top1 비중</div>
							<div class="ins-value">{filterInsights.top1Ratio.toFixed(1)}%</div>
						</div>
						<div class="ins-cell">
							<div class="ins-label">Top3 비중</div>
							<div class="ins-value">{filterInsights.top3Ratio.toFixed(1)}%</div>
						</div>
					</div>
					{#if filterInsights.top1Name}
						<div class="ins-sub">
							최대: {filterInsights.top1Name} · 정밀 엣지 {filterInsights.preciseEdges}건
						</div>
					{/if}
					{#if filterInsights.singleIndId}
						<button class="ins-link" onclick={() => enterIndustry(filterInsights!.singleIndId!)}>
							이 산업 내부 보기 →
						</button>
					{/if}
				</div>
			{/if}
			<div class="section industries">
				<h3>
					산업
					<span class="controls">
						<button onclick={() => toggleAllIndustries(true)}>전체</button>
						<button onclick={() => toggleAllIndustries(false)}>해제</button>
					</span>
				</h3>
				<ul>
					{#each industries as ind}
						<li>
							<label class="check industry-item">
								<input
									type="checkbox"
									checked={enabledIndustries.has(ind.id)}
									onchange={() => toggleIndustry(ind.id)}
								/>
								<span class="swatch" style="background:{ind.color}"></span>
								<span class="name">{ind.name}</span>
								<span class="count">{ind.count}</span>
							</label>
							<button
								class="detail-link"
								title="{ind.name} 내부 보기"
								onclick={() => enterIndustry(ind.id)}>→</button
							>
						</li>
					{/each}
				</ul>
			</div>
		{/if}
	</aside>

	<!-- 메인 지도 -->
	<main class="map-main">
		{#if viewMode === 'industry' && industryLoading && !industryDetail}
			<div class="loading-overlay">
				<div>
					<div>산업 데이터 로드 중…</div>
					{#if loadError}
						<div class="err">{loadError}</div>
					{/if}
				</div>
			</div>
		{/if}
		{#if viewMode === 'industry' && loadError && !industryDetail}
			<div class="loading-overlay error-overlay">
				<div>
					<div>⚠ 산업 데이터 로드 실패</div>
					<div class="err">{loadError}</div>
					<button class="retry" onclick={exitToAtlas}>← atlas 로 돌아가기</button>
				</div>
			</div>
		{/if}

		{#if viewMode === 'atlas'}
			<IndustryAtlas
				industries={data.atlas.industries.map((ind: any) => ({
					...ind,
					color: indColorMap.get(ind.id) || '#9ca3af'
				}))}
				flows={data.atlas.flows}
				onSelect={(ind: any) => enterIndustry(ind.id)}
			/>
		{:else if viewMode === 'industry' && industryDetail}
			<IndustryDrilldown
				nodes={industryNodes}
				links={industryLinks.map((l: any) => ({ ...l }))}
				stages={industryDetail?.stages || []}
				onNodeClick={handleNodeClick}
			/>
		{:else if viewMode === 'companies'}
			<EcosystemMap
				bind:this={mapRef}
				nodes={activeNodes}
				links={activeLinks}
				isAtlas={false}
				onNodeClick={handleNodeClick}
			/>
		{/if}
	</main>


	<!-- 오른쪽 상세: CompanyCard (회사 카드) -->
	{#if selectedNode && !selectedNode.isIndustry}
		<aside class="detail-panel" class:wide={comparing}>
			<div class="card-slot">
				<CompanyCard
					node={selectedNode}
					detail={selectedDetail}
					loading={selectedDetailLoading}
					compareDisabled={comparing}
					onAddCompare={addToCompare}
					onClose={() => handleNodeClick(null)}
				/>
			</div>
			{#if comparing && compareB}
				<div class="card-slot">
					<CompanyCard
						node={compareB}
						detail={compareBDetail}
						loading={false}
						compareDisabled={true}
						onClose={clearCompare}
					/>
				</div>
			{/if}
		</aside>
	{:else if selectedNode && selectedNode.isIndustry}
		<aside class="detail">
			<button class="close" onclick={() => (selectedNode = null)}>✕</button>
			<div class="detail-head">
				<h2>{selectedNode.label}</h2>
				<div class="badges">
					<span class="badge" style="background:{selectedNode.color}20; color:{selectedNode.color}">
						{selectedNode.industryName}
					</span>
				</div>
				<div class="big-stat">
					<span class="label">소속 회사</span>
					<span class="value">{selectedNode.nodeCount}사</span>
				</div>
				<div class="big-stat">
					<span class="label">산업 총 매출</span>
					<span class="value">{formatRev(selectedNode.revenue)}</span>
				</div>
				<div class="section">
					<button class="full-link" onclick={() => enterIndustry(selectedNode.industry)}>
						이 산업 내부 보기 →
					</button>
				</div>
			</div>
		</aside>
	{/if}
</div>

<style>
	.map-page {
		display: grid;
		grid-template-columns: 280px 1fr;
		height: 100dvh;
		background: #050811;
		color: #f1f5f9;
	}

	.sidebar {
		display: flex;
		flex-direction: column;
		overflow-y: auto;
		background: #0f1219;
		border-right: 1px solid #1e2433;
		padding: 16px 16px 64px;
		color: #f1f5f9;
	}

	.nav-links {
		display: flex;
		gap: 8px;
		margin-top: 8px;
	}
	.nav-links a {
		font-size: 11px;
		color: #60a5fa;
		text-decoration: none;
		padding: 3px 8px;
		background: rgba(96, 165, 250, 0.1);
		border-radius: 4px;
	}
	.nav-links a:hover {
		background: rgba(96, 165, 250, 0.25);
	}

	.header h1 {
		margin: 0 0 4px;
		font-size: 18px;
		color: #f1f5f9;
	}
	.header .sub {
		margin: 0;
		font-size: 12px;
		color: #94a3b8;
	}
	.crumb {
		background: none;
		border: none;
		color: #60a5fa;
		cursor: pointer;
		padding: 0;
		font-size: 12px;
	}
	.crumb:hover {
		text-decoration: underline;
	}

	.section {
		margin-top: 16px;
		padding-top: 16px;
		border-top: 1px solid #1e2433;
	}
	.section:first-of-type {
		border-top: none;
	}
	.section h3 {
		font-size: 11px;
		font-weight: 600;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0 0 8px;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}
	.info-tip {
		color: #64748b;
		cursor: help;
		font-size: 11px;
		margin-left: 4px;
	}
	.info-tip:hover {
		color: #94a3b8;
	}

	/* 색상 기준 셀렉터 */
	.color-switch {
		background: rgba(52, 211, 153, 0.04);
		border-radius: 8px;
		padding: 10px 12px;
		margin-top: 16px;
		border: 1px solid rgba(52, 211, 153, 0.15);
	}
	.metric-select {
		width: 100%;
		padding: 6px 10px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 6px;
		color: #f1f5f9;
		font-size: 12px;
		cursor: pointer;
	}
	.metric-select:focus {
		outline: none;
		border-color: #34d399;
	}
	.color-legend {
		display: flex;
		align-items: center;
		gap: 3px;
		margin-top: 8px;
		font-size: 10px;
		color: #64748b;
	}
	.lg-swatch {
		width: 14px;
		height: 8px;
		border-radius: 2px;
		display: inline-block;
	}
	.lg-label {
		color: #94a3b8;
		margin: 0 4px;
	}
	/* 관점 셀렉터 */
	.view-switch {
		background: rgba(96, 165, 250, 0.04);
		border-radius: 8px;
		padding: 10px 12px;
		margin-top: 16px;
		border: 1px solid rgba(96, 165, 250, 0.15);
	}
	.view-tabs {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.view-tab {
		background: transparent;
		border: 1px solid transparent;
		color: #cbd5e1;
		padding: 8px 10px;
		border-radius: 6px;
		cursor: pointer;
		text-align: left;
		font-size: 13px;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.view-tab:hover:not(:disabled) {
		background: rgba(96, 165, 250, 0.08);
		color: #f1f5f9;
	}
	.view-tab.active {
		background: rgba(96, 165, 250, 0.18);
		border-color: rgba(96, 165, 250, 0.45);
		color: #f1f5f9;
		font-weight: 600;
	}
	.view-tab:disabled {
		color: #475569;
		cursor: not-allowed;
	}
	.view-tab .hint {
		font-size: 10px;
		color: #64748b;
		font-weight: 400;
	}

	.controls button {
		font-size: 10px;
		padding: 2px 6px;
		background: #1e2433;
		color: #94a3b8;
		border: none;
		border-radius: 3px;
		cursor: pointer;
		margin-left: 4px;
	}
	.controls button:hover {
		background: #2a3142;
		color: #f1f5f9;
	}

	.search {
		width: 100%;
		padding: 8px 12px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 6px;
		font-size: 13px;
		color: #f1f5f9;
	}
	.search::placeholder {
		color: #64748b;
	}

	.check {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 13px;
		padding: 4px 0;
		cursor: pointer;
		color: #cbd5e1;
	}
	.check input {
		margin: 0;
	}
	.dot {
		width: 12px;
		height: 3px;
		border-radius: 2px;
	}
	.dot.supplier {
		background: #f97316;
	}
	.dot.affiliate {
		background: #d1d5db;
	}
	.dot.investor {
		background: #8b5cf6;
	}

	.range {
		display: block;
		font-size: 12px;
		color: #cbd5e1;
		margin-bottom: 8px;
	}
	.range input {
		width: 100%;
		margin-top: 4px;
	}

	.insight-box {
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 8px;
		padding: 12px;
	}
	.insight-box h3 {
		margin: 0 0 10px;
	}
	.ins-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
	}
	.ins-cell {
		padding: 6px 8px;
		background: #0f1219;
		border-radius: 6px;
	}
	.ins-label {
		font-size: 10px;
		color: #94a3b8;
		margin-bottom: 2px;
	}
	.ins-value {
		font-size: 14px;
		font-weight: 600;
		color: #f1f5f9;
	}
	.ins-sub {
		margin-top: 8px;
		font-size: 11px;
		color: #64748b;
	}
	.ins-link {
		display: block;
		margin-top: 10px;
		padding: 6px 10px;
		background: rgba(96, 165, 250, 0.1);
		border: none;
		border-radius: 6px;
		color: #60a5fa;
		text-decoration: none;
		font-size: 12px;
		text-align: center;
		cursor: pointer;
		width: 100%;
	}
	.ins-link:hover {
		background: rgba(96, 165, 250, 0.2);
	}

	.industries ul,
	.stage-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.industries li,
	.stage-list li {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.atlas-item {
		display: flex;
		align-items: center;
		gap: 8px;
		background: transparent;
		border: none;
		color: #cbd5e1;
		font-size: 13px;
		padding: 5px 4px;
		width: 100%;
		cursor: pointer;
		text-align: left;
		border-radius: 4px;
	}
	.atlas-item:hover {
		background: rgba(96, 165, 250, 0.08);
		color: #f1f5f9;
	}
	.industry-item {
		padding: 3px 0;
		flex: 1;
	}
	.detail-link {
		background: none;
		border: none;
		color: #475569;
		text-decoration: none;
		font-size: 14px;
		padding: 2px 6px;
		border-radius: 4px;
		cursor: pointer;
	}
	.detail-link:hover {
		color: #60a5fa;
		background: rgba(96, 165, 250, 0.1);
	}
	.swatch {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.atlas-item .name,
	.industry-item .name,
	.stage-list .name {
		flex: 1;
	}
	.atlas-item .count,
	.industry-item .count,
	.stage-list .count {
		font-size: 11px;
		color: #64748b;
	}

	.map-main {
		position: relative;
		overflow: hidden;
	}

	.loading-overlay {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(5, 8, 17, 0.7);
		color: #cbd5e1;
		font-size: 14px;
		z-index: 10;
		backdrop-filter: blur(2px);
		text-align: center;
	}
	.loading-overlay .err {
		margin-top: 8px;
		color: #f87171;
		font-size: 12px;
		font-family: monospace;
		max-width: 600px;
	}
	.loading-overlay.error-overlay {
		background: rgba(127, 29, 29, 0.4);
	}
	.loading-overlay .retry {
		margin-top: 16px;
		padding: 6px 12px;
		background: rgba(96, 165, 250, 0.15);
		color: #60a5fa;
		border: 1px solid rgba(96, 165, 250, 0.4);
		border-radius: 6px;
		cursor: pointer;
		font-size: 12px;
	}
	.loading-overlay .retry:hover {
		background: rgba(96, 165, 250, 0.3);
	}

	.detail-panel {
		position: fixed;
		top: 0;
		right: 0;
		width: 380px;
		height: 100dvh;
		background: #0f1219;
		border-left: 1px solid #1e2433;
		overflow-y: auto;
		display: grid;
		grid-template-columns: 1fr;
		box-shadow: -4px 0 12px rgba(0, 0, 0, 0.5);
		z-index: 6;
	}
	.detail-panel.wide {
		width: 760px;
		grid-template-columns: 1fr 1fr;
	}
	.card-slot {
		border-right: 1px solid #1e2433;
		overflow-y: auto;
		max-height: 100dvh;
	}
	.detail-panel.wide .card-slot:last-child {
		border-right: none;
	}
	@media (max-width: 900px) {
		.detail-panel,
		.detail-panel.wide {
			width: 100%;
			grid-template-columns: 1fr;
		}
	}

	.detail {
		position: fixed;
		top: 0;
		right: 0;
		width: 360px;
		height: 100dvh;
		background: #0f1219;
		border-left: 1px solid #1e2433;
		padding: 16px;
		overflow-y: auto;
		box-shadow: -4px 0 12px rgba(0, 0, 0, 0.5);
		color: #f1f5f9;
	}
	.close {
		position: absolute;
		top: 12px;
		right: 12px;
		background: none;
		border: none;
		font-size: 18px;
		cursor: pointer;
		color: #64748b;
	}
	.close:hover {
		color: #f1f5f9;
	}
	.detail-head h2 {
		margin: 0;
		font-size: 20px;
		color: #f1f5f9;
	}
	.badges {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
		margin-bottom: 12px;
	}
	.badge {
		font-size: 11px;
		padding: 2px 8px;
		border-radius: 4px;
		font-weight: 500;
	}
	.big-stat {
		background: #050811;
		padding: 12px;
		border-radius: 8px;
		margin-bottom: 10px;
		border: 1px solid #1e2433;
	}
	.big-stat .label {
		font-size: 11px;
		color: #94a3b8;
		display: block;
		margin-bottom: 4px;
	}
	.big-stat .value {
		font-size: 20px;
		font-weight: 600;
		color: #f1f5f9;
	}
	.full-link {
		display: inline-block;
		margin-top: 8px;
		color: #60a5fa;
		text-decoration: none;
		font-size: 13px;
		background: none;
		border: none;
		padding: 0;
		cursor: pointer;
	}
	.full-link:hover {
		text-decoration: underline;
	}

	@media (max-width: 768px) {
		.map-page {
			grid-template-columns: 1fr;
		}
		.sidebar {
			display: none;
		}
		.detail {
			width: 100%;
			top: auto;
			bottom: 0;
			height: 50vh;
			border-left: none;
			border-top: 1px solid #e5e7eb;
		}
	}
</style>
