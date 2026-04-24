<script lang="ts">
	import { base } from '$app/paths';
	import Section from '$lib/components/ui/Section.svelte';
	import Card from '$lib/components/ui/Card.svelte';
	import Eyebrow from '$lib/components/ui/Eyebrow.svelte';
	import MonoNumber from '$lib/components/ui/MonoNumber.svelte';
	import Tag from '$lib/components/ui/Tag.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Bar from '$lib/components/ui/Bar.svelte';
	import { fmtKrwFromEok } from '$lib/format/krw';

	// ── DuckDB-WASM 도입 시뮬레이션 ──
	// 이 페이지는 Phase 0 검증 — 실제 WASM 통합은 사용자가
	// `cd landing && npm install @duckdb/duckdb-wasm` 후 진행.
	// 지금은 데이터 fetch + JS 집계로 비교용 mock.

	let stage: 'idle' | 'loading' | 'ready' | 'error' = $state('idle');
	let mode: 'js' | 'duckdb' = $state('js');
	let nodes: any[] = $state([]);
	let queryResult: any[] = $state([]);
	let queryTime = $state(0);
	let loadTime = $state(0);
	let totalSize = $state(0);
	let errorMsg = $state('');
	let duckdbConn: any = $state(null);

	let queryText = $state(`SELECT industry, COUNT(*) AS cnt, SUM(revenue) AS rev
FROM ecosystem
GROUP BY industry
ORDER BY rev DESC
LIMIT 10`);

	async function loadData() {
		stage = 'loading';
		errorMsg = '';
		const t0 = performance.now();
		try {
			const r = await fetch(`${base}/map/ecosystem.json`);
			const eco = await r.json();
			nodes = eco.nodes ?? [];
			totalSize = JSON.stringify(eco).length;
			loadTime = performance.now() - t0;
			runQueryJS();
			stage = 'ready';
		} catch (e: any) {
			errorMsg = String(e?.message ?? e);
			stage = 'error';
		}
	}

	async function loadDuckDB() {
		stage = 'loading';
		errorMsg = '';
		const t0 = performance.now();
		try {
			// CDN dynamic import — npm install 불필요
			// @ts-expect-error remote URL module
			const duckdb = await import(/* @vite-ignore */ 'https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0/+esm');
			const CDN = 'https://cdn.jsdelivr.net/npm/@duckdb/duckdb-wasm@1.29.0/dist/';
			const bundles = {
				mvp: { mainModule: `${CDN}duckdb-mvp.wasm`, mainWorker: `${CDN}duckdb-browser-mvp.worker.js` },
				eh: { mainModule: `${CDN}duckdb-eh.wasm`, mainWorker: `${CDN}duckdb-browser-eh.worker.js` }
			};
			const bundle = await (duckdb as any).selectBundle(bundles);
			const worker = new Worker(bundle.mainWorker!);
			const logger = new (duckdb as any).ConsoleLogger();
			const db = new (duckdb as any).AsyncDuckDB(logger, worker);
			await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
			duckdbConn = await db.connect();

			// ecosystem.json 의 nodes 를 DuckDB table 로 register
			const ecoUrl = `${location.origin}${base}/map/ecosystem.json`;
			const r = await fetch(ecoUrl);
			const eco = await r.json();
			nodes = eco.nodes ?? [];
			totalSize = JSON.stringify(eco).length;
			// nodes array → DuckDB table
			await db.registerFileText('ecosystem.json', JSON.stringify(nodes));
			await duckdbConn.query(`CREATE OR REPLACE TABLE ecosystem AS SELECT * FROM read_json_auto('ecosystem.json')`);
			loadTime = performance.now() - t0;
			mode = 'duckdb';
			runQuery();
			stage = 'ready';
		} catch (e: any) {
			errorMsg = `DuckDB-WASM 로드 실패: ${e?.message ?? e}`;
			stage = 'error';
		}
	}

	async function runQuery() {
		if (mode === 'duckdb' && duckdbConn) {
			runQueryDuckDB();
		} else {
			runQueryJS();
		}
	}

	function runQueryJS() {
		const t0 = performance.now();
		const groups = new Map<string, { industry: string; cnt: number; rev: number }>();
		for (const n of nodes) {
			const k = n.industry ?? 'unknown';
			const g = groups.get(k) ?? { industry: k, cnt: 0, rev: 0 };
			g.cnt += 1;
			g.rev += Number(n.revenue) || 0;
			groups.set(k, g);
		}
		queryResult = [...groups.values()].sort((a, b) => b.rev - a.rev).slice(0, 10);
		queryTime = performance.now() - t0;
	}

	async function runQueryDuckDB() {
		if (!duckdbConn) return;
		const t0 = performance.now();
		try {
			const result = await duckdbConn.query(queryText);
			queryResult = result.toArray().map((r: any) => ({
				industry: r.industry,
				cnt: Number(r.cnt),
				rev: Number(r.rev)
			}));
			queryTime = performance.now() - t0;
		} catch (e: any) {
			errorMsg = `쿼리 실패: ${e?.message ?? e}`;
		}
	}

	const maxRev = $derived(queryResult.length ? queryResult[0].rev : 1);
