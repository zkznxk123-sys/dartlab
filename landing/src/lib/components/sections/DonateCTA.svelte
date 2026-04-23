<script lang="ts">
	// @ts-nocheck
	/**
	 * 공통 후원 CTA — dartlab 전 페이지 통일.
	 *
	 * Variants:
	 *   - 'full'    : 좌 intro + 우 3-버튼 액션 그리드 (대시보드·홈 풀버전)
	 *   - 'compact' : 한 줄 카드 (아이콘 + 제목 + 후원 버튼). 블로그·독스 하단용
	 *   - 'inline'  : 배너 띠 (텍스트 + 후원 버튼 하나). Footer 바로 위
	 *
	 * 모든 버튼은 brand.ts 의 URL 을 사용 — 중복 금지.
	 */
	import { brand } from '$lib/brand';

	let {
		variant = 'compact',
		message,
		subtitle,
		showMap = false,
		showRepo = true,
		mapHref = '/map'
	}: {
		variant?: 'full' | 'compact' | 'inline';
		message?: string;
		subtitle?: string;
		showMap?: boolean;
		showRepo?: boolean;
		mapHref?: string;
	} = $props();

	const DEFAULT_TITLE = 'dartlab은 무료·오픈소스입니다';
	const DEFAULT_SUB =
		'DART 전 상장사 공시 · 공급망 네트워크 · 블로그 심층분석 — 모두 무료. 후원은 개발 가속에 쓰입니다.';

	const title = $derived(message ?? DEFAULT_TITLE);
	const sub = $derived(subtitle ?? DEFAULT_SUB);
</script>

