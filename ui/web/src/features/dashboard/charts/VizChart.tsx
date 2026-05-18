// View → shadcn ChartContainer + recharts 디스패처.
// catalog 의 series.color (hex) 를 chartConfig 로 변환 → ChartStyle 이 자동으로
// --color-{key} CSS 변수 inject. recharts Bar/Line 의 fill/stroke 는 var(--color-...).
// dark/light 토큰 매핑은 palette.applyShadcnPalette 가 catalog hex → CSS 변수 치환.

import {
	Area,
	Bar,
	BarChart,
	CartesianGrid,
	ComposedChart,
	Line,
	LineChart,
	PolarAngleAxis,
	PolarGrid,
	Radar,
	RadarChart,
	ReferenceLine,
	XAxis,
	YAxis,
} from 'recharts';

import {
	ChartContainer,
	ChartTooltip,
	ChartTooltipContent,
	type ChartConfig,
} from '@/components/ui/chart';
import { formatAxisTick, formatValue } from '@/lib/format';
import { applyShadcnPalette } from './palette';
import { makePeriodFormatter } from './period';
import { ComparisonTable } from '../cards/ComparisonTable';
import { DiffView } from '../cards/DiffView';
import { KpiTile } from '../cards/KpiTile';
import { NarrativeBridge } from '../cards/NarrativeBridge';
import { PhaseIndicator } from '../cards/PhaseIndicator';
import { ScoreBadge } from '../cards/ScoreBadge';
import { TopList } from '../cards/TopList';
import { GaugeChart } from './GaugeChart';
import { HeatmapChart } from './HeatmapChart';
import { SankeyChart } from './SankeyChart';
import { ScatterChart } from './ScatterChart';
import type { RechartsSpec, RechartsSeries } from '../api/client';

interface Props {
	spec: RechartsSpec;
	height?: number;
	// 카드 size — 카탈로그 colSpan × rowSpan. 카드 컴포넌트 내부 layout dispatch 용.
	// 1×1 KpiTile 은 값+미니 spark 옆 배치, 2×2+ 는 spark 본체 + 값 오버레이.
	size?: { w: number; h: number };
}

function toRows(spec: RechartsSpec): Array<Record<string, number | string | null>> {
	return spec.categories.map((cat, i) => {
		const row: Record<string, number | string | null> = { _x: cat };
		for (const s of spec.series) row[s.key] = s.data[i] ?? null;
		return row;
	});
}

function buildConfig(series: RechartsSeries[]): ChartConfig {
	const cfg: ChartConfig = {};
	for (const s of series) cfg[s.key] = { label: s.label, color: s.color };
	return cfg;
}

function hasRightAxis(series: RechartsSeries[]) {
	return series.some((s) => s.axis === 'right');
}

// axis 의 unit 추론 — 해당 axis 의 series 들이 모두 같은 unit 이면 그걸 사용. 혼합이면 빈 문자열.
function dominantUnit(series: RechartsSeries[], side: 'left' | 'right'): string {
	const units = series.filter((s) => (s.axis ?? 'left') === side).map((s) => s.unit ?? '');
	const distinct = Array.from(new Set(units.filter(Boolean)));
	return distinct.length === 1 ? distinct[0] : '';
}

function makeAxisFormatter(unit: string) {
	return (v: unknown) => formatAxisTick(v, unit);
}

function ErrorState({ title, error }: { title: string; error?: string }) {
	return (
		<div className="flex h-full flex-col items-center justify-center gap-1 p-4 text-center text-xs text-muted-foreground">
			<div className="font-medium text-foreground">{title}</div>
			<div className="line-clamp-3">{error || '데이터 없음'}</div>
		</div>
	);
}

