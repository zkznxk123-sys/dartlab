<!--
  BrandSwitch — 브랜드 색 테마 아이콘(팝오버). 전 표면 공유 SSOT 컨트롤(프레임워크 무관, document 직접).
  SNS 아이콘 행에 인라인으로 붙는다(터미널 topbar · 카드 페이지 · 랜딩 Header 동일).
  documentElement 에 data-brand(프리셋)·data-conv(상승색)·--p-accent-500/--p-red-500(커스텀) 세팅 →
  tokens.css SSOT 를 통해 랜딩·터미널·뷰어·report·카드가 리빌드 없이 실시간 리테마. localStorage 영속.
  아이콘 옆 점(swatch)은 현재 강조색.
-->
<script lang="ts">
	let { label = '브랜드 색 테마' }: { label?: string } = $props();

	const hasDoc = typeof document !== 'undefined';

	// 프리셋 = primary(메인 랜딩 지배색)+accent 동시. tokens.css :root[data-brand=...] 와 1:1.
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
		if (!hasDoc) return;
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
		if (!hasDoc) return;
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

	const swatch = $derived(brand === 'custom' ? custom : (PRESETS.find((p) => p.id === brand)?.hex ?? '#ff3f6f'));

	if (hasDoc) {
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
		if (!(e.target as HTMLElement)?.closest?.('.bswWrap')) open = false;
	}
</script>

<svelte:window onclick={open ? onWindowClick : undefined} />

<div class="bswWrap">
	<button class="bswIcon" onclick={() => (open = !open)} title={label} aria-label={label} aria-expanded={open}>
		<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
			<circle cx="13.5" cy="6.5" r=".5" fill="currentColor" />
			<circle cx="17.5" cy="10.5" r=".5" fill="currentColor" />
			<circle cx="8.5" cy="7.5" r=".5" fill="currentColor" />
			<circle cx="6.5" cy="12.5" r=".5" fill="currentColor" />
			<path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z" />
		</svg>
		<span class="bswDot" style="background:{swatch}"></span>
	</button>
	{#if open}
		<div class="bswPop">
			<div class="bswHead">브랜드색 — 한 곳에서 전 화면(메인 랜딩 포함) 적용</div>
			<div class="bswRow">
				{#each PRESETS as p (p.id)}
					<button class="bswChip" class:on={brand === p.id} style="--sw:{p.hex}" onclick={() => pickPreset(p.id)}>{p.name}</button>
				{/each}
			</div>
			<label class="bswCustom">
				<span>커스텀</span>
				<input type="color" value={custom} oninput={(e) => pickCustom(e.currentTarget.value)} />
			</label>
			<button class="bswConv" class:on={greenUp} onclick={toggleConv}>
				상승색 <b>{greenUp ? '초록(green-up)' : '빨강(KR)'}</b>
			</button>
		</div>
	{/if}
</div>

<style>
	.bswWrap {
		position: relative;
		display: inline-flex;
	}
	.bswIcon {
		position: relative;
		width: 28px;
		height: 28px;
		border-radius: 6px;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		color: var(--dl-ink-dim, #8a93a3);
		background: transparent;
		border: 0;
		cursor: pointer;
		transition: color 0.15s, background 0.15s;
	}
	.bswIcon:hover {
		color: var(--dl-ink, #e8eaef);
		background: rgba(255, 255, 255, 0.08);
	}
	.bswDot {
		position: absolute;
		right: 3px;
		bottom: 3px;
		width: 7px;
		height: 7px;
		border-radius: 50%;
		box-shadow: 0 0 0 1.5px var(--dl-bg-base, #0f0f10);
	}
	.bswPop {
		position: absolute;
		top: calc(100% + 6px);
		right: 0;
		z-index: 300;
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 10px;
		width: 234px;
		background: var(--dl-bg-modal, #25272d);
		border: 1px solid var(--dl-line-strong, rgba(255, 255, 255, 0.12));
		border-radius: 10px;
		box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
		font-family: var(--dl-font-ui, sans-serif);
	}
	.bswHead {
		font-size: 10px;
		color: var(--dl-ink-dim, #8a93a3);
	}
	.bswRow {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}
	.bswChip {
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
	.bswChip::before {
		content: '';
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: var(--sw);
	}
	.bswChip.on {
		border-color: var(--sw);
		background: color-mix(in srgb, var(--sw) 14%, transparent);
	}
	.bswCustom {
		display: flex;
		align-items: center;
		justify-content: space-between;
		font-size: 11px;
		color: var(--dl-ink-mute, #a3a8b3);
	}
	.bswCustom input {
		width: 42px;
		height: 24px;
		border: none;
		background: none;
		cursor: pointer;
		padding: 0;
	}
	.bswConv {
		padding: 5px 8px;
		border-radius: 6px;
		font-size: 11px;
		color: var(--dl-ink, #e8eaef);
		background: transparent;
		border: 1px solid var(--dl-line, rgba(255, 255, 255, 0.08));
		cursor: pointer;
		text-align: left;
	}
	.bswConv.on {
		border-color: var(--dl-good, #34d399);
		color: var(--dl-good, #34d399);
	}
</style>
