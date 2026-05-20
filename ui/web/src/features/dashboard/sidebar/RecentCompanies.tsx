// 사이드바 최근 5 개 회사 핀.

import { Link } from '@tanstack/react-router';
import { History } from 'lucide-react';

import { SidebarGroup, SidebarGroupContent, SidebarGroupLabel, SidebarMenu, SidebarMenuButton, SidebarMenuItem } from '@/components/ui/sidebar';

import { usePrefetchCompany } from '../hooks/usePrefetchCompany';
import { useRecentCompanies } from '../hooks/useRecentCompanies';

export function RecentCompanies() {
	const { items } = useRecentCompanies();
	const prefetch = usePrefetchCompany();
	if (!items.length) return null;
	return (
		<SidebarGroup className="group-data-[collapsible=icon]:hidden">
			<SidebarGroupLabel className="text-[10px]">최근</SidebarGroupLabel>
			<SidebarGroupContent>
				<SidebarMenu>
					{items.map((r) => (
						<SidebarMenuItem key={r.stockCode}>
							<SidebarMenuButton
								asChild
								tooltip={`${r.corpName} (${r.stockCode})`}
								onMouseEnter={() => prefetch(r.stockCode, { full: false })}
								onFocus={() => prefetch(r.stockCode, { full: false })}
							>
								<Link to="/analysis/$code" params={{ code: r.stockCode }} search={{ period: 'quarterly' }}>
									<History />
									<span className="truncate">{r.corpName}</span>
									<span className="ml-auto font-mono text-[10px] text-muted-foreground">{r.stockCode}</span>
								</Link>
							</SidebarMenuButton>
						</SidebarMenuItem>
					))}
				</SidebarMenu>
			</SidebarGroupContent>
		</SidebarGroup>
	);
}
