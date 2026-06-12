// 마지막으로 사용자가 진입한 분석 모드 ('financial' | 'viewer' | 'terminal').
// 종목 전환 시 허브가 이 값을 보고 직전 모드 데이터 prefetch 우선순위를
// 결정한다. 사용자가 viewer 보다가 다른 종목 누르면 → 새 종목 viewer 데이터를
// 먼저 준비 (사용자가 같은 모드로 다시 들어갈 확률 높음).

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type DashboardMode = 'financial' | 'viewer' | 'terminal';

interface DashboardModeState {
	lastMode: DashboardMode | null;
	setLastMode: (mode: DashboardMode) => void;
}

export const useDashboardMode = create<DashboardModeState>()(
	persist(
		(set) => ({
			lastMode: null,
			setLastMode: (mode) => set({ lastMode: mode }),
		}),
		{ name: 'dash:lastMode' },
	),
);
