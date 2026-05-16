// 헤더 — h-12, border 없음.
// 좌: SidebarTrigger
// 우: Artifact panel toggle + sns 5 개 (GitHub · YouTube · Insta · Threads · Coffee), 각 Tooltip 표시.
// Provider 설정은 사이드바 헤더로 이동.
import { Github, Youtube, Instagram, Coffee, PanelRight } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { SidebarTrigger } from '@/components/ui/sidebar';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { ThreadsIcon } from '@/shell/icons/Threads';
import { brand } from '@/lib/brand';
import { useArtifact } from '@/features/chat/artifacts/store';

const socials: {
	label: string;
	href: string;
	Icon: React.ComponentType<{ className?: string }>;
}[] = [
	{ label: 'GitHub', href: brand.repo, Icon: Github },
	{ label: 'YouTube', href: brand.youtube, Icon: Youtube },
	{ label: 'Instagram', href: brand.instagram, Icon: Instagram },
	{ label: 'Threads', href: brand.threads, Icon: ThreadsIcon },
	{ label: 'Buy Me a Coffee', href: brand.coffee, Icon: Coffee },
];

export function SiteHeader() {
	const togglePanel = useArtifact((s) => s.togglePanel);
	const panelOpen = useArtifact((s) => s.open);
	return (
		<header className="flex h-12 shrink-0 items-center gap-1 px-3">
			<SidebarTrigger className="-ml-1" />
			<div className="ml-auto flex items-center -mr-1">
				{socials.map(({ label, href, Icon }) => (
					<Tooltip key={label}>
						<TooltipTrigger asChild>
							<Button variant="ghost" size="icon" className="size-8" asChild>
								<a href={href} target="_blank" rel="noopener noreferrer" aria-label={label}>
									<Icon />
								</a>
							</Button>
						</TooltipTrigger>
						<TooltipContent>{label}</TooltipContent>
					</Tooltip>
				))}
				<Tooltip>
					<TooltipTrigger asChild>
						<Button
							variant="ghost"
							size="icon"
							className="size-8 ml-1"
							onClick={togglePanel}
							aria-label="Artifact panel"
							aria-pressed={panelOpen}
						>
							<PanelRight />
						</Button>
					</TooltipTrigger>
					<TooltipContent>Artifact 패널 {panelOpen ? '닫기' : '열기'}</TooltipContent>
				</Tooltip>
			</div>
		</header>
	);
}
