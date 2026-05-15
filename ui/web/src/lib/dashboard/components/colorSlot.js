// colorSlot enum → shadcn chart-N HSL var.
// viz 가 색을 결정하지 않고 slot 만 — frontend 가 토큰 매핑.

const SLOT_TO_VAR = {
	primary: "--chart-1",
	secondary: "--chart-2",
	tertiary: "--chart-3",
	success: "--chart-4",
	warning: "--chart-5",
	destructive: "--chart-6",
	muted: "--muted-foreground",
};

export function slotColor(slot) {
	const v = SLOT_TO_VAR[slot] || "--chart-1";
	return `hsl(var(${v}))`;
}

export function slotVar(slot) {
	return SLOT_TO_VAR[slot] || "--chart-1";
}
