import { useQuery } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import {
	AlertTriangle,
	BarChart3,
	Building2,
	Clock,
	Database,
	FileText,
	GitBranch,
	Loader2,
	Search,
	ShieldAlert,
	Terminal as TerminalIcon,
	TrendingUp,
} from 'lucide-react';
import { useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
	fetchCompanyIndex,
	fetchCompanyInsights,
	fetchCompanyMeta,
	fetchCompanyNetwork,
	fetchCompanyScanAll,
	fetchCompanyTopic,
	searchCompanies,
	type CompanyIndexRow,
	type CompanyInsightsResponse,
	type CompanyNetworkResponse,
	type CompanyScanAllResponse,
	type SearchHit,
	type SerializedPayload,
	type SerializedTablePayload,
} from '@/features/dashboard/api/client';
import { dashKeys } from '@/features/dashboard/api/queryKeys';
import { PriceEventChart } from '@/features/dashboard/charts/PriceEventChart';
import { cn } from '@/lib/utils';

import { TERMINAL_DATA_SOURCES } from './landingParity';

interface Props {
	code: string;
}

type ScanAxis = 'governance' | 'debt' | 'capital' | 'workforce';
type StatementTopic = 'IS' | 'BS' | 'CF' | 'ratios';

interface TerminalMetric {
	id: string;
	label: string;
	value: number;
	unit?: string;
	subtitle?: string;
	intent?: 'primary' | 'positive' | 'negative' | 'neutral' | 'accent';
}

interface RiskLine {
	label: string;
	value: string;
	tone: 'danger' | 'warn' | 'good' | 'neutral';
}

interface TerminalBundle {
	index?: Awaited<ReturnType<typeof fetchCompanyIndex>>;
	scan?: CompanyScanAllResponse;
	insights?: CompanyInsightsResponse;
	network?: CompanyNetworkResponse;
}

const SCAN_AXES: ScanAxis[] = ['governance', 'debt', 'capital', 'workforce'];
const SCAN_LABEL: Record<ScanAxis, string> = {
	governance: '거버넌스',
	debt: '채무',
	capital: '주주환원',
	workforce: '인력',
};
const STATEMENTS: Array<{ topic: StatementTopic; label: string }> = [
	{ topic: 'IS', label: '손익' },
	{ topic: 'BS', label: '재무상태' },
	{ topic: 'CF', label: '현금흐름' },
	{ topic: 'ratios', label: '비율' },
];
const AREA_LABEL: Record<string, string> = {
	performance: '실적',
	profitability: '수익성',
	health: '건전성',
	cashflow: '현금흐름',
	governance: '거버넌스',
	risk: '리스크',
	opportunity: '기회',
};
const PREFERRED_SCAN_FIELDS: Record<ScanAxis, string[]> = {
	governance: ['등급', '총점', '지분율', '감사의견', '중도사임'],
	debt: ['위험등급', '부채비율', 'ICR', '총부채', '단기비중'],
	capital: ['분류', '환원점수', 'DPS', '배당수익률', '최근증자'],
	workforce: ['직원수', '평균급여_만원', '직원당매출_억', '최고보수_억', '공개인원'],
};

function today(): string {
	return new Date().toISOString().slice(0, 10);
}

function ninetyDaysAgo(): string {
	const d = new Date();
	d.setDate(d.getDate() - 90);
	return d.toISOString().slice(0, 10);
}

function fmt(value: number | null | undefined, unit?: string): string {
	if (value == null || Number.isNaN(value)) return '-';
	const abs = Math.abs(value);
	if (unit === '%' || abs < 1000) return `${value.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}${unit ?? ''}`;
	if (abs >= 1e12) return `${(value / 1e12).toLocaleString('ko-KR', { maximumFractionDigits: 2 })}조`;
	if (abs >= 1e8) return `${(value / 1e8).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}억`;
	return value.toLocaleString('ko-KR', { maximumFractionDigits: 0 });
}

function valueText(value: unknown): string {
	if (value == null || value === '') return '-';
	if (typeof value === 'boolean') return value ? '예' : '아니오';
	if (typeof value === 'number') return fmt(value);
	return String(value);
}

async function optional<T>(promise: Promise<T>): Promise<T | undefined> {
	try {
		return await promise;
	} catch {
		return undefined;
	}
}