{#if variant === 'full'}
	<section class="dl-donate dl-donate--full container">
		<div class="dl-donate-row">
			<div class="dl-donate-intro">
				<div class="dl-donate-kicker">FREE · OPEN SOURCE</div>
				<h3>{title}</h3>
				<p>{sub}</p>
				<div class="dl-donate-pills">
					<span class="pill">DART 전 상장사</span>
					<span class="pill">공급망 네트워크</span>
					<span class="pill">블로그 심층분석</span>
				</div>
			</div>

			<div class="dl-donate-actions">
				{#if showMap}
					<a href={mapHref} class="dl-donate-card">
						<div class="dl-dc-icon">📍</div>
						<div class="dl-dc-body">
							<div class="dl-dc-title">산업지도</div>
							<div class="dl-dc-sub">공급망·경쟁사 네트워크 탐색</div>
						</div>
						<div class="dl-dc-arrow">→</div>
					</a>
				{/if}

				<a
					href={brand.coffee}
					target="_blank"
					rel="noopener"
					class="dl-donate-card dl-donate-card--donate"
				>
					<div class="dl-dc-icon">☕</div>
					<div class="dl-dc-body">
						<div class="dl-dc-title">Buy Me A Coffee</div>
						<div class="dl-dc-sub">무료 제공 유지를 위한 후원</div>
					</div>
					<div class="dl-dc-arrow">→</div>
				</a>

				{#if showRepo}
					<a href={brand.repo} target="_blank" rel="noopener" class="dl-donate-card">
						<div class="dl-dc-icon">⭐</div>
						<div class="dl-dc-body">
							<div class="dl-dc-title">GitHub 에서 별 주기</div>
							<div class="dl-dc-sub">소스코드 · 이슈 · 로드맵</div>
						</div>
						<div class="dl-dc-arrow">→</div>
					</a>
				{/if}
			</div>
		</div>
	</section>
{:else if variant === 'compact'}
	<section class="dl-donate dl-donate--compact">
		<div class="dl-donate-compact-inner">
			<div class="dl-donate-compact-icon">☕</div>
			<div class="dl-donate-compact-body">
				<div class="dl-donate-compact-title">{title}</div>
				<div class="dl-donate-compact-sub">{sub}</div>
			</div>
			<a href={brand.coffee} target="_blank" rel="noopener" class="dl-donate-btn">
				<span>후원</span>
				<span>→</span>
			</a>
		</div>
	</section>
{:else}
	<!-- inline -->
	<section class="dl-donate dl-donate--inline">
		<div class="dl-donate-inline-inner container">
			<span class="dl-donate-inline-dot" aria-hidden="true"></span>
			<span class="dl-donate-inline-text">
				<strong>dartlab 은 무료·오픈소스.</strong>
				계속 유지되도록 후원해주세요.
			</span>
			<a href={brand.coffee} target="_blank" rel="noopener" class="dl-donate-btn">
				<span>☕ 후원</span>
			</a>
			{#if showRepo}
				<a href={brand.repo} target="_blank" rel="noopener" class="dl-donate-btn dl-donate-btn--ghost">
					<span>⭐ GitHub</span>
				</a>
			{/if}
		</div>
	</section>
{/if}

<style>
	.dl-donate {
		position: relative;
		z-index: 1;
	}

	/* ── FULL variant ── */
	.dl-donate--full {
		padding: 48px 32px 64px;
	}
	.dl-donate-row {
		display: grid;
		grid-template-columns: 1fr 1.2fr;
		gap: 40px;
		align-items: start;
	}
	.dl-donate-kicker {
		font-size: 11px;
		font-weight: 700;
		letter-spacing: 0.14em;
		background: var(--grad-heat);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		margin-bottom: 10px;
	}
	.dl-donate-intro h3 {
		margin: 0 0 12px;
		font-size: 30px;
		letter-spacing: -0.02em;
		color: var(--text);
		line-height: 1.25;
	}
	.dl-donate-intro p {
		margin: 0 0 16px;
		color: var(--text-mid);
		line-height: 1.6;
		max-width: 460px;
	}
	.dl-donate-pills {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.dl-donate-actions {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.dl-donate-card {
		display: grid;
		grid-template-columns: 44px 1fr 24px;
		gap: 14px;
		align-items: center;
		padding: 16px 18px;
		border: 1px solid var(--border);
		border-radius: var(--r-lg);
		background: var(--card);
		transition: all 0.2s;
		text-decoration: none;
	}
	.dl-donate-card:hover {
		border-color: var(--border-accent);
		transform: translateY(-1px);
	}
	.dl-donate-card--donate {
		background: linear-gradient(90deg, rgba(234, 70, 71, 0.08), transparent);
	}
	.dl-donate-card--donate:hover {
		background: linear-gradient(90deg, rgba(234, 70, 71, 0.14), rgba(251, 146, 60, 0.06));
	}
	.dl-dc-icon {
		width: 44px;
		height: 44px;
		display: grid;
		place-items: center;
		border-radius: 10px;
		background: var(--grad-heat-soft);
		border: 1px solid var(--border-accent);
		font-size: 22px;
	}
	.dl-dc-title {
		font-size: 15px;
		font-weight: 600;
		color: var(--text);
		margin-bottom: 3px;
	}
	.dl-dc-sub {
		font-size: 12px;
		color: var(--text-dim);
	}
	.dl-dc-arrow {
		font-size: 20px;
		color: var(--orange);
	}
	@media (max-width: 900px) {
		.dl-donate-row {
			grid-template-columns: 1fr;
			gap: 24px;
		}
	}

	/* ── COMPACT variant ── */
	.dl-donate--compact {
		margin: 40px auto 24px;
		max-width: 760px;
		padding: 0 24px;
	}
	.dl-donate-compact-inner {
		display: flex;
		align-items: center;
		gap: 14px;
		padding: 16px 20px;
		border: 1px solid var(--border);
		border-radius: var(--r-lg);
		background: linear-gradient(90deg, rgba(234, 70, 71, 0.06), rgba(251, 146, 60, 0.02));
		transition: all 0.2s;
	}
	.dl-donate-compact-inner:hover {
		border-color: var(--border-accent);
	}
	.dl-donate-compact-icon {
		width: 40px;
		height: 40px;
		display: grid;
		place-items: center;
		border-radius: 10px;
		background: var(--grad-heat-soft);
		border: 1px solid var(--border-accent);
		font-size: 20px;
		flex-shrink: 0;
	}
	.dl-donate-compact-body {
		flex: 1;
		min-width: 0;
	}
	.dl-donate-compact-title {
		font-size: 14px;
		font-weight: 600;
		color: var(--text);
		margin-bottom: 2px;
	}
	.dl-donate-compact-sub {
		font-size: 12px;
		color: var(--text-mid);
		line-height: 1.4;
	}
	@media (max-width: 640px) {
		.dl-donate-compact-inner {
			flex-wrap: wrap;
		}
		.dl-donate-compact-sub {
			font-size: 11px;
		}
	}

	/* ── INLINE variant ── */
	.dl-donate--inline {
		border-top: 1px solid var(--border);
		border-bottom: 1px solid var(--border);
		padding: 18px 0;
		background: linear-gradient(180deg, rgba(234, 70, 71, 0.03), transparent);
	}
	.dl-donate-inline-inner {
		display: flex;
		align-items: center;
		gap: 14px;
		flex-wrap: wrap;
	}
	.dl-donate-inline-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--grad-heat);
		flex-shrink: 0;
	}
	.dl-donate-inline-text {
		flex: 1;
		font-size: 14px;
		color: var(--text-mid);
		min-width: 200px;
	}
	.dl-donate-inline-text strong {
		color: var(--text);
		font-weight: 600;
	}

	/* ── Shared buttons ── */
	.dl-donate-btn {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 8px 14px;
		border-radius: 8px;
		background: var(--grad-heat);
		color: #fff;
		font-size: 13px;
		font-weight: 600;
		text-decoration: none;
		transition: filter 0.15s;
		white-space: nowrap;
		flex-shrink: 0;
	}
	.dl-donate-btn:hover {
		filter: brightness(1.08);
	}
	.dl-donate-btn--ghost {
		background: transparent;
		color: var(--text);
		border: 1px solid var(--border);
	}
	.dl-donate-btn--ghost:hover {
		background: rgba(255, 255, 255, 0.04);
		border-color: var(--border-hi);
		filter: none;
	}
</style>
