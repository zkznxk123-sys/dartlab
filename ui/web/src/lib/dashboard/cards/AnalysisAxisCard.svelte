<!--
	AnalysisAxisCard — Company.analysis(axis) / quant / credit / industry 결과의 generic 렌더러.
	응답 shape 다양 — null-safe 분기 6 종:
	  · DataFrame envelope ({_type:'DataFrame', rows, columns})
	  · history ({history:[...periods], drivers? ...}) → 차트 + 표
	  · 빈 dict / null payload → 빈 상태
	  · flat dict (key→primitive) → KPI grid (sparkline 포함 array 처리)
	  · primitive array → sparkline
	  · object array (rows) → 표
	  · multi-line string (polars repr) → <pre>
-->
<script>
	import * as Card from "$lib/ui/card";
	import * as Table from "$lib/ui/table";
	import { Skeleton } from "$lib/ui/skeleton";
	import HistoryChart from "$lib/dashboard/cards/HistoryChart.svelte";
	import Sparkline from "$lib/dashboard/cards/Sparkline.svelte";
	import { cn } from "$lib/utils.js";

	let { payload = null, loading = false } = $props();

	function isFiniteNum(v) {
		return typeof v === "number" && Number.isFinite(v);
	}

	function formatScalar(v) {
		if (v === null || v === undefined) return "—";
		if (typeof v === "boolean") return v ? "✓" : "✗";
		if (typeof v === "number") {
			if (!Number.isFinite(v)) return "—";
			const a = Math.abs(v);
			if (a >= 1e12) return (v / 1e12).toFixed(2) + "T";
			if (a >= 1e9) return (v / 1e9).toFixed(2) + "B";
			if (a >= 1e6) return (v / 1e6).toFixed(2) + "M";
			if (a >= 1e3) return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
			if (Number.isInteger(v)) return v.toString();
			return v.toFixed(2);
		}
		if (typeof v === "string") return v;
		return String(v);
	}

	function cellContent(v) {
		if (v === null || v === undefined) return "—";
		if (Array.isArray(v)) return `[${v.length}]`;
		if (typeof v === "object") return "{…}";
		return formatScalar(v);
	}

	function isDataFrameEnvelope(v) {
		return (
			v &&
			typeof v === "object" &&
			v._type === "DataFrame" &&
			Array.isArray(v.rows) &&
			Array.isArray(v.columns)
		);
	}

	function isHistoryShape(v) {
		return v && typeof v === "object" && !Array.isArray(v) && Array.isArray(v.history);
	}

	function isPrimitiveArray(v) {
		return Array.isArray(v) && v.every((x) => x === null || typeof x === "number" || typeof x === "string");
	}

	function isObjectArray(v) {
		return Array.isArray(v) && v.length > 0 && v.every((x) => x !== null && typeof x === "object" && !Array.isArray(x));
	}

	function isMultilineString(v) {
		return typeof v === "string" && v.includes("\n");
	}

	function isPlainObject(v) {
		return v !== null && typeof v === "object" && !Array.isArray(v);
	}

	function collectColumns(rows) {
		const seen = new Set();
		for (const r of rows) {
			if (r && typeof r === "object") {
				for (const k of Object.keys(r)) seen.add(k);
			}
		}
		return [...seen];
	}

	function entryKind(v) {
		if (v === null || v === undefined) return "empty";
		if (isHistoryShape(v)) return "history";
		if (Array.isArray(v)) {
			if (v.length === 0) return "emptyArray";
			if (isPrimitiveArray(v)) return "primitiveArray";
			if (isObjectArray(v)) return "objectArray";
			return "primitiveArray";
		}
		if (isMultilineString(v)) return "preString";
		if (isPlainObject(v)) return "dict";
		return "primitive";
	}

	function entrySortKey(v) {
		const k = entryKind(v);
		const order = {
			history: 0,
			objectArray: 1,
			dict: 2,
			primitiveArray: 3,
			preString: 4,
			primitive: 5,
			emptyArray: 6,
			empty: 7,
		};
		return order[k] ?? 9;
	}

	const dfEnvelope = $derived(isDataFrameEnvelope(payload) ? payload : null);
	const isPayloadObject = $derived(payload !== null && typeof payload === "object" && !Array.isArray(payload) && !dfEnvelope);
	const entries = $derived(
		isPayloadObject
			? Object.entries(payload).sort(([, a], [, b]) => entrySortKey(a) - entrySortKey(b))
			: []
	);
	const nonEmptyEntries = $derived(entries.filter(([, v]) => entryKind(v) !== "empty" && entryKind(v) !== "emptyArray"));
	const emptyKeys = $derived(entries.filter(([, v]) => entryKind(v) === "empty" || entryKind(v) === "emptyArray").map(([k]) => k));
