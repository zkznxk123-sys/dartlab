<script lang="ts">
	import type { FilterCond, MetricDef } from './types';
	import { MoreVertical } from 'lucide-svelte';

	interface Props {
		metric?: MetricDef;
		fallbackKey: string;
		activeConds?: FilterCond[];
		values?: string[];
		onApply: (metric: string, conds: FilterCond[]) => void;
		onClear: (metric: string) => void;
	}

	let {
		metric,
		fallbackKey,
		activeConds = [],
		values = [],
		onApply,
		onClear
	}: Props = $props();

	let open = $state(false);
	let minInput = $state('');
	let maxInput = $state('');
	let textInput = $state('');
	let selectedValues = $state<string[]>([]);
	let excludeEmpty = $state(false);

	let key = $derived(metric?.key ?? fallbackKey);
	let label = $derived(metric?.label ?? fallbackKey);
	let type = $derived(metric?.type ?? 'text');
	let unit = $derived(metric?.unit ?? '');
	let hasFilter = $derived(activeConds.length > 0);
	let unitHint = $derived(
		unit === '억원'
			? '입력 단위: 억원 · 1,000 = 1,000억원'
			: unit
				? `입력 단위: ${unit}`
				: '표시값 기준'
	);
	let enumValues = $derived.by(() => {
		const raw = values.length > 0 ? values : Array.from(metric?.values ?? []);
		return Array.from(new Set(raw.filter((v) => v != null && String(v).trim()).map(String))).sort((a, b) =>
			a.localeCompare(b, 'ko-KR')
		);
	});

	function hydrate() {
		minInput = '';
		maxInput = '';
		textInput = '';
		selectedValues = [];
		excludeEmpty = false;
		for (const cond of activeConds) {
			if (cond.op === 'between') {
				minInput = formatNumberInput(cond.value == null ? '' : String(cond.value));
				maxInput = formatNumberInput(cond.value2 == null ? '' : String(cond.value2));
			} else if (cond.op === '>=') {
				minInput = formatNumberInput(cond.value == null ? '' : String(cond.value));
			} else if (cond.op === '<=') {
				maxInput = formatNumberInput(cond.value == null ? '' : String(cond.value));
			} else if (cond.op === 'contains') {
				textInput = cond.value == null ? '' : String(cond.value);
			} else if (cond.op === 'in' && Array.isArray(cond.value)) {
				selectedValues = cond.value.map(String);
			} else if (cond.op === '==' && cond.value != null) {
				selectedValues = [String(cond.value)];
			} else if (cond.op === 'exists') {
				excludeEmpty = true;
			}
		}
	}

	function toggle(e: MouseEvent) {
		e.stopPropagation();
		if (!open) hydrate();
		open = !open;
	}

	function parseNumber(input: string): number | null {
		const trimmed = input.trim().replace(/,/g, '');
		if (!trimmed) return null;
		const n = Number(trimmed);
		return Number.isFinite(n) ? n : null;
	}

	function formatNumberInput(input: string): string {
		const trimmed = input.trim().replace(/,/g, '');
		if (!trimmed || trimmed === '-' || trimmed === '.') return input;
		const n = Number(trimmed);
		if (!Number.isFinite(n)) return input;
		const hasDecimal = trimmed.includes('.');
		const [intPart, decimalPart] = trimmed.split('.');
		const sign = intPart.startsWith('-') ? '-' : '';
		const absInt = sign ? intPart.slice(1) : intPart;
		const grouped = `${sign}${Number(absInt || '0').toLocaleString('ko-KR')}`;
		return hasDecimal ? `${grouped}.${decimalPart ?? ''}` : grouped;
	}

	function formatMin() {
		minInput = formatNumberInput(minInput);
	}

	function formatMax() {
		maxInput = formatNumberInput(maxInput);
	}

	function toggleValue(value: string) {
		if (selectedValues.includes(value)) selectedValues = selectedValues.filter((v) => v !== value);
		else selectedValues = [...selectedValues, value];
	}

	function apply() {
		const next: FilterCond[] = [];
		if (type === 'number') {
			const min = parseNumber(minInput);
			const max = parseNumber(maxInput);
			if (min !== null && max !== null) next.push({ metric: key, op: 'between', value: min, value2: max });
			else if (min !== null) next.push({ metric: key, op: '>=', value: min });
			else if (max !== null) next.push({ metric: key, op: '<=', value: max });
			if (excludeEmpty) next.push({ metric: key, op: 'exists' });
		} else if (type === 'enum') {
			if (selectedValues.length > 0) next.push({ metric: key, op: 'in', value: selectedValues });
		} else {
			const q = textInput.trim();
			if (q) next.push({ metric: key, op: 'contains', value: q });
			if (excludeEmpty) next.push({ metric: key, op: 'exists' });
		}
		onApply(key, next);
		open = false;
	}

	function clear() {
		onClear(key);
		open = false;
	}
</script>