function isTablePayload(payload: SerializedPayload | undefined): payload is SerializedTablePayload {
	return payload?.type === 'table' && Array.isArray(payload.columns) && Array.isArray(payload.rows);
}

function scanPayload(scan: CompanyScanAllResponse | undefined, axis: ScanAxis): SerializedTablePayload | undefined {
	const payload = scan?.scans?.[axis];
	return isTablePayload(payload) ? payload : undefined;
}

function indexRows(payload: SerializedPayload | undefined): CompanyIndexRow[] {
	if (!isTablePayload(payload)) return [];
	return payload.rows
		.map((row) => row as CompanyIndexRow)
		.filter((row) => row.label || row.topic)
		.slice(0, 18);
}

function matchColumn(columns: string[], wanted: string): string | undefined {
	return columns.find((col) => col === wanted) ?? columns.find((col) => col.includes(wanted));
}

function scanPairs(payload: SerializedTablePayload | undefined, axis: ScanAxis): Array<{ label: string; value: string }> {
	const row = payload?.rows?.[0];
	if (!row || !payload) return [];
	const pairs: Array<{ label: string; value: string }> = [];
	for (const field of PREFERRED_SCAN_FIELDS[axis]) {
		const column = matchColumn(payload.columns, field);
		if (!column) continue;
		pairs.push({ label: column, value: valueText(row[column]) });
	}
	if (pairs.length >= 4) return pairs.slice(0, 6);
	for (const column of payload.columns) {
		if (column === 'stockCode' || pairs.some((pair) => pair.label === column)) continue;
		const text = valueText(row[column]);
		if (text === '-') continue;
		pairs.push({ label: column, value: text });
		if (pairs.length >= 6) break;
	}
	return pairs;
}

function toneForRisk(value: string): RiskLine['tone'] {
	if (/위험|경고|주의|D|E|F|red|high/i.test(value)) return 'danger';
	if (/보통|yellow|medium|C/i.test(value)) return 'warn';
	if (/양호|우수|A|B|low|green/i.test(value)) return 'good';
	return 'neutral';
}

function riskLines(insights: CompanyInsightsResponse | undefined, scan: CompanyScanAllResponse | undefined): RiskLine[] {
	const out: RiskLine[] = [];
	if (insights?.available) {
		for (const item of insights.anomalies ?? []) {
			out.push({
				label: item.category || item.severity || '이상 징후',
				value: item.text,
				tone: toneForRisk(`${item.severity ?? ''} ${item.text}`),
			});
			if (out.length >= 4) return out;
		}
		for (const [key, area] of Object.entries(insights.areas ?? {})) {
			const risk = area.risks?.[0];
			if (!risk && !area.grade) continue;
			out.push({
				label: AREA_LABEL[key] ?? key,
				value: risk?.text ?? `등급 ${area.grade}`,
				tone: toneForRisk(`${area.grade ?? ''} ${risk?.level ?? ''}`),
			});
			if (out.length >= 4) return out;
		}
	}
	for (const axis of SCAN_AXES) {
		const payload = scanPayload(scan, axis);
		const first = scanPairs(payload, axis)[0];
		if (!first) continue;
		out.push({
			label: SCAN_LABEL[axis],
			value: `${first.label} ${first.value}`,
			tone: toneForRisk(first.value),
		});
		if (out.length >= 4) break;
	}
	return out;
}

function periodColumn(col: string): boolean {
	return /^(FY\d{2}|20\d{2}|20\d{2}[./-]?Q[1-4]|\d{4}[./-]?[1-4]Q|Q[1-4])/.test(col);
}

function statementColumns(payload: SerializedTablePayload | undefined): string[] {
	if (!payload) return [];
	const label =
		payload.columns.find((col) => col === '항목') ??
		payload.columns.find((col) => col.toLowerCase() === 'label') ??
		payload.columns[0];
	const periods = payload.columns.filter(periodColumn).slice(0, 6);
	const others = payload.columns.filter((col) => col !== label && !periods.includes(col) && !['snakeId', 'tag'].includes(col)).slice(0, periods.length ? 0 : 4);
	return [label, ...periods, ...others].filter(Boolean);
}

function statementRows(payload: SerializedTablePayload | undefined, columns: string[]): Record<string, unknown>[] {
	if (!payload) return [];
	return payload.rows
		.filter((row) => columns.some((col) => valueText(row[col]) !== '-'))
		.slice(0, 16);
}

