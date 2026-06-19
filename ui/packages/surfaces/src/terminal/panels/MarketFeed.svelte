<script lang="ts">
	// 시장 공시 피드 — 좌측 패널 *전상장사* 최근 3개월 수시공시 시간순. 우측 단일기업(RightStack)과 다른
	// 멘탈모델: 행마다 회사가 바뀌고(회사명 1순위), 행 클릭 = onPick(회사 점프). market_recent.parquet
	// 통파일 1 GET(rt.filing.marketFeed). 주가영향 6탭 + 기관 보조칩. 호재/악재 판정 0 — 시간순 사실 나열.
	import type { MarketFiling } from '@dartlab/ui-contracts';
	import { useDartLabRuntime } from '@dartlab/ui-runtime';
	import type { Lang } from '../lib/types';
	import { MARKET_FEED_CATS, marketFeedCategory, isInstitutionalFiler } from '../lib/marketFeed';
	import Panel from '../ui/Panel.svelte';

	interface Props {
		lang: Lang;
		active: string; // 현재 선택 종목 — 행 강조
		onPick: (code: string) => void; // 행 클릭 → 회사 전환(차트+우측 패널 갱신)
	}
	let { lang, active, onPick }: Props = $props();
	const rt = useDartLabRuntime();

	const CAP = 200; // 표시 상한 — 전수는 칩 카운트로 표면화(top-N 침묵 절단 아님)
	type FeedState = 'loading' | 'ready' | 'empty' | 'error';
	let feedState = $state<FeedState>('loading');
	let rows = $state<MarketFiling[]>([]);
	let cat = $state('all');
	let instOnly = $state(false);

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
	const shown = $derived(filtered.slice(0, CAP));

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

	const mmdd = (d: string) => (d.length >= 10 ? d.slice(5).replace('-', '') : d); // YYYY-MM-DD → MMDD
	const t = (kr: string, en: string) => (lang === 'en' ? en : kr);
</script>

<Panel
	{lang}
	className="eMarketFeed"
	prov="real"
	title={{ kr: '시장 공시', en: 'MARKET FILINGS' }}
	sub={{ kr: '전상장사 · 최근 3개월', en: 'all listed · 3mo' }}
	flush
>
	<!-- 카테고리 칩 스트립 — 가로 스크롤. 활성 칩 amber underline + 전수 카운트 배지 -->
	<div class="feedCats">
		{#each MARKET_FEED_CATS as c (c.key)}
			<button class={'feedCat' + (cat === c.key ? ' on' : '')} onclick={() => (cat = c.key)}>
				{c.kr}{#if counts[c.key]}<span class="feedCatN">{counts[c.key].toLocaleString()}</span>{/if}
			</button>
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
		<div class="filingList feedList">
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
			{#if filtered.length > CAP}
				<div class="feedCap">{t(`최근순 ${CAP}건 표시 · 전체 ${filtered.length.toLocaleString()}건`, `${CAP} of ${filtered.length.toLocaleString()}`)}</div>
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
