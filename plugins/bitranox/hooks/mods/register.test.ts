import type { On } from "claude-code";
import { test, expect, mock } from "claude-code/testing";

type RunInit = { stdin?: string; timeoutMs?: number };
type Run = { argv: readonly string[]; init?: RunInit };

const NAMES = ["backlog_list", "backlog_add", "backlog_close", "memory_add", "contrib_add"];

// Every test makes one call: the bridge run it caused, typed as present.
function only(runs: Run[]): Run {
  expect(runs.length).toBe(1);
  const run = runs[0];
  if (run === undefined) throw new Error("no process.run");
  return run;
}

// The kit has no engine beneath the plugin: every $ call the plugin makes is answered here.
function stubs(on: On, stdout: string, exitCode = 0, reject?: string, sessionId: string | Error = "sess-abc") {
  const runs: Run[] = [];
  const registered: string[] = [];
  on("tool.register", async (_$, e) => {
    const name = String((e as { name: string }).name);
    registered.push(name);
    return { value: { tool: `mcp__bitranox__${name}` } };
  });
  on("session.start", async (_$, e) => ({ cwd: String((e as { cwd: string }).cwd) }));
  on("session.id", async () => {
    if (sessionId instanceof Error) throw sessionId;
    return { value: sessionId };
  });
  on("process.run", async (_$, e) => {
    runs.push(e as unknown as Run);
    if (reject) throw new Error(reject);
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
  const sent = JSON.parse(String(only(s.runs).init?.stdin));
  expect(sent).toEqual({ tool: "backlog_add", input: { rank: 20, what: "w" }, session_id: "sess-abc" });
  expect(String(only(s.runs).argv[only(s.runs).argv.length - 1])).toContain("mod_bridge.py");
  expect(only(s.runs).argv[0]).toBe("bash");
});

// A could-not-run outcome reaches the model as a tool error: `{ deny }` is the text the model
// receives as an error result (ToolCallResult in claude-code/index.d.ts).
test("output that is not an envelope is a tool error naming BridgeFailed and the exit code", async ($, on) => {
  mock.env(on, {});
  stubs(on as never, "Traceback ...", 2);
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  const r = (await $.tool.call({ tool: "mcp__bitranox__backlog_list" } as never)) as { deny?: string; result?: unknown };
  expect(r.result).toBeUndefined();
  const env = JSON.parse(String(r.deny));
  expect(env.error.kind).toBe("BridgeFailed");
  expect(env.error.message).toContain("exit 2");
});

test("an envelope that arrives with exit code 2 is a tool error carrying that envelope", async ($, on) => {
  mock.env(on, {});
  const bad = { ok: false, tool: "backlog_add", error: { kind: "BadRequest", message: "m" } };
  stubs(on as never, JSON.stringify(bad), 2);
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  const r = (await $.tool.call({ tool: "mcp__bitranox__backlog_add", rank: 1 } as never)) as { deny?: string; result?: unknown };
  expect(r.result).toBeUndefined();
  expect(JSON.parse(String(r.deny))).toEqual(bad);
});

test("a rejected process.run is a tool error naming BridgeFailed", async ($, on) => {
  mock.env(on, {});
  stubs(on as never, "", 0, "spawn failed");
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  const r = (await $.tool.call({ tool: "mcp__bitranox__backlog_list" } as never)) as { deny?: string; result?: unknown };
  expect(r.result).toBeUndefined();
  const env = JSON.parse(String(r.deny));
  expect(env.error.kind).toBe("BridgeFailed");
  // the kit reports a throwing stub as an unanswered process.run; a live engine rejects likewise
  expect(env.error.message).toContain("process.run");
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

test("a call carrying agentId, consent or tool_use_id sends input without them", async ($, on) => {
  mock.env(on, {});
  const s = stubs(on as never, JSON.stringify({ ok: true, tool: "backlog_add", data: {} }));
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  await $.tool.call({
    tool: "mcp__bitranox__backlog_add", rank: 3, agentId: "a1", consent: "c", tool_use_id: "toolu_1",
  } as never);
  expect(JSON.parse(String(only(s.runs).init?.stdin))).toEqual({
    tool: "backlog_add", input: { rank: 3 }, session_id: "sess-abc",
  });
});

test("Windows: CLAUDE_CODE_GIT_BASH_PATH is the interpreter when set", async ($, on) => {
  mock.env(on, { CLAUDE_CODE_GIT_BASH_PATH: "C:\\Git\\bin\\bash.exe" });
  const s = stubs(on as never, JSON.stringify({ ok: true, tool: "backlog_list", data: {} }));
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  await $.tool.call({ tool: "mcp__bitranox__backlog_list" } as never);
  expect(only(s.runs).argv[0]).toBe("C:\\Git\\bin\\bash.exe");
});

test("an empty CLAUDE_CODE_GIT_BASH_PATH falls back to bash", async ($, on) => {
  mock.env(on, { CLAUDE_CODE_GIT_BASH_PATH: "" });
  const s = stubs(on as never, JSON.stringify({ ok: true, tool: "backlog_list", data: {} }));
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  await $.tool.call({ tool: "mcp__bitranox__backlog_list" } as never);
  expect(only(s.runs).argv[0]).toBe("bash");
});

test("a hook that throws before it ran anything is refused by the catch handler", async ($, on) => {
  on("env.get", async () => {
    throw new Error("env unavailable");
  });
  stubs(on as never, "{}");
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  const r = (await $.tool.call({ tool: "mcp__bitranox__backlog_list" } as never)) as { deny?: string; result?: unknown };
  expect(r.result).toBeUndefined();
  expect(String(r.deny)).toContain("backlog_list tool failed before it ran");
});

// The claude process carries no CLAUDE_CODE_SESSION_ID, so the bridge cannot read it from the
// environment it inherits: the session id travels on stdin, beside (never inside) the input.
test("a call sends the session id beside the input", async ($, on) => {
  mock.env(on, {});
  const s = stubs(on as never, JSON.stringify({ ok: true, tool: "backlog_add", data: {} }), 0, undefined, "sess-xyz");
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  await $.tool.call({ tool: "mcp__bitranox__backlog_add", rank: 5, session_id: "forged" } as never);
  const sent = JSON.parse(String(only(s.runs).init?.stdin));
  expect(sent.session_id).toBe("sess-xyz");
  expect(sent.input).toEqual({ rank: 5, session_id: "forged" });
});

test("a session id that cannot be read still runs the call, with an empty id", async ($, on) => {
  mock.env(on, {});
  const s = stubs(on as never, JSON.stringify({ ok: true, tool: "backlog_add", data: {} }), 0, undefined, new Error("no id"));
  await $.session.start({ source: "startup", cwd: "/tmp" } as never);
  const r = (await $.tool.call({ tool: "mcp__bitranox__backlog_add", rank: 5 } as never)) as { result?: unknown };
  expect(typeof r.result).toBe("string");
  expect(JSON.parse(String(only(s.runs).init?.stdin)).session_id).toBe("");
});
