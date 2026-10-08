import type { On } from "claude-code";
import { test, expect, mock } from "claude-code/testing";

type RunInit = { stdin?: string; timeoutMs?: number };
type Run = { argv: readonly string[]; init?: RunInit };

const NAMES = ["backlog_list", "backlog_add", "backlog_close", "memory_add", "contrib_add"];

// The kit has no engine beneath the plugin: every $ call the plugin makes is answered here.
function stubs(on: On, stdout: string, exitCode = 0) {
  const runs: Run[] = [];
  const registered: string[] = [];
  on("tool.register", async (_$, e) => {
    const name = String((e as { name: string }).name);
    registered.push(name);
    return { value: { tool: `mcp__bitranox__${name}` } };
  });
  on("session.start", async (_$, e) => ({ cwd: String((e as { cwd: string }).cwd) }));
  on("process.run", async (_$, e) => {
    runs.push(e as unknown as Run);
    return { value: { exitCode, stdout, stderr: "boom", isStdoutTruncated: false, isStderrTruncated: false } };
  });
  return { runs, registered };
}

test("registers all five tools at session start", async ($, on) => {
  mock.env(on, {});
  const s = stubs(on as never, "{}");
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  expect([...s.registered].sort()).toEqual([...NAMES].sort());
});

test("a call sends the input without the reserved keys and relays the envelope", async ($, on) => {
  mock.env(on, {});
  const env = JSON.stringify({ ok: true, tool: "backlog_add", data: { rank: 20, line: "L" } });
  const s = stubs(on as never, env);
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  const r = await $.tool.call({ tool: "mcp__bitranox__backlog_add", rank: 20, what: "w" } as never);
  expect(typeof (r as { result: unknown }).result).toBe("string");
  expect(JSON.parse((r as { result: string }).result).data.line).toBe("L");
  const sent = JSON.parse(String(s.runs[0].init?.stdin));
  expect(sent).toEqual({ tool: "backlog_add", input: { rank: 20, what: "w" } });
  expect(String(s.runs[0].argv[s.runs[0].argv.length - 1])).toContain("mod_bridge.py");
  expect(s.runs[0].argv[0]).toBe("bash");
});

test("output that is not an envelope comes back as BridgeFailed with the exit code", async ($, on) => {
  mock.env(on, {});
  stubs(on as never, "Traceback ...", 2);
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  const r = await $.tool.call({ tool: "mcp__bitranox__backlog_list" } as never);
  // Core validates a registered tool's result as a string or content blocks; the kit does not.
  expect(typeof (r as { result: unknown }).result).toBe("string");
  const env = JSON.parse((r as { result: string }).result);
  expect(env.error.kind).toBe("BridgeFailed");
  expect(env.error.message).toContain("exit 2");
});

test("a refusal envelope (exit 1) is passed through unchanged as a string", async ($, on) => {
  mock.env(on, {});
  const refusal = { ok: false, tool: "backlog_add", error: { kind: "RankTaken", message: "m" } };
  stubs(on as never, JSON.stringify(refusal), 1);
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  const r = (await $.tool.call({ tool: "mcp__bitranox__backlog_add", rank: 1 } as never)) as { result: unknown };
  expect(typeof r.result).toBe("string");
  expect(JSON.parse(r.result as string)).toEqual(refusal);
});

test("a call carrying agentId or consent sends input without them", async ($, on) => {
  mock.env(on, {});
  const s = stubs(on as never, JSON.stringify({ ok: true, tool: "backlog_add", data: {} }));
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  await $.tool.call({ tool: "mcp__bitranox__backlog_add", rank: 3, agentId: "a1", consent: "c" } as never);
  expect(JSON.parse(String(s.runs[0].init?.stdin))).toEqual({ tool: "backlog_add", input: { rank: 3 } });
});

test("Windows: CLAUDE_CODE_GIT_BASH_PATH is the interpreter when set", async ($, on) => {
  mock.env(on, { CLAUDE_CODE_GIT_BASH_PATH: "C:\\Git\\bin\\bash.exe" });
  const s = stubs(on as never, JSON.stringify({ ok: true, tool: "backlog_list", data: {} }));
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  await $.tool.call({ tool: "mcp__bitranox__backlog_list" } as never);
  expect(s.runs[0].argv[0]).toBe("C:\\Git\\bin\\bash.exe");
});