</script>

{#if loading}
	<Card.Root>
		<Card.Header>
			<Skeleton class="h-5 w-32" />
		</Card.Header>
		<Card.Content>
			<Skeleton class="h-40 w-full" />
		</Card.Content>
	</Card.Root>
{:else if payload === null || payload === undefined}
	<Card.Root class="border-dashed">
		<Card.Content>
			<div class="py-8 text-center text-[12px] text-muted-foreground">분석 결과 없음</div>
		</Card.Content>
	</Card.Root>
{:else if dfEnvelope}
	<Card.Root>
		<Card.Header>
			<Card.Title class="text-[14px]">{dfEnvelope.rowCount} 행 × {dfEnvelope.columns.length} 열</Card.Title>
		</Card.Header>
		<Card.Content>
			<div class="overflow-x-auto">
				<Table.Root>
					<Table.Header>
						<Table.Row>
							{#each dfEnvelope.columns as col}
								<Table.Head class="text-[10px] uppercase tracking-wide whitespace-nowrap">{col}</Table.Head>
							{/each}
						</Table.Row>
					</Table.Header>
					<Table.Body>
						{#each dfEnvelope.rows as r}
							<Table.Row>
								{#each dfEnvelope.columns as col}
									<Table.Cell class="text-[12px] font-mono tabular-nums whitespace-nowrap">{cellContent(r[col])}</Table.Cell>
								{/each}
							</Table.Row>
						{/each}
					</Table.Body>
				</Table.Root>
			</div>
			{#if dfEnvelope.rowCount > dfEnvelope.rows.length}
				<div class="mt-2 text-[10px] text-muted-foreground">{dfEnvelope.rows.length} / {dfEnvelope.rowCount} 행 표시</div>
			{/if}
		</Card.Content>
	</Card.Root>
{:else if Array.isArray(payload)}
	{#if payload.length === 0}
		<Card.Root class="border-dashed">
			<Card.Content>
				<div class="py-8 text-center text-[12px] text-muted-foreground">결과 없음</div>
			</Card.Content>
		</Card.Root>
	{:else if isObjectArray(payload)}
		{@const cols = collectColumns(payload)}
		<Card.Root>
			<Card.Content class="pt-6">
				<div class="overflow-x-auto">
					<Table.Root>
						<Table.Header>
							<Table.Row>
								{#each cols as col}
									<Table.Head class="text-[10px] uppercase tracking-wide whitespace-nowrap">{col}</Table.Head>
								{/each}
							</Table.Row>
						</Table.Header>
						<Table.Body>
							{#each payload as r}
								<Table.Row>
									{#each cols as col}
										<Table.Cell class="text-[12px] font-mono tabular-nums whitespace-nowrap">{cellContent(r[col])}</Table.Cell>
									{/each}
								</Table.Row>
							{/each}
						</Table.Body>
					</Table.Root>
				</div>
			</Card.Content>
		</Card.Root>
	{:else}
		<Card.Root>
			<Card.Content class="pt-6 text-[12px] font-mono tabular-nums">
				{payload.map(formatScalar).join(", ")}
			</Card.Content>
		</Card.Root>
	{/if}
{:else if typeof payload !== "object"}
	<Card.Root>
		<Card.Content class="pt-6 text-[13px] font-mono tabular-nums">{formatScalar(payload)}</Card.Content>
	</Card.Root>
{:else if entries.length === 0}
	<Card.Root class="border-dashed">
		<Card.Content>
			<div class="py-8 text-center text-[12px] text-muted-foreground">분석 결과 없음</div>
		</Card.Content>
	</Card.Root>
{:else}
	<div class="grid grid-cols-1 gap-4">
		{#each nonEmptyEntries as [metricKey, value]}
			{@const kind = entryKind(value)}
			<Card.Root>
				<Card.Header class="pb-3">
					<Card.Title class="text-[14px]">{metricKey}</Card.Title>
				</Card.Header>
				<Card.Content>
					{#if kind === "history"}
						{@const cols = collectColumns(value.history)}
						<div class="mb-4">
							<HistoryChart history={value.history} chartType="line" />
						</div>
						<details class="border-t border-border pt-2">
							<summary class="cursor-pointer text-[11px] text-muted-foreground hover:text-foreground select-none">상세 표 ({value.history.length} 기간)</summary>
							<div class="mt-2 overflow-x-auto max-h-80">
								<Table.Root>
									<Table.Header>
										<Table.Row>
											{#each cols as col}
												<Table.Head class={cn("text-[10px] uppercase tracking-wide whitespace-nowrap", col === "period" && "sticky left-0 bg-card")}>{col}</Table.Head>
											{/each}
										</Table.Row>
									</Table.Header>
									<Table.Body>
										{#each value.history as r}
											<Table.Row>
												{#each cols as col}
													<Table.Cell class={cn("text-[12px] font-mono tabular-nums whitespace-nowrap", col === "period" && "sticky left-0 bg-card font-medium text-foreground")}>
														{cellContent(r[col])}
													</Table.Cell>
												{/each}
											</Table.Row>
										{/each}
									</Table.Body>
								</Table.Root>
							</div>
						</details>
						{#if value.summary}
							<div class="mt-3 text-[11px] text-muted-foreground border-t border-border pt-2">
								{typeof value.summary === "string" ? value.summary : JSON.stringify(value.summary)}
							</div>
						{/if}
					{:else if kind === "objectArray"}
						{@const cols = collectColumns(value)}
						<div class="overflow-x-auto max-h-80">
							<Table.Root>
								<Table.Header>
									<Table.Row>
										{#each cols as col}
											<Table.Head class="text-[10px] uppercase tracking-wide whitespace-nowrap">{col}</Table.Head>
										{/each}
									</Table.Row>
								</Table.Header>
								<Table.Body>
									{#each value as r}
										<Table.Row>
											{#each cols as col}
												<Table.Cell class="text-[12px] font-mono tabular-nums whitespace-nowrap">{cellContent(r[col])}</Table.Cell>
											{/each}
										</Table.Row>
									{/each}
								</Table.Body>
							</Table.Root>
						</div>
					{:else if kind === "primitiveArray"}
						{@const nums = value.filter(isFiniteNum)}
						{#if nums.length >= 2}
							<div class="flex items-center gap-4">
								<Sparkline data={value} class="h-12 flex-1" />
								<div class="text-[11px] text-muted-foreground font-mono whitespace-nowrap">
									{formatScalar(value[0])} → {formatScalar(value[value.length - 1])}
								</div>
							</div>
						{:else}
							<div class="text-[12px] font-mono">{value.map(formatScalar).join(", ")}</div>
						{/if}
					{:else if kind === "dict"}
						<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
							{#each Object.entries(value) as [k, v]}
								{@const innerKind = entryKind(v)}
								<div class="rounded-md border border-border bg-card/40 p-2.5">
									<div class="text-[10px] text-muted-foreground uppercase tracking-wide truncate" title={k}>{k}</div>
									{#if innerKind === "primitiveArray" && v.filter(isFiniteNum).length >= 2}
										<Sparkline data={v} class="h-8 mt-1" />
									{:else if innerKind === "empty" || innerKind === "emptyArray"}
										<div class="text-[13px] font-mono text-muted-foreground">—</div>
									{:else if innerKind === "primitive"}
										<div class="text-[13px] font-mono tabular-nums truncate" title={String(v)}>{formatScalar(v)}</div>
									{:else if innerKind === "primitiveArray"}
										<div class="text-[11px] font-mono truncate">{v.map(formatScalar).join(", ")}</div>
									{:else if innerKind === "objectArray"}
										<div class="text-[11px] font-mono text-muted-foreground">[{v.length}개]</div>
									{:else if innerKind === "dict"}
										<div class="text-[11px] font-mono text-muted-foreground">{`{${Object.keys(v).length} keys}`}</div>
									{:else}
										<div class="text-[11px] font-mono text-muted-foreground truncate">{cellContent(v)}</div>
									{/if}
								</div>
							{/each}
						</div>
					{:else if kind === "preString"}
						<pre class="text-[11px] font-mono leading-snug overflow-x-auto bg-muted/40 rounded-md p-2 max-h-80">{value}</pre>
					{:else if kind === "primitive"}
						<div class="text-[13px] font-mono tabular-nums">{formatScalar(value)}</div>
					{/if}
				</Card.Content>
			</Card.Root>
		{/each}

		{#if emptyKeys.length > 0}
			<Card.Root class="border-dashed">
				<Card.Content class="py-3">
					<div class="text-[11px] text-muted-foreground">
						<span class="font-medium">데이터 없음:</span> {emptyKeys.join(" · ")}
					</div>
				</Card.Content>
			</Card.Root>
		{/if}
	</div>
{/if}