function labelColumn(payload: SerializedTablePayload | undefined): string | undefined {
	if (!payload) return undefined;
	return payload.columns.find((col) => col === '항목') ?? payload.columns.find((col) => col.toLowerCase() === 'label') ?? payload.columns[0];
}

function latestPeriodColumn(payload: SerializedTablePayload | undefined): string | undefined {
	return payload?.columns.find(periodColumn);
}

function numericValue(value: unknown): number | null {
	if (typeof value === 'number' && Number.isFinite(value)) return value;
	if (typeof value !== 'string') return null;
	const parsed = Number(value.replace(/,/g, '').trim());
	return Number.isFinite(parsed) ? parsed : null;
}

function metricFromStatement(
	payload: SerializedTablePayload | undefined,
	id: string,
	label: string,
	needles: string[],
	subtitle: string,
): TerminalMetric | null {
	const labelCol = labelColumn(payload);
	const periodCol = latestPeriodColumn(payload);
	if (!payload || !labelCol || !periodCol) return null;
	const row = payload.rows.find((candidate) => {
		const text = String(candidate[labelCol] ?? '');
		return needles.some((needle) => text.includes(needle));
	});
	const value = numericValue(row?.[periodCol]);
	if (value == null) return null;
	return { id, label, value, subtitle: `${subtitle} · ${periodCol}` };
}

function collectStatementMetrics(
	income: SerializedTablePayload | undefined,
	balance: SerializedTablePayload | undefined,
	cashflow: SerializedTablePayload | undefined,
): TerminalMetric[] {
	return [
		metricFromStatement(income, 'revenue', '매출액', ['매출액', '수익'], '손익'),
		metricFromStatement(income, 'operatingIncome', '영업이익', ['영업이익'], '손익'),
		metricFromStatement(balance, 'assets', '자산총계', ['자산총계', '자산 총계'], '재무상태'),
		metricFromStatement(cashflow, 'operatingCashflow', '영업CF', ['영업활동', '영업 현금'], '현금흐름'),
	].filter((metric): metric is TerminalMetric => metric != null);
}

function nodeLabel(node: unknown): string {
	if (!node || typeof node !== 'object') return '';
	const obj = node as Record<string, unknown>;
	return String(obj.corpName ?? obj.name ?? obj.label ?? obj.id ?? '');
}

function relationCount(network: CompanyNetworkResponse | undefined): { nodes: number; links: number } {
	const nodes = Array.isArray(network?.nodes) ? network.nodes.length : 0;
	const links = Array.isArray(network?.links) ? network.links.length : Array.isArray(network?.edges) ? network.edges.length : 0;
	return { nodes, links };
}

function MetricStrip({
	metrics,
	loading,
}: {
	metrics: TerminalMetric[];
	loading: boolean;
}) {
	if (loading) {
		return (
			<div className="grid grid-cols-4 gap-2">
				{Array.from({ length: 4 }).map((_, i) => (
					<Skeleton key={i} className="h-[74px]" />
				))}
			</div>
		);
	}
	return (
		<div className="grid grid-cols-4 gap-2">
			{metrics.map((metric) => (
				<div key={metric.id} className="min-w-0 rounded-md border bg-card px-3 py-2">
					<div className="truncate text-[11px] text-muted-foreground">{metric.label}</div>
					<div className="mt-1 truncate text-lg font-semibold tabular-nums">{fmt(metric.value, metric.unit)}</div>
					<div className="mt-1 truncate text-[10px] text-muted-foreground">{metric.subtitle}</div>
				</div>
			))}
		</div>
	);
}

