<script lang="ts">
	// 전문 증권사급 주가차트 — klinecharts(v9) CORE. 차트 크롬은 모드별 컴포넌트로 분리:
	//   일반 = ChartMenus(칩+드롭다운) / 전체화면 = ChartRibbon(2단 전문 리본). 상태는 ChartCtl 단일 SSOT.
	// 본 컴포넌트 = 차트 인스턴스 수명주기 + 데이터(lazy 백필) + 상태→차트 반영 effect 들만.
	// 전체 이력(2010~) lazy 로드, 인스턴스 영속(회사전환=applyNewData, dispose 안 함). SSR 안전.
	import { untrack } from 'svelte';
	import { KRX_MIN_YEAR, MACRO_SERIES, MACRO_ATTRIBUTION, type Candle } from '@dartlab/ui-contracts';
	import { useDartLabRuntime } from '@dartlab/ui-runtime';
	import { aggregateCandles, adjustCandles, heikinAshi } from './candleMath';
	import type { Lang } from '../lib/types';
	import { runBacktest, type BtResult } from '../lib/backtest';
	import { focusDisclosure } from '../lib/disclosureFocus.svelte'; // 공시 dot 클릭 → 우측 공시목록 그 날짜로
	import { registerBtIndicators, publishBt, applyBt, clearBt } from './btLayer';
	import { registerEconIndicator, ECON_INDICATOR, type EconExtend } from './econOverlay';
	import { registerExtraIndicators } from './extraIndicators';
	import { ChartCtl, PERIOD_N, TF_DIV, type CandleStyle, type OverlayKey, type SubKey, type TfKey } from './chartState.svelte';
	import { loadDraws, saveDraws, type SavedDraw } from './drawStore';
	import { publishView } from './seriesBus';
	import { registerWorkOverlays, MEASURE_NAME, TEXT_NAME } from './avwapOverlay';
	import { registerVolumeProfile, VP_INDICATOR } from './volumeProfile';
	import { registerCmpIndicator, CMP_INDICATOR, type CmpExtend } from './compareOverlay';
	import { downloadSnapshot } from './snapshot';
	import { IND_DEFS } from './indicatorParams';
	import ChartMenus from './ChartMenus.svelte';
	import ChartRibbon from './ChartRibbon.svelte';
	import DrawToolbar from './DrawToolbar.svelte';
	import BacktestStrip from './BacktestStrip.svelte';

	interface Props {
		candles: Candle[]; // 초기(현재+직전 연도)
		code: string;
		name?: string;
		lang: Lang;
		events?: { date: string; label: string; url?: string; kind?: 'report' | 'capital' | 'disclosure' }[];
		// 공시 레일(02 §4) — 날짜 그룹별 그날 공시 전부(items). 캔들 고가 텍스트 아님 = x축 라벨 아래 전용 dot 레일.
		// 호버=그날 공시 전 항목 툴팁, 클릭=우측 정기/비정기 공시목록 그 날짜로(원문 링크 아님).
		disclosures?: { date: string; items: { title: string; rceptNo: string; url: string; kind: 'regular' | 'nonreg' }[] }[];
		valBand?: { lo: number; mid: number; hi: number } | null;
		peers?: { code: string; name: string }[]; // 동종업계 — 종목비교(VS) 후보
		// 전체화면 심볼 점프 — 검색은 엔진(suggest), 전환은 onPick (터미널 pick 관통)
		suggest?: (q: string, n: number) => { code: string; name: string; industry: string }[];
		onPick?: (code: string) => void;
		onSrc?: (line: string) => void; // 출처(공공누리)를 차트 하단 대신 패널 헤더에 표기하도록 부모로 끌어올림(econ/adj 반응 유지)
	}
	let { candles, code, name = '', lang, events, disclosures = [], valBand, peers = [], suggest, onPick, onSrc }: Props = $props();
	const rt = useDartLabRuntime();
	const browser = typeof window !== 'undefined'; // $app/environment 결합 제거 (4a-3)

	const ctl = new ChartCtl();
	let el: HTMLDivElement | null = $state(null);
	let chart = $state<any>(null);
	let btResult = $state<BtResult | null>(null);
	// ⛔ 불변식: chart.applyNewData 는 reapply() 단일 지점 (bumpDataRev 동행). pushTick 은 제외.
	// dataRev++ 직접 사용 금지 — $effect 안 증감은 읽기+쓰기라 self-dep 무한루프(effect_update_depth_exceeded).
	let dataRev = $state(0);
	let dataRevSeq = 0;
	const bumpDataRev = () => (dataRev = ++dataRevSeq);
	let btRunSeq = 0; // 비반응 — BT calcParams 재계산 트리거용 단조 증가
	let econOn = false; // ECON indicator 생성 여부 (비반응)
	let econToken = 0; // stale async 가드
	let cmpOn = false; // 종목비교(CMP) indicator 생성 여부 (비반응)
	let cmpToken = 0;

	let kc: any = null;
	const subPanes = new Map<SubKey, string>();
	const mainOn = new Set<OverlayKey>();
	let vpOn = false; // 매물대 indicator 생성 여부 (비반응)
	const appliedParams: Record<string, number[]> = {}; // indParams diff 스냅샷 (비반응)
	let bandIds: string[] = [];
	let eventIds: string[] = [];
	let refIds: string[] = [];
	// 드로잉 — drawMap = 완성 드로잉 id→직렬화 (localStorage 영속 SSOT). pending = 진행중(ESC 취소 대상).
	const drawMap = new Map<string, SavedDraw>();
	let pendingDrawId: string | null = null;
	let selectedDrawId: string | null = null;
	// load-more 상태 (비반응 — 콜백이 읽음). oldestYear↔newestYear = 현재 로드된 이력 범위.
	// viewLen = 현재 tf 로 차트에 적용된 봉 수 (주/월 집계 후 길이 — applySpacing 기준).
	const hist = { code: '', oldestYear: 9999, newestYear: 0, loading: false, viewLen: 0 };
	let appliedTf: TfKey = 'D'; // tf effect 의 mount 중복 재적용 차단용 비반응 스냅샷
	let appliedStyle: CandleStyle = ctl.candleStyle; // HA ↔ 비HA 전환만 데이터 재적용 (스냅샷 가드)
	// 바 리플레이 — replayCutT = 현재 리플레이 봉 라벨(YYYYMMDD, 비반응). displaySeries 가 이 날짜까지
	// 절단해 BT·기준선이 "그 시점까지 데이터만으로" 재계산되는 정직한 리플레이를 만든다.
	let replayCutT: string | null = null;
	let appliedReplay = { on: false, idx: -1 }; // replay effect 중복 재적용 차단 스냅샷

	const toMs = (t: string) => Date.UTC(+t.slice(0, 4), +t.slice(4, 6) - 1, +t.slice(6, 8));
	// x축 날짜 라벨을 한국식 간단 표기로 압축 — 라이브러리 기본(YYYY-MM·MM-DD·YYYY)을 YY.MM·MM.DD·YYYY 로.
	// registerXAxis 가 이미 계산된 ticks 의 text 만 치환(틱 산출·간격 로직은 라이브러리 그대로 — 회귀 0).
	function compactAxisText(s: string): string {
		let m: RegExpExecArray | null;
		if ((m = /^(\d{2})(\d{2})-(\d{2})-(\d{2})/.exec(s))) return `${m[2]}.${m[3]}`; // YYYY-MM-DD(앵커) → YY.MM
		if ((m = /^(\d{2})(\d{2})-(\d{2})$/.exec(s))) return `${m[2]}.${m[3]}`; // YYYY-MM → YY.MM
		if (/^\d{2}-\d{2}$/.test(s)) return s.replace('-', '.'); // MM-DD → MM.DD
		return s; // YYYY · HH:mm 등 그대로
	}
	// turnover 는 억 단위 — {turnover} 플레이스홀더가 콤마만 붙이고 축약을 안 해 원 단위면
	// "446,546,135,655" 생짜 노출 (TVAL 페인·매물대 가중치도 동일 단위 공유, 상대값이라 무영향)
	const toK = (c: Candle) => ({ timestamp: toMs(c.t), open: c.o, high: c.h, low: c.l, close: c.c, volume: c.v, turnover: c.tv != null ? c.tv / 1e8 : undefined });

	// 공시 레일(02 §4) — disclosures(날짜 그룹) 각 날짜를 convertToPixel 로 x 픽셀화해 x축 날짜라벨 "아래" 전용 띠에 dot 배치.
	// 캔들 고가 텍스트 annotation(폭주·가격 차폐, §2.2 금지) 폐기. 레일 띠 = 캔버스가 끝나는 chartWrap 하단 padding 영역
	// (terminal.css .chartWrap padding-bottom — 출처 자리를 레일 lane 으로 전용). 좌표/폭은 el(캔버스) geometry 기준이라
	// 일반·전체화면(좌 58·하 22 padding) 모두 정렬. pan/zoom·resize 는 onScroll/onZoom·ResizeObserver 로 재계산.
	// 좌표 실패/범위 밖은 graceful skip(렌더 0·crash 0).
	type RailItem = { title: string; rceptNo: string; url: string; kind: 'regular' | 'nonreg' };
	type RailDot = { x: number; date: string; items: RailItem[] };
	let railBox = $state<{ left: number; top: number; width: number; canvasTop: number } | null>(null);
	let railDots = $state<RailDot[]>([]);
	let hoverRail = $state<{ x: number; date: string; items: RailItem[] } | null>(null); // 호버 = 그날 공시 전부 툴팁(일자 헤더 포함)
	const ymdDash = (d: string) => `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`; // YYYYMMDD → YYYY-MM-DD
	function recomputeRail() {
		const c = chart;
		if (!c || !el) { railDots = []; railBox = null; return; }
		// 레일 띠 = 캔버스 바로 아래(canvas bottom → chartWrap 하단). offsetLeft/Top 이 전체화면 padding 을 자동 반영.
		// canvasTop = 캔버스 상단 — dot 호버 시 그 날짜 세로 가이드선을 캔버스 전 높이로 그릴 때 사용.
		railBox = { left: el.offsetLeft, top: el.offsetTop + el.offsetHeight, width: el.offsetWidth, canvasTop: el.offsetTop };
		if (!disclosures.length) { railDots = []; return; }
		const w = el.offsetWidth;
		const out: RailDot[] = [];
		for (const d of disclosures) {
			if (!/^\d{8}$/.test(d.date) || !d.items.length) continue;
			let x: number | undefined;
			try {
				const px = c.convertToPixel({ timestamp: toMs(d.date), value: 0 }, { paneId: 'candle_pane' });
				x = Array.isArray(px) ? px[0]?.x : px?.x;
			} catch { continue; }
			if (typeof x !== 'number' || !Number.isFinite(x) || x < -4 || x > w + 4) continue;
			out.push({ x, date: d.date, items: d.items });
		}
		railDots = out;
		if (hoverRail && !out.length) hoverRail = null;
	}
	// 데이터/기간/봉주기/disclosures/전체화면 변경 시 재계산 (rAF = 차트 렌더 후 좌표 안정).
	$effect(() => {
		void dataRev;
		void ctl.period;
		void ctl.tf;
		void ctl.full;
		void disclosures;
		if (browser) requestAnimationFrame(recomputeRail);
	});
	// 캔버스 크기 변화(전체화면 토글·창 리사이즈·페인 경계 드래그) → 레일 geometry·dot x 재정렬.
	$effect(() => {
		if (!browser || !el) return;
		const ro = new ResizeObserver(() => requestAnimationFrame(recomputeRail));
		ro.observe(el);
		return () => ro.disconnect();
	});
	// 출처(공공누리)를 차트 하단 캡션 대신 패널 헤더로 — econ/수정주가/HA 변화에 반응(srcText 가 ctl 읽음).
	$effect(() => {
		onSrc?.(srcText());
	});
	// 리본 Row1 정보 — 표시 시계열(리플레이 절단·수정주가 반영) 기준이라 리플레이 중에도 정직.
	// dataRev = reapply 동행 신호 (displaySeries 내부 untrack 읽기를 대신 깨운다).
	const ribbonInfo = $derived.by<{ last: number; prev: number | null; date: string; hi: number; lo: number } | null>(() => {
		void dataRev;
		if (!candles.length) return null;
		const s = displaySeries();
		if (!s.length) {
			const n = candles.length;
			return { last: candles[n - 1].c, prev: n >= 2 ? candles[n - 2].c : null, date: candles[n - 1].t, hi: candles[n - 1].h, lo: candles[n - 1].l };
		}
		const lastK = s[s.length - 1];
		const win = s.slice(-252);
		let hi = -Infinity;
		let lo = Infinity;
		for (const k of win) {
			if (k.h > hi) hi = k.h;
			if (k.l < lo) lo = k.l;
		}
		return { last: lastK.c, prev: s.length >= 2 ? s[s.length - 2].c : null, date: lastK.t, hi, lo };
	});
	// 상태 피드백 1줄 — 자동 tf 상향·과거 백필 침묵 동작을 리본에 노출 ("버그처럼 보이는 정상동작" 제거)
	let notice = $state<string | null>(null);
	let noticeTimer: ReturnType<typeof setTimeout> | null = null;
	function setNotice(msg: string, ms = 2400) {
		notice = msg;
		if (noticeTimer) clearTimeout(noticeTimer);
		noticeTimer = setTimeout(() => (notice = null), ms);
	}
	// 전체화면 오버레이 2종 — 심볼 점프 팔레트(⌘K·/) + 단축키 도움말(?)
	let jumpOpen = $state(false);
	let jumpQ = $state('');
	let jumpIdx = $state(0);
	let jumpInput = $state<HTMLInputElement | null>(null);
	const jumpList = $derived(jumpOpen && suggest ? suggest(jumpQ, 8) : []);
	let helpOpen = $state(false);
	function jumpTo(c: string) {
		jumpOpen = false;
		jumpQ = '';
		jumpIdx = 0;
		onPick?.(c);
	}

	// 캔들 툴팁 — 한국어 압축형 + 등락률({change} 내장 placeholder, 전일종가 대비 자동색).
	// 배열은 wholesale 교체(라이브러리 명시 특례) — 기본 6줄을 우리 줄로 완전 대체.
	const tooltipCustom = (lg: Lang) =>
		lg === 'en'
			? [
					{ title: 'O', value: '{open}' }, { title: 'H', value: '{high}' }, { title: 'L', value: '{low}' },
					{ title: 'C', value: '{close}' }, { title: 'Vol', value: '{volume}' }, { title: 'TVal(100M)', value: '{turnover}' }, { title: 'Chg', value: '{change}' }
				]
			: [
					{ title: '시', value: '{open}' }, { title: '고', value: '{high}' }, { title: '저', value: '{low}' },
					{ title: '종', value: '{close}' }, { title: '량', value: '{volume}' }, { title: '대금(억)', value: '{turnover}' }, { title: '등락', value: '{change}' }
				];
	// 'ha'(하이킨아시)는 데이터 변환(reapply) — klinecharts 캔들 타입으로는 candle_solid 로 그린다.
	const kcCandleType = (t: CandleStyle) => (t === 'ha' ? 'candle_solid' : t);
	// 차트 캔버스 활자 — 터미널 본체와 동일 스택. 기본 'Helvetica Neue' 는 한글이 없어 거래량
	// 축의 만·억 이 시스템 폰트(맑은 고딕)로 폴백돼 숫자와 다른 활자·다른 덩치로 렌더됐다.
	// 숫자 = JetBrains Mono(터미널 .mono 와 동일), 한글 = Pretendard 폴백으로 전 페인 통일.
	const CHART_FONT = "'JetBrains Mono', 'Pretendard Variable', ui-monospace, monospace";
	const themeStyles = () => ({
		grid: { horizontal: { color: 'rgba(48,58,78,0.55)' }, vertical: { color: 'rgba(38,46,62,0.3)' } },
		candle: {
			type: kcCandleType(ctl.candleStyle),
			bar: { upColor: '#34d399', downColor: '#f0616f', noChangeColor: '#8b919e', upBorderColor: '#34d399', downBorderColor: '#f0616f', noChangeBorderColor: '#8b919e', upWickColor: '#5eead4', downWickColor: '#fb7185', noChangeWickColor: '#8b919e' },
			area: { lineColor: '#5b9bf0', lineSize: 1.4, backgroundColor: [{ offset: 0, color: 'rgba(91,155,240,0.22)' }, { offset: 1, color: 'rgba(91,155,240,0.01)' }] },
			priceMark: { high: { color: '#8b919e', textFamily: CHART_FONT }, low: { color: '#8b919e', textFamily: CHART_FONT }, last: { upColor: '#34d399', downColor: '#f0616f', noChangeColor: '#8b919e', text: { color: '#0b0e14', family: CHART_FONT } } },
			tooltip: { offsetTop: 26, custom: tooltipCustom(lang), text: { color: '#cfd3dc', size: 11, family: CHART_FONT }, rect: { color: 'rgba(14,17,23,0.85)', borderColor: '#222b3a' } }
		},
		indicator: { tooltip: { text: { color: '#8b919e', size: 10, family: CHART_FONT } } },
		xAxis: { axisLine: { color: '#222b3a' }, tickLine: { color: '#222b3a' }, tickText: { color: '#8b919e', size: 10, family: CHART_FONT } },
		yAxis: { type: ctl.yMode, axisLine: { color: '#222b3a' }, tickLine: { color: '#222b3a' }, tickText: { color: '#8b919e', size: 10, family: CHART_FONT } },
		separator: { color: '#222b3a', fill: true, activeBackgroundColor: 'rgba(251,146,60,0.1)' },
		crosshair: { horizontal: { line: { color: 'rgba(251,146,60,0.45)' }, text: { backgroundColor: '#b45309', family: CHART_FONT } }, vertical: { line: { color: 'rgba(251,146,60,0.45)' }, text: { backgroundColor: '#b45309', family: CHART_FONT } } }
	});

	// 보조 페인 높이 — 컨테이너 비례(16%) 적응. 전체화면 진입 시 78px 고정 납작 페인 방지.
	function subPaneHeight(): number {
		const h = el?.clientHeight || 480;
		return Math.max(72, Math.min(240, Math.round(h * 0.16)));
	}

	// ── 차트 인스턴스 생성 (mount 1 회, el 기준) ──
	$effect(() => {
		const node = el;
		if (!browser || !node) return;
		let disposed = false;
		let local: any = null;
		(async () => {
			const mod: any = await import('klinecharts');
			if (disposed || !node) return;
			kc = mod;
			registerBtIndicators(mod);
			registerEconIndicator(mod);
			registerExtraIndicators(mod);
			registerWorkOverlays(mod);
			registerVolumeProfile(mod);
			registerCmpIndicator(mod);
			// x축 날짜 라벨 간단화 — 기본 축('default')의 createTicks 가 받는 defaultTicks 의 text 만 YY.MM 으로 재포맷.
			// 패턴 미일치(HH:mm 등)는 그대로 통과(타 차트 무해). init 전 등록해야 차트가 픽업. 재등록은 idempotent.
			try {
				mod.registerXAxis({
					name: 'default',
					createTicks: ({ defaultTicks }: { defaultTicks: { coord: number; value: number | string; text: string }[] }) =>
						defaultTicks.map((t) => ({ ...t, text: compactAxisText(t.text) }))
				});
			} catch { /* registerXAxis 미지원 빌드 — 기본 라벨 유지 */ }
			local = mod.init(node, { styles: themeStyles() });
			if (!local) return;
			local.setPriceVolumePrecision(0, 0);
			// 미래(데이터 없는) 우측 영역 0 — 차트는 반드시 마지막 봉까지만. 옛 12px 여백이
			// 줌아웃 시 ~3봉의 미래 축으로 보이던 것 제거 (EOD 차트에 미래 축은 무의미).
			local.setOffsetRightDistance(0);
			try { local.setMaxOffsetRightDistance(0); } catch { /* 구버전 무시 */ }
			// 공시 레일 — pan/zoom 시 dot x 재정렬 (rAF 디바운스). 미지원 버전은 데이터 effect 재계산만.
			try {
				local.subscribeAction('onScroll', () => requestAnimationFrame(recomputeRail));
				local.subscribeAction('onZoom', () => requestAnimationFrame(recomputeRail));
			} catch { /* 구버전 무시 */ }
			// timestamp 는 Date.UTC 자정 — timezone 미설정 시 XAxis 라벨이 브라우저 로컬 TZ 로 풀려
			// 미주 사용자에게 하루 전 날짜로 표시되는 조용한 오류. 명시 고정.
			try { local.setTimezone('UTC'); } catch { /* */ }
			// 일봉 날짜 포맷 — 기본 'YYYY-MM-DD HH:mm' 하드코딩이 일봉에 09:00 같은 무의미 시각 노출.
			// Tooltip(0)·Crosshair(1) 만 날짜로, XAxis 등은 라이브러리 기본 유지.
			const fmtYmd = (ts: number) => {
				const d = new Date(ts);
				const p = (n: number) => String(n).padStart(2, '0');
				return `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())}`;
			};
			// 큰 수 표기 — 라이브러리 기본 K/M/B(서양식) 대신 만·억·조. 거래량(주)·거래대금(원)
			// 축 라벨·툴팁 공통. 자릿수 규칙 고정: 조·억 = 소수 2자리, 만 = 정수, 만 미만 = 정수 콤마.
			const fmtBigKr = (value: string | number): string => {
				const v = Number(value);
				if (!Number.isFinite(v)) return String(value);
				const a = Math.abs(v);
				if (a >= 1e12) return (v / 1e12).toFixed(2) + '조';
				if (a >= 1e8) return (v / 1e8).toFixed(2) + '억';
				if (a >= 1e4) return Math.round(v / 1e4).toLocaleString() + '만';
				return Math.round(v).toLocaleString();
			};
			try {
				local.setCustomApi({
					formatDate: (dtf: unknown, ts: number, format: string, type: number) => {
						if (type === 0 || type === 1) return fmtYmd(ts);
						try { return mod.utils.formatDate(dtf, ts, format); } catch { return fmtYmd(ts); }
					},
					formatBigNumber: fmtBigKr
				});
			} catch { /* setCustomApi 미지원 빌드 — 기본 포맷 유지 */ }
			// 전체 이력 lazy 로드 — 좌측(forward) 도달 시 더 오래된 연도 prepend.
			// 주/월봉은 부분연도 prepend 가 버킷 경계를 깨므로 tf effect 가 전체 백필 후 재적용 (여기선 무시).
			local.setLoadDataCallback((p: any) => {
				const done = (rows: any[], more: boolean) => { try { p.callback(rows, more); } catch { /* */ } };
				// ⚠ untrack 필수 — klinecharts 는 applyNewData 안에서 본 콜백을 동기 호출(backward)한다.
				// 여기 상태 읽기가 reapply 를 부른 effect(회사전환 등)의 의존이 되면 유령 재실행 루프.
				const s = untrack(() => ({ replayOn: ctl.replay.on, tf: ctl.tf }));
				if (s.replayOn) return done([], false); // 리플레이 — 절단 시계열에 과거 prepend 금지
				if (s.tf !== 'D') return done([], false);
				if (p.type !== 'forward' || hist.loading) return done([], hist.oldestYear - 1 >= KRX_MIN_YEAR);
				const next = hist.oldestYear - 1;
				if (next < KRX_MIN_YEAR) return done([], false);
				hist.loading = true;
				rt.price.older(hist.code, next)
					.then((older) => {
						hist.oldestYear = next;
						hist.loading = false;
						let rows = older;
						// 수정주가 ON — prepend 분도 전체 체이닝 재계산의 선두 슬라이스로 보정
						// (원본 그대로 붙이면 분할 이전 연도가 보정 스케일과 어긋난 절벽을 만든다)
						if (ctl.adj && older.length) {
							const adj = adjustCandles(rt.price.loaded(hist.code));
							if (adj.length >= older.length) rows = adj.slice(0, older.length);
						}
						done(rows.map(toK), next - 1 >= KRX_MIN_YEAR);
					})
					.catch(() => { hist.loading = false; done([], false); });
			});
			chart = local;
		})();
		return () => {
			disposed = true;
			if (local && kc) { try { kc.dispose(local); } catch { /* */ } }
			subPanes.clear();
			mainOn.clear();
			econOn = false;
			vpOn = false;
			cmpOn = false;
			for (const k of Object.keys(appliedParams)) delete appliedParams[k];
			bandIds = [];
			eventIds = [];
			refIds = [];
			drawMap.clear();
			pendingDrawId = null;
			selectedDrawId = null;
			if (chart === local) chart = null;
		};
	});

	// 전체 표시 시계열 = 원본 일봉 → (수정주가 보정). reapply 내부 전용 (리플레이 절단 이전 원본).
	function fullSeries(): Candle[] {
		const all = rt.price.loaded(hist.code);
		const base = all.length ? all : candles; // 캐시 미시드 방어 — prop 직접 적용
		if (!base.length) return base;
		return untrack(() => ctl.adj) ? adjustCandles(base) : base;
	}

	// 표시 시계열 (BT·기준선·이벤트 마커 공용) — 리플레이 중엔 현재 봉 날짜까지 절단.
	// 절단 덕에 dataRev 의존 effect(BT·52주 기준선)가 그 시점까지 데이터만으로 정직하게 재계산된다.
	function displaySeries(): Candle[] {
		const all = fullSeries();
		if (replayCutT == null) return all;
		let end = all.length;
		while (end > 0 && all[end - 1].t > replayCutT) end--;
		return all.slice(0, end);
	}

	// 로드된 전체 이력을 현재 tf 시점(일=원본, 주/월/분기/년=집계)으로 재적용 — applyNewData 단일 지점.
	// 리플레이 ON 이면 idx 봉까지 절단, 하이킨아시면 적용 직전 변환(버스·BT 는 원본 가격 유지).
	function reapply(c: any) {
		const tfv = untrack(() => ctl.tf);
		const base = fullSeries();
		if (!base.length) return;
		let view = tfv === 'D' ? base : aggregateCandles(base, tfv);
		hist.viewLen = view.length; // 전체 길이 (리플레이 절단 전 — applySpacing·replay len 기준)
		// ⚠ untrack 은 콜백 안 읽기만 보호 — proxy 를 꺼내 밖에서 .on 읽으면 호출 effect 에 의존이 생긴다
		const rp = untrack(() => ({ on: ctl.replay.on, idx: ctl.replay.idx }));
		if (rp.on) {
			view = view.slice(0, Math.min(rp.idx, view.length - 1) + 1);
			replayCutT = view[view.length - 1].t;
		} else {
			replayCutT = null;
		}
		publishView(view, toMs); // AVWAP·측정룰러가 구독하는 표시 시계열 버스 (원본 가격)
		const out = untrack(() => ctl.candleStyle) === 'ha' ? heikinAshi(view) : view;
		c.applyNewData(out.map(toK), !rp.on && tfv === 'D' && hist.oldestYear - 1 >= KRX_MIN_YEAR);
		bumpDataRev();
	}

	// 리플레이를 reapply 없이 종료 — 직후 자체 reapply 하는 effect(회사전환·tf·adj)용 (이중 재적용 방지).
	function exitReplaySilently() {
		untrack(() => {
			if (!ctl.replay.on) return;
			ctl.replayExit();
			appliedReplay = { on: false, idx: ctl.replay.idx };
		});
	}

	// ── 데이터 적용 (회사전환 = applyNewData, dispose 안 함 = 영속) ──
	$effect(() => {
		const cs = candles;
		const c = chart;
		if (!c || !cs || cs.length === 0) return;
		hist.code = code;
		hist.oldestYear = +cs[0].t.slice(0, 4);
		hist.newestYear = +cs[cs.length - 1].t.slice(0, 4);
		hist.loading = false;
		exitReplaySilently(); // 회사 전환 — 이전 회사 시점 리플레이는 무의미
		reapply(c);
		bandIds.forEach((id) => c.removeOverlay(id));
		eventIds.forEach((id) => c.removeOverlay(id));
		refIds.forEach((id) => c.removeOverlay(id));
		try { c.removeOverlay({ groupId: 'draw' }); } catch { /* */ }
		bandIds = [];
		eventIds = [];
		refIds = [];
		drawMap.clear();
		pendingDrawId = null;
		selectedDrawId = null;
		restoreDraws(c); // 회사별 저장 드로잉 복원 (drawCount 동기화 포함)
		untrack(() => ctl.clearCompares()); // 이전 회사 기준 종목비교 해제
		// untrack — applyPeriodFull 의 ctl.period 읽기가 본 effect 의존이 되면 기간 클릭마다
		// 회사전환 전체(재적용+드로잉 삭제)가 재실행되고, viewLen 갱신 전 이중 tf 상향(W→M)까지 일으킨다.
		untrack(() => applyPeriodFull(c));
		// 주/월봉 유지 상태로 회사 전환 — 집계 정합 위해 전체 백필 (gov 전이력 회사는 no-op)
		if (untrack(() => ctl.tf) !== 'D') void backfillTo(c, KRX_MIN_YEAR);
	});

	// 가시 봉 수 재배치 — 현재 tf 적용 후 봉 수(viewLen) 기준. klinecharts BarSpace 하한 = 1px:
	// 미달이면 한 단계 굵은 봉으로 자동 상향 (일→주→월, HTS 관행. MAX 일봉 ~4천개 = 물리적 표시 불가).
	function applySpacing(c: any) {
		const tfv = untrack(() => ctl.tf);
		const len = hist.viewLen || candles.length || 1;
		const N = Math.min(Math.ceil((PERIOD_N[ctl.period] ?? len) / TF_DIV[tfv]), len);
		const w = el?.clientWidth || 800;
		const space = w / Math.max(1, N);
		if (space < 1 && (tfv === 'D' || tfv === 'W')) {
			const next = tfv === 'D' ? 'W' : 'M';
			setNotice(T(`봉 ${N.toLocaleString()}개 — 1px 미달, ${next === 'W' ? '주봉' : '월봉'} 자동 전환`, `${N.toLocaleString()} bars — auto ${next} timeframe`));
			ctl.tf = next; // tf effect 가 재적용+재배치 이어받음 (분기·년은 수동 전용 — 자동 상향 제외)
			return;
		}
		try { c.setBarSpace(Math.max(1, Math.min(30, space))); c.scrollToRealTime(0); } catch { /* */ }
	}

	// 목표 연도까지 능동 백필 → (변경 시) 전체 재적용 + 재배치. 기간 점프·주/월봉 전환 공용.
	async function backfillTo(c: any, target: number) {
		const code0 = hist.code;
		if (!code0) return;
		let changed = false;
		while (hist.oldestYear > Math.max(target, KRX_MIN_YEAR) && !hist.loading) {
			const y = hist.oldestYear - 1;
			hist.loading = true;
			notice = T(`과거 시세 불러오는 중 … ${y}`, `loading history … ${y}`); // 진행 중 상시 — 완료 시 해제
			try { await rt.price.older(code0, y); } catch { hist.loading = false; break; }
			hist.loading = false;
			if (hist.code !== code0 || chart !== c) { notice = null; return; } // 회사 전환·차트 교체 → 중단
			hist.oldestYear = y;
			changed = true;
		}
		notice = null;
		if (changed && chart === c && hist.code === code0) {
			reapply(c);
			applySpacing(c);
		}
	}

	// 기간(특히 3Y/MAX)·줌아웃 시 필요한 과거연도까지 백필.
	const yearsForPeriod = (p: string): number => (p === 'MAX' ? 999 : Math.ceil((PERIOD_N[p] ?? 252) / 252) + 1);
	function applyPeriodFull(c: any) {
		applySpacing(c);
		const target = ctl.period === 'MAX' ? KRX_MIN_YEAR : Math.max(KRX_MIN_YEAR, hist.newestYear - yearsForPeriod(ctl.period) + 1);
		void backfillTo(c, target);
	}

	// ── 봉 주기(일/주/월/분기/년) 전환 → 전체 백필 후 집계 재적용. BT 는 일봉 전용이라 자동 해제. ──
	$effect(() => {
		const tfv = ctl.tf;
		const c = chart;
		if (!c || !candles.length) return;
		if (tfv === appliedTf) return;
		appliedTf = tfv;
		exitReplaySilently(); // 봉 주기 전환 — 리플레이 idx 좌표계가 깨지므로 자동 종료
		if (tfv !== 'D') ctl.btKey = null;
		const code0 = hist.code;
		(async () => {
			if (tfv !== 'D') await backfillTo(c, KRX_MIN_YEAR);
			if (chart !== c || hist.code !== code0) return;
			reapply(c);
			applySpacing(c);
		})();
	});

	// ── 수정주가 토글 → 재적용 (mount·회사전환 중복 적용은 스냅샷 가드) ──
	let appliedAdj = true;
	$effect(() => {
		const a = ctl.adj;
		const c = chart;
		if (!c || !candles.length) return;
		if (a === appliedAdj) return;
		appliedAdj = a;
		exitReplaySilently(); // 보정 전환 — 절단 기준 가격이 달라지므로 자동 종료
		reapply(c);
	});

	// ── 바 리플레이 — on/idx 변경 → 절단 재적용 (dataRev 동행으로 BT·기준선 자동 추종) ──
	$effect(() => {
		const on = ctl.replay.on;
		const idx = ctl.replay.idx;
		const c = chart;
		if (!c || !candles.length) return;
		if (on === appliedReplay.on && idx === appliedReplay.idx) return;
		appliedReplay = { on, idx };
		reapply(c);
	});

	// 자동재생 — replayMs(400/150ms 2단) 간격 한 봉 전진. 끝 봉 도달 시 replayStep 이 playing 을 끄면 cleanup.
	$effect(() => {
		if (!ctl.replay.on || !ctl.replay.playing) return;
		const t = setInterval(() => ctl.replayStep(), ctl.replayMs);
		return () => clearInterval(t);
	});

	// 리플레이 진입 — 시작점 = 현재 기간 윈도 시작(최소 30봉 워밍업), 현재 tf 봉 수로 환산.
	function enterReplay() {
		if (!chart || !hist.viewLen) return;
		const n = Math.ceil((PERIOD_N[ctl.period] ?? 252) / TF_DIV[ctl.tf]);
		const idx = Math.min(Math.max(30, hist.viewLen - n), hist.viewLen - 1);
		ctl.replay = { on: true, idx, playing: false, start: idx, len: hist.viewLen };
	}

	// ── 매물대 토글 → VPVR indicator 생성/제거 (candle_pane, figures:[] = y축 무왜곡) ──
	$effect(() => {
		const on = ctl.showVP;
		const c = chart;
		if (!c) return;
		if (on && !vpOn) {
			vpOn = !!c.createIndicator({ name: VP_INDICATOR }, true, { id: 'candle_pane' });
		} else if (!on && vpOn) {
			try { c.removeIndicator('candle_pane', VP_INDICATOR); } catch { /* */ }
			vpOn = false;
		}
	});

	// 메인 오버레이 reconcile (다중 — candle_pane 스택). ICHI 활성 시 선행스팬용 우측 여백 확보.
	$effect(() => {
		const want = new Set(ctl.overlays);
		const c = chart;
		if (!c) return;
		for (const k of [...mainOn]) if (!want.has(k)) { c.removeIndicator('candle_pane', k); mainOn.delete(k); delete appliedParams[k]; }
		ctl.overlays.forEach((k) => {
			if (mainOn.has(k)) return;
			// 커스텀 없으면 IND_DEFS 기본 명시 전달 — RSI 14 등 전문가 표준 교정값 적용
			const cp = ctl.indParams[k] ?? (IND_DEFS[k]?.defaults.length ? IND_DEFS[k].defaults : undefined);
			if (c.createIndicator(cp ? { name: k, calcParams: cp } : k, true, { id: 'candle_pane' })) {
				mainOn.add(k);
				if (cp) appliedParams[k] = cp;
			}
		});
		// 우측 여백은 항상 0 — 일목(ICHI) 구름 미래연장도 미래 축을 열지 않는다 (데이터 끝 = 차트 끝 불변).
		try { c.setOffsetRightDistance(0); } catch { /* */ }
	});

	// 보조지표 페인 reconcile
	$effect(() => {
		const want = new Set(ctl.subs);
		const c = chart;
		if (!c) return;
		for (const [k, paneId] of [...subPanes]) if (!want.has(k)) { c.removeIndicator(paneId); subPanes.delete(k); delete appliedParams[k]; }
		ctl.subs.forEach((k) => {
			if (subPanes.has(k)) return;
			const cp = ctl.indParams[k] ?? (IND_DEFS[k]?.defaults.length ? IND_DEFS[k].defaults : undefined);
			// 자릿수 통일 — 라이브러리 기본 precision 4(RSI 64.7436 류) 과잉. 수량 페인(VOL·TVAL·OBV·PVT)은
			// 정수 + 만·억 단위, 그 외 오실레이터는 소수 2자리 고정.
			const precision = k === 'VOL' || k === 'TVAL' || k === 'OBV' || k === 'PVT' ? 0 : 2;
			const id = c.createIndicator({ name: k, precision, ...(cp ? { calcParams: cp } : {}) }, false, { id: `pane_${k}`, height: subPaneHeight(), minHeight: 48, dragEnabled: true });
			if (id) {
				subPanes.set(k, id);
				if (cp) appliedParams[k] = cp;
			}
		});
	});

	// 지표 파라미터 적용 — appliedParams 스냅샷과 diff, 변경분만 overrideIndicator.
	// ⚠ override 에 minValue/maxValue 절대 전달 금지 (klinecharts 내부 오배선 — calcParams 만).
	$effect(() => {
		const ip = ctl.indParams;
		const c = chart;
		if (!c) return;
		const names = new Set([...Object.keys(ip), ...Object.keys(appliedParams)]);
		for (const k of names) {
			const next = ip[k] ?? IND_DEFS[k]?.defaults;
			const prev = appliedParams[k];
			if (!next || (prev && prev.length === next.length && prev.every((v, i) => v === next[i]))) continue;
			const paneId = mainOn.has(k as OverlayKey) ? 'candle_pane' : subPanes.get(k as SubKey);
			if (!paneId) continue;
			try { c.overrideIndicator({ name: k, calcParams: next }, paneId); } catch { /* */ }
			if (ip[k]) appliedParams[k] = next;
			else delete appliedParams[k];
			// ICHI 파라미터 변경도 우측 여백 불변(0) — 미래 축 금지 룰과 동일
		}
	});

	// 적정주가 밴드 → priceLine 오버레이 (토글)
	$effect(() => {
		const vb = valBand;
		const on = ctl.showBand;
		const c = chart;
		if (!c) return;
		bandIds.forEach((id) => c.removeOverlay(id));
		bandIds = [];
		if (on && vb && vb.hi > vb.lo) {
			const mk = (price: number, color: string) => c.createOverlay({ name: 'priceLine', points: [{ value: price }], lock: true, styles: { line: { color, style: 'dashed', size: 1 }, text: { color } } });
			bandIds = [mk(vb.hi, 'rgba(96,165,250,0.5)'), mk(vb.mid, 'rgba(96,165,250,0.85)'), mk(vb.lo, 'rgba(96,165,250,0.5)')].filter(Boolean) as string[];
		}
	});

	// 52주 고가·저가·전일종가 기준선 (HTS 관례 색: 고=적, 저=청, 전일=회) — 일봉 기준 산출.
	$effect(() => {
		const on = ctl.showRefs;
		void ctl.adj;
		void dataRev;
		const c = chart;
		if (!c) return;
		refIds.forEach((id) => c.removeOverlay(id));
		refIds = [];
		if (!on) return;
		const base = displaySeries();
		if (base.length < 2) return;
		const win = base.slice(-252);
		let hi = -Infinity;
		let lo = Infinity;
		for (const k of win) {
			if (k.h > hi) hi = k.h;
			if (k.l < lo) lo = k.l;
		}
		const prevC = base[base.length - 2].c;
		const mk = (price: number, color: string) => c.createOverlay({ name: 'priceLine', points: [{ value: price }], lock: true, styles: { line: { color, style: 'dashed', size: 1 }, text: { color } } });
		refIds = [mk(hi, 'rgba(240,97,111,0.65)'), mk(lo, 'rgba(96,165,250,0.65)'), mk(prevC, 'rgba(139,145,158,0.65)')].filter(Boolean) as string[];
	});

	// 실적·공시 시점 마커 → simpleAnnotation (토글, 가장 가까운 거래일 스냅).
	// 표시 시계열(수정주가 반영) 기준으로 고가 스냅 — 원본 기준이면 분할 이전 마커가 차트 밖으로 나간다.
	$effect(() => {
		const evs = events;
		const on = ctl.showEvents;
		void ctl.adj;
		const cs = candles.length ? displaySeries() : candles;
		const c = chart;
		if (!c || !cs.length) return;
		eventIds.forEach((id) => c.removeOverlay(id));
		eventIds = [];
		if (!on || !evs || !evs.length) return;
		const first = cs[0].t;
		const last = cs[cs.length - 1].t;
		const snap = (d: string) => { let best = cs[0]; let bd = Infinity; for (const k of cs) { const dd = Math.abs(Number(k.t) - Number(d)); if (dd < bd) { bd = dd; best = k; } } return best; };
		const ids: string[] = [];
		for (const ev of evs) {
			if (ev.date < first || ev.date > last) continue;
			const k = snap(ev.date);
			// 공시 시점 = dartlab 고유 강점. 비정기 material 공시(disclosure)는 cyan, 실적·증자(report·capital)는 orange.
			// url 보유 마커는 클릭 시 해당 DART 공시를 새 탭으로 — 가격차트가 곧 네비게이션 가능한 공시 타임라인.
			const disc = ev.kind === 'disclosure';
			const fg = disc ? '#22d3ee' : '#fb923c';
			const bg = disc ? 'rgba(34,211,238,0.12)' : 'rgba(251,146,60,0.12)';
			const bd = disc ? 'rgba(34,211,238,0.5)' : 'rgba(251,146,60,0.5)';
			const evUrl = ev.url;
			const id = c.createOverlay({
				name: 'simpleAnnotation',
				extendData: ev.label,
				points: [{ timestamp: toMs(k.t), value: k.h }],
				styles: { text: { color: fg, backgroundColor: bg, borderColor: bd } },
				onClick: evUrl
					? () => {
							window.open(evUrl, '_blank', 'noopener,noreferrer');
							return false;
						}
					: null
			});
			if (id) ids.push(id as string);
		}
		eventIds = ids;
	});

	// Y축 모드 / 캔들 스타일
	$effect(() => {
		const m = ctl.yMode;
		const c = chart;
		if (!c) return;
		try { c.setStyles({ yAxis: { type: m } }); } catch { /* */ }
	});
	$effect(() => {
		const t = ctl.candleStyle;
		const lg = lang;
		const c = chart;
		if (!c) return;
		try { c.setStyles({ candle: { type: kcCandleType(t), tooltip: { custom: tooltipCustom(lg) } } }); } catch { /* */ }
		// HA ↔ 비HA 전환은 데이터 변환이 바뀌므로 재적용 (스냅샷 가드 — mount·단순 타입 전환은 스킵)
		if (t !== appliedStyle) {
			const wasHa = appliedStyle === 'ha';
			appliedStyle = t;
			if (wasHa || t === 'ha') reapply(c);
		}
	});

	// period 변경 → 가시 봉 수 + 필요 시 과거 백필. 리플레이는 시작점 기준이 달라지므로 자동 종료.
	$effect(() => {
		void ctl.period;
		const c = chart;
		if (!c || !candles.length) return;
		untrack(() => { if (ctl.replay.on) ctl.replayExit(); }); // 비silent — replay effect 가 전체 복원
		applyPeriodFull(c);
	});

	// 백테스트 — 의존: 프리셋·파라미터·비용(토글+bp)·기간·dataRev(applyNewData 동행).
	$effect(() => {
		const c = chart;
		const key = ctl.btKey;
		const p = ctl.btParams;
		const wc = ctl.btCosts;
		const bp = ctl.btCostsBp;
		void dataRev;
		void ctl.period;
		if (!c) return;
		if (!key) {
			clearBt(c);
			btResult = null;
			return;
		}
		void ctl.adj;
		// 표시 시계열(수정주가 기본 ON)로 백테스트 — 원본이면 분할 절벽을 -98% 폭락으로 오인한다.
		const all = displaySeries();
		if (!all.length) return;
		const win = Math.min(PERIOD_N[ctl.period] ?? all.length, all.length);
		const res = runBacktest(all, key, p, { windowBars: win, withCosts: wc, costsBp: bp, spec: { code, name, market: 'KR', dataSource: 'gov/prices', adjusted: ctl.adj } });
		btResult = res;
		publishBt(res, all);
		if (res) applyBt(c, ++btRunSeq);
		else clearBt(c);
	});

	// 종목비교 오버레이 — 피어 회사파일 로드 → 수정주가 동일 보정 → CMP 생성/override.
	// 피어 보정 누락 = 피어 분할이 상대수익률을 왜곡하므로 본주와 같은 adj 정책 강제.
	$effect(() => {
		const list = ctl.compares;
		const adjOn = ctl.adj;
		const c = chart;
		if (!c) return;
		if (!list.length) {
			if (cmpOn) {
				try { c.removeIndicator('candle_pane', CMP_INDICATOR); } catch { /* */ }
				cmpOn = false;
			}
			return;
		}
		const token = ++cmpToken;
		const yr = new Date().getFullYear();
		Promise.all(list.map((p) => rt.price.initial(p.code, yr))).then((rs) => {
			if (token !== cmpToken || chart !== c) return;
			const loaded = list
				.map((p, i) => {
					const cs = rs[i]?.candles ?? [];
					return { code: p.code, name: p.name, candles: adjOn ? adjustCandles(cs) : cs };
				})
				.filter((p) => p.candles.length);
			const extendData: CmpExtend = { peers: loaded };
			if (cmpOn) c.overrideIndicator({ name: CMP_INDICATOR, extendData }, 'candle_pane');
			else cmpOn = !!c.createIndicator({ name: CMP_INDICATOR, extendData }, true, { id: 'candle_pane' });
			// 기간 수익률 미니표 (VS 팝오버) — 이미 로드한 피어 캔들 재사용, 추가 다운로드 0
			const mainAll = untrack(() => fullSeries());
			cmpRows = [
				{ name, code, r: CMP_RET_BARS.map((n) => retOf(mainAll.length ? mainAll : candles, n)) },
				...loaded.map((p) => ({ name: p.name, code: p.code, r: CMP_RET_BARS.map((n) => retOf(p.candles, n)) }))
			];
		});
	});
	// 본주+비교종목 기간 수익률 (1M/3M/6M/1Y) — VS 팝오버 미니표 데이터
	const CMP_RET_BARS = [21, 63, 132, 252];
	const retOf = (cs: Candle[], n: number): number | null =>
		cs.length > n && cs[cs.length - 1 - n].c ? (cs[cs.length - 1].c / cs[cs.length - 1 - n].c - 1) * 100 : null;
	let cmpRows = $state<{ name: string; code: string; r: (number | null)[] }[]>([]);
	$effect(() => {
		if (!ctl.compares.length) cmpRows = [];
	});

	// 경제지표 오버레이 — 선택 → 로드 → 생성/override (figures:[] = 캔들 y축 무왜곡, econOverlay.ts)
	$effect(() => {
		const ids = ctl.econ;
		const c = chart;
		const lg = lang;
		if (!c) return;
		if (!ids.length) {
			if (econOn) {
				try { c.removeIndicator('candle_pane', ECON_INDICATOR); } catch { /* */ }
				econOn = false;
			}
			return;
		}
		const token = ++econToken;
		Promise.all(ids.map((id) => rt.macro.getSeries(id))).then((lists) => {
			if (token !== econToken || chart !== c) return; // 선택 변경·인스턴스 교체 → 폐기
			const series = ids
				.map((id, i) => ({ def: MACRO_SERIES.find((s) => s.id === id)!, points: lists[i] ?? [] }))
				.filter((s) => s.points.length);
			const extendData: EconExtend = { lang: lg, series }; // 항상 새 참조 → setExtendData 재계산 보장
			if (econOn) c.overrideIndicator({ name: ECON_INDICATOR, extendData }, 'candle_pane');
			else econOn = !!c.createIndicator({ name: ECON_INDICATOR, extendData }, true, { id: 'candle_pane' });
		});
	});

	// 전체화면 토글 → resize + 보조 페인 비례 재배분 + 전문가 단축키 레이어.
	// ESC 2단(진행중 드로잉 취소 → 닫기) · Delete 선택삭제 · ←/→ 스크롤(Shift=한 화면) ·
	// +/− 줌 · 1~6 기간 · D/W/M 봉주기 — 전체화면 한정 (일반 모드 = 페이지 스크롤 충돌).
	$effect(() => {
		if (!browser) return;
		const c = chart;
		void ctl.full;
		requestAnimationFrame(() => {
			try {
				c?.resize();
				const ph = subPaneHeight();
				for (const paneId of subPanes.values()) c?.setPaneOptions({ id: paneId, height: ph });
			} catch { /* */ }
		});
		if (!ctl.full) {
			// 전체화면 닫힘 — 리플레이 컨트롤(리본)이 사라지므로 동행 종료 (replay effect 가 전체 복원)
			untrack(() => { if (ctl.replay.on) ctl.replayExit(); });
			jumpOpen = false;
			helpOpen = false;
			// 일반 모드 — Shift+F 전체화면 진입 (그 외 단일 키는 페이지 스크롤·검색과 충돌하므로 추가 금지)
			const onKeyMini = (e: KeyboardEvent) => {
				const tgt = e.target as HTMLElement | null;
				if (tgt && (tgt.tagName === 'INPUT' || tgt.tagName === 'TEXTAREA' || tgt.isContentEditable)) return;
				if (e.shiftKey && (e.key === 'F' || e.key === 'f') && !e.metaKey && !e.ctrlKey && !e.altKey) {
					e.preventDefault();
					ctl.full = true;
				}
			};
			window.addEventListener('keydown', onKeyMini);
			return () => window.removeEventListener('keydown', onKeyMini);
		}
		const PERIOD_KEYS = ['1M', '3M', '6M', '1Y', '3Y', 'MAX'] as const;
		const onKey = (e: KeyboardEvent) => {
			const k = e.key;
			// 심볼 점프 — ⌘K·/ (TV 관행). input 가드보다 먼저: Terminal 전역 핸들러는 전체화면을
			// 감지해 양보한다 (보이지 않는 검색창 포커스 트랩 버그 수정 짝).
			if (((e.metaKey || e.ctrlKey) && k.toLowerCase() === 'k') || (k === '/' && !(e.target as HTMLElement | null)?.closest?.('input,textarea'))) {
				if (suggest && onPick) {
					e.preventDefault();
					jumpOpen = !jumpOpen;
					helpOpen = false;
					if (jumpOpen) requestAnimationFrame(() => jumpInput?.focus());
					return;
				}
			}
			const tgt = e.target as HTMLElement | null;
			if (tgt && (tgt.tagName === 'INPUT' || tgt.tagName === 'TEXTAREA' || tgt.isContentEditable)) return;
			if (k === 'Escape') {
				// 우선순위: 점프/도움말 닫기 → 진행중 드로잉 취소 → 리플레이 종료 → 전체화면 닫기
				if (jumpOpen || helpOpen) { jumpOpen = false; helpOpen = false; return; }
				if (cancelPendingDraw()) return;
				if (ctl.replay.on) { ctl.replayExit(); return; }
				ctl.full = false;
			} else if (k === '?') {
				helpOpen = !helpOpen;
				jumpOpen = false;
			} else if (k === ' ' && ctl.replay.on) {
				e.preventDefault(); // 리플레이 — 스페이스 = 재생/정지 (동영상 멘탈모델)
				ctl.replay.playing = !ctl.replay.playing;
			} else if (k === 'Delete' || k === 'Backspace') {
				removeDraw(selectedDrawId);
			} else if (k === 'ArrowLeft' || k === 'ArrowRight') {
				e.preventDefault();
				if (ctl.replay.on) { if (k === 'ArrowRight') ctl.replayStep(); else ctl.replayStepBack(); return; } // 리플레이 — →/← 한 봉 전·후진
				const bs = (() => { try { return c?.getBarSpace?.() ?? 8; } catch { return 8; } })();
				const w = el?.clientWidth || 800;
				const step = e.shiftKey ? w : bs * 8;
				try { c?.scrollByDistance(k === 'ArrowLeft' ? step : -step, 0); } catch { /* */ }
			} else if (k === '+' || k === '=') {
				try { c?.zoomAtCoordinate(1.15); } catch { /* */ }
			} else if (k === '-' || k === '_') {
				try { c?.zoomAtCoordinate(0.87); } catch { /* */ }
			} else if (k >= '1' && k <= '6' && !e.metaKey && !e.ctrlKey && !e.altKey) {
				ctl.period = PERIOD_KEYS[+k - 1];
			} else if ((k === 'd' || k === 'D') && !e.metaKey && !e.ctrlKey) {
				ctl.tf = 'D';
			} else if ((k === 'w' || k === 'W') && !e.metaKey && !e.ctrlKey) {
				ctl.tf = 'W';
			} else if ((k === 'm' || k === 'M') && !e.metaKey && !e.ctrlKey) {
				ctl.tf = 'M';
			} else if ((k === 'q' || k === 'Q') && !e.metaKey && !e.ctrlKey) {
				ctl.tf = 'Q';
			} else if ((k === 'y' || k === 'Y') && !e.metaKey && !e.ctrlKey) {
				ctl.tf = 'Y';
			} else if ((k === 'r' || k === 'R') && !e.metaKey && !e.ctrlKey) {
				if (ctl.replay.on) ctl.replayExit();
				else enterReplay(); // 리플레이 토글
			} else if ((k === 'a' || k === 'A') && !e.metaKey && !e.ctrlKey) {
				ctl.adj = !ctl.adj; // 수정주가
			} else if ((k === 'l' || k === 'L') && !e.metaKey && !e.ctrlKey) {
				ctl.yMode = ctl.yMode === 'log' ? 'normal' : 'log'; // 로그축
			} else if ((k === 'g' || k === 'G') && !e.metaKey && !e.ctrlKey) {
				ctl.showRefs = !ctl.showRefs; // 52주·전일 기준선
			} else if ((k === 'f' || k === 'F') && !e.metaKey && !e.ctrlKey && !e.shiftKey) {
				ctl.full = false; // 진입(Shift+F)과 대칭
			} else if ((k === 's' || k === 'S') && !e.metaKey && !e.ctrlKey) {
				snapshot();
			}
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});

	// ── 드로잉 — 완성 시점 카운트·우클릭/Delete 삭제·드래그 편집 재저장·회사별 localStorage 영속 ──
	const serializeDraw = (o: any): SavedDraw => ({
		name: o.name,
		points: (o.points ?? []).map((p: any) => ({ timestamp: p.timestamp, value: p.value })),
		...(typeof o.extendData === 'string' && o.extendData ? { text: o.extendData } : {})
	});
	function persistDraws() { saveDraws(hist.code, [...drawMap.values()]); }
	// 텍스트 주석 인라인 에디터 — 배치/더블클릭 시 점 위에 입력창. Enter 확정·Esc/빈값 취소(도형 제거).
	let textEdit = $state<{ id: string; x: number; y: number; value: string } | null>(null);
	function openTextEditor(o: any) {
		if (!chart || !o?.id) return;
		let x = 90;
		let y = 60;
		try {
			const p0 = o.points?.[0];
			const px = chart.convertToPixel({ timestamp: p0?.timestamp, value: p0?.value }, { paneId: 'candle_pane' });
			const p = Array.isArray(px) ? px[0] : px;
			if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) { x = p.x; y = p.y; }
		} catch { /* 좌표 실패 — 기본 위치 */ }
		textEdit = { id: o.id, x, y, value: typeof o.extendData === 'string' ? o.extendData : '' };
	}
	function commitText(save: boolean) {
		const te = textEdit;
		textEdit = null;
		if (!te) return;
		const val = save ? te.value.trim() : '';
		if (!val) { removeDraw(te.id); return; }
		try { chart?.overrideOverlay({ id: te.id, extendData: val }); } catch { /* */ }
		const d = drawMap.get(te.id);
		if (d) { drawMap.set(te.id, { ...d, text: val }); persistDraws(); }
	}
	const focusOnMount = (el: HTMLInputElement) => { el.focus(); el.select(); };
	function drawOpts(toolName: string, points?: SavedDraw['points'], text?: string) {
		const ephemeral = toolName === MEASURE_NAME; // 측정룰러 — 영속 제외, 선택 해제 시 자동 제거
		return {
			name: toolName,
			groupId: 'draw',
			...(points ? { points } : {}),
			...(text ? { extendData: text } : {}),
			mode: ctl.magnet ? 'weak_magnet' : 'normal',
			onDrawEnd: (e: any) => {
				const o = e.overlay;
				if (!o?.id) return;
				if (pendingDrawId === o.id) pendingDrawId = null;
				if (ephemeral) return;
				drawMap.set(o.id, serializeDraw(o));
				ctl.drawCount = drawMap.size;
				persistDraws();
				// 텍스트 주석 — 배치 직후 인라인 입력 (연속 그리기 재시작 없음)
				if (toolName === TEXT_NAME && typeof o.extendData !== 'string') { setTimeout(() => openTextEditor(o), 0); return; }
				// 연속 그리기 — 같은 도구 즉시 재시작. setTimeout 0 = klinecharts 클릭 이벤트 재진입 회피.
				// 복원(points 사전 채움)은 onDrawEnd 미발화라 회사전환 시 유령 도구가 생기지 않는다.
				if (ctl.stayDraw) setTimeout(() => startDraw(toolName), 0);
			},
			onDoubleClick: (e: any) => {
				if (toolName === TEXT_NAME) { openTextEditor(e.overlay); return true; }
				return false;
			},
			onPressedMoveEnd: (e: any) => {
				const o = e.overlay;
				if (!o?.id || !drawMap.has(o.id)) return;
				drawMap.set(o.id, serializeDraw(o));
				persistDraws();
			},
			onSelected: (e: any) => { selectedDrawId = e.overlay?.id ?? null; },
			onDeselected: (e: any) => {
				if (selectedDrawId === e.overlay?.id) selectedDrawId = null;
				if (ephemeral && e.overlay?.id) { try { chart?.removeOverlay(e.overlay.id); } catch { /* */ } }
			},
			onRightClick: (e: any) => { removeDraw(e.overlay?.id); return true; }
		};
	}
	function removeDraw(id?: string | null) {
		if (!id) return;
		try { chart?.removeOverlay(id); } catch { /* */ }
		drawMap.delete(id);
		if (selectedDrawId === id) selectedDrawId = null;
		if (pendingDrawId === id) pendingDrawId = null;
		ctl.drawCount = drawMap.size;
		persistDraws();
	}
	function cancelPendingDraw(): boolean {
		if (!pendingDrawId) return false;
		try { chart?.removeOverlay(pendingDrawId); } catch { /* */ }
		pendingDrawId = null;
		return true;
	}
	function restoreDraws(c: any) {
		for (const d of loadDraws(hist.code)) {
			const id = c.createOverlay(drawOpts(d.name, d.points, d.text));
			if (id) drawMap.set(id as string, d);
		}
		ctl.drawCount = drawMap.size;
	}
	function startDraw(toolName: string) {
		try {
			cancelPendingDraw(); // 미완 도형 교체 — 유령 진행상태 방지
			const id = chart?.createOverlay(drawOpts(toolName));
			if (id) pendingDrawId = id as string;
		} catch { /* */ }
	}
	function clearDraw() {
		try { chart?.removeOverlay({ groupId: 'draw' }); } catch { /* */ }
		drawMap.clear();
		pendingDrawId = null;
		selectedDrawId = null;
		ctl.drawCount = 0;
		persistDraws();
	}
	// 차트 환경 설정 영속 — persist() 내부의 상태 읽기가 전부 의존이 되어 변경 시마다 저장
	$effect(() => {
		ctl.persist();
	});

	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	// 출처 표기 SSOT — DOM 캡션과 스냅샷 띠가 같은 문자열 (공공누리 출처표시 의무)
	const srcText = () =>
		T('출처: 금융위원회·한국거래소 (공공데이터포털)', 'Source: FSC · KRX (data.go.kr)') +
		(ctl.econ.length ? ' · ' + MACRO_ATTRIBUTION : '') +
		(ctl.adj ? T(' · 수정주가', ' · adjusted') : '') +
		(ctl.candleStyle === 'ha' ? ' · HA' : ''); // 하이킨아시 = 변형값 정직 고지
	function snapshot() {
		const ymd = candles.length ? candles[candles.length - 1].t : '';
		const date = ymd ? `${ymd.slice(0, 4)}-${ymd.slice(4, 6)}-${ymd.slice(6, 8)}` : '';
		void downloadSnapshot(chart, { fileTag: `${code}_${ymd}`, srcLine: `${name} ${code} · ${date} · ${srcText()}` }).catch(() => { /* 이미지 합성 실패 — 무해 */ });
	}
	// 실시간 틱 (나중 가격 API 연결 시 호출) — 일봉 전용 (주/월 집계 봉에 일봉 append 방지)
	export function pushTick(c: Candle) { if (ctl.tf !== 'D') return; try { chart?.updateData(toK(c)); } catch { /* */ } }
