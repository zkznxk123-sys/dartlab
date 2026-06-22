<script lang="ts">
	// 시장 공시 피드 — 좌측 패널 *전상장사* 최근 3개월 수시공시 시간순. 우측 단일기업(RightStack)과 다른
	// 멘탈모델: 행마다 회사가 바뀌고(회사명 1순위), 행 클릭 = onPick(회사 점프). market_recent.parquet
	// 통파일 1 GET(rt.filing.marketFeed). 주가영향 6탭 + 기관 보조칩. 호재/악재 판정 0 — 시간순 사실 나열.
	import type { MarketFiling } from '@dartlab/ui-contracts';
	import { useDartLabRuntime } from '@dartlab/ui-runtime';
	import type { Lang } from '../lib/types';
	import { Search } from 'lucide-svelte';
	import { MARKET_FEED_CATS, marketFeedCategory, isInstitutionalFiler } from '../lib/marketFeed';
	import Panel from '../ui/Panel.svelte';

	interface Props {
		lang: Lang;
		active: string; // 현재 선택 종목 — 행 강조
		onPick: (code: string) => void; // 행 클릭 → 회사 전환(차트+우측 패널 갱신)
		onFilingSearch?: () => void; // 공시 본문 검색(⌘⇧F) — 시장공시 헤더 아래 배치(읽기↔찾기 한 쌍)
	}
	let { lang, active, onPick, onFilingSearch }: Props = $props();
	const rt = useDartLabRuntime();

	const STEP = 200; // 무한스크롤 윈도우 증가 단위 — 스크롤 끝마다 +200. 데이터(38k)는 이미 메모리라 재fetch 0.
	type FeedState = 'loading' | 'ready' | 'empty' | 'error';
	let feedState = $state<FeedState>('loading');
	let rows = $state<MarketFiling[]>([]);
	let cat = $state('all');
	let instOnly = $state(false);
	let cap = $state(STEP); // 현재 렌더 윈도우 — 가상화 라이브러리 금지(IntersectionObserver DOM 직접)
	let listEl = $state<HTMLDivElement | null>(null);
	let sentinel = $state<HTMLDivElement | null>(null);

	// 분류는 1회 계산(파생 메모이즈) — 탭 전환마다 재분류 금지. bake 가 이미 rcept_dt 내림차순.
	// 기관 표식 — 제출자명이 기관 시그널 AND 제출자≠회사(자기보고 제외). 증권사가 *자기* 발행실적보고서를
	// 내는 건 외부 기관투자자 포지션이 아니므로 ● 금지(적대검증: flr==corp 자기보고는 ownership 아님).
	const classified = $derived(
		rows.map((r) => ({
			r,
			cat: marketFeedCategory(r.reportNm),
			inst: isInstitutionalFiler(r.filer) && r.filer.trim() !== r.corpName.trim()
		}))
	);
	const counts = $derived.by(() => {
		const m: Record<string, number> = { all: classified.length };
		for (const c of MARKET_FEED_CATS) if (c.key !== 'all') m[c.key] = 0;
		for (const x of classified) if (m[x.cat] != null) m[x.cat] += 1;
		return m;
	});
	const showInstChip = $derived(cat === 'all' || cat === 'ownership');
	const filtered = $derived(
		classified.filter((x) => (cat === 'all' || x.cat === cat) && (!(instOnly && showInstChip) || x.inst))
	);
	const shown = $derived(filtered.slice(0, cap));
	// 데이터 as-of — bake 가 rcept_dt 내림차순이라 rows[0] 이 최신. 90일 rolling 인데 데이터가 며칠
	// stale 일 수 있어 '기준일'을 정직 표면화(데이터 max ≠ today 가능). 재정렬 0(rows[0] O(1)).
	const asOf = $derived(rows.length ? rows[0].rceptDate : '');

	$effect(() => {
		let cancelled = false;
		feedState = 'loading';
		rt.filing
			.marketFeed()
			.then((f) => {
				if (cancelled) return;
				rows = f;
				feedState = f.length ? 'ready' : 'empty';
			})
			.catch(() => {
				if (!cancelled) feedState = 'error';
			});
		return () => {
			cancelled = true;
		};
	});

	// 탭/필터 전환 시 윈도우 리셋(과스크롤 방지). cat·instOnly 만 의존(classified/filtered 재계산과 분리).
	$effect(() => {
		cat;
		instOnly;
		cap = STEP;
	});

	// 무한스크롤 — sentinel(리스트 끝)이 뷰포트에 닿으면 cap 점증. 데이터는 이미 메모리(재fetch 0·재분류 0).
	// 효과 본문은 sentinel/listEl 만 읽음(cap·filtered 는 콜백에서만 읽어 IO 재생성 방지).
	$effect(() => {
		if (!sentinel || !listEl) return;
		const io = new IntersectionObserver(
			(entries) => {
				if (entries[0]?.isIntersecting && cap < filtered.length) cap += STEP;
			},
			{ root: listEl, rootMargin: '300px' }
		);
		io.observe(sentinel);
		return () => io.disconnect();
	});

	const mmdd = (d: string) => (d.length >= 10 ? d.slice(5).replace('-', '') : d); // YYYY-MM-DD → MMDD
	const t = (kr: string, en: string) => (lang === 'en' ? en : kr);
