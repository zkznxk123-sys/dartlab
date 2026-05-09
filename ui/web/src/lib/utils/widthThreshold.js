/**
 * 가로 긴 콘텐츠 (DataFrame · 마크다운 표 · 차트) 가 챗 컬럼 (max-w 720px) 에서
 * 깨지지 않도록, 자동으로 우측 워크벤치로 라우팅할지 판단하는 임계 SSOT.
 *
 * 한 곳에서 룰 관리 — DataFrame 컬럼 수 / 차트 가로비 / 마크다운 표 등 표면별
 * 가공 함수 (`isWideTable`, `isWideChart`, `isWideMarkdownTable`) 가 동일 임계를
 * 참조한다.
 */

export const CHAT_COLUMN_WIDTH = 720; // ConversationMessage user/answer max-w 와 일치
export const MIN_COLUMN_PIXELS = 80; // 한 컬럼이 사람 읽기에 필요한 최소 폭
export const MAX_COLUMNS_INLINE = 6; // 그 이상이면 가로 스크롤 발생
export const MAX_CHART_ASPECT = 2; // width / height — 그 이상은 와이드

/**
 * tableHead (list[dict]) 가 인라인 챗 컬럼에서 깨질 만큼 넓은가.
 *
 * @param {Array<object>} tableHead — agent_gateway 가 내려보낸 도구 결과의 tableHead.
 * @param {number} [explicitCols] — 명시 컬럼 수 (있으면 우선).
 */
export function isWideTable(tableHead, explicitCols) {
	const cols = countTableColumns(tableHead, explicitCols);
	if (cols > MAX_COLUMNS_INLINE) return true;
	if (cols * MIN_COLUMN_PIXELS > CHAT_COLUMN_WIDTH) return true;
	return false;
}

export function countTableColumns(tableHead, explicitCols) {
	if (typeof explicitCols === "number" && explicitCols > 0) return explicitCols;
	if (!Array.isArray(tableHead) || !tableHead.length) return 0;
	const first = tableHead[0];
	if (first && typeof first === "object" && !Array.isArray(first)) {
		return Object.keys(first).length;
	}
	if (Array.isArray(first)) return first.length;
	return 0;
}

/**
 * 차트 spec 의 가로비가 인라인에서 깨질 만큼 와이드한가.
 * @param {{ aspect?: number, wide?: boolean, layout?: string }} spec
 */
export function isWideChart(spec) {
	if (!spec || typeof spec !== "object") return false;
	if (spec.wide === true) return true;
	if (typeof spec.aspect === "number" && spec.aspect > MAX_CHART_ASPECT) return true;
	if (typeof spec.layout === "string" && spec.layout.toLowerCase() === "wide") return true;
	return false;
}

/**
 * 마크다운 표 문자열에서 컬럼 수 추정 (헤더 라인의 `|` 카운트).
 */
export function isWideMarkdownTable(markdown) {
	if (typeof markdown !== "string" || !markdown.includes("|")) return false;
	const headerLine = markdown.split("\n").find((line) => line.trim().startsWith("|"));
	if (!headerLine) return false;
	const cols = headerLine.split("|").filter((p) => p.trim().length > 0).length;
	return cols > MAX_COLUMNS_INLINE;
}
