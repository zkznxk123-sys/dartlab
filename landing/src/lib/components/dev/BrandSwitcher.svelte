<!--
  BrandSwitcher — dev 전용 브랜드 색 시도 위젯 (프로덕션 번들에서 제거됨, {#if dev}).
  강조 프리셋/커스텀 색을 documentElement 에 세팅(--p-accent-500 seed 또는 data-brand 속성) →
  tokens.css SSOT 를 통해 랜딩·터미널·scan·map·viewer·report·카드가 리빌드 없이 실시간 리테마.
  상승색 컨벤션(KR 빨강-up ↔ green-up)은 직교 속성 data-conv 로 별도 토글. 선택은 localStorage 영속.
-->
<script lang="ts">
	import { browser, dev } from '$app/environment';

	const PRESETS = [
		{ id: '', label: '핑크', hex: '#ff3f6f' },
		{ id: 'amber', label: '앰버', hex: '#fb923c' },
		{ id: 'gold', label: '골드', hex: '#f5b301' },
		{ id: 'teal', label: '틸', hex: '#2dd4bf' },
		{ id: 'violet', label: '바이올렛', hex: '#a78bfa' }
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
</script>

{#if dev}
	<div class="bs">
		<button class="bsToggle" onclick={() => (open = !open)} title="브랜드 색 시도 (dev 전용)" aria-label="브랜드 색 시도">🎨</button>
		{#if open}
			<div class="bsPanel">
				<div class="bsHead">강조색 — 한 곳에서 전 표면 시도 <span class="bsDev">dev</span></div>
				<div class="bsRow">
					{#each PRESETS as p (p.id)}
						<button class="bsChip" class:on={brand === p.id} style="--sw:{p.hex}" onclick={() => pickPreset(p.id)}>{p.label}</button>
					{/each}
				</div>
				<label class="bsCustom">
					<span>커스텀</span>
					<input type="color" value={custom} oninput={(e) => pickCustom(e.currentTarget.value)} />
				</label>
				<button class="bsConv" class:on={greenUp} onclick={toggleConv}>
					상승색: <b>{greenUp ? '초록 (green-up)' : '빨강 (KR)'}</b>
				</button>
			</div>
		{/if}
	</div>
{/if}

<style>
	.bs {
		position: fixed;
		left: 12px;
		bottom: 12px;
		z-index: 99999;
		font-family: var(--dl-font-mono, monospace);
	}
	.bsToggle {
		width: 34px;
		height: 34px;
		border-radius: 8px;
		background: var(--dl-bg-modal, #25272d);
		border: 1px solid var(--dl-line-strong, rgba(255, 255, 255, 0.12));
		font-size: 16px;
		cursor: pointer;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.45);
	}
	.bsPanel {
		margin-top: 8px;
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 10px;
		width: 232px;
		background: var(--dl-bg-modal, #25272d);
		border: 1px solid var(--dl-line-strong, rgba(255, 255, 255, 0.12));
		border-radius: 10px;
		box-shadow: 0 8px 28px rgba(0, 0, 0, 0.5);
	}
	.bsHead {
		font-size: 10px;
		color: var(--dl-ink-dim, #6b7280);
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.bsDev {
		font-size: 8px;
		padding: 0 4px;
		border-radius: 3px;
		background: var(--dl-accent-soft, rgba(255, 63, 111, 0.12));
		color: var(--dl-accent, #ff3f6f);
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
		border: 1px solid var(--dl-line, rgba(255, 255, 255, 0.06));
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
		border: 1px solid var(--dl-line, rgba(255, 255, 255, 0.06));
		cursor: pointer;
		text-align: left;
	}
	.bsConv.on {
		border-color: var(--dl-good, #34d399);
		color: var(--dl-good, #34d399);
	}
</style>
