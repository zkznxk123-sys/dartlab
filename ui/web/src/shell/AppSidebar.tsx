// 사이드바 — collapsible="icon".
// 헤더: avatar/brand + mode 토글 + theme 토글 + provider 설정 (+ 현재 provider 배지 한 줄).
// AskNav: [새 대화] [검색] [대화 리스트 — 각 항목 ⋯ 메뉴: 마크다운 저장 · 삭제(confirm)]
// DashboardNav: 재무제표 nav 만.
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useLocation, useNavigate } from '@tanstack/react-router';
import {
	Download,
	FileText,
	LayoutDashboard,
	MessageSquare,
	MessageSquarePlus,
	MoreHorizontal,
	Moon,
	Pencil,
	Pin,
	PinOff,
	Search,
	Settings,
	Sun,
	Trash2,
} from 'lucide-react';

import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
	DropdownMenu,
	DropdownMenuContent,
	DropdownMenuItem,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import {
	Sidebar,
	SidebarContent,
	SidebarGroup,
	SidebarGroupContent,
	SidebarHeader,
	SidebarMenu,
	SidebarMenuAction,
	SidebarMenuButton,
	SidebarMenuItem,
	SidebarRail,
} from '@/components/ui/sidebar';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { useTheme } from '@/shell/ThemeProvider';
import { ProviderSettingsDialog } from '@/features/provider/ProviderSettingsDialog';
import { useChat, type Conversation } from '@/features/chat/store/chat';
import { downloadMarkdown } from '@/features/chat/store/export';

interface ProviderStatusResp {
	providers: Record<
		string,
		{ selected?: boolean; label?: string; model?: string; auth?: string }
	>;
}

async function fetchProviderBadge(): Promise<{ label: string; model: string } | null> {
	const r = await fetch('/api/status');
	if (!r.ok) return null;
	const data: ProviderStatusResp = await r.json();
	for (const p of Object.values(data.providers || {})) {
		if (p.selected) return { label: p.label || '', model: p.model || '' };
	}
	return null;
}

export function AppSidebar() {
	const { pathname } = useLocation();
	const navigate = useNavigate();
	const { theme, setTheme } = useTheme();

	const isDashboard = pathname.startsWith('/dashboard');
	const isDark =
		theme === 'dark' ||
		(theme === 'system' &&
			typeof window !== 'undefined' &&
			window.matchMedia('(prefers-color-scheme: dark)').matches);

	const { data: providerBadge } = useQuery({
		queryKey: ['provider-badge'],
		queryFn: fetchProviderBadge,
		staleTime: 30_000,
	});

	return (
		<Sidebar collapsible="icon">
			<SidebarHeader>
				<div className="flex items-center gap-1">
					<Link to="/ask" className="flex items-center gap-2 min-w-0 flex-1 no-underline text-foreground">
						<Avatar className="size-8 rounded-lg shrink-0">
							<AvatarImage src="/avatar.png" alt="DartLab" />
							<AvatarFallback className="rounded-lg">DL</AvatarFallback>
						</Avatar>
						<div className="grid min-w-0 flex-1 text-left leading-tight group-data-[collapsible=icon]:hidden">
							<span className="truncate text-sm font-semibold">DartLab</span>
							<span className="truncate text-xs text-muted-foreground">v0.10.0</span>
						</div>
					</Link>
					<div className="flex items-center group-data-[collapsible=icon]:hidden">
						<Tooltip>
							<TooltipTrigger asChild>
								<Button
									variant="ghost"
									size="icon"
									className="size-7"
									onClick={() => navigate({ to: isDashboard ? '/ask' : '/dashboard' })}
									aria-label={isDashboard ? 'Ask 모드' : 'Dashboard 모드'}
								>
									{isDashboard ? <MessageSquare /> : <LayoutDashboard />}
								</Button>
							</TooltipTrigger>
							<TooltipContent>{isDashboard ? 'Ask 모드' : 'Dashboard 모드'}</TooltipContent>
						</Tooltip>
						<Tooltip>
							<TooltipTrigger asChild>
								<Button
									variant="ghost"
									size="icon"
									className="size-7"
									onClick={() => setTheme(isDark ? 'light' : 'dark')}
									aria-label={isDark ? 'Light 모드' : 'Dark 모드'}
								>
									{isDark ? <Sun /> : <Moon />}
								</Button>
							</TooltipTrigger>
							<TooltipContent>{isDark ? 'Light 모드' : 'Dark 모드'}</TooltipContent>
						</Tooltip>
						<Tooltip>
							<TooltipTrigger asChild>
								<span>
									<ProviderSettingsDialog
										trigger={
											<Button
												variant="ghost"
												size="icon"
												className="size-7"
												aria-label="AI Provider 설정"
											>
												<Settings />
											</Button>
										}
									/>
								</span>
							</TooltipTrigger>
							<TooltipContent>AI Provider 설정</TooltipContent>
						</Tooltip>
					</div>
				</div>
				{providerBadge && (
					<div className="mt-1.5 flex items-center gap-1.5 group-data-[collapsible=icon]:hidden">
						<Badge variant="secondary" className="font-normal text-[10px]">
							{providerBadge.label}
						</Badge>
						{providerBadge.model && (
							<span className="font-mono text-[10px] text-muted-foreground truncate">
								{providerBadge.model}
							</span>
						)}
					</div>
				)}
			</SidebarHeader>

			<SidebarContent>{isDashboard ? <DashboardNav /> : <AskNav />}</SidebarContent>
			<SidebarRail />
		</Sidebar>
	);
}