</script>

<Panel
	{lang}
	className="eMarketFeed"
	prov="real"
	title={{ kr: '시장 공시', en: 'MARKET FILINGS' }}
	sub={{
		kr: asOf ? `전상장사 · ~${asOf} 기준` : '전상장사 · 최근 3개월',
		en: asOf ? `all listed · as-of ${asOf}` : 'all listed · 3mo'
	}}
	flush
>
	<!-- 공시 본문 검색 — 시장공시 헤더 바로 아래(읽기↔찾기 한 쌍). 클릭=⌘⇧F 다이얼로그(FilingSearchDialog). -->
	{#if onFilingSearch}
		<button class="feedSearchBar" onclick={() => onFilingSearch?.()} title={t('전역 공시 본문 검색 (⌘⇧F)', 'global filing full-text search (⌘⇧F)')}>
			<Search class="feedSearchIcon" size={13} />
			<span class="feedSearchPh">{t('공시 본문 검색', 'Search filing text')}</span>
			<kbd class="feedSearchKbd">⌘⇧F</kbd>
		</button>
	{/if}

	<!-- 카테고리 칩 스트립 — 라벨만(컴팩트)이라 좁은 좌측 패널서도 전 탭 노출. 공시 갯수는 hover tooltip. -->
	<div class="feedCats">
		{#each MARKET_FEED_CATS as c (c.key)}
			<button
				class={'feedCat' + (cat === c.key ? ' on' : '')}
				onclick={() => (cat = c.key)}
				title={counts[c.key] != null ? `${c.kr} ${counts[c.key].toLocaleString()}${lang === 'en' ? '' : '건'}` : c.kr}
			>{c.kr}</button>
		{/each}
	</div>

	<!-- 기관 보조칩 — 지분·내부자/전체 탭에서만. flr_nm 기반·근사(약10%)·미식별 다수 정직 라벨 -->
	{#if showInstChip}
		<div class="feedSub">
			<button
				class={'feedInst' + (instOnly ? ' on' : '')}
				onclick={() => (instOnly = !instOnly)}
				title={t(
					'제출자명(flr_nm) 기반 기관·연금 식별 — 부분식별(약 10%)·미식별 다수. 행 hover 로 제출자 원문 확인',
					'filer-name based · partial (~10%) · hover row for raw filer'
				)}>{t('기관·연금', 'Institutional')}{instOnly ? ' ✓' : ''}</button
			>
			<span class="feedInstNote">{t('제출자 기준 · 근사', 'by filer · approx')}</span>
		</div>
	{/if}

	{#if feedState === 'ready'}
		<div class="filingList feedList" bind:this={listEl}>
			{#each shown as x (x.r.rceptNo)}
				<div
					class={'filingRow feedRow' + (active === x.r.stockCode ? ' on' : '')}
					role="button"
					tabindex="0"
					onclick={() => onPick(x.r.stockCode)}
					onkeydown={(e) => e.key === 'Enter' && onPick(x.r.stockCode)}
					title={x.r.corpName + ' · ' + x.r.reportNm + (x.r.filer ? ' · ' + x.r.filer : '')}
				>
					<span class="feedCorp"
						><span class="feedCorpName">{x.r.corpName}</span>{#if x.inst}<span class="feedInstDot" title={x.r.filer}>●</span>{/if}</span
					>
					<span class="flType feedNm">{x.r.reportNm}</span>
					<span class="flDate mono">{mmdd(x.r.rceptDate)}</span>
					<a class="flArrow" href={x.r.url} target="_blank" rel="noopener" onclick={(e) => e.stopPropagation()}>↗</a>
				</div>
			{/each}
			{#if cap < filtered.length}
				<div class="feedCap" bind:this={sentinel}>{t(`${cap.toLocaleString()} / ${filtered.length.toLocaleString()}건 · 스크롤하면 더 보기`, `${cap.toLocaleString()} / ${filtered.length.toLocaleString()} · scroll for more`)}</div>
			{:else if filtered.length > STEP}
				<div class="feedCap">{t(`전체 ${filtered.length.toLocaleString()}건`, `all ${filtered.length.toLocaleString()}`)}</div>
			{/if}
		</div>
	{:else if feedState === 'loading'}
		<div class="storyEmpty">{t('시장 공시 불러오는 중 …', 'loading market filings …')}</div>
	{:else if feedState === 'error'}
		<div class="storyEmpty">{t('시장 공시를 불러오지 못함', 'failed to load market filings')}</div>
	{:else}
		<div class="storyEmpty">{t('최근 공시 없음', 'no recent filings')}</div>
	{/if}
</Panel>