function TrendChart({ spec, height }: { spec: RechartsSpec; height: number }) {
	const rows = toRows(spec);
	const config = buildConfig(spec.series);
	const types = new Set(spec.series.map((s) => s.type || 'bar'));
	const onlyLines = types.size === 1 && types.has('line');
	const onlyBars = types.size === 1 && types.has('bar');
	const stacked = Boolean(spec.options?.stacked);
	const rightAxis = hasRightAxis(spec.series);
	const refLines = (spec.options?.refLines as Array<{ value: number; label?: string }> | undefined) || [];
	const fmtPeriod = makePeriodFormatter(spec.categories);

	const dense = spec.categories.length > 16;
	const renderSeries = spec.series.map((s) => {
		const t = s.type || (onlyLines ? 'line' : 'bar');
		const axisId = s.axis === 'right' ? 'right' : 'left';
		const colorVar = `var(--color-${s.key})`;
		if (t === 'line') {
			return (
				<Line
					key={s.key}
					yAxisId={axisId}
					type="monotone"
					dataKey={s.key}
					name={s.label}
					stroke={colorVar}
					strokeWidth={2.5}
					dot={dense ? { r: 1.5, fill: colorVar, strokeWidth: 0 } : { r: 3, fill: colorVar }}
					activeDot={{ r: 5, fill: colorVar, strokeWidth: 2, stroke: 'var(--background)' }}
					connectNulls
				/>
			);
		}
		if (t === 'area') {
			return (
				<Area
					key={s.key}
					yAxisId={axisId}
					type="monotone"
					dataKey={s.key}
					name={s.label}
					stroke={colorVar}
					fill={colorVar}
					fillOpacity={0.25}
					strokeWidth={1.5}
					stackId={stacked && s.stack ? s.stack : undefined}
					connectNulls
				/>
			);
		}
		return (
			<Bar
				key={s.key}
				yAxisId={axisId}
				dataKey={s.key}
				name={s.label}
				fill={colorVar}
				radius={[1, 1, 0, 0]}
				stackId={stacked && s.stack ? s.stack : stacked ? 'stack' : undefined}
			/>
		);
	});

	const Wrapper = onlyLines ? LineChart : onlyBars ? BarChart : ComposedChart;

	return (
		<ChartContainer config={config} className="!aspect-auto w-full" style={{ height, minWidth: 0 }}>
			<Wrapper
				accessibilityLayer
				data={rows}
				margin={{ top: 6, right: 12, bottom: 4, left: 4 }}
				barCategoryGap={dense ? '5%' : '15%'}
				barGap={1}
			>
				<CartesianGrid vertical={false} strokeDasharray="3 3" />
				<XAxis
					dataKey="_x"
					tickLine={false}
					axisLine={false}
					tickMargin={6}
					fontSize={10}
					tickFormatter={fmtPeriod}
					minTickGap={dense ? 24 : 8}
					interval="preserveStartEnd"
				/>
				<YAxis
					yAxisId="left"
					tickLine={false}
					axisLine={false}
					tickFormatter={makeAxisFormatter(dominantUnit(spec.series, 'left'))}
					fontSize={10}
					width={44}
				/>
				{rightAxis && (
					<YAxis
						yAxisId="right"
						orientation="right"
						tickLine={false}
						axisLine={false}
						tickFormatter={makeAxisFormatter(dominantUnit(spec.series, 'right'))}
						fontSize={10}
						width={44}
					/>
				)}
				{refLines.map((rl, i) => (
					<ReferenceLine
						key={`ref-${i}`}
						yAxisId="left"
						y={rl.value}
						stroke="hsl(var(--muted-foreground))"
						strokeDasharray="4 4"
						label={{ value: rl.label, fontSize: 10 }}
					/>
				))}
				<ChartTooltip
					content={
						<ChartTooltipContent
							indicator="dot"
							labelFormatter={(label) => fmtPeriod(String(label))}
							formatter={(value, name) => {
								const ser = spec.series.find((s) => s.label === name || s.key === name);
								return [formatValue(value as number, ser?.unit ?? ''), ser?.label ?? String(name)];
							}}
						/>
					}
				/>
				{/* v3-r6 — chart canvas legend 제거. mini-table 가 legend 역할 (color-dot + 라벨 + 값). chart canvas 침범 회피. */}
				{renderSeries}
			</Wrapper>
		</ChartContainer>
	);
}

function RadarBlock({ spec, height }: { spec: RechartsSpec; height: number }) {
	const config = buildConfig(spec.series);
	const rows = spec.categories.map((cat, i) => {
		const row: Record<string, string | number | null> = { _x: cat };
		for (const s of spec.series) row[s.key] = s.data[i] ?? null;
		return row;
	});
	return (
		<ChartContainer config={config} className="!aspect-auto w-full" style={{ height, minWidth: 0 }}>
			<RadarChart data={rows}>
				<PolarGrid />
				<PolarAngleAxis dataKey="_x" fontSize={10} />
				{spec.series.map((s) => (
					<Radar
						key={s.key}
						dataKey={s.key}
						name={s.label}
						stroke={`var(--color-${s.key})`}
						fill={`var(--color-${s.key})`}
						fillOpacity={0.3}
					/>
				))}
				<ChartTooltip content={<ChartTooltipContent indicator="dot" />} />
				{/* v3-r6 — chart canvas legend 제거. mini-table 가 legend 역할 (color-dot + 라벨 + 값). chart canvas 침범 회피. */}
			</RadarChart>
		</ChartContainer>
	);
}

// 단일 KPI 카드 — 1 entry = 1 tile (bento 1×1 default).
// 백워드 호환: spec.tiles 가 여러 개여도 첫 번째만 렌더 (옛 strip catalog 잔존 시).
function KpiTileSingle({ spec, size }: { spec: RechartsSpec; size?: { w: number; h: number } }) {
	const tiles = spec.tiles ?? [];
	if (!tiles.length) {
		return <ErrorState title={spec.title} error="KPI 데이터 없음" />;
	}
	const t = tiles[0];
	const deltaPct =
		t.value != null && t.prev != null && t.prev !== 0
			? ((t.value - t.prev) / Math.abs(t.prev)) * 100
			: null;
	const tone: 'positive' | 'negative' | 'neutral' =
		t.intent === 'positive' ? 'positive' : t.intent === 'negative' ? 'negative' : 'neutral';
	return (
		<div className="h-full w-full">
			<KpiTile
				label={t.label}
				value={t.value ?? null}
				unit={t.unit}
				deltaPct={deltaPct}
				subtitle={t.subtitle}
				tone={tone}
				sparkline={t.sparkline}
				rangeMin={t.rangeMin}
				rangeMax={t.rangeMax}
				size={size}
			/>
		</div>
	);
}