function DashboardNav() {
	const { pathname } = useLocation();
	const items = [{ title: '재무제표', url: '/dashboard', icon: FileText }];
	return (
		<SidebarGroup>
			<SidebarGroupContent>
				<SidebarMenu>
					{items.map((item) => {
						const isActive = pathname === item.url || pathname.startsWith(item.url + '/');
						return (
							<SidebarMenuItem key={item.url}>
								<SidebarMenuButton asChild isActive={isActive} tooltip={item.title}>
									<Link to={item.url}>
										<item.icon />
										<span>{item.title}</span>
									</Link>
								</SidebarMenuButton>
							</SidebarMenuItem>
						);
					})}
				</SidebarMenu>
			</SidebarGroupContent>
		</SidebarGroup>
	);
}

function AskNav() {
	const conversations = useChat((s) => s.conversations);
	const activeId = useChat((s) => s.activeId);
	const newConversation = useChat((s) => s.newConversation);
	const switchConversation = useChat((s) => s.switchConversation);
	const deleteConversation = useChat((s) => s.deleteConversation);
	const renameConversation = useChat((s) => s.renameConversation);
	const togglePin = useChat((s) => s.togglePin);

	const [q, setQ] = useState('');
	const filtered = q.trim()
		? conversations.filter((c) => {
				const hay = (
					c.title +
					' ' +
					c.messages
						.map((m) => m.parts.map((p) => (p.type === 'text' ? p.text : '')).join(''))
						.join(' ')
				).toLowerCase();
				return hay.includes(q.trim().toLowerCase());
			})
		: conversations;

	// 고정 먼저, 그 다음 updatedAt desc.
	const sorted = [...filtered].sort((a, b) => {
		if (a.pinnedAt && !b.pinnedAt) return -1;
		if (!a.pinnedAt && b.pinnedAt) return 1;
		if (a.pinnedAt && b.pinnedAt) return b.pinnedAt - a.pinnedAt;
		return b.updatedAt - a.updatedAt;
	});

	return (
		<>
			<SidebarGroup>
				<SidebarGroupContent>
					<SidebarMenu>
						<SidebarMenuItem>
							<SidebarMenuButton onClick={() => newConversation()} tooltip="새 대화 (Ctrl/⌘+K)">
								<MessageSquarePlus />
								<span>새 대화</span>
							</SidebarMenuButton>
						</SidebarMenuItem>
					</SidebarMenu>
				</SidebarGroupContent>
			</SidebarGroup>

			<SidebarGroup className="group-data-[collapsible=icon]:hidden">
				<SidebarGroupContent>
					<div className="relative px-2">
						<Search className="pointer-events-none absolute left-4 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
						<Input
							value={q}
							onChange={(e) => setQ(e.target.value)}
							placeholder="대화 검색…"
							className="h-8 pl-7 text-xs"
						/>
					</div>
				</SidebarGroupContent>
			</SidebarGroup>

			<SidebarGroup className="group-data-[collapsible=icon]:hidden">
				<SidebarGroupContent>
					<SidebarMenu>
						{sorted.length === 0 ? (
							<SidebarMenuItem>
								<div className="px-2 py-1 text-xs text-muted-foreground">
									{q.trim() ? '검색 결과 없음' : '대화 없음'}
								</div>
							</SidebarMenuItem>
						) : (
							sorted.map((c) => (
								<ConversationItem
									key={c.id}
									conversation={c}
									active={c.id === activeId}
									onSwitch={() => switchConversation(c.id)}
									onDelete={() => deleteConversation(c.id)}
									onRename={(title) => renameConversation(c.id, title)}
									onTogglePin={() => togglePin(c.id)}
								/>
							))
						)}
					</SidebarMenu>
				</SidebarGroupContent>
			</SidebarGroup>
		</>
	);
}