</script>

<div class="chartWrap" class:full={ctl.full} role="img" aria-label="price chart" style={ctl.full ? '' : 'height:480px;min-height:360px;'}>
	<div class="chartHost" bind:this={el}></div>

	{#if railBox && railDots.length}
		<!-- 공시 위치 레일(02 §4) — x축 날짜라벨 아래 전용 띠. left/top/width=캔버스 geometry(전체화면 padding 자동 반영).
		     호버=그날 공시 전부 툴팁, 클릭=우측 정기/비정기 공시목록 그 날짜로(focusDisclosure — 원문 링크 아님). -->
		<div class="discRail" style={`left:${railBox.left}px;top:${railBox.top}px;width:${railBox.width}px`} aria-label={T('공시 위치', 'disclosure markers')}>
			{#each railDots as d (d.date)}
				<button
					class="discDot"
					class:multi={d.items.length > 1}
					class:hasReg={d.items.some((i) => i.kind === 'regular')}
					style={`left:${d.x}px;opacity:${Math.min(0.4 + d.items.length * 0.12, 0.92)}`}
					aria-label={`${d.date.slice(0, 4)}-${d.date.slice(4, 6)}-${d.date.slice(6, 8)} ${T('공시', 'filings')} ${d.items.length}`}
					onmouseenter={() => (hoverRail = { x: d.x, date: d.date, items: d.items })}
					onmouseleave={() => (hoverRail = null)}
					onfocus={() => (hoverRail = { x: d.x, date: d.date, items: d.items })}
					onblur={() => (hoverRail = null)}
					onclick={() => focusDisclosure(d.date)}
				></button>
			{/each}
			{#if hoverRail}
				{@const ht = hoverRail}
				<div class="discTip mono" style={`left:${Math.min(Math.max(ht.x, 132), railBox.width - 132)}px`} role="tooltip">
					<div class="discTipHd"><b class="discTipDate">{ymdDash(ht.date)}</b> · {T('공시', 'filings')} {ht.items.length}{T('건', '')}</div>
					{#each ht.items.slice(0, 12) as it (it.rceptNo)}
						<div class="discTipRow">{#if it.kind === 'regular'}<span class="discTipTag">{T('정기', 'REG')}</span>{/if}{it.title}</div>
					{/each}
					{#if ht.items.length > 12}<div class="discTipMore">{T('외 ', '+')}{ht.items.length - 12}{T('건', '')}</div>{/if}
					<div class="discTipFoot">{T('클릭 → 우측 공시목록', 'click → filings list')}</div>
				</div>
			{/if}
		</div>
		{#if hoverRail}
			<!-- 그 공시일 세로 가이드선 — 캔버스 전 높이(차트 크로스헤어 결). dot↔캔들 x 일치 확인 + 위치 강조. -->
			<div class="discGuide" style={`left:${railBox.left + hoverRail.x}px;top:${railBox.canvasTop}px;height:${railBox.top - railBox.canvasTop}px`}></div>
		{/if}
	{/if}

	{#if textEdit}
		<input
			class="drawTextIn mono"
			style={`left:${Math.round(Math.max(4, textEdit.x - 80))}px; top:${Math.round(Math.max(4, textEdit.y - 38))}px`}
			bind:value={textEdit.value}
			use:focusOnMount
			placeholder={T('메모 입력 후 Enter', 'note + Enter')}
			maxlength="80"
			onkeydown={(e) => {
				e.stopPropagation();
				if (e.key === 'Enter' && !e.isComposing) commitText(true);
				else if (e.key === 'Escape') commitText(false);
			}}
			onblur={() => commitText(true)}
		/>
	{/if}

	{#if ctl.full}
		<ChartRibbon {ctl} {lang} hasBand={!!valBand} {name} {code} info={ribbonInfo} {notice} {peers} {cmpRows} canJump={!!(suggest && onPick)} onSnapshot={snapshot} onReplay={enterReplay} onJump={() => { jumpOpen = true; helpOpen = false; requestAnimationFrame(() => jumpInput?.focus()); }} onHelp={() => { helpOpen = !helpOpen; jumpOpen = false; }} />
		<DrawToolbar {ctl} {lang} onDraw={startDraw} onClearDraw={clearDraw} />

		{#if jumpOpen}
			<!-- 심볼 점프 팔레트 (⌘K · /) — 전체화면을 떠나지 않는 종목 전환 -->
			<div class="chartJump" role="dialog" aria-label={T('종목 점프', 'symbol jump')}>
				<input
					class="cjInput mono"
					bind:this={jumpInput}
					bind:value={jumpQ}
					spellcheck={false}
					placeholder={T('종목코드 · 회사명 — Enter 전환', 'code or name — Enter to switch')}
					oninput={() => (jumpIdx = 0)}
					onkeydown={(e) => {
						e.stopPropagation();
						if (e.key === 'Escape') { jumpOpen = false; return; }
						if (!jumpList.length) return;
						if (e.key === 'ArrowDown') { e.preventDefault(); jumpIdx = (jumpIdx + 1) % jumpList.length; }
						else if (e.key === 'ArrowUp') { e.preventDefault(); jumpIdx = (jumpIdx - 1 + jumpList.length) % jumpList.length; }
						else if (e.key === 'Enter' && !e.isComposing) { e.preventDefault(); jumpTo(jumpList[Math.max(0, jumpIdx)].code); }
					}}
				/>
				{#if jumpList.length}
					<div class="cjList">
						{#each jumpList as s, i (s.code)}
							<button type="button" class={'cjRow' + (i === jumpIdx ? ' on' : '')} onmousedown={() => jumpTo(s.code)} onmouseenter={() => (jumpIdx = i)}>
								<b>{s.name}</b><span class="mono">{s.code}</span><i>{s.industry}</i>
							</button>
						{/each}
					</div>
				{:else if jumpQ.trim()}
					<div class="cjEmpty">{T('검색 결과 없음', 'no match')}</div>
				{/if}
			</div>
		{/if}

		{#if helpOpen}
			<!-- 단축키·숨은기능 도움말 (?) — 발견성: 만들어 둔 기능을 "존재하게" 만드는 1장 -->
			<div class="chartHelp" role="dialog" aria-label={T('단축키 도움말', 'shortcuts')}>
				<div class="chHd">{T('단축키 · 숨은 기능', 'SHORTCUTS & HIDDEN GEMS')}<button class="cbtn cIco" onclick={() => (helpOpen = false)} title="ESC">✕</button></div>
				<div class="chCols">
					<div>
						<div class="chLbl">{T('탐색', 'NAVIGATE')}</div>
						<div class="chRow"><kbd>⌘K</kbd><kbd>/</kbd><span>{T('종목 점프 (전체화면 유지)', 'symbol jump')}</span></div>
						<div class="chRow"><kbd>1</kbd>–<kbd>6</kbd><span>{T('기간 1M·3M·6M·1Y·3Y·MAX', 'period presets')}</span></div>
						<div class="chRow"><kbd>D</kbd><kbd>W</kbd><kbd>M</kbd><kbd>Q</kbd><kbd>Y</kbd><span>{T('봉 주기', 'timeframe')}</span></div>
						<div class="chRow"><kbd>←</kbd><kbd>→</kbd><span>{T('스크롤 · Shift=한 화면', 'scroll · Shift=page')}</span></div>
						<div class="chRow"><kbd>+</kbd><kbd>−</kbd><span>{T('줌', 'zoom')}</span></div>
						<div class="chRow"><kbd>F</kbd><kbd>ESC</kbd><span>{T('전체화면 닫기 (일반 모드 Shift+F 진입)', 'exit fullscreen (Shift+F to enter)')}</span></div>
					</div>
					<div>
						<div class="chLbl">{T('보기 토글', 'VIEW')}</div>
						<div class="chRow"><kbd>A</kbd><span>{T('수정주가', 'adjusted price')}</span></div>
						<div class="chRow"><kbd>L</kbd><span>{T('로그축', 'log axis')}</span></div>
						<div class="chRow"><kbd>G</kbd><span>{T('52주 고저·전일 기준선', '52w/prev refs')}</span></div>
						<div class="chRow"><kbd>S</kbd><span>{T('차트 PNG 저장 (출처 띠 포함)', 'save PNG')}</span></div>
						<div class="chLbl">{T('리플레이', 'REPLAY')}</div>
						<div class="chRow"><kbd>R</kbd><span>{T('리플레이 시작/종료', 'toggle replay')}</span></div>
						<div class="chRow"><kbd>Space</kbd><span>{T('재생/정지', 'play/pause')}</span></div>
						<div class="chRow"><kbd>→</kbd><kbd>←</kbd><span>{T('한 봉 전진/후진', 'step fwd/back')}</span></div>
					</div>
					<div>
						<div class="chLbl">{T('드로잉', 'DRAW')}</div>
						<div class="chRow"><kbd>{T('우클릭', 'R-click')}</kbd><span>{T('도형 삭제', 'delete shape')}</span></div>
						<div class="chRow"><kbd>Del</kbd><span>{T('선택 도형 삭제', 'delete selected')}</span></div>
						<div class="chRow"><kbd>{T('더블클릭', 'Dbl-click')}</kbd><span>{T('텍스트 주석 편집', 'edit text note')}</span></div>
						<div class="chLbl">{T('숨은 기능', 'HIDDEN')}</div>
						<div class="chRow"><span>{T('페인 경계 드래그 = 높이 조절', 'drag pane divider = resize')}</span></div>
						<div class="chRow"><span>{T('드로잉·지표·차트틀은 자동 저장', 'drawings/indicators auto-saved')}</span></div>
						<div class="chRow"><span>{T('차트 좌측 끝 = 과거 자동 로드(2010~)', 'scroll left = auto backfill')}</span></div>
					</div>
				</div>
			</div>
		{/if}
	{:else}
		<ChartMenus {ctl} {lang} hasBand={!!valBand} onDraw={startDraw} onClearDraw={clearDraw} onSnapshot={snapshot} />
	{/if}

	<!-- 출처(공공누리)는 차트 하단 캡션이 아니라 패널 헤더로 — onSrc 콜백(srcText). 스냅샷 PNG 는 srcText 를 띠로 합성(SSOT 유지). -->

	{#if btResult && ctl.btKey}
		<BacktestStrip result={btResult} presetLabel={ctl.activeBt ? T(ctl.activeBt.kr, ctl.activeBt.en) : ''} period={ctl.period} withCosts={ctl.btCosts} adjusted={ctl.adj} {lang} onClear={() => (ctl.btKey = null)} />
	{/if}
</div>

<style>
	/* 공시 위치 레일 — x축 날짜라벨 "아래" 전용 띠(캔버스 하단 padding 영역). left/top/width 는 인라인(캔버스 geometry),
	   bottom:0 으로 띠 높이를 chartWrap 하단까지 채운다. dot 은 중립 슬레이트(축 furniture 처럼 — 알람색 아님). */
	.discRail {
		position: absolute;
		bottom: 0;
		pointer-events: none;
		z-index: 3;
	}
	.discDot {
		position: absolute;
		top: 50%;
		transform: translate(-50%, -50%);
		width: 6px;
		height: 6px;
		padding: 0;
		border: none;
		border-radius: 50%;
		background: #8b97ad; /* 건수=opacity(인라인) */
		cursor: pointer;
		pointer-events: auto;
		transition: transform 0.1s, background 0.1s;
	}
	.discDot.multi {
		width: 8px;
		height: 8px;
		background: #aeb9cc;
	}
	/* 정기보고서(사업/반기/분기) 포함 날짜 — 한눈에 찾도록 amber 링 (캔들 실적 마커와 같은 계열색) */
	.discDot.hasReg {
		box-shadow: 0 0 0 1.5px rgba(251, 146, 60, 0.7);
	}
	.discDot:hover,
	.discDot:focus-visible {
		transform: translate(-50%, -50%) scale(1.5);
		background: #cfe0ff;
		outline: none;
	}
	/* 호버 툴팁 — 그날 공시 전부. 레일 위로 띄움(chartWrap overflow:hidden 안이라 위로는 안 잘림). pointer-events:none. */
	.discTip {
		position: absolute;
		bottom: calc(100% + 4px);
		transform: translateX(-50%);
		min-width: 180px;
		max-width: 264px;
		pointer-events: none;
		background: rgba(12, 16, 24, 0.96);
		border: 1px solid #2a3142;
		border-radius: 4px;
		padding: 5px 7px;
		z-index: 12;
		box-shadow: 0 6px 18px rgba(0, 0, 0, 0.45);
	}
	.discTipHd {
		font-size: 9px;
		color: #8b919e;
		letter-spacing: 0.4px;
		margin-bottom: 3px;
	}
	.discTipDate {
		color: #e2e8f5;
		font-weight: 700;
		font-size: 10px;
	}
	.discTipRow {
		font-size: 10.5px;
		line-height: 1.45;
		color: #cfd3dc;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.discTipTag {
		display: inline-block;
		font-size: 8px;
		color: #fb923c;
		border: 1px solid rgba(251, 146, 60, 0.5);
		border-radius: 2px;
		padding: 0 3px;
		margin-right: 4px;
		vertical-align: 1px;
	}
	.discTipMore {
		font-size: 9.5px;
		color: #6b7280;
		margin-top: 2px;
	}
	.discTipFoot {
		font-size: 9px;
		color: #5b8aa0;
		margin-top: 4px;
		border-top: 1px solid #1c2330;
		padding-top: 3px;
	}
	/* 공시일 세로 가이드선 — dot 호버 시 캔버스 전 높이. 차트 크로스헤어(amber)와 같은 결, 살짝 옅게. */
	.discGuide {
		position: absolute;
		width: 1px;
		pointer-events: none;
		background: rgba(174, 185, 204, 0.5);
		z-index: 4;
	}
</style>
