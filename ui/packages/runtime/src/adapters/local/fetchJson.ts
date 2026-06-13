// 로컬 어댑터 공용 — /api JSON GET + 미배선 트립와이어.
// getJson: 실패(4xx/5xx/네트워크) = null 정직 표기. 호출측이 계약대로 null/빈값으로 해석한다.
// silent fallback 금지 규약(runtime.ts) 준수 — 다른 데이터 소스로 우회하지 않고 단일 경로의 부재만 null 로 표기.

export function notWiredYet(what: string, stage: string): never {
	throw new Error(`[local adapter] ${what} 는 ${stage}에서 구현된다 — 이 호출이 보이면 배선 순서 위반이다.`);
}

export async function getJson<T>(apiBase: string, path: string): Promise<T | null> {
	try {
		const r = await fetch(`${apiBase}${path}`);
		if (!r.ok) return null;
		return (await r.json()) as T;
	} catch {
		return null;
	}
}
