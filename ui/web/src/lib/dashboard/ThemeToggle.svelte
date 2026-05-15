<!--
	ThemeToggle — dark / light / auto 3-state cycle button.
	아이콘만, compact. tooltip 으로 next state 안내.
-->
<script>
	import { Moon, Sun, Monitor } from "lucide-svelte";
	import { getTheme } from "$lib/stores/theme.svelte.js";
	import { cn } from "$lib/utils.js";

	let { class: klass = "" } = $props();
	const theme = getTheme();

	const label = $derived(
		theme.value === "dark"
			? "라이트로 전환"
			: theme.value === "light"
				? "자동(시스템)으로 전환"
				: "다크로 전환"
	);
</script>

<button
	type="button"
	class={cn(
		"inline-flex items-center justify-center h-8 w-8 rounded-md border border-border bg-card text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors",
		klass
	)}
	title={label}
	aria-label={label}
	onclick={() => theme.cycle()}
>
	{#if theme.value === "dark"}
		<Moon size={14} />
	{:else if theme.value === "light"}
		<Sun size={14} />
	{:else}
		<Monitor size={14} />
	{/if}
</button>
