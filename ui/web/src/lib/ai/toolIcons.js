/**
 * Tool 아이콘 매핑 — 별 모듈로 분리.
 *
 * ToolBlock.svelte 가 본 모듈을 import. 컴포넌트 안에 lucide 다수 import 하면
 * visual-language SSOT 의 lucide 임계 (≤4) 위반. 매핑은 의미 단위 — 도구 종류별 아이콘.
 *
 * 사용처: ToolBlock.svelte 의 ICON_MAP.
 */

import {
	BarChart3,
	BookOpen,
	CheckCheck,
	Code2,
	Cpu,
	Database,
	Globe,
	MessageSquare,
	Save,
	Search,
	Sparkles,
	Terminal,
	Wrench,
} from "lucide-svelte";

export const TOOL_ICON_MAP = {
	Terminal,
	Code2,
	Database,
	Search,
	BarChart3,
	BookOpen,
	CheckCheck,
	Cpu,
	Globe,
	Sparkles,
	MessageSquare,
	Wrench,
	Save,
};

/** Default fallback icon when tool name has no specific mapping. */
export const DEFAULT_TOOL_ICON = Terminal;
