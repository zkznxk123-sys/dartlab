<!--
  BrandSwitcher — 강조색 테마 아이콘(팝오버). SNS 아이콘 행에 인라인으로 붙거나(Header),
  고정 컨테이너로 띄울 수 있다(터미널 /lab). documentElement 에 data-brand / data-conv /
  --p-accent-500(커스텀) 세팅 → tokens.css SSOT 를 통해 랜딩·터미널·뷰어·report·카드가
  리빌드 없이 실시간 리테마. 선택은 localStorage 영속.
  아이콘 버튼은 현재 강조색을 스워치(원형)로 보여줘 직관적.
-->
<script lang="ts">
	import { browser } from '$app/environment';
	import { Palette } from 'lucide-svelte';

	// title/aria 라벨만 props (배치는 부모가 정함)
	let { label = '브랜드 색 테마' }: { label?: string } = $props();

	const PRESETS = [
		{ id: '', name: '핑크', hex: '#ff3f6f' },
		{ id: 'amber', name: '앰버', hex: '#fb923c' },
		{ id: 'gold', name: '골드', hex: '#f5b301' },
		{ id: 'teal', name: '틸', hex: '#2dd4bf' },
		{ id: 'violet', name: '바이올렛', hex: '#a78bfa' }
	];

	let open = $state(false);
	let brand = $state(''); // '' | preset id | 'custom'
	let custom = $state('#ff3f6f');
	let greenUp = $state(false);

	function hexToRgb(h: string): string {
		const n = parseInt(h.replace('#', ''), 16);
		return `${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}`;
	}
	function applyAccent() {
		const el = document.documentElement;
		if (brand === 'custom') {
			el.style.setProperty('--p-accent-500', custom);
			el.style.setProperty('--p-accent-500-rgb', hexToRgb(custom));
			el.removeAttribute('data-brand');
		} else {
			el.style.removeProperty('--p-accent-500');
			el.style.removeProperty('--p-accent-500-rgb');
			if (brand) el.dataset.brand = brand;
			else el.removeAttribute('data-brand');
		}
	}
	function applyConv() {
		const el = document.documentElement;
		if (greenUp) el.dataset.conv = 'green-up';
		else el.removeAttribute('data-conv');
	}
	function persist() {
		try {
			localStorage.setItem('dl-brand', brand === 'custom' ? `custom:${custom}` : brand);
			localStorage.setItem('dl-conv', greenUp ? 'green-up' : '');
		} catch {
			/* noop */
		}
	}
	function pickPreset(id: string) {
		brand = id;
		applyAccent();
		persist();
	}
	function pickCustom(v: string) {
		custom = v;
		brand = 'custom';
		applyAccent();
		persist();
	}
	function toggleConv() {
		greenUp = !greenUp;
		applyConv();
		persist();
	}

	// 현재 강조색 스워치(아이콘 옆 점) — 프리셋/커스텀 반영
	const swatch = $derived(brand === 'custom' ? custom : (PRESETS.find((p) => p.id === brand)?.hex ?? '#ff3f6f'));

	if (browser) {
		try {
			const b = localStorage.getItem('dl-brand') || '';
			if (b.startsWith('custom:')) {
				custom = b.slice(7);
				brand = 'custom';
			} else {
				brand = b;
			}
			greenUp = localStorage.getItem('dl-conv') === 'green-up';
		} catch {
			/* noop */
		}
		applyAccent();
		applyConv();
	}

	function onWindowClick(e: MouseEvent) {
		if (!(e.target as HTMLElement)?.closest?.('.bsWrap')) open = false;
	}
</script>

<svelte:window onclick={open ? onWindowClick : undefined} />

<div class="bsWrap">
	<button class="bsIcon" onclick={() => (open = !open)} title={label} aria-label={label} aria-expanded={open}>
		<Palette size={15} strokeWidth={1.75} />
		<span class="bsDot" style="background:{swatch}"></span>
	</button>
	{#if open}
		<div class="bsPop">
			<div class="bsHead">브랜드색 — 한 곳에서 전 화면(메인 랜딩 포함) 적용</div>
			<div class="bsRow">
				{#each PRESETS as p (p.id)}
					<button class="bsChip" class:on={brand === p.id} style="--sw:{p.hex}" onclick={() => pickPreset(p.id)}>{p.name}</button>
				{/each}
			</div>
			<label class="bsCustom">
				<span>커스텀</span>
				<input type="color" value={custom} oninput={(e) => pickCustom(e.currentTarget.value)} />
			</label>
			<button class="bsConv" class:on={greenUp} onclick={toggleConv}>
				상승색 <b>{greenUp ? '초록(green-up)' : '빨강(KR)'}</b>
			</button>
		</div>
	{/if}
</div>

<style>
	.bsWrap {
		position: relative;
		display: inline-flex;
	}
	.bsIcon {
		position: relative;
		width: 28px;
		height: 28px;
		border-radius: 6px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		color: var(--dl-ink-dim, #6b7280);
		background: transparent;
		border: 0;
		cursor: pointer;
		transition: color 0.15s, background 0.15s;
	}
	.bsIcon:hover {
		color: var(--dl-ink, #e8eaef);
		background: rgba(255, 255, 255, 0.06);
	}
	.bsDot {
		position: absolute;
		right: 3px;
		bottom: 3px;
		width: 7px;
		height: 7px;
		border-radius: 50%;
		box-shadow: 0 0 0 1.5px var(--dl-bg-base, #0f0f10);
	}
	.bsPop {
		position: absolute;
		top: calc(100% + 6px);
		right: 0;
		z-index: 200;
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 10px;
		width: 230px;
		background: var(--dl-bg-modal, #25272d);
		border: 1px solid var(--dl-line-strong, rgba(255, 255, 255, 0.12));
		border-radius: 10px;
		box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
		font-family: var(--dl-font-ui, sans-serif);
	}
	.bsHead {
		font-size: 10px;
		color: var(--dl-ink-dim, #6b7280);
	}
	.bsRow {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}
	.bsChip {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		padding: 3px 8px 3px 6px;
		border-radius: 6px;
		font-size: 11px;
		color: var(--dl-ink, #e8eaef);
		background: transparent;
		border: 1px solid var(--dl-line, rgba(255, 255, 255, 0.08));
		cursor: pointer;
	}
	.bsChip::before {
		content: '';
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: var(--sw);
	}
	.bsChip.on {
		border-color: var(--sw);
		background: color-mix(in srgb, var(--sw) 14%, transparent);
	}
	.bsCustom {
		display: flex;
		align-items: center;
		justify-content: space-between;
		font-size: 11px;
		color: var(--dl-ink-mute, #a3a8b3);
	}
	.bsCustom input {
		width: 42px;
		height: 24px;
		border: none;
		background: none;
		cursor: pointer;
		padding: 0;
	}
	.bsConv {
		padding: 5px 8px;
		border-radius: 6px;
		font-size: 11px;
		color: var(--dl-ink, #e8eaef);
		background: transparent;
		border: 1px solid var(--dl-line, rgba(255, 255, 255, 0.08));
		cursor: pointer;
		text-align: left;
	}
	.bsConv.on {
		border-color: var(--dl-good, #34d399);
		color: var(--dl-good, #34d399);
	}
</style>
