// 헤더 — h-12, border 없음.
// 좌: SidebarTrigger
// 우: sns 5 개 (GitHub · YouTube · Insta · Threads · Coffee), 각 Tooltip 표시.
// Provider 설정은 사이드바 헤더로 이동.
import { Github, Youtube, Instagram, Coffee } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { SidebarTrigger } from '@/components/ui/sidebar';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { ThreadsIcon } from '@/shell/icons/Threads';
import { brand } from '@/lib/brand';

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
			</div>
		</header>
	);
}
