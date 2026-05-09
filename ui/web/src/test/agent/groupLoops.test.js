import { describe, it, expect } from "vitest";
import { groupLoops } from "../../lib/agent/conversationModel.js";

describe("groupLoops", () => {
	it("연속 activity 를 phase 별 loop-card 로 묶는다", () => {
		const parts = [
			{ type: "activity", id: "a1", summary: "skill 검색", status: "done" },
			{ type: "activity", id: "a2", summary: "recipe 결정", status: "done" },
			{ type: "activity", id: "a3", summary: "도구 실행", status: "running" },
		];
		const out = groupLoops(parts);
		expect(out).toHaveLength(2);
		expect(out[0].type).toBe("loop-card");
		expect(out[0].label).toBe("계획");
		expect(out[0].rows).toHaveLength(2);
		expect(out[1].label).toBe("실행");
		expect(out[1].running).toBe(true);
	});

	it("RESEARCH 도구 (ReadSkill·ReadCapability·GetSkillBody) 는 skill row kind 로 묶인다", () => {
		const parts = [
			{ type: "tool", id: "t1", name: "ReadSkill", status: "done", summary: "ask_pattern" },
			{ type: "tool", id: "t2", name: "ReadCapability", status: "done", summary: "scan" },
		];
		const out = groupLoops(parts);
		expect(out).toHaveLength(1);
		expect(out[0].type).toBe("loop-card");
		expect(out[0].label).toBe("사전조사");
		expect(out[0].rows.every((r) => r.kind === "skill")).toBe(true);
		expect(out[0].toolCount).toBe(2);
	});

	it("일반 도구 (RunPython 등) 는 tool row kind 로 묶인다", () => {
		const parts = [
			{ type: "tool", id: "t1", name: "RunPython", status: "done", summary: "매출 계산" },
			{ type: "tool", id: "t2", name: "EngineCall", status: "done", summary: "scan growth" },
		];
		const out = groupLoops(parts);
		expect(out).toHaveLength(1);
		expect(out[0].label).toBe("도구 실행");
		expect(out[0].rows.every((r) => r.kind === "tool")).toBe(true);
	});

	it("백엔드 passLabel 메타가 있으면 같은 pass 를 한 카드로", () => {
		const parts = [
			{ type: "tool", id: "t1", name: "RunPython", status: "done", passLabel: "WORK" },
			{ type: "activity", id: "a1", summary: "결과 검토", status: "done", passLabel: "WORK" },
			{ type: "tool", id: "t2", name: "Verify", status: "done", passLabel: "CRITIQUE" },
		];
		const out = groupLoops(parts);
		expect(out).toHaveLength(2);
		expect(out[0].label).toBe("WORK");
		expect(out[0].rows).toHaveLength(2);
		expect(out[1].label).toBe("CRITIQUE");
	});

	it("view-spec / text / failure 는 그대로 통과", () => {
		const parts = [
			{ type: "tool", id: "t1", name: "RunPython", status: "done" },
			{ type: "view-spec", id: "v1", spec: { component: "chart" } },
			{ type: "text", id: "x1", content: "최종 답변" },
			{ type: "failure", id: "f1", summary: "검증 실패" },
		];
		const out = groupLoops(parts);
		expect(out).toHaveLength(4);
		expect(out[0].type).toBe("loop-card");
		expect(out[1].type).toBe("view-spec");
		expect(out[2].type).toBe("text");
		expect(out[3].type).toBe("failure");
	});

	it("running row 가 있으면 loop-card.running = true, status = running", () => {
		const parts = [
			{ type: "tool", id: "t1", name: "RunPython", status: "done" },
			{ type: "tool", id: "t2", name: "RunPython", status: "running" },
		];
		const out = groupLoops(parts);
		expect(out[0].running).toBe(true);
		expect(out[0].status).toBe("running");
	});

	it("error row 가 하나라도 있으면 loop-card.status = error 로 우선", () => {
		const parts = [
			{ type: "tool", id: "t1", name: "RunPython", status: "done" },
			{ type: "tool", id: "t2", name: "RunPython", status: "error", summary: "실패" },
		];
		const out = groupLoops(parts);
		expect(out[0].errorCount).toBe(1);
		expect(out[0].status).toBe("error");
	});

	it("빈 / 비배열 입력 — 빈 배열 반환", () => {
		expect(groupLoops([])).toEqual([]);
		expect(groupLoops(null)).toEqual([]);
		expect(groupLoops(undefined)).toEqual([]);
	});
});
