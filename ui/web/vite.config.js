import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";
import legacy from "@vitejs/plugin-legacy";
import path from "path";

const BUILD_ID = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);

export default defineConfig({
	plugins: [
		svelte(),
		tailwindcss(),
		legacy({
			targets: ["defaults", "not IE 11", "Android >= 80", "Chrome >= 80"],
			modernPolyfills: true,
			renderLegacyChunks: true,
		}),
	],
	define: {
		__BUILD_ID__: JSON.stringify(BUILD_ID),
	},
	resolve: {
		alias: {
			$lib: path.resolve("./src/lib"),
		},
	},
	build: {
		outDir: "build",
		emptyOutDir: true,
		// 명시적 target — 일부 모바일 Chrome이 최신 ES 문법 못 파싱하는 경우 대비.
		// es2020 = Chrome 80+, Safari 13.1+ (대부분 폰 호환)
		target: "es2020",
	},
	server: {
		proxy: {
			"/api": "http://localhost:8400",
		},
	},
});
