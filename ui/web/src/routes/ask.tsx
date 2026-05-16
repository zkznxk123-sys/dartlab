// Ask 라우트 — __root 가 SidebarProvider 제공, 여기는 Chat 만.
import { createFileRoute } from '@tanstack/react-router';
import { Chat } from '@/features/chat/components/Chat';

export const Route = createFileRoute('/ask')({
	component: () => <Chat />,
});
