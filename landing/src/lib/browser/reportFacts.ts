// 보고서 비재무 fact 매퍼 — 정기보고서 parquet row → LiveCompanyReportFact. companyLive 에서 격리(순수 row-shaper).
// 타입 import 는 erased(런타임 circular 무해) — 값 의존은 companyLive→reportFacts 단방향.
import type { LiveCompanyReportFact } from './companyLive';

export function toDividendFact(row: any): LiveCompanyReportFact | null {
	if (!row) return null;
	return {
		key: 'dividend',
		label: '배당',
		value: row.thstrm ?? row.se ?? '확인',
		detail: [row.year, row.stlm_dt].filter(Boolean).join(' · '),
		source: '정기보고서 배당'
	};
}

export function toTreasuryFact(row: any): LiveCompanyReportFact | null {
	if (!row) return null;
	return {
		key: 'treasuryStock',
		label: '자사주',
		value: row.trmend_qy ?? '확인',
		detail: [row.year, row.stock_knd, row.change_qy_acqs ? `취득 ${row.change_qy_acqs}` : null]
			.filter(Boolean)
			.join(' · '),
		source: '정기보고서 자사주'
	};
}

export function toExecutiveFact(rows: any[]): LiveCompanyReportFact | null {
	if (!rows.length) return null;
	return {
		key: 'executive',
		label: '임원',
		value: `${rows.length}명`,
		detail: rows.map((r) => [r.nm, r.ofcps].filter(Boolean).join(' ')).join(' · '),
		source: '정기보고서 임원'
	};
}

export function toAuditFact(row: any): LiveCompanyReportFact | null {
	if (!row) return null;
	return {
		key: 'auditOpinion',
		label: '감사의견',
		value: row.adt_opinion ?? '확인',
		detail: [row.year, row.adtor, row.emphs_matter || row.core_adt_matter].filter(Boolean).join(' · '),
		source: '정기보고서 감사'
	};
}

export function toMajorHolderFact(row: any): LiveCompanyReportFact | null {
	if (!row) return null;
	return {
		key: 'majorHolder',
		label: '주요주주',
		value: row.mxmm_shrholdr_nm ?? '확인',
		detail: [row.year, row.qota_rt ? `${row.qota_rt}%` : null, row.change_cause].filter(Boolean).join(' · '),
		source: '정기보고서 주주'
	};
}

export function toCorporateBondFact(row: any): LiveCompanyReportFact | null {
	if (!row) return null;
	return {
		key: 'corporateBond',
		label: '회사채',
		value: row.facvalu_totamt ?? row.scrits_knd_nm ?? '확인',
		detail: [row.year, row.scrits_knd_nm, row.intrt, row.evl_grad_instt].filter(Boolean).join(' · '),
		source: '정기보고서 회사채'
	};
}
