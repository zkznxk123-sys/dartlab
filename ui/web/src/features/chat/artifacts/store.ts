// Artifact 패널 상태 — 우측 Sheet 양식.
// ChatGPT Canvas / Claude Artifacts 패턴 — 차트/표 + workspace 컨텍스트 함께.
import { create } from 'zustand';

import type { ViewSpecPart } from '@/features/chat/store/chat';

interface ArtifactState {
	open: boolean;
	current: ViewSpecPart | null;
	openArtifact: (part: ViewSpecPart) => void;
	togglePanel: () => void; // workspace 컨텍스트만 보고 싶을 때 — current 없이 panel open/close
	close: () => void;
}

export const useArtifact = create<ArtifactState>((set, get) => ({
	open: false,
	current: null,
	openArtifact: (part) => set({ open: true, current: part }),
	togglePanel: () => set({ open: !get().open }),
	close: () => set({ open: false }),
}));
