<script lang="ts">
	// 정량재무제표 다이얼로그 — 공식 dart/finance parquet 을 DuckDB-WASM(워커)으로 query. 와이드 센터 모달.
	// statement 탭(IS/BS/CF/CIS/자본변동) × 빈도(연간/분기/누적) × 범위(연결/개별). EDGAR(us)는 v1 준비중.
	import { X } from 'lucide-svelte';
	import { fade, scale } from 'svelte/transition';
	import { marketForCode } from '$lib/viewer/dartUrl';
	import { financeAvailability, loadFinanceStatement, loadSceMatrix, type FinanceAvailability } from '$lib/viewer/finance/financeQuery';
	import {
		FREQ_BY_KIND,
		FREQ_LABELS,
		KIND_LABELS,
		SCOPE_LABELS,
		UNIT_DIVISORS,
		UNIT_LABELS,
		type FinanceFreq,
		type FinanceKind,
		type FinanceScope,
		type FinanceStatement,
		type FinanceUnit,
		type SceMatrixData
	} from '$lib/viewer/finance/types';
	import FinanceTable from './FinanceTable.svelte';
	import SceMatrix from './SceMatrix.svelte';

	let { code, corpName, open, onclose }: { code: string; corpName: string; open: boolean; onclose: () => void } = $props();

	const KINDS: FinanceKind[] = ['IS', 'BS', 'CF', 'CIS', 'SCE'];
	const UNITS: FinanceUnit[] = ['원', '백만', '억'];
	let kind = $state<FinanceKind>('IS');
	let freq = $state<FinanceFreq>('annual');
	let scope = $state<FinanceScope>('CFS');
	let unit = $state<FinanceUnit>('백만');
	const divisor = $derived(UNIT_DIVISORS[unit]);
	const market = $derived(marketForCode(code));

	// 회사 가용성 (scope × statement) — open·code 1회 probe. 빈 scope 토글·빈 statement 탭 제거.
	let avail = $state<FinanceAvailability | null>(null);
	const availableScopes = $derived<FinanceScope[]>(avail?.scopes.length ? avail.scopes : ['CFS', 'OFS']);
	const availableKinds = $derived<FinanceKind[]>(avail ? (avail.byScope[scope] ?? []) : KINDS);

	// 표시 탭 — 손익계산서 항상 노출: IS 있으면 IS, 없으면 단일 포괄손익(CIS)이 손익 포함이므로 CIS 를 '손익계산서'로.
	// 포괄손익은 2표식(IS·CIS 둘 다)일 때만 별도. → IS-주력이든 단일이든 항상 '손익계산서' 탭에서 P&L.
	const displayTabs = $derived.by(() => {
		const has = new Set(availableKinds);
		const tabs: { label: string; kind: FinanceKind }[] = [];
		if (has.has('IS')) tabs.push({ label: '손익계산서', kind: 'IS' });
		else if (has.has('CIS')) tabs.push({ label: '손익계산서', kind: 'CIS' });
		if (has.has('BS')) tabs.push({ label: '재무상태표', kind: 'BS' });
		if (has.has('CF')) tabs.push({ label: '현금흐름표', kind: 'CF' });
		if (has.has('IS') && has.has('CIS')) tabs.push({ label: '포괄손익', kind: 'CIS' });
		if (has.has('SCE')) tabs.push({ label: '자본변동표', kind: 'SCE' });
		return tabs;
	});
	function firstTabKind(a: FinanceKind[]): FinanceKind {
		const has = new Set(a);
		if (has.has('IS')) return 'IS';
		if (has.has('CIS')) return 'CIS';
		return a[0] ?? 'BS';
	}
	function pickKind(k: FinanceKind) {
		kind = k;
		if (!FREQ_BY_KIND[k].includes(freq)) freq = FREQ_BY_KIND[k][0]; // 가용 빈도 보정
	}

	let statement = $state<FinanceStatement | null>(null);
	let sceData = $state<SceMatrixData | null>(null);
	let scePeriod = $state('');
	let loading = $state(false);
	let errorMsg = $state<string | null>(null);

	function usOrDeviceMsg(m: string): string {
		return m === 'US' ? 'EDGAR 정량재무제표는 준비 중입니다.' : '정량재무제표를 불러올 수 없습니다 (기기 제약 가능).';
	}

	// 가용성 probe (open·code). financeAvailability 는 scope 무관(전체) — 한 번에.
	let lastAvailKey = '';
	$effect(() => {
		if (!open) {
			lastAvailKey = '';
			return;
		}
		const m = market, c = code;
		const key = `${m}:${c}`;
		if (key === lastAvailKey) return;
		lastAvailKey = key;
		void financeAvailability(c, m)
			.then((a) => (avail = a))
			.catch(() => {});
	});

	// 무효 선택 보정 — scope 없으면 가용 첫 범위로, kind 없으면 손익계산서 우선. 보정 후 유효(수렴).
	$effect(() => {
		if (!open || !avail) return;
		if (!availableScopes.includes(scope)) {
			scope = availableScopes[0];
			return;
		}
		if (!availableKinds.includes(kind)) pickKind(firstTabKind(availableKinds));
	});

	// 선택 조합 → DuckDB 로드. lastKey(비반응) 재실행 차단. SCE 는 matrix(loadSceMatrix), 그 외 account×period.
	let lastKey = '';
	$effect(() => {
		if (!open) {
			lastKey = '';
			return;
		}
		const m = market, c = code, k = kind, f = freq, s = scope;
		const key = `${m}:${c}:${k}:${f}:${s}`;
		if (key === lastKey) return;
		lastKey = key;
		loading = true;
		errorMsg = null;
		statement = null;
		sceData = null;
		if (k === 'SCE') {
			loadSceMatrix(c, m, s)
				.then((d) => {
					sceData = d;
					if (d && d.periods.length) {
						if (!d.periods.includes(scePeriod)) scePeriod = d.periods[0];
					} else errorMsg = d === null ? usOrDeviceMsg(m) : '자본변동표 데이터가 없습니다.';
				})
				.catch((e) => (errorMsg = `로드 실패: ${e instanceof Error ? e.message : String(e)}`))
				.finally(() => (loading = false));
		} else {
			loadFinanceStatement(c, m, k, f, s)
				.then((st) => {
					statement = st;
					if (st === null) errorMsg = usOrDeviceMsg(m);
				})
				.catch((e) => (errorMsg = `로드 실패: ${e instanceof Error ? e.message : String(e)}`))
				.finally(() => (loading = false));
		}
	});

	// Esc 닫기
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

	const isEmpty = $derived(kind !== 'SCE' && statement != null && statement.rows.length === 0);
	const sceEmpty = $derived(kind === 'SCE' && sceData != null && sceData.periods.length === 0);
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
				{#each displayTabs as t (t.label)}
					<button type="button" class="tab" class:active={kind === t.kind} onclick={() => pickKind(t.kind)} title={t.label}>{t.label}</button>
				{/each}
			</div>
			<div class="segs">
				{#if kind === 'SCE'}
					<div class="seg" title="기간 (자본변동표는 기간별)">
						{#each (sceData?.periods ?? []).slice(0, 8) as p (p)}
							<button type="button" class="seg-btn" class:active={scePeriod === p} onclick={() => (scePeriod = p)}>{p}</button>
						{/each}
					</div>
				{:else}
					<div class="seg" title="빈도">
						{#each FREQ_BY_KIND[kind] as f (f)}
							<button type="button" class="seg-btn" class:active={freq === f} onclick={() => (freq = f)}>{FREQ_LABELS[f]}</button>
						{/each}
					</div>
				{/if}
				{#if availableScopes.length > 1}
					<div class="seg" title="범위 (연결/개별)">
						{#each availableScopes as s (s)}
							<button type="button" class="seg-btn" class:active={scope === s} onclick={() => (scope = s)}>{SCOPE_LABELS[s]}</button>
						{/each}
					</div>
				{/if}
				<div class="seg" title="단위">
					{#each UNITS as u (u)}
						<button type="button" class="seg-btn" class:active={unit === u} onclick={() => (unit = u)}>{u}</button>
					{/each}
				</div>
				<span class="unit">단위: {UNIT_LABELS[unit]}</span>
			</div>
		</div>

		<div class="body">
			{#if loading}
				<div class="state"><div class="spinner"></div><p>{KIND_LABELS[kind]} 불러오는 중</p></div>
			{:else if errorMsg}
				<div class="state"><p>{errorMsg}</p></div>
			{:else if kind === 'SCE'}
				{#if sceEmpty || !sceData || !scePeriod}
					<div class="state"><p>이 회사는 자본변동표({SCOPE_LABELS[scope]}) 데이터가 없습니다.</p></div>
				{:else}
					<SceMatrix data={sceData} period={scePeriod} {divisor} />
				{/if}
			{:else if isEmpty}
				<div class="state"><p>이 회사는 {KIND_LABELS[kind]}({FREQ_LABELS[freq]}·{SCOPE_LABELS[scope]}) 정량 데이터가 없습니다.</p></div>
			{:else if statement}
				<FinanceTable {statement} {divisor} />
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
