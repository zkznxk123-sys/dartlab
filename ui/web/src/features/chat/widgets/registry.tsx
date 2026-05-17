// VIEW_SPEC 의 spec.kind 별 위젯 dispatcher.
// dartlab CompileVisual chartType: line/bar/table/radar/waterfall/heatmap/histogram/combo/sparkline/pie/price-chart
// 본 PR 범위: line · area · bar · table · kpi. 그 외는 JSON fallback.
import { BarChartWidget } from './BarChartWidget';
import { KpiWidget } from './KpiWidget';
import { LineChartWidget } from './LineChartWidget';
import { TableWidget } from './TableWidget';

function isObj(x: unknown): x is Record<string, unknown> {
	return !!x && typeof x === 'object' && !Array.isArray(x);
}

export function VizWidget({ spec }: { spec: unknown }) {
	if (!isObj(spec)) return null;
	const kind = typeof spec.kind === 'string' ? spec.kind : null;
	// CompileVisual 양식: spec.chartType + spec.data
	const chartType = typeof spec.chartType === 'string' ? spec.chartType : null;
	const effective = chartType ?? kind;
	switch (effective) {
		case 'line':
		case 'sparkline':
			return <LineChartWidget spec={spec} />;
		case 'area':
			return <LineChartWidget spec={{ ...spec, kind: 'area' }} />;
		case 'bar':
		case 'histogram':
			return <BarChartWidget spec={spec} />;
		case 'table':
			return <TableWidget spec={spec} />;
		case 'kpi':
			return <KpiWidget spec={spec} />;
		default:
			return null;
	}
}