function RiskPanel({
	insights,
	scan,
	loading,
}: {
	insights: CompanyInsightsResponse | undefined;
	scan: CompanyScanAllResponse | undefined;
	loading: boolean;
}) {
	const lines = riskLines(insights, scan);
	const toneClass: Record<RiskLine['tone'], string> = {
		danger: 'border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300',
		warn: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300',
		good: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
		neutral: 'border-border bg-background text-foreground',
	};
	return (
		<Card>
			<CardHeader className="pb-2">
				<CardTitle className="flex items-center gap-2 text-sm">
					<ShieldAlert className="size-4 text-muted-foreground" />
					리스크 경고등
				</CardTitle>
			</CardHeader>
			<CardContent className="space-y-2">
				{loading ? (
					<>
						<Skeleton className="h-11" />
						<Skeleton className="h-11" />
					</>
				) : lines.length ? (
					lines.map((line, i) => (
						<div key={`${line.label}-${i}`} className={cn('rounded-md border px-2.5 py-2 text-xs', toneClass[line.tone])}>
							<div className="font-medium">{line.label}</div>
							<div className="mt-1 line-clamp-2 text-muted-foreground">{line.value}</div>
						</div>
					))
				) : (
					<div className="rounded-md border bg-background p-3 text-xs text-muted-foreground">표시할 경고 없음</div>
				)}
			</CardContent>
		</Card>
	);
}

function InsightSummaryPanel({
	insights,
	loading,
}: {
	insights: CompanyInsightsResponse | undefined;
	loading: boolean;
}) {
	const summary =
		insights?.summary ??
		Object.values(insights?.areas ?? {})
			.map((area) => area.summary)
			.find(Boolean);
	const grades = Object.entries(insights?.grades ?? {}).slice(0, 6);
	return (
		<Card>
			<CardHeader className="pb-2">
				<CardTitle className="flex items-center gap-2 text-sm">
					<Database className="size-4 text-muted-foreground" />
					요약
				</CardTitle>
			</CardHeader>
			<CardContent className="space-y-2">
				{loading ? (
					<>
						<Skeleton className="h-16" />
						<Skeleton className="h-8" />
					</>
				) : (
					<>
						<div className="rounded-md border bg-background p-3 text-xs leading-relaxed text-muted-foreground">
							{summary || '요약 없음'}
						</div>
						{grades.length > 0 && (
							<div className="grid grid-cols-3 gap-1.5">
								{grades.map(([key, value]) => (
									<div key={key} className="min-w-0 rounded-md border bg-background px-2 py-1.5">
										<div className="truncate text-[10px] text-muted-foreground">{AREA_LABEL[key] ?? key}</div>
										<div className="mt-0.5 truncate text-xs font-semibold">{value}</div>
									</div>
								))}
							</div>
						)}
					</>
				)}
			</CardContent>
		</Card>
	);
}

function AxisSnapshotPanel({
	scan,
	loading,
}: {
	scan: CompanyScanAllResponse | undefined;
	loading: boolean;
}) {
	const axes: ScanAxis[] = ['capital', 'debt', 'workforce'];
	return (
		<Card>
			<CardHeader className="pb-2">
				<CardTitle className="flex items-center gap-2 text-sm">
					<BarChart3 className="size-4 text-muted-foreground" />
					환원 · 채무 · 인력
				</CardTitle>
			</CardHeader>
			<CardContent className="space-y-2">
				{loading ? (
					<>
						<Skeleton className="h-14" />
						<Skeleton className="h-14" />
						<Skeleton className="h-14" />
					</>
				) : (
					axes.map((axis) => {
						const pairs = scanPairs(scanPayload(scan, axis), axis).slice(0, 3);
						return (
							<div key={axis} className="rounded-md border bg-background p-2">
								<div className="mb-1.5 text-xs font-medium">{SCAN_LABEL[axis]}</div>
								{pairs.length ? (
									<div className="grid grid-cols-3 gap-1.5">
										{pairs.map((pair) => (
											<div key={`${axis}-${pair.label}`} className="min-w-0">
												<div className="truncate text-[10px] text-muted-foreground">{pair.label}</div>
												<div className="mt-0.5 truncate text-xs font-semibold tabular-nums">{pair.value}</div>
											</div>
										))}
									</div>
								) : (
									<div className="text-xs text-muted-foreground">데이터 없음</div>
								)}
							</div>
						);
					})
				)}
			</CardContent>
		</Card>
	);
}

