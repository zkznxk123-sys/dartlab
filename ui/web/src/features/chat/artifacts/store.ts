// Artifact 패널 상태 — 우측 Sheet 양식.
import { create } from 'zustand';

import type { ViewSpecPart } from '@/features/chat/store/chat';

interface ArtifactState {
	open: boolean;
	current: ViewSpecPart | null;
	openArtifact: (part: ViewSpecPart) => void;
	close: () => void;
}

export const useArtifact = create<ArtifactState>((set) => ({
	open: false,
	current: null,
	openArtifact: (part) => set({ open: true, current: part }),
	close: () => set({ open: false }),
}));
