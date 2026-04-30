export function isMeaningfulVisualSpec(spec: unknown): boolean {
  if (!spec || typeof spec !== "object") return false;
  const obj = spec as Record<string, unknown>;
  const vizType = String(obj.vizType ?? (obj.diagramType ? "diagram" : "chart"));
  if (vizType === "diagram") return typeof obj.source === "string" && obj.source.trim().length > 0;
  if (vizType !== "chart") return true;

  const chartType = String(obj.chartType ?? "");
  if (chartType === "heatmap" || chartType === "sparkline") {
    return Array.isArray(obj.series) && obj.series.length > 0;
  }
  if (chartType === "radar") {
    return cleanCategories(obj.categories).length >= 3 && hasNumericSeries(obj, 3);
  }
  return isMeaningfulCategorySeriesChart(obj);
}

function isMeaningfulCategorySeriesChart(spec: Record<string, unknown>): boolean {
  const categories = cleanCategories(spec.categories);
  if (categories.length < 2 || new Set(categories).size < 2) return false;
  return hasNumericSeries(spec, 2, categories.length);
}

function hasNumericSeries(spec: Record<string, unknown>, minValues: number, maxLength?: number): boolean {
  const series = spec.series;
  if (!Array.isArray(series)) return false;
  return series.some((row) => {
    if (!row || typeof row !== "object") return false;
    const data = (row as { data?: unknown }).data;
    if (!Array.isArray(data)) return false;
    const values = maxLength === undefined ? data : data.slice(0, maxLength);
    return values.filter((value) => Number.isFinite(toNumber(value))).length >= minValues;
  });
}

function cleanCategories(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item ?? "").trim()).filter(Boolean);
}

function toNumber(value: unknown): number {
  if (typeof value === "number") return value;
  if (typeof value !== "string") return Number.NaN;
  const normalized = value.replace(/,/g, "").replace("%", "").trim();
  if (!normalized) return Number.NaN;
  return Number(normalized);
}
