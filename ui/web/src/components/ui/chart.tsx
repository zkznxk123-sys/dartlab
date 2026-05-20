// shadcn/ui Chart — recharts 위에 ChartContainer/Tooltip/Legend wrapper.
// CSS 변수 (--chart-1 ~ 8) 로 색상 토큰화, dark/light 자동 추종.

import * as React from 'react';
import * as RechartsPrimitive from 'recharts';

import { cn } from '@/lib/utils';

const THEMES = { light: '', dark: '.dark' } as const;

export type ChartConfig = {
	[k in string]: {
		label?: React.ReactNode;
		icon?: React.ComponentType;
	} & ({ color?: string; theme?: never } | { color?: never; theme: Record<keyof typeof THEMES, string> });
};

type ChartContextProps = { config: ChartConfig };

const ChartContext = React.createContext<ChartContextProps | null>(null);

function useChart() {
	const ctx = React.useContext(ChartContext);
	if (!ctx) throw new Error('useChart must be used within <ChartContainer />');
	return ctx;
}

interface ChartContainerProps extends React.ComponentProps<'div'> {
	config: ChartConfig;
	children: React.ComponentProps<typeof RechartsPrimitive.ResponsiveContainer>['children'];
}

export function ChartContainer({ id, className, children, config, ...props }: ChartContainerProps) {
	const uniqueId = React.useId();
	const chartId = `chart-${id || uniqueId.replace(/:/g, '')}`;
	return (
		<ChartContext.Provider value={{ config }}>
			<div
				data-chart={chartId}
				className={cn(
					// shadcn default: `flex aspect-video justify-center` → `block relative w-full`.
					// 이유: `flex` parent 안 ResponsiveContainer 가 첫 paint frame 에 부모 dim
					// 측정 실패 → width=-1 / height=-1 워닝 발생 (AreaChart-*.js:14). `block` +
					// `relative` 로 ResponsiveContainer 의 부모 dim 안정 측정. aspect-video 는
					// 호출자가 style.height 명시하므로 불필요. text-xs 와 recharts selector
					// 토큰은 그대로 (shadcn 색·음영 룰 준수).
					"relative block w-full text-xs [&_.recharts-cartesian-axis-tick_text]:fill-muted-foreground [&_.recharts-cartesian-grid_line[stroke='#ccc']]:stroke-border/50 [&_.recharts-curve.recharts-tooltip-cursor]:stroke-border [&_.recharts-dot[stroke='#fff']]:stroke-transparent [&_.recharts-layer]:outline-none [&_.recharts-polar-grid_[stroke='#ccc']]:stroke-border [&_.recharts-radial-bar-background-sector]:fill-muted [&_.recharts-rectangle.recharts-tooltip-cursor]:fill-muted [&_.recharts-reference-line_[stroke='#ccc']]:stroke-border [&_.recharts-sector[stroke='#fff']]:stroke-transparent [&_.recharts-sector]:outline-none [&_.recharts-surface]:outline-none",
					className,
				)}
				{...props}
			>
				<ChartStyle id={chartId} config={config} />
				{/* block parent 안에서 width="100%" 가 정확 측정. 옛 99% 트릭은 flex parent
				    의 first-frame 0 측정 회피용이었으나 block + relative 로 근본 차단. */}
				<RechartsPrimitive.ResponsiveContainer width="100%" height="100%" minHeight={0} minWidth={0}>
					{children}
				</RechartsPrimitive.ResponsiveContainer>
			</div>
		</ChartContext.Provider>
	);
}

function ChartStyle({ id, config }: { id: string; config: ChartConfig }) {
	const colorConfig = Object.entries(config).filter(([, v]) => v.theme || v.color);
	if (!colorConfig.length) return null;
	return (
		<style
			dangerouslySetInnerHTML={{
				__html: Object.entries(THEMES)
					.map(
						([theme, prefix]) => `
${prefix} [data-chart=${id}] {
${colorConfig
	.map(([k, item]) => {
		const color = item.theme?.[theme as keyof typeof item.theme] || item.color;
		return color ? `  --color-${k}: ${color};` : null;
	})
	.filter(Boolean)
	.join('\n')}
}
`,
					)
					.join('\n'),
			}}
		/>
	);
}

