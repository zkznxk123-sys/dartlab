// L6 — 일자별 events Sheet 본문. 공시·RSS·GDELT 3 source 분리 list.
//
// dartwings popup (260~360px) → shadcn Sheet (480px) 격상. 더 풍부한 정보:
//   - 공시 click → external DART URL (또는 옵션 onItemClick 위임 — analysis viewer 등 내부 viewer 라우팅).
//   - 뉴스 click → 외부 URL new tab.

import type { DayEvents, DisclosureItem, NewsItem } from '../api/priceEvents';

interface Props {
	date: string;
	events: DayEvents | undefined;
	onItemClick?: (item: DisclosureItem | NewsItem, kind: 'disclosure' | 'news_rss' | 'news_gdelt') => void;
}

const SENTIMENT_COLOR = {
	pos: 'text-rose-500',
	neg: 'text-blue-500',
	neutral: 'text-slate-500',
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
	return (
		<div className="border-t border-slate-200 py-3 dark:border-slate-700">
			<div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</div>
			<div className="space-y-2">{children}</div>
		</div>
	);
}

function DisclosureRow({ item, onClick }: { item: DisclosureItem; onClick: () => void }) {
	return (
		<button
			type="button"
			onClick={onClick}
			className="w-full rounded border border-slate-200 px-2 py-1.5 text-left text-sm hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
		>
			<div className="flex items-center justify-between gap-2">
				<span className="line-clamp-1">{item.title}</span>
				<span className="text-xs text-slate-400">[{item.discType}]</span>
			</div>
		</button>
	);
}

function NewsRow({ item, onClick }: { item: NewsItem; onClick: () => void }) {
	const label = item.sentiment_label ?? 'neutral';
	const colorClass = SENTIMENT_COLOR[label as keyof typeof SENTIMENT_COLOR] ?? SENTIMENT_COLOR.neutral;
	return (
		<button
			type="button"
			onClick={onClick}
			className="w-full rounded border border-slate-200 px-2 py-1.5 text-left text-sm hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
		>
			<div className="line-clamp-1">{item.title}</div>
			<div className="mt-0.5 flex items-center gap-2 text-xs text-slate-400">
				<span>{item.source}</span>
				{item.sentiment_score != null && (
					<span className={colorClass}>· {item.sentiment_score.toFixed(2)}</span>
				)}
			</div>
		</button>
	);
}

export function EventSidePanel({ date, events, onItemClick }: Props) {
	const disclosures = events?.disclosures ?? [];
	const news_rss = events?.news_rss ?? [];
	const news_gdelt = events?.news_gdelt ?? [];
	const total = disclosures.length + news_rss.length + news_gdelt.length;

	const handle = (item: DisclosureItem | NewsItem, kind: 'disclosure' | 'news_rss' | 'news_gdelt') => {
		if (onItemClick) {
			onItemClick(item, kind);
			return;
		}
		// 기본: 외부 URL new tab
		if ('url' in item && item.url) {
			window.open(item.url, '_blank', 'noopener,noreferrer');
		}
	};

	return (
		<div className="flex h-full flex-col">
			<div className="mb-2 text-base font-semibold">
				{date}
				<span className="ml-2 text-sm text-slate-500">총 {total}건</span>
			</div>
			{disclosures.length > 0 && (
				<Section title={`공시 ${disclosures.length}건`}>
					{disclosures.map((it, i) => (
						<DisclosureRow key={`disc-${i}`} item={it} onClick={() => handle(it, 'disclosure')} />
					))}
				</Section>
			)}
			{news_rss.length > 0 && (
				<Section title={`RSS 뉴스 ${news_rss.length}건`}>
					{news_rss.map((it, i) => (
						<NewsRow key={`rss-${i}`} item={it} onClick={() => handle(it, 'news_rss')} />
					))}
				</Section>
			)}
			{news_gdelt.length > 0 && (
				<Section title={`GDELT 글로벌 ${news_gdelt.length}건`}>
					{news_gdelt.map((it, i) => (
						<NewsRow key={`gdelt-${i}`} item={it} onClick={() => handle(it, 'news_gdelt')} />
					))}
				</Section>
			)}
			{total === 0 && <div className="text-sm text-slate-500">이 일자에 등록된 이벤트가 없습니다.</div>}
		</div>
	);
}
