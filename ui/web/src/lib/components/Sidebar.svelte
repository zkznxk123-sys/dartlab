<script>
	import { cn } from "$lib/utils.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import { MoreHorizontal, Pin, Plus, Search, Settings, Trash2 } from "lucide-svelte";

	let {
		conversations = [],
		activeId = null,
		open = true,
		width = 260,
		version = "",
		onNewChat,
		onSelect,
		onDelete,
		onDeleteAll,
		onRename,
		onDuplicate,
		onTogglePin,
		onOpenSettings,
	} = $props();

	let searchQuery = $state("");
	let editingId = $state(null);
	let editTitle = $state("");
	let openMenuId = $state(null);

	function toggleMenu(id, e) {
		e?.stopPropagation();
		openMenuId = openMenuId === id ? null : id;
	}
	function closeMenu() { openMenuId = null; }

	let filteredConversations = $derived(
		searchQuery.trim()
			? conversations.filter((c) => c.title.toLowerCase().includes(searchQuery.toLowerCase()))
			: conversations
	);
	let pinnedItems = $derived(filteredConversations.filter((c) => c.pinned));
	let unpinnedItems = $derived(filteredConversations.filter((c) => !c.pinned));
</script>

<aside
	class="surface-panel flex flex-col h-full bg-dl-bg-darker border-r border-dl-border transition-all duration-300 flex-shrink-0 overflow-hidden"
	style="{open ? `width: ${width}px` : 'width: 52px'}"