export function VizChart({ spec: rawSpec, height = 280, size }: Props) {
	const spec = applyShadcnPalette(rawSpec);

	if (spec.componentType === 'Error' || spec.error) {
		return (
			<div style={{ height }} className="w-full">
				<ErrorState title={spec.title} error={spec.error} />
			</div>
		);
	}

	// kind 별 dispatch — 시계열 외 카드 패턴.
	switch (spec.kind) {
		case 'kpiTile':
			return <KpiTileSingle spec={spec} size={size} />;
		case 'diffView':
			return (
				<DiffView
					items={(spec.tiles ?? []).map((t) => ({
						label: t.label,
						current: t.value ?? null,
						previous: t.prev ?? null,
						unit: t.unit,
					}))}
					periodLabel={spec.periodLabel ?? 'YoY'}
				/>
			);
		case 'topList': {
			if (!spec.items?.length) return <ErrorState title={spec.title} error="신호 없음" />;
			return (
				<TopList
					items={spec.items.map((it) => ({
						label: it.label,
						value: it.value ?? 0,
						unit: it.unit,
						delta: it.delta ?? undefined,
						description: it.description,
					}))}
				/>
			);
		}
		case 'comparisonTable': {
			if (!spec.rows?.length)
				return <ErrorState title={spec.title} error="동종 비교 데이터 없음" />;
			return (
				<ComparisonTable
					rows={spec.rows.map((r) => ({
						metric: r.label,
						value: r.self ?? null,
						peer: r.peerMedian ?? null,
						percentile: r.percentile ?? null,
						unit: r.unit ?? '',
					}))}
				/>
			);
		}
		case 'gauge': {
			if (spec.value == null)
				return <ErrorState title={spec.title} error="게이지 데이터 없음" />;
			return (
				<GaugeChart
					value={spec.value}
					min={spec.minValue ?? 0}
					max={spec.maxValue ?? 100}
					bands={(spec.bands ?? []).map((b) => ({
						from: b.fromValue,
						to: b.toValue,
						label: b.label,
						tone: (b.intent === 'primary' ? 'neutral' : (b.intent ?? 'neutral')) as
							| 'positive'
							| 'neutral'
							| 'accent'
							| 'negative',
					}))}
					hint={spec.subtitle}
					unit={spec.options?.unit as string | undefined}
					height={height}
				/>
			);
		}
		case 'phaseIndicator': {
			if (!spec.phases?.length)
				return <ErrorState title={spec.title} error="단계 데이터 없음" />;
			return (
				<PhaseIndicator
					stages={spec.phases}
					activeIndex={spec.current ?? 0}
					confidence={spec.confidence ?? undefined}
					hint={spec.subtitle}
				/>
			);
		}
		case 'sankey': {
			if (!spec.nodes?.length || !spec.links?.length)
				return <ErrorState title={spec.title} error="흐름 데이터 없음" />;
			return <SankeyChart nodes={spec.nodes} links={spec.links} height={height} />;
		}
		case 'scatter': {
			if (!spec.points?.length)
				return <ErrorState title={spec.title} error="산점 데이터 없음" />;
			return (
				<ScatterChart
					points={spec.points}
					xLabel={spec.xLabel}
					yLabel={spec.yLabel}
					xUnit={spec.xUnit}
					yUnit={spec.yUnit}
					xRef={spec.xRef ?? undefined}
					yRef={spec.yRef ?? undefined}
					height={height}
				/>
			);
		}
		case 'matrix': {
			if (!spec.cells?.length)
				return <ErrorState title={spec.title} error="격자 데이터 없음" />;
			return (
				<HeatmapChart
					cells={spec.cells.map((c) => ({
						row: c.row,
						col: c.col,
						value: c.value,
						unit: c.unit,
					}))}
					rowOrder={spec.rowOrder}
					colOrder={spec.colOrder}
					tone={spec.tone}
					height={height}
				/>
			);
		}
		case 'radar': {
			if (!spec.series?.length || !spec.categories?.length)
				return <ErrorState title={spec.title} error="레이더 데이터 없음" />;
			return <RadarBlock spec={spec} height={height} />;
		}
		case 'narrativeBridge': {
			return (
				<NarrativeBridge
					transitions={spec.transitions ?? []}
					summaryLine={spec.summaryLine}
				/>
			);
		}
		case 'scoreBadge': {
			return (
				<ScoreBadge
					grade={spec.grade}
					overallScore={spec.overallScore}
					dimensions={spec.dimensions}
					summaryLine={spec.summaryLine}
				/>
			);
		}
		default:
			break;
	}

	const empty = !spec.series.length || !spec.categories.length;
	if (empty) {
		return (
			<div style={{ height }} className="w-full">
				<ErrorState title={spec.title} error="시계열 데이터 없음" />
			</div>
		);
	}
	if (spec.componentType === 'RadarChart') return <RadarBlock spec={spec} height={height} />;
	return <TrendChart spec={spec} height={height} />;
}
