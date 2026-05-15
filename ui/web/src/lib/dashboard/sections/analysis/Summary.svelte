<!--
	Analysis > 종합평가 — scorecard.items[area, grade] + piotroski + summaryFlags.
-->
<script>
	import { isFiniteNum } from "$lib/dashboard/chart/util.js";

	let { payload = null, loading = false } = $props();

	const items = $derived(Array.isArray(payload?.scorecard?.items) ? payload.scorecard.items : []);
	const profile = $derived(payload?.scorecard?.profile || "—");
	const pTotal = $derived(payload?.piotroski?.total);
	const pInterp = $derived(payload?.piotroski?.interpretation || "—");
	const pItems = $derived(Array.isArray(payload?.piotroski?.items) ? payload.piotroski.items : []);
	const summaryFlags = $derived(Array.isArray(payload?.summaryFlags) ? payload.summaryFlags : []);

	function gradeColor(g) {
		if (typeof g !== "string") return "var(--ed-text)";
		if (/^A/i.test(g) || g === "강함" || g === "우수") return "var(--ed-up)";
		if (/^[CDF]/i.test(g) || g === "약함" || g === "취약") return "var(--ed-down)";
		return "var(--ed-text-2)";
	}

	function piotroskiTone(total) {
		if (!isFiniteNum(total)) return { color: "var(--ed-text)", interp: "—" };
		if (total >= 7) return { color: "var(--ed-up)", interp: "strong" };
		if (total >= 4) return { color: "var(--ed-text-2)", interp: "moderate" };
		return { color: "var(--ed-down)", interp: "weak" };
	}

	const pTone = $derived(piotroskiTone(pTotal));
</script>

{#if loading}
	<div class="flex flex-col gap-3">{#each Array(3) as _}<div class="editorial-skeleton h-32"></div>{/each}</div>
{:else if !payload}
	<div class="ed-card" style="border-style: dashed;"><div class="ed-eyebrow">No data</div></div>
{:else}
	<div class="flex flex-col gap-3">
		<!-- Hero -->
		<div class="ed-card">
			<div class="flex items-baseline justify-between mb-3">
				<div class="ed-eyebrow">Overall Scorecard · {items.length} 영역</div>
				<div class="text-[10px]" style="color: var(--ed-text-3);">profile: {profile}</div>
			</div>
			<div class="flex items-baseline gap-10 flex-wrap">
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Piotroski</div>
					<div class="text-[40px] ed-num leading-none mt-1" style="color: {pTone.color}; font-family: var(--font-display);">
						{isFiniteNum(pTotal) ? pTotal : "—"}<span class="text-[16px]" style="color: var(--ed-text-3);">/9</span>
					</div>
					<div class="text-[11px] mt-1" style="color: {pTone.color};">{pInterp}</div>
				</div>
				<div>
					<div class="text-[10px] uppercase tracking-wide" style="color: var(--ed-text-3);">Profile</div>
					<div class="text-[24px] font-bold leading-none mt-1" style="color: var(--ed-text); font-family: var(--font-display);">{profile}</div>
				</div>
			</div>
		</div>

		<!-- Scorecard areas -->
		{#if items.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-3">영역별 등급</div>
				<div class="grid grid-cols-2 md:grid-cols-4 gap-2">
					{#each items as it}
						<div class="rounded border p-2.5" style="border-color: var(--ed-line); background: var(--ed-surface-2);">
							<div class="text-[10px] uppercase tracking-wide truncate" style="color: var(--ed-text-3);">{it.area ?? "—"}</div>
							<div class="text-[18px] font-medium mt-1" style="color: {gradeColor(it.grade)}; font-family: var(--font-display);">{it.grade ?? "—"}</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Piotroski 9 signals -->
		{#if pItems.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-3">Piotroski 9 시그널</div>
				<ul class="grid grid-cols-1 md:grid-cols-3 gap-1.5">
					{#each pItems as p}
						<li class="grid grid-cols-[1fr_24px] items-center gap-2 px-2.5 py-1.5 rounded border text-[12px]"
							style="border-color: var(--ed-line); background: var(--ed-surface-2);">
							<span style="color: var(--ed-text);">{p.signal ?? "—"}</span>
							<span class="text-right" style="color: {p.pass ? 'var(--ed-up)' : 'var(--ed-down)'};">{p.pass ? "✓" : "✗"}</span>
						</li>
					{/each}
				</ul>
			</div>
		{/if}

		{#if summaryFlags.length > 0}
			<div class="ed-card">
				<div class="ed-eyebrow mb-2">Summary Flags ({summaryFlags.length})</div>
				<ul class="flex flex-col gap-1.5 text-[12px]">{#each summaryFlags as f}<li style="color: var(--ed-text-2);">{typeof f === 'string' ? f : (f.message || JSON.stringify(f))}</li>{/each}</ul>
			</div>
		{/if}
	</div>
{/if}
