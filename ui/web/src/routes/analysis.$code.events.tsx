// /analysis/$code/events — 주가 + 이벤트 (공시 + RSS news + GDELT news + L4 shocks + L5 regime) 차트.
//
// L6 PriceEventChart 컴포넌트를 풀스크린 단일 카드로 박아 둠. 사용자 직설 — "과거 캔들 + 일자별 점 +
// hover 시 정보 + click 시 원문 모달" 그대로 구현.

import { createFileRoute } from '@tanstack/react-router';
import { useMemo, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';

import { PriceEventChart } from '@/features/dashboard/charts/PriceEventChart';
import type { EventSource } from '@/features/dashboard/api/priceEvents';

interface SearchParams {
	period: 'annual' | 'quarterly';
}

export const Route = createFileRoute('/analysis/$code/events')({
	validateSearch: (search: Record<string, unknown>): SearchParams => ({
		period: search.period === 'annual' ? 'annual' : 'quarterly',
	}),
	component: EventsPage,
});

function _today(): string {
	const d = new Date();
	return d.toISOString().slice(0, 10);
}

function _aYearAgo(): string {
	const d = new Date();
	d.setFullYear(d.getFullYear() - 1);
	return d.toISOString().slice(0, 10);
}

function EventsPage() {
	const { code } = Route.useParams();

	const [source, setSource] = useState<EventSource>('all');
	const [showShocks, setShowShocks] = useState(true);
	const [showRegime, setShowRegime] = useState(true);

	const start = useMemo(() => _aYearAgo(), []);
	const end = useMemo(() => _today(), []);

	return (
		<div className="p-4">
			<Card>
				<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
					<CardTitle className="text-base">주가 + 이벤트 차트 (L6)</CardTitle>
					<div className="flex items-center gap-3 text-xs">
						<div className="flex gap-1">
							{(['all', 'disclosure', 'news_rss', 'news_gdelt'] as const).map((s) => (
								<Button
									key={s}
									type="button"
									size="sm"
									variant={source === s ? 'default' : 'outline'}
									onClick={() => setSource(s)}
								>
									{s === 'all' ? '전체' : s === 'disclosure' ? '공시' : s === 'news_rss' ? 'RSS' : 'GDELT'}
								</Button>
							))}
						</div>
						<div className="flex items-center gap-2">
							<Switch id="shocks" checked={showShocks} onCheckedChange={setShowShocks} />
							<Label htmlFor="shocks" className="text-xs">3σ shock</Label>
						</div>
						<div className="flex items-center gap-2">
							<Switch id="regime" checked={showRegime} onCheckedChange={setShowRegime} />
							<Label htmlFor="regime" className="text-xs">regime</Label>
						</div>
					</div>
				</CardHeader>
				<CardContent>
					<PriceEventChart
						stockCode={code}
						start={start}
						end={end}
						market="KR"
						source={source}
						showShocks={showShocks}
						showRegime={showRegime}
						height={520}
					/>
				</CardContent>
			</Card>
		</div>
	);
}