<span class="filter-wrap">
	<button
		type="button"
		class="filter-btn"
		class:active={hasFilter}
		aria-label="{label} 필터"
		title="{label} 필터"
		onclick={toggle}
	>
		<MoreVertical size={13} strokeWidth={2.2} />
	</button>
	{#if open}
		<div class="popover" role="dialog" aria-label="{label} 필터 설정">
			<div class="pop-head">
				<span>{label} 필터</span>
				<button type="button" class="x-btn" onclick={() => (open = false)} aria-label="닫기">×</button>
			</div>

			{#if type === 'number'}
				<div class="unit-hint">{unitHint}</div>
				<div class="field-grid">
					<label>
						<span>최소</span>
						<input
							bind:value={minInput}
							inputmode="decimal"
							placeholder={unit === '억원' ? '예: 1,000' : '이상'}
							onblur={formatMin}
						/>
					</label>
					<label>
						<span>최대</span>
						<input
							bind:value={maxInput}
							inputmode="decimal"
							placeholder={unit === '억원' ? '예: 10,000' : '이하'}
							onblur={formatMax}
						/>
					</label>
				</div>
				<label class="check-row">
					<input type="checkbox" bind:checked={excludeEmpty} />
					<span>빈 값 제외</span>
				</label>
			{:else if type === 'enum'}
				<div class="enum-list">
					{#each enumValues as value (value)}
						<label class="check-row">
							<input
								type="checkbox"
								checked={selectedValues.includes(value)}
								onchange={() => toggleValue(value)}
							/>
							<span>{value}</span>
						</label>
					{/each}
					{#if enumValues.length === 0}
						<div class="empty">선택 가능한 값이 없습니다.</div>
					{/if}
				</div>
			{:else}
				<label class="text-field">
					<span>포함</span>
					<input bind:value={textInput} placeholder="검색어" />
				</label>
				<label class="check-row">
					<input type="checkbox" bind:checked={excludeEmpty} />
					<span>빈 값 제외</span>
				</label>
			{/if}

			<div class="actions">
				<button type="button" class="clear" onclick={clear} disabled={!hasFilter}>해제</button>
				<button type="button" class="apply" onclick={apply}>적용</button>
			</div>
		</div>
	{/if}
</span>

<style>
	.filter-wrap {
		position: relative;
		display: inline-flex;
		align-items: center;
	}
	.filter-btn {
		width: 18px;
		height: 17px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		border: 1px solid transparent;
		border-radius: 3px;
		background: transparent;
		color: #64748b;
		line-height: 1;
		cursor: pointer;
		padding: 0;
	}
	.filter-btn:hover,
	.filter-btn.active {
		color: #fb923c;
		border-color: rgba(251, 146, 60, 0.45);
		background: rgba(251, 146, 60, 0.08);
	}
	.popover {
		position: absolute;
		top: 23px;
		right: 0;
		width: 236px;
		box-sizing: border-box;
		padding: 10px;
		background: #0f172a;
		border: 1px solid #334155;
		border-radius: 6px;
		box-shadow: 0 18px 40px -16px rgba(0, 0, 0, 0.8);
		z-index: 120;
		color: #cbd5e1;
		font-size: 11px;
		text-align: left;
	}
	.pop-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 9px;
		color: #f1f5f9;
		font-weight: 700;
	}
	.x-btn {
		border: none;
		background: transparent;
		color: #64748b;
		cursor: pointer;
		padding: 0;
		font-size: 14px;
	}
	.field-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
	}
	.unit-hint {
		margin-bottom: 8px;
		padding: 5px 7px;
		border: 1px solid rgba(30, 36, 51, 0.9);
		border-radius: 4px;
		background: rgba(5, 8, 17, 0.55);
		color: #94a3b8;
		font-size: 10px;
		line-height: 1.35;
	}
	label {
		display: flex;
		flex-direction: column;
		gap: 4px;
		min-width: 0;
		color: #94a3b8;
	}
	input {
		width: 100%;
		box-sizing: border-box;
		height: 26px;
		border: 1px solid #1e2433;
		border-radius: 4px;
		background: #050811;
		color: #e2e8f0;
		padding: 0 7px;
		font: inherit;
		outline: none;
	}
	input:focus {
		border-color: rgba(251, 146, 60, 0.6);
	}
	.text-field {
		margin-bottom: 8px;
	}
	.check-row {
		display: flex;
		flex-direction: row;
		align-items: center;
		gap: 7px;
		margin-top: 8px;
		color: #cbd5e1;
	}
	.check-row input {
		width: 13px;
		height: 13px;
		padding: 0;
		accent-color: #fb923c;
	}
	.enum-list {
		max-height: 180px;
		overflow-y: auto;
		padding-right: 2px;
	}
	.empty {
		color: #64748b;
		padding: 8px 0;
	}
	.actions {
		display: flex;
		justify-content: flex-end;
		gap: 6px;
		margin-top: 10px;
		padding-top: 8px;
		border-top: 1px solid #1e2433;
	}
	.actions button {
		height: 24px;
		border-radius: 3px;
		padding: 0 9px;
		font-size: 11px;
		font-weight: 700;
		cursor: pointer;
	}
	.clear {
		border: 1px solid #334155;
		background: transparent;
		color: #94a3b8;
	}
	.clear:disabled {
		opacity: 0.45;
		cursor: default;
	}
	.apply {
		border: 1px solid rgba(251, 146, 60, 0.65);
		background: rgba(251, 146, 60, 0.14);
		color: #fb923c;
	}
</style>
