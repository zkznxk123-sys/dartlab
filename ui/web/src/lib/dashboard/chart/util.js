// Editorial chart util — number format / KRW unit / scale helper.

export function isFiniteNum(v) {
	return typeof v === "number" && Number.isFinite(v);
}

/** KRW 단위 정규화 — 천원/백만/억/조. */
export function fmtKrw(v) {
	if (!isFiniteNum(v)) return "—";
	const a = Math.abs(v);
	if (a >= 1e12) return (v / 1e12).toFixed(2) + "조";
	if (a >= 1e8) return (v / 1e8).toFixed(2) + "억";
	if (a >= 1e6) return (v / 1e6).toFixed(2) + "M";
	if (a >= 1e3) return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
	if (Number.isInteger(v)) return v.toString();
	return v.toFixed(2);
}

/** 퍼센트 — 응답이 이미 % 단위 (15.4 = 15.4%) 가정. */
export function fmtPct(v, digits = 1) {
	if (!isFiniteNum(v)) return "—";
	return v.toFixed(digits) + "%";
}

/** 부호 포함 ratio — +/-12.3pp 같은 driver contribution. */
export function fmtPp(v, digits = 1) {
	if (!isFiniteNum(v)) return "—";
	const sign = v > 0 ? "+" : "";
	return sign + v.toFixed(digits) + "pp";
}

/** generic short — 분기/연간 period label */
export function fmtPeriod(p) {
	if (p == null) return "";
	return String(p);
}

/** color signal */
export function signColor(v) {
	if (!isFiniteNum(v)) return "var(--ed-text-3)";
	if (v > 0) return "var(--ed-up)";
	if (v < 0) return "var(--ed-down)";
	return "var(--ed-text-2)";
}

/** linear scale */
export function linearScale(domain, range) {
	const [d0, d1] = domain;
	const [r0, r1] = range;
	const span = d1 - d0 || 1;
	return (v) => r0 + ((v - d0) / span) * (r1 - r0);
}

/** symmetric domain around 0 (positive + negative both visible) */
export function symmetricDomain(values, pad = 0.05) {
	const max = Math.max(0, ...values.filter(isFiniteNum));
	const min = Math.min(0, ...values.filter(isFiniteNum));
	const range = max - min || 1;
	return [min - range * pad, max + range * pad];
}

/** clamp */
export function clamp(v, lo, hi) {
	return Math.max(lo, Math.min(hi, v));
}
