// 산업지도 계약 — public = static map JSON(HF seed), local = 로컬 API (02 §3.5).
// 잠정 표면: map JSON 6종(ecosystem·atlas·industryStats·meta·movers·timeline)의 정밀 타입은
// 단계-8(MapSurface 추출) 착수 전 02/03 개정으로 확정한다 (07 원장 entry 의무).

export interface IndustrySummary {
	id: string;
	name: string;
}

export interface IndustryMapData {
	id: string;
	payload: Record<string, unknown>; // 잠정 — 단계-8 전 정밀화
}

export interface MapPort {
	listIndustries(): Promise<IndustrySummary[]>;
	getIndustryMap(id: string): Promise<IndustryMapData | null>;
}