function ScanPanel({
	scan,
	loading,
}: {
	scan: CompanyScanAllResponse | undefined;
	loading: boolean;
}) {
	return (
		<Card>
			<CardHeader className="pb-2">
				<CardTitle className="flex items-center gap-2 text-sm">
					<BarChart3 className="size-4 text-muted-foreground" />
					스캔 보드
				</CardTitle>
			</CardHeader>
			<CardContent>
				{loading ? (
					<Skeleton className="h-36" />
				) : (
					<Tabs defaultValue="governance" className="gap-3">
						<TabsList className="grid h-8 w-full grid-cols-4">
							{SCAN_AXES.map((axis) => (
								<TabsTrigger key={axis} value={axis} className="text-xs">
									{SCAN_LABEL[axis]}
								</TabsTrigger>
							))}
						</TabsList>
						{SCAN_AXES.map((axis) => {
							const payload = scanPayload(scan, axis);
							const pairs = scanPairs(payload, axis);
							return (
								<TabsContent key={axis} value={axis} className="mt-0">
									<div className="grid grid-cols-2 gap-2">
										{pairs.length ? (
											pairs.map((pair) => (
												<div key={pair.label} className="min-w-0 rounded-md border bg-background p-2">
													<div className="truncate text-[10px] text-muted-foreground">{pair.label}</div>
													<div className="mt-1 truncate text-sm font-semibold tabular-nums">{pair.value}</div>
												</div>
											))
										) : (
											<div className="col-span-2 rounded-md border bg-background p-3 text-xs text-muted-foreground">데이터 없음</div>
										)}
									</div>
								</TabsContent>
							);
						})}
					</Tabs>
				)}
			</CardContent>
		</Card>
	);
}

