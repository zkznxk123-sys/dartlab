import { describe, it, expect } from "vitest";
import { groupLoops } from "../../lib/agent/conversationModel.js";

describe("groupLoops — 한 메시지 = 한 loop-card", () => {
	it("연속 activity·tool·skill 모두 단일 loop-card 1개로 묶음", () => {
		const parts = [
			{ type: "activity", id: "a1", summary: "skill 검색", status: "done" },
			{ type: "tool", id: "t1", name: "ReadSkill", status: "done", summary: "ask_pattern" },
			{ type: "tool", id: "t2", name: "ReadCapability", status: "done", summary: "scan" },
			{ type: "tool", id: "t3", name: "RunPython", status: "done", summary: "매출 계산" },
			{ type: "tool", id: "t4", name: "Read", status: "done", summary: "파일 인용" },
			{ type: "tool", id: "t5", name: "RunPython", status: "running", summary: "차트" },
		];
		const out = groupLoops(parts);
		expect(out).toHaveLength(1);
		expect(out[0].type).toBe("loop-card");
		expect(out[0].rows).toHaveLength(6);
		expect(out[0].running).toBe(true);
		expect(out[0].toolCount).toBe(5);
		expect(out[0].activityCount).toBe(1);
	});

	it("RESEARCH 도구는 row.kind = skill, 일반 도구는 row.kind = tool, activity 는 activity", () => {
		const parts = [
			{ type: "activity", id: "a1", summary: "계획", status: "done" },
			{ type: "tool", id: "t1", name: "ReadSkill", status: "done" },
			{ type: "tool", id: "t2", name: "RunPython", status: "done" },
		];
		const out = groupLoops(parts);
		const kinds = out[0].rows.map((r) => r.kind);
		expect(kinds).toEqual(["activity", "skill", "tool"]);
	});

	it("view-spec / text / failure 는 동위로 통과 — bucket 닫고 그 part 그대로", () => {
		const parts = [
			{ type: "tool", id: "t1", name: "RunPython", status: "done" },
			{ type: "view-spec", id: "v1", spec: { component: "chart" } },
			{ type: "tool", id: "t2", name: "RunPython", status: "done" },
			{ type: "text", id: "x1", content: "최종 답변" },
			{ type: "failure", id: "f1", summary: "검증 실패" },
		];
		const out = groupLoops(parts);
		expect(out).toHaveLength(5);
		expect(out[0].type).toBe("loop-card");
		expect(out[0].rows).toHaveLength(1);
		expect(out[1].type).toBe("view-spec");
		expect(out[2].type).toBe("loop-card");
		expect(out[2].rows).toHaveLength(1);
		expect(out[3].type).toBe("text");
		expect(out[4].type).toBe("failure");
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

	it("error row 가 하나라도 있으면 loop-card.status = error 우선", () => {
		const parts = [
			{ type: "tool", id: "t1", name: "RunPython", status: "done" },
			{ type: "tool", id: "t2", name: "RunPython", status: "error", summary: "실패" },
		];
		const out = groupLoops(parts);
		expect(out[0].errorCount).toBe(1);
		expect(out[0].status).toBe("error");
	});

	it("label — 첫 activity phase 우선, activity 없으면 '분석'", () => {
		expect(groupLoops([{ type: "activity", summary: "검증 통과", status: "done" }])[0].label).toBe("검증");
		expect(groupLoops([{ type: "activity", summary: "skill 검색", status: "done" }])[0].label).toBe("계획");
		expect(groupLoops([{ type: "tool", id: "t1", name: "RunPython", status: "done" }])[0].label).toBe("분석");
	});

	it("빈 / 비배열 입력 — 빈 배열 반환", () => {
		expect(groupLoops([])).toEqual([]);
		expect(groupLoops(null)).toEqual([]);
		expect(groupLoops(undefined)).toEqual([]);
	});

	it("같은 메시지 안 RESEARCH 도구가 흩어져도 한 카드 — 사용자 정의 '한 루프' 정합", () => {
		const parts = [
			{ type: "activity", id: "a1", summary: "사전조사", status: "done" },
			{ type: "tool", id: "t1", name: "ReadSkill", status: "done" },
			{ type: "tool", id: "t2", name: "RunPython", status: "done" },
			{ type: "tool", id: "t3", name: "ReadCapability", status: "done" },
			{ type: "tool", id: "t4", name: "RunPython", status: "done" },
		];
		const out = groupLoops(parts);
		expect(out).toHaveLength(1);
		expect(out[0].rows).toHaveLength(5);
	});
});