function ConversationItem({
	conversation,
	active,
	onSwitch,
	onDelete,
	onRename,
	onTogglePin,
}: {
	conversation: Conversation;
	active: boolean;
	onSwitch: () => void;
	onDelete: () => void;
	onRename: (title: string) => void;
	onTogglePin: () => void;
}) {
	const [confirmOpen, setConfirmOpen] = useState(false);
	const [renaming, setRenaming] = useState(false);
	const [draft, setDraft] = useState(conversation.title);
	const pinned = !!conversation.pinnedAt;

	function commitRename() {
		setRenaming(false);
		if (draft.trim() && draft.trim() !== conversation.title) {
			onRename(draft);
		} else {
			setDraft(conversation.title);
		}
	}

	if (renaming) {
		return (
			<SidebarMenuItem>
				<div className="flex w-full items-center gap-1 px-2 py-1">
					<Input
						value={draft}
						onChange={(e) => setDraft(e.target.value)}
						onBlur={commitRename}
						onKeyDown={(e) => {
							if (e.key === 'Enter') commitRename();
							if (e.key === 'Escape') {
								setRenaming(false);
								setDraft(conversation.title);
							}
						}}
						autoFocus
						className="h-7 text-xs"
					/>
				</div>
			</SidebarMenuItem>
		);
	}

	return (
		<SidebarMenuItem>
			<SidebarMenuButton
				isActive={active}
				onClick={onSwitch}
				onDoubleClick={() => setRenaming(true)}
				tooltip={conversation.title}
			>
				{pinned ? <Pin className="text-[#ea4647]" /> : <MessageSquare />}
				<span className="truncate">{conversation.title || '새 대화'}</span>
			</SidebarMenuButton>
			<DropdownMenu>
				<DropdownMenuTrigger asChild>
					<SidebarMenuAction showOnHover aria-label="대화 메뉴">
						<MoreHorizontal />
					</SidebarMenuAction>
				</DropdownMenuTrigger>
				<DropdownMenuContent align="end" side="right">
					<DropdownMenuItem onClick={onTogglePin}>
						{pinned ? (
							<>
								<PinOff className="mr-2 size-3.5" />
								고정 해제
							</>
						) : (
							<>
								<Pin className="mr-2 size-3.5" />
								고정
							</>
						)}
					</DropdownMenuItem>
					<DropdownMenuItem onClick={() => setRenaming(true)}>
						<Pencil className="mr-2 size-3.5" />
						이름 변경
					</DropdownMenuItem>
					<DropdownMenuItem onClick={() => downloadMarkdown(conversation)}>
						<Download className="mr-2 size-3.5" />
						마크다운으로 저장
					</DropdownMenuItem>
					<DropdownMenuSeparator />
					<DropdownMenuItem
						onClick={(e) => {
							e.preventDefault();
							setConfirmOpen(true);
						}}
						className="text-destructive focus:text-destructive"
					>
						<Trash2 className="mr-2 size-3.5" />
						대화 삭제
					</DropdownMenuItem>
				</DropdownMenuContent>
			</DropdownMenu>
			<AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
				<AlertDialogContent>
					<AlertDialogHeader>
						<AlertDialogTitle>이 대화를 삭제할까요?</AlertDialogTitle>
						<AlertDialogDescription>
							"{conversation.title || '새 대화'}" 의 모든 메시지가 영구 삭제됩니다.
						</AlertDialogDescription>
					</AlertDialogHeader>
					<AlertDialogFooter>
						<AlertDialogCancel>취소</AlertDialogCancel>
						<AlertDialogAction
							onClick={onDelete}
							className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
						>
							삭제
						</AlertDialogAction>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>
		</SidebarMenuItem>
	);
}