function DartFactsPanel({
	rows,
	loading,
	onOpenViewer,
}: {
	rows: CompanyIndexRow[];
	loading: boolean;
	onOpenViewer: () => void;
}) {
	return (
		<Card>
			<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
				<CardTitle className="flex items-center gap-2 text-sm">
					<FileText className="size-4 text-muted-foreground" />
					DART 팩트
				</CardTitle>
				<Button type="button" size="icon" variant="ghost" className="size-7" onClick={onOpenViewer} title="공시뷰어 열기">
					<FileText className="size-4" />
				</Button>
			</CardHeader>
			<CardContent className="space-y-2">
				{loading ? (
					<>
						<Skeleton className="h-12" />
						<Skeleton className="h-12" />
					</>
				) : rows.length ? (
					rows.slice(0, 5).map((row, i) => (
						<button
							key={`${row.chapter ?? row.topic ?? row.label}-${i}`}
							type="button"
							onClick={onOpenViewer}
							className="block w-full rounded-md border bg-background p-2 text-left hover:bg-accent"
						>
							<div className="flex items-center justify-between gap-2 text-xs">
								<span className="min-w-0 truncate font-medium">{row.label || row.topic || row.chapter}</span>
								<span className="shrink-0 font-mono text-[10px] text-muted-foreground">{row.periods || row.kind}</span>
							</div>
							{row.preview && <div className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">{row.preview}</div>}
						</button>
					))
				) : (
					<div className="rounded-md border bg-background p-3 text-xs text-muted-foreground">팩트 없음</div>
				)}
			</CardContent>
		</Card>
	);
}

function NetworkPanel({
	network,
	loading,
	sector,
	market,
}: {
	network: CompanyNetworkResponse | undefined;
	loading: boolean;
	sector?: string;
	market?: string;
}) {
	const counts = relationCount(network);
	const labels = Array.isArray(network?.nodes) ? network.nodes.map(nodeLabel).filter(Boolean).slice(0, 5) : [];
	return (
		<Card>
			<CardHeader className="pb-2">
				<CardTitle className="flex items-center gap-2 text-sm">
					<GitBranch className="size-4 text-muted-foreground" />
					관계 · 동종
				</CardTitle>
			</CardHeader>
			<CardContent className="space-y-2">
				{loading ? (
					<Skeleton className="h-24" />
				) : network?.available ? (
					<>
						<div className="grid grid-cols-2 gap-2">
							<div className="rounded-md border bg-background p-2">
								<div className="text-[10px] text-muted-foreground">노드</div>
								<div className="text-lg font-semibold tabular-nums">{counts.nodes}</div>
							</div>
							<div className="rounded-md border bg-background p-2">
								<div className="text-[10px] text-muted-foreground">연결</div>
								<div className="text-lg font-semibold tabular-nums">{counts.links}</div>
							</div>
						</div>
						<div className="flex flex-wrap gap-1">
							{labels.map((label) => (
								<Badge key={label} variant="outline" className="max-w-full truncate">
									{label}
								</Badge>
							))}
						</div>
					</>
				) : (
					<div className="rounded-md border bg-background p-3 text-xs">
						<div className="font-medium">{sector || '업종 정보 없음'}</div>
						<div className="mt-1 text-muted-foreground">{market || '시장 정보 없음'}</div>
					</div>
				)}
			</CardContent>
		</Card>
	);
}

function DisclosureIndexPanel({
	rows,
	onOpenViewer,
	loading,
}: {
	rows: CompanyIndexRow[];
	onOpenViewer: () => void;
	loading: boolean;
}) {
	return (
		<Card>
			<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
				<CardTitle className="flex items-center gap-2 text-sm">
					<FileText className="size-4 text-muted-foreground" />
					공시 인덱스
				</CardTitle>
				<Button type="button" size="icon" variant="ghost" className="size-7" onClick={onOpenViewer} title="공시뷰어 열기">
					<FileText className="size-4" />
				</Button>
			</CardHeader>
			<CardContent className="space-y-1">
				{loading ? (
					<>
						<Skeleton className="h-8" />
						<Skeleton className="h-8" />
						<Skeleton className="h-8" />
					</>
				) : rows.length ? (
					rows.slice(0, 8).map((row, i) => (
						<button
							key={`${row.topic ?? row.label}-${i}`}
							type="button"
							onClick={onOpenViewer}
							className="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-xs hover:bg-accent"
						>
							<span className="min-w-0 truncate">{row.label || row.topic}</span>
							<span className="shrink-0 font-mono text-[10px] text-muted-foreground">{row.periods || row.kind}</span>
						</button>
					))
				) : (
					<div className="rounded-md border bg-background p-3 text-xs text-muted-foreground">인덱스 없음</div>
				)}
			</CardContent>
		</Card>
	);
}

function StatementPanel({
	code,
}: {
	code: string;
}) {
	const [topic, setTopic] = useState<StatementTopic>('IS');
	const { data, isFetching } = useQuery({
		queryKey: dashKeys.companyTopic(code, topic),
		queryFn: () => fetchCompanyTopic(code, topic),
		staleTime: 10 * 60_000,
	});
	const payload = isTablePayload(data?.payload) ? data.payload : undefined;
	const columns = statementColumns(payload);
	const rows = statementRows(payload, columns);
	return (
		<Card>
			<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
				<CardTitle className="flex items-center gap-2 text-sm">
					<Database className="size-4 text-muted-foreground" />
					재무제표
				</CardTitle>
				{isFetching && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
			</CardHeader>
			<CardContent>
				<Tabs value={topic} onValueChange={(v) => setTopic(v as StatementTopic)} className="gap-3">
					<TabsList className="grid h-8 w-full grid-cols-4">
						{STATEMENTS.map((entry) => (
							<TabsTrigger key={entry.topic} value={entry.topic} className="text-xs">
								{entry.label}
							</TabsTrigger>
						))}
					</TabsList>
					<TabsContent value={topic} className="mt-0">
						{isFetching && !rows.length ? (
							<Skeleton className="h-52" />
						) : rows.length ? (
							<div className="max-h-[340px] overflow-auto rounded-md border tiny-scroll">
								<Table>
									<TableHeader>
										<TableRow>
											{columns.map((col) => (
												<TableHead key={col} className={cn('h-8 text-[11px]', periodColumn(col) && 'text-right')}>
													{col}
												</TableHead>
											))}
										</TableRow>
									</TableHeader>
									<TableBody>
										{rows.map((row, i) => (
											<TableRow key={String(row[columns[0]] ?? i)}>
												{columns.map((col, colIndex) => (
													<TableCell
														key={col}
														className={cn('max-w-[160px] truncate py-1.5 text-xs', colIndex > 0 && 'text-right tabular-nums')}
														title={valueText(row[col])}
													>
														{valueText(row[col])}
													</TableCell>
												))}
											</TableRow>
										))}
									</TableBody>
								</Table>
							</div>
						) : (
							<div className="rounded-md border bg-background p-3 text-xs text-muted-foreground">표시할 원표 없음</div>
						)}
					</TabsContent>
				</Tabs>
			</CardContent>
		</Card>
	);
}

export function TerminalTab({ code }: Props) {
	const navigate = useNavigate();
	const [query, setQuery] = useState('');
	const [hits, setHits] = useState<SearchHit[]>([]);
	const [source, setSource] = useState<'all' | 'disclosure' | 'news_rss' | 'news_gdelt'>('disclosure');
	const start = useMemo(() => ninetyDaysAgo(), []);
	const end = useMemo(() => today(), []);

	const { data: meta } = useQuery({
		queryKey: dashKeys.companyMeta(code),
		queryFn: () => fetchCompanyMeta(code),
		staleTime: 10 * 60_000,
	});
	const { data: incomeStatement, isLoading: incomeLoading } = useQuery({
		queryKey: dashKeys.companyTopic(code, 'IS'),
		queryFn: () => fetchCompanyTopic(code, 'IS'),
		staleTime: 10 * 60_000,
	});
	const incomePayload = isTablePayload(incomeStatement?.payload) ? incomeStatement.payload : undefined;
	const companyReady = !!incomePayload;
	const { data: balanceStatement, isLoading: balanceLoading } = useQuery({
		queryKey: dashKeys.companyTopic(code, 'BS'),
		queryFn: () => fetchCompanyTopic(code, 'BS'),
		staleTime: 10 * 60_000,
		enabled: companyReady,
	});
	const { data: cashflowStatement, isLoading: cashflowLoading } = useQuery({
		queryKey: dashKeys.companyTopic(code, 'CF'),
		queryFn: () => fetchCompanyTopic(code, 'CF'),
		staleTime: 10 * 60_000,
		enabled: companyReady,
	});
	const { data: bundle, isLoading: bundleLoading } = useQuery<TerminalBundle>({
		queryKey: dashKeys.terminalBundle(code),
		queryFn: async () => {
			const [indexResult, scanResult, insightsResult, networkResult] = await Promise.all([
				optional(fetchCompanyIndex(code)),
				optional(fetchCompanyScanAll(code)),
				optional(fetchCompanyInsights(code)),
				optional(fetchCompanyNetwork(code, 1)),
			]);
			return {
				index: indexResult,
				scan: scanResult,
				insights: insightsResult,
				network: networkResult,
			};
		},
		staleTime: 10 * 60_000,
		enabled: companyReady,
	});

	const metrics = collectStatementMetrics(
		incomePayload,
		isTablePayload(balanceStatement?.payload) ? balanceStatement.payload : undefined,
		isTablePayload(cashflowStatement?.payload) ? cashflowStatement.payload : undefined,
	);
	const metric = metrics[0];
	const financialLoading = incomeLoading || balanceLoading || cashflowLoading;
	const rows = indexRows(bundle?.index?.payload);
	const scan = bundle?.scan;
	const insights = bundle?.insights;
	const network = bundle?.network;
	const availableScanCount = SCAN_AXES.filter((axis) => scanPayload(scan, axis)).length;

	async function runSearch(value = query) {
		if (!value.trim()) return;
		const results = await searchCompanies(value.trim(), 8);
		setHits(results);
	}

	function pickCompany(nextCode: string) {
		navigate({ to: '/analysis/$code/terminal', params: { code: nextCode }, search: { period: 'quarterly' } });
	}

	function openViewer() {
		navigate({ to: '/analysis/$code/viewer', params: { code }, search: { period: 'quarterly' } });
	}

	return (
		<div className="grid h-full min-h-0 grid-cols-[280px_minmax(0,1fr)_400px] overflow-hidden bg-background">
			<aside className="min-h-0 overflow-y-auto border-r bg-card/40 p-3 tiny-scroll">
				<div className="flex items-center gap-2">
					<TerminalIcon className="size-4 text-muted-foreground" />
					<div className="text-sm font-semibold">터미널</div>
				</div>
				<form
					className="mt-3"
					onSubmit={(e) => {
						e.preventDefault();
						void runSearch();
					}}
				>
					<div className="relative">
						<Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
						<Input
							value={query}
							onChange={(e) => setQuery(e.target.value)}
							placeholder="종목코드 · 회사명"
							className="h-9 pl-8 text-xs"
						/>
					</div>
				</form>
				<div className="mt-3 space-y-1">
					{hits.map((hit) => (
						<button
							key={hit.stockCode}
							type="button"
							onClick={() => pickCompany(hit.stockCode)}
							className={cn(
								'flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-xs hover:bg-accent',
								hit.stockCode === code && 'bg-accent text-accent-foreground',
							)}
						>
							<span className="min-w-0 truncate">{hit.corpName}</span>
							<span className="font-mono text-[10px] text-muted-foreground">{hit.stockCode}</span>
						</button>
					))}
				</div>
				<div className="mt-5 space-y-3">
					<Card>
						<CardHeader className="pb-2">
							<CardTitle className="flex items-center gap-2 text-sm">
								<Building2 className="size-4 text-muted-foreground" />
								회사
							</CardTitle>
						</CardHeader>
						<CardContent>
							<div className="truncate text-sm font-semibold">{meta?.corpName || code}</div>
							<div className="mt-1 font-mono text-xs text-muted-foreground">{code}</div>
							<div className="mt-3 flex flex-wrap gap-1">
								{meta?.market && <Badge variant="secondary">{meta.market}</Badge>}
								{meta?.sector && <Badge variant="outline">{meta.sector}</Badge>}
								{availableScanCount > 0 && <Badge variant="outline">scan {availableScanCount}</Badge>}
							</div>
						</CardContent>
					</Card>
					<DisclosureIndexPanel rows={rows} onOpenViewer={openViewer} loading={bundleLoading} />
				</div>
			</aside>

			<main className="min-h-0 overflow-y-auto p-3 tiny-scroll">
				<div className="mb-3 flex items-center justify-between gap-3">
					<div className="min-w-0">
						<div className="text-xs text-muted-foreground">공시 기본 · 최근 90일</div>
						<h1 className="truncate text-lg font-semibold">{meta?.corpName || code} 터미널</h1>
					</div>
					<div className="flex items-center gap-2 text-xs text-muted-foreground">
						<Clock className="size-3.5" />
						{new Date().toLocaleTimeString('ko-KR', { hour12: false })} KST
					</div>
				</div>
				<div className="space-y-3">
					<MetricStrip metrics={metrics} loading={financialLoading} />
					<Card>
						<CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
							<CardTitle className="flex items-center gap-2 text-sm">
								<TrendingUp className="size-4 text-muted-foreground" />
								가격 · 공시 · 뉴스 이벤트
							</CardTitle>
							<div className="flex gap-1">
								{(['all', 'disclosure', 'news_rss', 'news_gdelt'] as const).map((s) => (
									<Button key={s} type="button" size="sm" variant={source === s ? 'default' : 'outline'} onClick={() => setSource(s)}>
										{s === 'all' ? '전체' : s === 'disclosure' ? '공시' : s === 'news_rss' ? 'RSS' : 'GDELT'}
									</Button>
								))}
							</div>
						</CardHeader>
						<CardContent>
							{companyReady ? (
								<PriceEventChart
									stockCode={code}
									start={start}
									end={end}
									market="KR"
									source={source}
									showShocks={false}
									showRegime={false}
									height={430}
								/>
							) : (
								<Skeleton className="h-[430px]" />
							)}
						</CardContent>
					</Card>
					<StatementPanel code={code} />
				</div>
			</main>

			<aside className="min-h-0 overflow-y-auto border-l bg-card/40 p-3 tiny-scroll">
				<div className="flex items-center justify-between gap-2">
					<div className="flex items-center gap-2 text-sm font-semibold">
						<Database className="size-4 text-muted-foreground" />
						수치 패널
					</div>
					{metric && <Badge variant="outline">{metric.label}</Badge>}
				</div>
				<div className="mt-3 grid gap-3">
					<InsightSummaryPanel insights={insights} loading={bundleLoading} />
					<RiskPanel insights={insights} scan={scan} loading={bundleLoading} />
					<AxisSnapshotPanel scan={scan} loading={bundleLoading} />
					<ScanPanel scan={scan} loading={bundleLoading} />
					<NetworkPanel network={network} loading={bundleLoading} sector={meta?.sector} market={meta?.market} />
					<DartFactsPanel rows={rows} loading={bundleLoading} onOpenViewer={openViewer} />
					<Card>
						<CardHeader className="pb-2">
							<CardTitle className="flex items-center gap-2 text-sm">
								<AlertTriangle className="size-4 text-muted-foreground" />
								출처
							</CardTitle>
						</CardHeader>
						<CardContent className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
							{TERMINAL_DATA_SOURCES.map((sourceLabel) => (
								<div key={sourceLabel} className="rounded-md border bg-background p-2">
									{sourceLabel}
								</div>
							))}
						</CardContent>
					</Card>
				</div>
			</aside>
		</div>
	);
}
