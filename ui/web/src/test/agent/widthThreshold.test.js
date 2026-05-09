import { describe, it, expect } from "vitest";
import {
	isWideTable,
	isWideChart,
	isWideMarkdownTable,
	countTableColumns,
} from "../../lib/utils/widthThreshold.js";

describe("isWideTable", () => {
	it("6 컬럼 이하는 인라인", () => {
		const head = [{ a: 1, b: 2, c: 3, d: 4, e: 5, f: 6 }];
		expect(isWideTable(head)).toBe(false);
	});
	it("7 컬럼 이상은 와이드", () => {
		const head = [{ a: 1, b: 2, c: 3, d: 4, e: 5, f: 6, g: 7 }];
		expect(isWideTable(head)).toBe(true);
	});
	it("explicitCols 우선", () => {
		expect(isWideTable([{ a: 1 }], 14)).toBe(true);
		expect(isWideTable([{ a: 1, b: 2, c: 3, d: 4, e: 5, f: 6, g: 7, h: 8 }], 3)).toBe(false);
	});
	it("빈 / 비배열 — false", () => {
		expect(isWideTable([])).toBe(false);
		expect(isWideTable(null)).toBe(false);
	});
	it("배열 형식 첫 행도 처리", () => {
		expect(isWideTable([[1, 2, 3, 4, 5, 6, 7]])).toBe(true);
	});
});

describe("isWideChart", () => {
	it("aspect > 2 → 와이드", () => {
		expect(isWideChart({ aspect: 2.5 })).toBe(true);
		expect(isWideChart({ aspect: 1.6 })).toBe(false);
	});
	it("wide: true 명시 → 와이드", () => {
		expect(isWideChart({ wide: true })).toBe(true);
	});
	it("layout: wide → 와이드", () => {
		expect(isWideChart({ layout: "wide" })).toBe(true);
		expect(isWideChart({ layout: "WIDE" })).toBe(true);
		expect(isWideChart({ layout: "compact" })).toBe(false);
	});
	it("null / undefined / 빈 객체 → false", () => {
		expect(isWideChart(null)).toBe(false);
		expect(isWideChart(undefined)).toBe(false);
		expect(isWideChart({})).toBe(false);
	});
});

describe("isWideMarkdownTable", () => {
	it("7+ 컬럼 헤더 → 와이드", () => {
		const md = "| a | b | c | d | e | f | g |\n| --- | --- | --- | --- | --- | --- | --- |\n| 1 | 2 | 3 | 4 | 5 | 6 | 7 |";
		expect(isWideMarkdownTable(md)).toBe(true);
	});
	it("6 컬럼 — 인라인 OK", () => {
		const md = "| a | b | c | d | e | f |\n| --- | --- | --- | --- | --- | --- |\n";
		expect(isWideMarkdownTable(md)).toBe(false);
	});
	it("표 없으면 false", () => {
		expect(isWideMarkdownTable("그냥 텍스트")).toBe(false);
		expect(isWideMarkdownTable("")).toBe(false);
		expect(isWideMarkdownTable(null)).toBe(false);
	});
});

describe("countTableColumns", () => {
	it("dict 첫 행 키 개수", () => {
		expect(countTableColumns([{ a: 1, b: 2, c: 3 }])).toBe(3);
	});
	it("array 첫 행 길이", () => {
		expect(countTableColumns([[1, 2, 3, 4]])).toBe(4);
	});
	it("explicit 우선", () => {
		expect(countTableColumns([{ a: 1 }], 99)).toBe(99);
	});
	it("빈 → 0", () => {
		expect(countTableColumns([])).toBe(0);
		expect(countTableColumns(null)).toBe(0);
	});
});