export const ChartTooltip = RechartsPrimitive.Tooltip;

interface ChartTooltipContentProps {
	active?: boolean;
	payload?: Array<{
		dataKey?: string;
		name?: string;
		value?: number | string;
		color?: string;
		payload?: Record<string, unknown>;
	}>;
	label?: string | number;
	labelFormatter?: (label: string, payload: Array<unknown>) => React.ReactNode;
	formatter?: (
		value: number | string,
		name: string,
		item: unknown,
		index: number,
		payload: unknown,
	) => React.ReactNode;
	color?: string;
	className?: string;
	hideLabel?: boolean;
	hideIndicator?: boolean;
	indicator?: 'line' | 'dot' | 'dashed';
	nameKey?: string;
	labelKey?: string;
}

export const ChartTooltipContent = React.forwardRef<HTMLDivElement, ChartTooltipContentProps>(
	(
		{
			active,
			payload,
			className,
			indicator = 'dot',
			hideLabel = false,
			hideIndicator = false,
			label,
			labelFormatter,
			formatter,
			color,
			nameKey,
			labelKey,
		},
		ref,
	) => {
		const { config } = useChart();

		const tooltipLabel = React.useMemo(() => {
			if (hideLabel || !payload?.length) return null;
			const [item] = payload as Array<{ dataKey?: string; name?: string; value?: number; payload?: Record<string, unknown> }>;
			const key = `${labelKey || item.dataKey || item.name || 'value'}`;
			const itemConfig = getPayloadConfigFromPayload(config, item, key);
			const value =
				!labelKey && typeof label === 'string'
					? config[label as keyof typeof config]?.label || label
					: itemConfig?.label;
			if (labelFormatter) {
				return <div className={cn('font-medium')}>{labelFormatter(value as string, payload as never)}</div>;
			}
			if (!value) return null;
			return <div className={cn('font-medium')}>{value}</div>;
		}, [label, labelFormatter, payload, hideLabel, labelKey, config]);

		if (!active || !payload?.length) return null;

		const nestLabel = payload.length === 1 && indicator !== 'dot';

		return (
			<div
				ref={ref}
				className={cn(
					// label 좌·value 우 정렬 위해 충분한 min-width + nowrap. 운영자 명시 2026-05-19.
					'grid min-w-[11rem] items-start gap-1.5 rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl',
					className,
				)}
			>
				{!nestLabel ? tooltipLabel : null}
				<div className="grid gap-1">
					{(payload as Array<{ dataKey?: string; name?: string; value?: number; color?: string; payload?: Record<string, unknown> }>).map(
						(item, index) => {
							const key = `${nameKey || item.name || item.dataKey || 'value'}`;
							const itemConfig = getPayloadConfigFromPayload(config, item, key);
							const indicatorColor = color || item.color;
							return (
								<div
									key={item.dataKey || index}
									className={cn(
										// flex-nowrap — label / value 같은 줄 양끝 정렬 보장. 너비 좁아 wrap 시 value 가 label 앞으로 가는 회귀 차단.
										'flex w-full flex-nowrap items-center gap-2.5 [&>svg]:h-2.5 [&>svg]:w-2.5 [&>svg]:text-muted-foreground',
									)}
								>
									{(() => {
										// formatter 가 있어도 indicator + 라벨좌·값우 layout 으로 정렬한다.
										// recharts convention: formatter return [content, name]. content=값, name=라벨.
										let displayLabel: React.ReactNode = itemConfig?.label || item.name;
										let displayValue: React.ReactNode =
											item.value !== undefined ? formatTooltipNumber(item.value as number) : null;
										if (formatter && item?.value !== undefined && item.name) {
											const r = formatter(item.value as never, item.name as never, item as never, index, item.payload as never);
											if (Array.isArray(r)) {
												// [content, name] — content 가 값(이미 단위 포맷), name 이 라벨.
												if (r[0] !== undefined) displayValue = r[0] as React.ReactNode;
												if (r[1] !== undefined) displayLabel = r[1] as React.ReactNode;
											} else if (r !== undefined && r !== null) {
												// 단순 ReactNode 반환 — 값 자리에 박음.
												displayValue = r as React.ReactNode;
											}
										}
										return (
											<>
												{itemConfig?.icon ? (
													<itemConfig.icon />
												) : (
													!hideIndicator && (
														<div
															className={cn('shrink-0 rounded-[2px] border-[--color-border] bg-[--color-bg]', {
																'h-2.5 w-2.5': indicator === 'dot',
																'w-1 h-3': indicator === 'line',
																'w-0 border-[1.5px] border-dashed bg-transparent': indicator === 'dashed',
																'my-0.5': nestLabel && indicator === 'dashed',
															})}
															style={
																{
																	'--color-bg': indicatorColor,
																	'--color-border': indicatorColor,
																} as React.CSSProperties
															}
														/>
													)
												)}
												<span className="min-w-0 flex-1 truncate text-left text-muted-foreground">
													{displayLabel}
												</span>
												{displayValue != null && (
													<span className="shrink-0 text-right font-mono font-medium tabular-nums text-foreground">
														{displayValue}
													</span>
												)}
											</>
										);
									})()}
								</div>
							);
						},
					)}
				</div>
			</div>
		);
	},
);
ChartTooltipContent.displayName = 'ChartTooltipContent';

