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

// ── 마지막 점검(cron liveness) — HF push 시각(데이터 변경)과 별개. 분기 데이터(finance·report)는
//    매일 체크하지만 변경 없으면 push 0 → push 시각만 보면 stale 처럼 보인다. 담당 워크플로의 마지막
//    *예약(schedule) 실행* 시각으로 "점검은 살아있나(변경이 없을 뿐)" vs "cron 사망" 을 구분한다.
//    GitHub Actions 공개 REST(공개 repo·CORS 허용·무인증)로 event=schedule 최근 run 1회 조회(세션 캐시,
//    워크플로 다수를 단일 요청으로 커버 → rate-limit 절약). 실패 = null('—' 정직). 수동 dispatch 는
//    schedule 이 아니라 제외(순수 cron 생존 신호). 운영자 push 시각 노출과 동질의 공개 정보. */
const RUNS_API =
	'https://api.github.com/repos/eddmpython/dartlab/actions/runs?event=schedule&per_page=80';

interface RunInfo {
	at: string;
	conclusion: string | null;
	status: string;
}
let runsPromise: Promise<Map<string, RunInfo>> | null = null; // 워크플로 파일명 → 최신 schedule run
function loadScheduledRuns(): Promise<Map<string, RunInfo>> {
	if (runsPromise) return runsPromise;
	runsPromise = (async (): Promise<Map<string, RunInfo>> => {
		const map = new Map<string, RunInfo>();
		try {
			const resp = await fetch(RUNS_API, { headers: { Accept: 'application/vnd.github+json' } });
			if (!resp.ok) return map;
			const data = (await resp.json()) as { workflow_runs?: Array<{ path?: string; run_started_at?: string; created_at?: string; conclusion?: string | null; status?: string }> };
			// API 는 생성 역순(최신 우선) — 워크플로별 첫 등장만 채택(= 최신).
			for (const run of data.workflow_runs ?? []) {
				const file = (run.path ?? '').split('/').pop();
				if (!file || map.has(file)) continue;
				map.set(file, { at: run.run_started_at || run.created_at || '', conclusion: run.conclusion ?? null, status: run.status ?? '' });
			}
		} catch {
			/* 네트워크/rate-limit 실패 = '—' 정직 폴백 */
		}
		return map;
	})();
	return runsPromise;
}

/** 담당 워크플로의 마지막 schedule 실행 시각(ISO) + 결과. 미존재/실패 = null. */
export function fetchLastCheck(workflowFile: string): Promise<{ at: string; conclusion: string | null } | null> {
	return loadScheduledRuns().then((m) => {
		const hit = m.get(workflowFile);
		return hit && hit.at ? { at: hit.at, conclusion: hit.conclusion } : null;
	});
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
