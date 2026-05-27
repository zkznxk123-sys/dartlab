// financial 탭의 3-mode periodView + TTM 가용성 메타. CompanyHeader (read) ↔
// financial.tsx (write) 간 동기화. URL search param 이 SSOT 이지만 ttmAvailability
// 는 backend 응답 메타라 별도 상태로 전달.

import { create } from 'zustand';

export type PeriodView = 'annual' | 'quarterlyRaw' | 'quarterlyTtm';

export interface TtmAvailability {
	annualFyYears: number;
	quarterlyPeriods: number;
	ttmFullCount: number;
	ttmFallbackCount: number;
	sufficient: boolean;
}

interface FinancialViewState {
	ttmAvail: TtmAvailability | null;
	setTtmAvail: (a: TtmAvailability | null) => void;
}

export const useFinancialView = create<FinancialViewState>((set) => ({
	ttmAvail: null,
	setTtmAvail: (a) => set({ ttmAvail: a }),
}));