</script>

<svelte:head>
	<title>DuckDB-WASM 검증 · /lab</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<header class="lab-nav">
	<div class="nav-inner">
		<a href="{base}/lab" class="brand">
			<span class="brand-mark">dartlab</span>
			<span class="brand-slash">/</span>
			<span class="brand-ctx">lab · duckdb</span>
		</a>
		<div class="nav-actions">
			<Button variant="ghost" size="sm" href="{base}/lab">/lab</Button>
			<Button variant="ghost" size="sm" href="{base}/lab/map">/lab/map</Button>
			<Button variant="ghost" size="sm" href="{base}/lab/dashboard/005930">/lab/dashboard</Button>
		</div>
	</div>
</header>

<Section
	number="00"
	eyebrow="PHASE 0 · 데이터 레이어 검증"
	title="DuckDB-WASM + parquet"
	subtitle="브라우저에서 SQL 로 회사 데이터 집계. 서버 없이. dartlab 5-15MB parquet 은 검증 사례 (Wheeler 72GB) 의 0.02% 규모."
>
	<div class="status-row">
		<Tag tone={stage === 'ready' ? 'good' : stage === 'error' ? 'bad' : stage === 'loading' ? 'warn' : 'neutral'} filled>
			{stage === 'ready' ? `${mode === 'duckdb' ? 'DuckDB-WASM' : 'JS'} 로드 완료` : stage === 'loading' ? '로딩 중' : stage === 'error' ? '오류' : '대기'}
		</Tag>
		{#if stage === 'idle'}
			<Button variant="secondary" onclick={loadData}>JS 모드 (즉시)</Button>
			<Button variant="primary" onclick={loadDuckDB}>DuckDB-WASM 모드 (CDN ~3MB)</Button>
		{:else if stage === 'ready' && mode === 'js'}
			<Button variant="primary" onclick={loadDuckDB}>DuckDB-WASM 으로 전환</Button>
		{:else if stage === 'ready' && mode === 'duckdb'}
			<Button variant="secondary" onclick={runQuery}>SQL 재실행</Button>
		{:else if stage === 'error'}
			<Button variant="secondary" onclick={() => { stage = 'idle'; errorMsg = ''; }}>다시</Button>
		{/if}
	</div>

	{#if errorMsg}
		<Card padded>
			<div class="dl-eyebrow" style="color: var(--dl-bad);">ERROR</div>
			<p class="dl-body-sm" style="margin-top: var(--dl-s-2); color: var(--dl-bad); white-space: pre-wrap;">{errorMsg}</p>
		</Card>
	{/if}

	{#if stage === 'ready'}
		<div class="metrics-grid">
			<Card padded>
				<div class="dl-label">데이터 크기</div>
				<MonoNumber value={(totalSize / 1024 / 1024).toFixed(2)} suffix=" MB" size="lg" tone="ink" align="left" />
			</Card>
			<Card padded>
				<div class="dl-label">노드 수</div>
				<MonoNumber value={nodes.length.toLocaleString()} suffix=" 사" size="lg" tone="ink" align="left" />
			</Card>
			<Card padded>
				<div class="dl-label">로드 시간</div>
				<MonoNumber value={loadTime.toFixed(0)} suffix=" ms" size="lg" tone="info" align="left" />
			</Card>
			<Card padded>
				<div class="dl-label">쿼리 시간</div>
				<MonoNumber value={queryTime.toFixed(2)} suffix=" ms" size="lg" tone="good" align="left" />
			</Card>
		</div>
	{/if}
</Section>

{#if stage === 'ready'}
	<Section
		eyebrow="LIVE QUERY"
		title="업종별 매출 Top 10"
		subtitle="현재는 JS 집계 (Map/sort). DuckDB-WASM 로 교체 시 위 SQL 그대로 사용 가능."
	>
		<div class="query-grid">
			<Card eyebrow="SQL" padded>
				<pre class="sql"><code>{queryText}</code></pre>
			</Card>

			<Card eyebrow="결과" padded>
				<table class="result-table">
					<thead>
						<tr>
							<th class="dl-label">#</th>
							<th class="dl-label">업종</th>
							<th class="dl-label" style="text-align: right">사</th>
							<th class="dl-label" style="text-align: right">총 매출</th>
							<th class="dl-label">상대</th>
						</tr>
					</thead>
					<tbody>
						{#each queryResult as r, i}
							<tr>
								<td><span class="dl-mono dim">{(i + 1).toString().padStart(2, '0')}</span></td>
								<td><span class="ind-name">{r.industry}</span></td>
								<td style="text-align: right"><MonoNumber value={r.cnt} size="sm" tone="ink" align="right" /></td>
								<td style="text-align: right"><MonoNumber value={fmtKrwFromEok(r.rev / 1e8)} size="sm" tone="ink" align="right" /></td>
								<td style="min-width: 120px"><Bar value={r.rev} max={maxRev} tone="brand" /></td>
							</tr>
						{/each}
					</tbody>
				</table>
			</Card>
		</div>
	</Section>
{/if}

<Section
	eyebrow="다음 단계"
	title="DuckDB-WASM 실제 통합 가이드"
	subtitle="이 페이지는 데이터 레이어 검증용 mock. 실제 WASM 통합 절차."
	container="article"
>
	<Card padded>
		<ol class="steps">
			<li>
				<strong>npm install</strong>
				<pre class="cmd"><code>cd landing && npm install @duckdb/duckdb-wasm</code></pre>
			</li>
			<li>
				<strong>parquet 파일 생성</strong> — Python script 로 ecosystem.json + finance.json 통합 → companies.parquet
			</li>
			<li>
				<strong>호스팅</strong> — 작으면 GitHub Pages, 50MB 초과면 Cloudflare R2 custom domain (HF Range CORS 회피)
			</li>
			<li>
				<strong>lazy loader</strong> — `landing/src/lib/data/duckdb.ts` 에 import (chunked, 첫 진입 부담 회피)
			</li>
			<li>
				<strong>OPFS 캐시</strong> — 버전 prefix 파일명 ({'`finance-v{sha}.parquet`'}) + 부팅 시 구버전 remove
			</li>
			<li>
				<strong>iOS Safari 가드</strong> — UA 감지 시 WASM Memory 512MB 고정 (2GB 초기화 시 즉시 OOM)
			</li>
		</ol>
	</Card>
</Section>

<footer class="lab-foot">
	<Eyebrow text="END · /lab/duckdb — Phase 0 검증 페이지" />
</footer>

<style>
	.lab-nav {
		position: sticky; top: 0; z-index: 30;
		border-bottom: 1px solid var(--dl-line);
		background: rgba(15, 15, 16, 0.85);
		backdrop-filter: blur(14px);
	}
	.nav-inner {
		max-width: var(--dl-w-max); margin-inline: auto;
		padding: var(--dl-s-3) var(--dl-s-6);
		display: flex; justify-content: space-between; align-items: center;
	}
	.brand { display: inline-flex; align-items: baseline; gap: var(--dl-s-2); text-decoration: none; color: var(--dl-ink); }
	.brand-mark { font-family: var(--dl-font-head); font-weight: 700; font-size: 18px; letter-spacing: -0.02em; }
	.brand-slash { color: var(--dl-ink-faint); font-weight: 300; }
	.brand-ctx { font-family: var(--dl-font-mono); font-size: 11px; text-transform: uppercase; letter-spacing: 0.16em; color: var(--dl-orange); }
	.nav-actions { display: flex; gap: var(--dl-s-1); }

	.status-row { display: flex; align-items: center; gap: var(--dl-s-3); margin-bottom: var(--dl-s-4); }
	.metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--dl-s-3); }

	.query-grid { display: grid; grid-template-columns: 1fr 1.4fr; gap: var(--dl-s-3); align-items: start; }
	.sql {
		font-family: var(--dl-font-mono);
		font-size: 12px;
		color: var(--dl-orange);
		background: var(--dl-bg-base);
		padding: var(--dl-s-3);
		border-radius: var(--dl-r-sm);
		margin: 0;
		white-space: pre-wrap;
		line-height: 1.6;
	}

	.result-table { width: 100%; border-collapse: collapse; font-size: 13px; }
	.result-table th, .result-table td { padding: var(--dl-s-2) var(--dl-s-3); border-bottom: 1px solid var(--dl-line); }
	.result-table th { text-align: left; font-size: 10px; }
	.result-table tr:last-child td { border-bottom: none; }
	.dim { color: var(--dl-ink-faint); }
	.ind-name { font-size: 13px; color: var(--dl-ink); }

	.steps { list-style: none; padding: 0; margin: 0; counter-reset: step; }
	.steps li {
		counter-increment: step;
		padding: var(--dl-s-3) 0;
		border-bottom: 1px solid var(--dl-line);
	}
	.steps li:last-child { border-bottom: none; }
	.steps li::before {
		content: counter(step, decimal-leading-zero);
		display: inline-block;
		font-family: var(--dl-font-mono);
		font-size: 10px;
		color: var(--dl-orange);
		margin-right: var(--dl-s-3);
	}
	.steps strong { font-weight: 700; color: var(--dl-ink-print); }
	.cmd {
		display: block;
		margin-top: var(--dl-s-2);
		padding: var(--dl-s-2) var(--dl-s-3);
		background: var(--dl-bg-base);
		border: 1px solid var(--dl-line);
		border-radius: var(--dl-r-sm);
		font-family: var(--dl-font-mono);
		font-size: 12px;
		color: var(--dl-good);
	}

	.lab-foot { padding: var(--dl-s-7) var(--dl-s-6); text-align: center; border-top: 1px solid var(--dl-line); }

	@media (max-width: 720px) {
		.metrics-grid { grid-template-columns: 1fr; }
		.query-grid { grid-template-columns: 1fr; }
	}
</style>