>
	{#if open}
		<div class="flex flex-col h-full" style="min-width: {width}px">
			<!-- Brand: 워드마크. 아바타 폐기. -->
			<div class="px-4 pt-4 pb-3">
				<div class="text-[15px] font-bold text-dl-text tracking-tight">DartLab</div>
				<div class="text-[10px] uppercase tracking-[0.16em] text-dl-text-dim">Analysis Workspace</div>
			</div>

			<!-- New Chat + Delete All -->
			<div class="px-3 pb-2">
				<div class="flex items-center gap-2">
					<Button variant="secondary" class="flex-1 justify-start gap-2" onclick={onNewChat}>
						<Plus size={16} />
						새 대화
					</Button>
					{#if conversations.length > 0}
						<button
							class="p-2 rounded-md text-dl-text-dim hover:text-dl-primary hover:bg-dl-primary/5 transition-colors"
							onclick={onDeleteAll}
							title="모든 대화 삭제"
							aria-label="모든 대화 삭제"
						>
							<Trash2 size={14} />
						</button>
					{/if}
				</div>
			</div>

			<!-- Search -->
			<div class="px-3 pb-2">
				<div class="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-dl-bg-card border border-dl-border/30">
					<Search size={12} class="text-dl-text-dim flex-shrink-0" />
					<input
						type="text"
						bind:value={searchQuery}
						placeholder="대화 검색..."
						class="flex-1 bg-transparent border-none outline-none text-[12px] text-dl-text placeholder:text-dl-text-dim"
					/>
				</div>
			</div>

			<!-- Conversation List: 그룹 라벨 (오늘/어제/이번 주/이전) 폐기. 핀 영역만 분리. -->
			<div class="flex-1 overflow-y-auto px-2 py-1 space-y-3">
				{#if pinnedItems.length > 0}
					<div>
						<div class="flex items-center gap-1 px-3 py-1 text-[10px] font-medium uppercase tracking-[0.14em] text-dl-text-dim">
							<Pin size={9} class="text-dl-accent" /> 핀 고정
						</div>
						{#each pinnedItems as conv}
							{@render conversationRow(conv, true)}
						{/each}
					</div>
				{/if}
				{#if unpinnedItems.length > 0}
					<div>
						{#each unpinnedItems as conv}
							{@render conversationRow(conv, false)}
						{/each}
					</div>
				{/if}
			</div>

			<!-- Footer: 설정 + 버전 -->
			<div class="flex-shrink-0 flex items-center gap-2 border-t border-dl-border/30 px-3 py-2">
				{#if onOpenSettings}
					<button
						class="flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] text-dl-text-dim hover:bg-dl-bg-card hover:text-dl-text transition-colors"
						onclick={onOpenSettings}
					>
						<Settings size={12} /> 설정
					</button>
				{/if}
				<div class="flex-1"></div>
				{#if version}
					<span class="text-[10px] text-dl-text-dim font-mono">v{version}</span>
				{/if}
			</div>
		</div>
	{:else}
		<!-- Collapsed: MessageSquare 10 개 일렬 폐기. 새 대화 + 핀만. -->
		<div class="flex flex-col items-center h-full min-w-[52px] py-3 gap-2">
			<button
				class="p-2 rounded-md text-dl-text-muted hover:text-dl-text hover:bg-dl-bg-card/50 transition-colors"
				onclick={onNewChat}
				title="새 대화"
				aria-label="새 대화"
			>
				<Plus size={18} />
			</button>
			{#if pinnedItems.length > 0}
				<div class="flex-1 overflow-y-auto flex flex-col items-center gap-1 w-full px-1">
					{#each pinnedItems as conv}
						<button
							class={cn(
								"p-2 rounded-md transition-colors w-full flex justify-center",
								conv.id === activeId
									? "bg-dl-bg-card text-dl-text"
									: "text-dl-text-dim hover:text-dl-text-muted hover:bg-dl-bg-card/50"
							)}
							onclick={() => onSelect?.(conv.id)}
							title={conv.title}
							aria-label={conv.title}
						>
							<Pin size={14} class="text-dl-accent" />
						</button>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</aside>

{#snippet conversationRow(conv, isPinned)}
	<div
		class={cn(
			"group relative w-full flex items-center rounded-md px-3 py-1.5 text-left text-[13px] transition-colors duration-150",
			conv.id === activeId
				? "bg-dl-surface-active text-dl-text"
				: "text-dl-text-muted hover:bg-dl-bg-card/60 hover:text-dl-text"
		)}
	>
		<button
			class="flex min-w-0 flex-1 items-center gap-1.5 text-left"
			onclick={() => onSelect?.(conv.id)}
			aria-current={conv.id === activeId ? "true" : undefined}
		>
			{#if isPinned}
				<Pin size={11} class="flex-shrink-0 text-dl-accent" />
			{/if}
			{#if editingId === conv.id}
				<input
					type="text"
					bind:value={editTitle}
					class="flex-1 bg-transparent border-none outline-none text-[13px] text-dl-text"
					onkeydown={(e) => {
						if (e.key === "Enter") { onRename?.(conv.id, editTitle.trim()); editingId = null; }
						if (e.key === "Escape") { editingId = null; }
					}}
					onblur={() => { onRename?.(conv.id, editTitle.trim()); editingId = null; }}
					onfocus={(e) => e.target.select()}
				/>
			{:else}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<span
					class={cn(
						"flex-1 truncate font-medium",
						conv.id === activeId ? "text-dl-text" : "text-dl-text-muted group-hover:text-dl-text"
					)}
					ondblclick={(e) => { e.stopPropagation(); editingId = conv.id; editTitle = conv.title; }}
				>{conv.title}</span>
			{/if}
		</button>
		<div class="relative">
			<button
				class="invisible group-hover:visible p-1 rounded hover:bg-dl-bg-card-hover text-dl-text-dim hover:text-dl-text transition-colors"
				onclick={(e) => toggleMenu(conv.id, e)}
				aria-label={`${conv.title} 메뉴`}
				aria-expanded={openMenuId === conv.id}
			>
				<MoreHorizontal size={14} />
			</button>
			{#if openMenuId === conv.id}
				<!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
				<div
					class="absolute right-0 top-7 z-30 w-36 rounded-md border border-dl-border bg-dl-bg-card shadow-lg shadow-black/40 py-1 text-[12px] text-dl-text-muted"
					role="menu"
					onclick={(e) => e.stopPropagation()}
				>
					<button
						class="block w-full px-3 py-1.5 text-left hover:bg-dl-bg-card-hover hover:text-dl-text"
						onclick={() => { editingId = conv.id; editTitle = conv.title; closeMenu(); }}
					>이름 변경</button>
					{#if onTogglePin}
						<button
							class="block w-full px-3 py-1.5 text-left hover:bg-dl-bg-card-hover hover:text-dl-text"
							onclick={() => { onTogglePin(conv.id); closeMenu(); }}
						>{conv.pinned ? "핀 해제" : "핀 고정"}</button>
					{/if}
					{#if onDuplicate}
						<button
							class="block w-full px-3 py-1.5 text-left hover:bg-dl-bg-card-hover hover:text-dl-text"
							onclick={() => { onDuplicate(conv.id); closeMenu(); }}
						>복제</button>
					{/if}
					<button
						class="block w-full px-3 py-1.5 text-left text-red-400 hover:bg-red-500/10"
						onclick={() => { onDelete?.(conv.id); closeMenu(); }}
					>삭제</button>
				</div>
			{/if}
		</div>
	</div>
{/snippet}
