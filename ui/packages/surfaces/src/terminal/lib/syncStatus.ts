// 동기화 실측 — HF tree API 의 lastCommit 시각으로 "마지막 실제 push" 를 행마다 확인.
// 선언된 갱신 주기("매일 동기화")가 아니라 측정값을 보여주는 출처 모달의 정공 —
// allFilings·panel·macro 등 cron 파이프라인의 생존 여부가 화면에서 그대로 검증된다.
// prices-snapshot 4/24·dashboards 4/22 동결 사고(빌드는 되는데 발행이 죽은 채 아무도 모름)의 재발 감시.
const API_ROOT = 'https://huggingface.co/api/datasets/eddmpython/dartlab-data';

const cache = new Map<string, Promise<string | null>>(); // 세션 캐시 — 모달 재오픈 시 재조회 없음

interface TreeEntry {
	path: string;
	lastCommit?: { date?: string };
}

/** 마지막 실제 push 시각(ISO). file 지정 = paths-info 단건(대형 dir 의 tree 1000개 페이지 한계 회피 —
 * allFilings 일별 1000+ 파일 실측), dir 만 = tree 1페이지 내 최신. 실패 = null(정직 '—').
 * paths-info 는 form-urlencoded POST = CORS preflight 없는 simple request. */
export function fetchLastSync(dir: string, file?: string): Promise<string | null> {
	const key = `${dir}|${file ?? ''}`;
	const hit = cache.get(key);
	if (hit) return hit;
	const p = (async (): Promise<string | null> => {
		try {
			if (file) {
				const resp = await fetch(`${API_ROOT}/paths-info/main`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
					body: `paths=${encodeURIComponent(`${dir}/${file}`)}&expand=true`
				});
				if (!resp.ok) return null;
				const entries = (await resp.json()) as TreeEntry[];
				return entries[0]?.lastCommit?.date ?? null;
			}
			const resp = await fetch(`${API_ROOT}/tree/main/${encodeURI(dir)}?expand=true`);
			if (!resp.ok) return null;
			const entries = (await resp.json()) as TreeEntry[];
			const dates = entries.map((e) => e.lastCommit?.date).filter((d): d is string => !!d).sort();
			return dates.at(-1) ?? null;
		} catch {
			return null;
		}
	})();
	cache.set(key, p);
	return p;
}

/** ISO → '3시간 전 (06-12 23:14)' 식 상대+절대 병기 (KST 로컬 표기). */
export function fmtSync(iso: string, lang: 'kr' | 'en'): string {
	const t = new Date(iso);
	if (Number.isNaN(t.getTime())) return '—';
	const mins = Math.max(0, Math.round((Date.now() - t.getTime()) / 60000));
	const rel =
		mins < 60
			? lang === 'en'
				? `${mins}m ago`
				: `${mins}분 전`
			: mins < 60 * 48
				? lang === 'en'
					? `${Math.round(mins / 60)}h ago`
					: `${Math.round(mins / 60)}시간 전`
				: lang === 'en'
					? `${Math.round(mins / 1440)}d ago`
					: `${Math.round(mins / 1440)}일 전`;
	const pad = (n: number) => String(n).padStart(2, '0');
	return `${rel} (${pad(t.getMonth() + 1)}-${pad(t.getDate())} ${pad(t.getHours())}:${pad(t.getMinutes())})`;
}

/** 신선도 톤 — 기대 주기(expectDays) 대비: ≤2× 정상, ≤4× 주의, 초과 = 지연(적색). */
export function syncTone(iso: string, expectDays: number): 'tUp' | 'tWarn' | 'tDn' {
	const t = new Date(iso).getTime();
	if (Number.isNaN(t)) return 'tWarn';
	const ageDays = (Date.now() - t) / 86400000;
	if (ageDays <= expectDays * 2) return 'tUp';
	if (ageDays <= expectDays * 4) return 'tWarn';
	return 'tDn';
}
