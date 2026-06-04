<script lang="ts">
	// 정량재무제표 다이얼로그 — 공식 dart/finance parquet 을 DuckDB-WASM(워커)으로 query. 와이드 센터 모달.
	// statement 탭(IS/BS/CF/CIS/자본변동) × 빈도(연간/분기/누적) × 범위(연결/개별). EDGAR(us)는 v1 준비중.
	import { X } from 'lucide-svelte';
	import { fade, scale } from 'svelte/transition';
	import { marketForCode } from '$lib/viewer/dartUrl';
	import { loadFinanceStatement } from '$lib/viewer/finance/financeQuery';
	import {
		FREQ_BY_KIND,
		FREQ_LABELS,
		KIND_LABELS,
		SCOPE_LABELS,
		type FinanceFreq,
		type FinanceKind,
		type FinanceScope,
		type FinanceStatement
	} from '$lib/viewer/finance/types';
	import FinanceTable from './FinanceTable.svelte';

	let { code, corpName, open, onclose }: { code: string; corpName: string; open: boolean; onclose: () => void } = $props();

	const KINDS: FinanceKind[] = ['IS', 'BS', 'CF', 'CIS', 'SCE'];
	let kind = $state<FinanceKind>('IS');
	let freq = $state<FinanceFreq>('annual');
	let scope = $state<FinanceScope>('CFS');

	let statement = $state<FinanceStatement | null>(null);
	let loading = $state(false);
	let errorMsg = $state<string | null>(null);

	const market = $derived(marketForCode(code));

	function pickKind(k: FinanceKind) {
		kind = k;
		if (!FREQ_BY_KIND[k].includes(freq)) freq = FREQ_BY_KIND[k][0]; // 가용 빈도 보정
	}

	// open + 선택 조합 → DuckDB 로드 (조합별 1회 캐시). lastKey(비반응)로 동일 조합 effect 재실행 차단(루프 가드),
	// 캐시 히트는 로컬 cached 로(쓴 state 를 다시 읽지 않음 — self-dependency 루프 회피).
	const cache = new Map<string, FinanceStatement | null>();
	let lastKey = '';
	$effect(() => {
		if (!open) {
			lastKey = '';
			return;
		}
		const m = market, c = code, k = kind, f = freq, s = scope;
		const key = `${m}:${c}:${k}:${f}:${s}`;
		if (key === lastKey) return; // 같은 조합 재실행 차단
		lastKey = key;
		if (cache.has(key)) {
			const cached = cache.get(key) ?? null;
			statement = cached;
			errorMsg = cached === null ? usOrDeviceMsg(m) : null;
			loading = false;
			return;
		}
		loading = true;
		errorMsg = null;
		statement = null;
		loadFinanceStatement(c, m, k, f, s)
			.then((st) => {
				cache.set(key, st);
				statement = st;
				if (st === null) errorMsg = usOrDeviceMsg(m);
			})
			.catch((e) => (errorMsg = `로드 실패: ${e instanceof Error ? e.message : String(e)}`))
			.finally(() => (loading = false));
	});

	function usOrDeviceMsg(m: string): string {
		return m === 'US' ? 'EDGAR 정량재무제표는 준비 중입니다.' : '정량재무제표를 불러올 수 없습니다 (기기 제약 가능).';
	}

	// Esc 닫기 (모달만, 전체화면 유지).
	$effect(() => {
		if (!open) return;
		const onKey = (e: KeyboardEvent) => {
			if (e.key === 'Escape') {
				e.stopPropagation();
				onclose();
			}
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});

	const isEmpty = $derived(statement != null && statement.rows.length === 0);
</script>

{#if open}
	<button type="button" class="overlay" aria-label="닫기" onclick={onclose} transition:fade={{ duration: 150 }}></button>
	<div class="modal" role="dialog" aria-modal="true" aria-label="정량재무제표" transition:scale={{ start: 0.98, duration: 180 }}>
		<header class="mh">
			<div class="mh-title"><span class="mh-corp">{corpName || code}</span><span class="mh-sub">정량재무제표</span></div>
			<button type="button" class="mh-close" onclick={onclose} title="닫기 (Esc)"><X size={16} /></button>
		</header>

		<div class="controls">
			<div class="tabs">
				{#each KINDS as k (k)}
					<button type="button" class="tab" class:active={kind === k} onclick={() => pickKind(k)} title={KIND_LABELS[k]}>{KIND_LABELS[k]}</button>
				{/each}
			</div>
			<div class="segs">
				<div class="seg" title="빈도">
					{#each FREQ_BY_KIND[kind] as f (f)}
						<button type="button" class="seg-btn" class:active={freq === f} onclick={() => (freq = f)}>{FREQ_LABELS[f]}</button>
					{/each}
				</div>
				<div class="seg" title="범위 (연결/개별)">
					{#each ['CFS', 'OFS'] as s (s)}
						<button type="button" class="seg-btn" class:active={scope === s} onclick={() => (scope = s as FinanceScope)}>{SCOPE_LABELS[s as FinanceScope]}</button>
					{/each}
				</div>
				<span class="unit">단위: 원</span>
			</div>
		</div>

		<div class="body">
			{#if loading}
				<div class="state"><div class="spinner"></div><p>{KIND_LABELS[kind]} 불러오는 중</p></div>
			{:else if errorMsg}
				<div class="state"><p>{errorMsg}</p></div>
			{:else if isEmpty}
				<div class="state"><p>이 회사는 {KIND_LABELS[kind]}({FREQ_LABELS[freq]}·{SCOPE_LABELS[scope]}) 정량 데이터가 없습니다.</p></div>
			{:else if statement}
				<FinanceTable {statement} />
			{/if}
		</div>
	</div>
{/if}

<style>
	.overlay {
		position: fixed;
		inset: 0;
		z-index: 400;
		border: 0;
		padding: 0;
		background: rgba(2, 4, 9, 0.66);
		cursor: default;
	}
	.modal {
		position: fixed;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		z-index: 401;
		width: min(1320px, 96vw);
		height: min(86vh, 920px);
		display: flex;
		flex-direction: column;
		background: #0a0e18;
		border: 1px solid #263145;
		border-radius: 10px;
		box-shadow: 0 24px 64px rgba(0, 0, 0, 0.55);
		overflow: hidden;
	}
	.mh {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		padding: 11px 14px;
		border-bottom: 1px solid #1e2433;
	}
	.mh-title {
		display: flex;
		align-items: baseline;
		gap: 8px;
		min-width: 0;
	}
	.mh-corp {
		font-size: 15px;
		font-weight: 700;
		color: #f1f5f9;
	}
	.mh-sub {
		font-size: 11px;
		color: #94a3b8;
	}
	.mh-sub::before {
		content: '·';
		margin-right: 6px;
		color: #475569;
	}
	.mh-close {
		flex-shrink: 0;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: transparent;
		color: #94a3b8;
		cursor: pointer;
	}
	.mh-close:hover {
		border-color: #fb923c;
		color: #fb923c;
	}
	.controls {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 10px;
		padding: 9px 14px;
		border-bottom: 1px solid #1e2433;
	}
	.tabs {
		display: inline-flex;
		gap: 2px;
	}
	.tab {
		padding: 5px 11px;
		border: 1px solid transparent;
		border-radius: 6px;
		background: transparent;
		color: #94a3b8;
		font: inherit;
		font-size: 12px;
		cursor: pointer;
	}
	.tab:hover {
		color: #cbd5e1;
	}
	.tab.active {
		background: rgba(251, 146, 60, 0.12);
		border-color: rgba(251, 146, 60, 0.5);
		color: #fb923c;
		font-weight: 600;
	}
	.segs {
		display: inline-flex;
		align-items: center;
		gap: 12px;
	}
	.seg {
		display: inline-flex;
		gap: 2px;
		padding: 2px;
		border: 1px solid #1e2433;
		border-radius: 6px;
	}
	.seg-btn {
		padding: 3px 9px;
		border: none;
		border-radius: 4px;
		background: transparent;
		color: #94a3b8;
		font: inherit;
		font-size: 11px;
		cursor: pointer;
	}
	.seg-btn:hover {
		color: #cbd5e1;
	}
	.seg-btn.active {
		background: rgba(251, 146, 60, 0.14);
		color: #fb923c;
		font-weight: 600;
	}
	.unit {
		font-size: 11px;
		color: #64748b;
	}
	.body {
		flex: 1 1 auto;
		min-height: 0;
		overflow: hidden;
	}
	.state {
		height: 100%;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 12px;
	}
	.state p {
		color: #94a3b8;
		font-size: 13px;
	}
	.spinner {
		width: 26px;
		height: 26px;
		border: 2px solid #1e2433;
		border-top-color: #fb923c;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