function formatTooltipNumber(v: unknown): string {
	if (v === null || v === undefined || typeof v !== 'number' || !Number.isFinite(v)) return '–';
	const abs = Math.abs(v);
	if (abs >= 1e12) {
		const t = v / 1e12;
		return (Math.abs(t) >= 10 ? Math.round(t).toLocaleString() : t.toFixed(1)) + '조';
	}
	if (abs >= 1e8) {
		const e = v / 1e8;
		return (Math.abs(e) >= 100 ? Math.round(e).toLocaleString() : e.toFixed(1)) + '억';
	}
	if (abs >= 1e4) return Math.round(v / 1e4).toLocaleString() + '만';
	if (abs >= 1000) return v.toLocaleString();
	if (Number.isInteger(v)) return v.toString();
	if (abs >= 100) return v.toFixed(0);
	if (abs >= 10) return v.toFixed(1);
	return v.toFixed(2);
}

export const ChartLegend = RechartsPrimitive.Legend;

interface ChartLegendContentProps extends React.ComponentProps<'div'> {
	hideIcon?: boolean;
	nameKey?: string;
	payload?: Array<{ value?: string; dataKey?: string; color?: string }>;
	verticalAlign?: 'top' | 'bottom' | 'middle';
}

export function ChartLegendContent({ className, hideIcon = false, payload, verticalAlign = 'bottom', nameKey }: ChartLegendContentProps) {
	const { config } = useChart();
	if (!payload?.length) return null;
	return (
		<div className={cn('flex items-center justify-center gap-4 flex-wrap', verticalAlign === 'top' ? 'pb-4' : 'pt-4 pb-2', className)}>
			{payload.map((item) => {
				const key = `${nameKey || item.dataKey || 'value'}`;
				const itemConfig = getPayloadConfigFromPayload(config, item, key);
				return (
					<div key={item.value} className={cn('flex items-center gap-1.5 [&>svg]:h-3 [&>svg]:w-3 [&>svg]:text-muted-foreground')}>
						{itemConfig?.icon && !hideIcon ? (
							<itemConfig.icon />
						) : (
							<div className="h-2 w-2 shrink-0 rounded-[2px]" style={{ backgroundColor: item.color }} />
						)}
						{itemConfig?.label || item.value}
					</div>
				);
			})}
		</div>
	);
}

function getPayloadConfigFromPayload(
	config: ChartConfig,
	payload: unknown,
	key: string,
): ChartConfig[string] | undefined {
	if (!payload || typeof payload !== 'object') return undefined;
	const payloadObj = payload as Record<string, unknown>;
	const payloadPayload =
		'payload' in payloadObj && typeof payloadObj.payload === 'object' && payloadObj.payload !== null
			? (payloadObj.payload as Record<string, unknown>)
			: undefined;
	let configKey: string = key;
	if (key in payloadObj && typeof payloadObj[key] === 'string') configKey = payloadObj[key] as string;
	else if (payloadPayload && key in payloadPayload && typeof payloadPayload[key] === 'string')
		configKey = payloadPayload[key] as string;
	return configKey in config ? config[configKey] : config[key];
}
