/**
 * Tool section titles — IN/OUT 레이블 대신 tool 성격에 맞는 한국어 제목.
 * 각 블록 상단에 "무엇을 했는가" 표시.
 */
const TOOL_TITLES = {
	analysis:      { in: "분석 조건",    out: "재무 분석 결과" },
	credit:        { in: "조회 종목",    out: "신용 평가" },
	debt:          { in: "조회 조건",    out: "부채 구조" },
	capital:       { in: "조회 조건",    out: "주주환원 분석" },
	governance:    { in: "조회 조건",    out: "지배구조 분석" },
	audit:         { in: "조회 조건",    out: "감사 분석" },
	show:          { in: "조회 토픽",    out: "원본 데이터" },
	search:        { in: "검색 조건",    out: "공시 검색 결과" },
	searchCompany: { in: "검색어",       out: "종목 검색 결과" },
	scan:          { in: "스캔 조건",    out: "전종목 비교 결과" },
	macro:         { in: "축",           out: "매크로 분석" },
	gather:        { in: "수집 조건",    out: "수집 데이터" },
	quant:         { in: "축",           out: "정량 분석 결과" },
	review:        { in: "조건",         out: "종합 보고서" },
	topdown:       { in: "시장",         out: "탑다운 추천" },
	pastInsight:   { in: "조회 종목",    out: "과거 분석" },
	industry:      { in: "축",           out: "산업 분석" },
	validateStory: { in: "검증 대상",    out: "검증 결과" },
	capabilities:  { in: "조회 키",      out: "기능 상세" },
	pythonExec:    { in: "코드",         out: "실행 결과" },
	news:          { in: "조회 조건",    out: "뉴스" },
	liveFilings:   { in: "조회 조건",    out: "실시간 공시" },
	filings:       { in: "조회 조건",    out: "공시 목록" },
	disclosure:    { in: "조회 조건",    out: "공시 내용" },
	diff:          { in: "비교 대상",    out: "변경 사항" },
	sectorInsights:{ in: "섹터",         out: "업종 분석" },
	codeName:      { in: "종목코드",     out: "종목명" },
	causalWeights: { in: "조회 조건",    out: "인과 가중치" },
	keywordTrend:  { in: "키워드",       out: "추이" },
	search_reference: { in: "검색 조건", out: "스킬/참조" },
	read_context: { in: "읽기 조건", out: "문맥" },
	inspect_dataset: { in: "데이터셋", out: "스키마/기준일" },
	run_python: { in: "코드", out: "실행 근거" },
	compile_visual: { in: "표 근거", out: "시각화" },
};

/**
 * 주어진 tool name 에 대한 IN/OUT 섹션 제목.
 */
export function getToolTitles(name) {
	const t = TOOL_TITLES[name];
	return {
		in: t?.in || "조건",
		out: t?.out || "결과",
	};
}

/**
 * Tool call/result human-readable summaries — SSOT.
 *
 * MessageBubble · EvidenceModal 등이 이 한 곳만 참조.
 * 백엔드가 이미 사람친화 label ("재무분석 — 종합평가 — 241560") 과
 * summary ("F-Score 7/9, 안정성 B" 같은 1줄) 을 내려주므로,
 * 프론트는 그것을 골라 쓰고 args raw dump 는 노출하지 않는다.
 */

const AXIS_LABELS = {
	종합평가: "종합평가",
	수익성: "수익성",
	안정성: "안정성",
	성장성: "성장성",
	효율성: "효율성",
	현금흐름: "현금흐름",
	지배구조: "지배구조",
	예측신호: "예측 신호",
	valuation: "밸류에이션",
	profitability: "수익성",
	stability: "안정성",
	growth: "성장성",
	cycle: "사이클",
	IS: "손익계산서",
	BS: "재무상태표",
	CF: "현금흐름표",
	CIS: "포괄손익계산서",
	SCE: "자본변동표",
};

function niceAxis(value) {
	if (!value) return "";
	return AXIS_LABELS[value] || String(value);
}

/**
 * tool 호출을 Python 함수 호출 코드로 포맷.
 * dartlab 노트북/REPL 에 그대로 복붙 가능한 형태.
 *
 * 예: formatCallCode("scan", {axis: "profitability", sortBy: "ROE", limit: 10})
 *     → 'scan(axis="profitability", sortBy="ROE", limit=10)'
 */
export function formatCallCode(name, args) {
	if (!name) return "";
	if (!args || typeof args !== "object") return `${name}()`;
	const parts = [];
	for (const [key, val] of Object.entries(args)) {
		if (val === null || val === undefined || val === "") continue;
		let repr;
		if (typeof val === "string") repr = `"${val.replace(/"/g, '\\"')}"`;
		else if (typeof val === "boolean") repr = val ? "True" : "False";
		else if (typeof val === "number") repr = String(val);
		else {
			try { repr = JSON.stringify(val); } catch { repr = String(val); }
		}
		parts.push(`${key}=${repr}`);
	}
	return `${name}(${parts.join(", ")})`;
}

/**
 * 결과 1줄 요약 — 헤더 우측에 노출되는 텍스트.
 * 우선순위: backend summary > 에러 마스킹 > 빈 문자열.
 */
export function summarizeResult(pair) {
	if (!pair?.result) return "";
	if (pair.result.status === "error") return "데이터 없음";
	const s = pair.result.summary;
	if (typeof s === "string" && s.trim()) return s.trim();
	return "";
}

export function isToolError(pair) {
	return pair?.result?.status === "error";
}

/**
 * expand 시 IN 블록 위에 보일 "무엇을 물어봤는가" 자연어 요약.
 * 헤더 label 이 이미 포함한 정보는 반복하지 않되, 추가 인자가 있으면 풀어서 보여준다.
 */
export function describeCallArgs(call) {
	const args = call?.arguments;
	if (!args || typeof args !== "object") return "";
	const parts = [];
	if (args.axis) parts.push(`축: ${niceAxis(args.axis)}`);
	if (args.topic) parts.push(`토픽: ${niceAxis(args.topic)}`);
	if (args.module) parts.push(`모듈: ${args.module}`);
	if (args.keyword) parts.push(`키워드: "${args.keyword}"`);
	if (args.query) parts.push(`질의: "${args.query}"`);
	if (args.target) parts.push(`대상: ${args.target}`);
	if (args.path) parts.push(`경로: ${args.path}`);
	if (args.code) parts.push(`코드: ${String(args.code).split("\n").find(line => line.trim()) || ""}`);
	if (args.stockCode) parts.push(`종목: ${args.stockCode}`);
	if (args.market) parts.push(`시장: ${String(args.market).toUpperCase()}`);
	if (args.period) parts.push(`기간: ${args.period}`);
	if (args.view) parts.push(`관점: ${args.view}`);
	return parts.join(" · ");
}

/**
 * 에러 메시지에서 스택트레이스를 떼고 type + message 1줄만 추출.
 * 사용자에게는 "[tool error] ValueError: 섹션을 찾을 수 없습니다" 정도만.
 */
export function cleanErrorMessage(raw) {
	if (typeof raw !== "string") return "";
	const firstLine = raw.split("\n")[0] || "";
	return firstLine.replace(/^\[tool error\]\s*/, "").trim();
}
