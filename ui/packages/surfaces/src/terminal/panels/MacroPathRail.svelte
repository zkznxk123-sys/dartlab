<script lang="ts">
	import type { Lang } from '../lib/types';
	import type { MacroPathSectorNode, MacroPathView } from '../lib/macroLens';

	interface Props {
		view: MacroPathView;
		lang: Lang;
		mode?: 'compact' | 'full';
		onSector?: (industryId: string) => void;
	}
	let { view, lang, mode = view.mode, onSector }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	const sectorLabel = (s: MacroPathSectorNode) => lang === 'en' ? s.labelEn : s.labelKr;
	const label = (s: MacroPathSectorNode) => s.blended == null ? T('미산출', 'missing') : s.blended.toFixed(2);
	const isClickable = (s: MacroPathSectorNode) => !!s.industryId;
	function activate(s: MacroPathSectorNode) {
		if (s.industryId) onSector?.(s.industryId);
	}
	function onKey(e: KeyboardEvent, s: MacroPathSectorNode) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			activate(s);
		}
	}
	const compactSectors = $derived(view.sectorNodes.filter((s) => s.key !== 'all').slice(0, 6));
	const allLinks = $derived(view.allSectorLinks.slice(0, 2));
	const fullLinks = $derived([...view.links, ...view.allSectorLinks]);
</script>

<section class={'mpr ' + mode} aria-label="Macro path rail">
	<div class="mprHead">
		<span>{T('전파', 'Path')}</span>
		<b>{T('동행≠인과', 'co-move≠causation')}</b>
		<em>{view.asOf ?? '—'}</em>
	</div>
	{#if mode === 'compact'}
		<div class="mprChips">
			{#each compactSectors as s (s.key)}
				<button class={'mprChip ' + s.tone} class:on={s.active} disabled={!isClickable(s)} onclick={() => activate(s)} onkeydown={(e) => onKey(e, s)} title={`${sectorLabel(s)} · ${s.tailwindLabelKr} · ${label(s)}`}>
					<span>{sectorLabel(s)}</span><em>{label(s)}</em>
				</button>
			{/each}
			{#each allLinks as link (link.id)}
				<span class={'mprChip all ' + link.styleClass} title={link.note}><span>{T('전 섹터', 'All')}</span><em>{link.evidenceLabel}</em></span>
			{/each}
		</div>
		<div class="mprCaption">{T(view.captionKr, view.captionEn)}</div>
	{:else}
		<div class="mprLegend">
			<span class="observed">OBS</span><span class="prior">PRIOR</span><span class="template">TPL</span><span class="blocked">LOCK</span>
		</div>
		<div class="mprRows">
			{#each fullLinks as link (link.id)}
				<div class={'mprRow ' + link.styleClass + ' ' + link.signClass} class:active={link.active} style={`--mpr-op:${link.opacity}`}>
					<div class="mprDriver">
						<span>{link.market}</span>
						<b>{link.driverLabel}</b>
						<em>{link.signLabel} · {link.evidenceLabel}</em>
					</div>
					<div class="mprChannel"><b>{T(link.channelLabelKr, link.channelLabelEn)}</b><em>{link.financialLine}</em></div>
					<div class="mprSectors">
						{#each link.sectorNodes as s (s.key)}
							<button class={'mprChip ' + s.tone} class:on={s.active} disabled={!isClickable(s)} onclick={() => activate(s)} onkeydown={(e) => onKey(e, s)} title={`${sectorLabel(s)} · ${s.tailwindLabelKr} · ${label(s)}`}>
								<span>{sectorLabel(s)}</span><em>{s.key === 'all' ? link.evidenceLabel : label(s)}</em>
							</button>
						{/each}
					</div>
				</div>
			{/each}
		</div>
		<div class="mprCaption">{T(view.captionKr, view.captionEn)}</div>
	{/if}
</section>

<style>
	.mpr { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
	.mprHead { display: flex; align-items: center; gap: 6px; min-width: 0; }
	.mprHead span { color: var(--amber); font-family: var(--cond); font-size: 9px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; }
	.mprHead b { color: var(--fg); font-size: 9.5px; font-weight: 700; }
	.mprHead em { margin-left: auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--dim); font-family: var(--mono); font-style: normal; font-size: 8.5px; }
	.mprChips, .mprSectors { display: flex; flex-wrap: wrap; gap: 4px; min-width: 0; }
	.mprChip { max-width: 100%; min-width: 0; display: inline-flex; align-items: center; gap: 4px; border: 1px solid var(--bd); border-radius: 3px; background: var(--dl-bg-deep); color: var(--dim); padding: 2px 5px; font-size: 9px; cursor: pointer; }
	.mprChip span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mprChip em { flex: 0 0 auto; color: var(--dimmer); font-family: var(--mono); font-style: normal; font-size: 8px; }
	.mprChip.good, .mprChip.up { border-color: rgba(52,211,153,.32); color: var(--up); }
	.mprChip.down { border-color: rgba(240,97,111,.34); color: var(--dn); }
	.mprChip.neutral { color: var(--dim); }
	.mprChip.all { cursor: default; color: var(--amber); border-color: rgba(251,146,60,.32); }
	.mprChip.on { outline: 1px solid var(--amber); outline-offset: -1px; }
	.mprChip:disabled { cursor: default; opacity: .72; }
	.mprCaption { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--dim); font-size: 9px; }
	.mpr.full { border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.014); padding: 10px; }
	.mprLegend { display: flex; flex-wrap: wrap; gap: 5px; }
	.mprLegend span { border: 1px solid var(--bd); border-radius: 999px; padding: 2px 7px; color: var(--dim); font-family: var(--mono); font-size: 8.5px; }
	.mprLegend .observed { color: var(--up); border-color: rgba(52,211,153,.4); }
	.mprLegend .prior { color: var(--amber); border-color: rgba(251,146,60,.4); }
	.mprLegend .template { border-style: dashed; }
	.mprLegend .blocked { color: var(--dn); border-style: dotted; }
	.mprRows { display: grid; gap: 6px; min-width: 0; }
	.mprRow { display: grid; grid-template-columns: minmax(120px, .85fr) minmax(110px, .9fr) minmax(0, 1.5fr); gap: 8px; align-items: center; min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: rgba(255,255,255,.012); padding: 7px; opacity: var(--mpr-op, 1); }
	.mprRow.template { border-style: dashed; }
	.mprRow.blocked { border-style: dotted; opacity: .68; }
	.mprRow.active { outline: 1px solid var(--amber); outline-offset: -1px; }
	.mprDriver, .mprChannel { min-width: 0; display: grid; gap: 2px; }
	.mprDriver span, .mprDriver b, .mprDriver em, .mprChannel b, .mprChannel em { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mprDriver span { color: var(--amber); font-family: var(--mono); font-size: 8px; }
	.mprDriver b, .mprChannel b { color: var(--fg); font-size: 10.5px; }
	.mprDriver em, .mprChannel em { color: var(--dim); font-style: normal; font-size: 9px; }
	.mprRow.pos .mprDriver em { color: var(--up); }
	.mprRow.neg .mprDriver em { color: var(--dn); }
	.mprRow.mix .mprDriver em { color: var(--warn); }
	@media (max-width: 760px) {
		.mprRow { grid-template-columns: 1fr; align-items: start; }
	}
</style>
