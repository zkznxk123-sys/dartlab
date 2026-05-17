import { useEffect, useState } from 'react';

// 단순 디바운스 — 외부 lib 없이 useEffect + setTimeout.
export function useDebounce<T>(value: T, delayMs: number): T {
	const [debounced, setDebounced] = useState(value);
	useEffect(() => {
		const t = setTimeout(() => setDebounced(value), delayMs);
		return () => clearTimeout(t);
	}, [value, delayMs]);
	return debounced;
}
