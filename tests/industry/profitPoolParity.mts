// industry-analysis-lab Phase A 구멍1 — profit-pool 브라우저 롤업 parity 게이트 (standalone node, vitest 0).
//
// surfaces/landing 에는 test-runner 가 없으므로 (CI 미배선 — 운영자 결정 [07 §3], 06 §4 수동줄) 본
// 스크립트를 tsx 로 직접 돌린다. SOURCE OF TRUTH = ui/packages/surfaces/src/map/industryPool.ts.
//
//   실행: npx tsx tests/industry/profitPoolParity.mts
//
// dual-source SSOT 단언 (07 §구멍4, critic mustFix):
//   엔진 캐논(tests/industry/test_financials_sanity.py::TestProfitPoolDerived) 과 *완전일치*를
//   강제하지 않는다 (브라우저 per-node opMargin vs 엔진 Σopinc/Σrev 는 모집단·커버리지가 달라 거짓
//   실패). 대신 브라우저 롤업이 (a) revenue-weighted (단순평균 아님) (b) coverageRatio 를 항상
//   노출 (결손 0 채움 금지) 함을 단언 — 화면이 커버리지 차이를 라벨할 수 있게.

import { rollupProfitPool } from '../../ui/packages/surfaces/src/map/industryPool.ts';

let failures = 0;
function ok(label: string): void {
	console.log(`  PASS  ${label}`);
}
function fail(label: string, detail: string): void {
	failures += 1;
	console.log(`  FAIL  ${label}\n        ${detail}`);
}
function eq(label: string, got: unknown, want: unknown): void {
	if (got === want) ok(label);
	else fail(label, `got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);
}

// ── (1) revenue-weighted ≠ 단순평균 ──
// big 매출 100·마진 10%, small 매출 1·마진 50% → 가중 (100·10+1·50)/101 = 10.4, 단순평균 30.
{
	const r = rollupProfitPool([
		{
			key: 'fab',
			name: '전공정',
			nodes: [
				{ revenue: 100, opMargin: 10 },
				{ revenue: 1, opMargin: 50 }
			]
		}
	])[0];
	eq('(1) revenue-weighted margin = 10.4 (단순평균 30 아님)', r.opMarginPct, 10.4);
	eq('(1) coverageRatio = 1.0 (둘 다 opMargin present)', r.coverageRatio, 1.0);
}

// ── (2) coverageRatio 결손 제외 (0 채움 금지) ──
// a·b present, c opMargin null → coverage 2/3, margin 은 a·b 만 가중(10.4), c 0 채움 안 함.
{
	const r = rollupProfitPool([
		{
			key: 'fab',
			name: '전공정',
			nodes: [
				{ revenue: 100, opMargin: 10 },
				{ revenue: 1, opMargin: 50 },
				{ revenue: 5, opMargin: null }
			]
		}
	])[0];
	eq('(2) companyCount = 3 (결손 포함 전체)', r.companyCount, 3);
	eq('(2) coverageRatio = 0.667 (2/3)', r.coverageRatio, 0.667);
	eq('(2) margin = 10.4 (결손 c 제외, 0 채움 시 깎였을 것)', r.opMarginPct, 10.4);
	eq('(2) revenue = 106 (매출은 전체 합산)', r.revenue, 106);
}

// ── (3) opMargin 전무 / 매출 0 → margin null, coverage 0 (division 에러·0 채움 금지) ──
{
	const r = rollupProfitPool([
		{ key: 'x', name: 'x', nodes: [{ revenue: 0, opMargin: null }] }
	])[0];
	eq('(3) opMarginPct = null (0 아님)', r.opMarginPct, null);
	eq('(3) coverageRatio = 0', r.coverageRatio, 0);
}

// ── (4) dual-source 노출 — 모든 stage row 가 coverageRatio number 보유 ──
{
	const rows = rollupProfitPool([
		{ key: 'a', name: 'a', nodes: [{ revenue: 10, opMargin: 5 }] },
		{ key: 'b', name: 'b', nodes: [] }
	]);
	const allHaveCoverage = rows.every((r) => typeof r.coverageRatio === 'number');
	eq('(4) 모든 stage 가 coverageRatio 노출 (화면 라벨 가능)', allHaveCoverage, true);
	eq('(4) 빈 stage coverage 0', rows[1].coverageRatio, 0);
}

console.log(`\n${failures === 0 ? 'ALL PASS' : `${failures} FAILURE(S)`}\n`);
process.exit(failures === 0 ? 0 : 1);
