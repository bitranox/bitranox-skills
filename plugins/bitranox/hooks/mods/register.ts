import type { Register } from "claude-code";

// The tools' rules live in hooks/mod_bridge.py and the Python it calls; this module only relays.
const TIMEOUT_MS = 60_000;
const RESERVED = new Set(["tool", "tool_use_id"]);

const str = (description: string) => ({ type: "string", description });

const TOOLS = [
  {
    name: "backlog_list",
    description:
      "List this repo's OPEN-WORK.md backlog items (open by default). Read it before backlog_add to choose a rank.",
    inputSchema: { type: "object", properties: { state: { type: "string", enum: ["open", "closed", "all"] } } },
  },
  {
    name: "backlog_add",
    description:
      "Add one item to this repo's OPEN-WORK.md backlog. YOU choose the rank: USER items above FOUND ones, a USER item the user deferred below the live USER items but above every FOUND one, bigger size first within an origin. The tool refuses a rank any line already holds (closed lines included) and suggests free tens. Omit `raised` unless you know when it was first raised: the tool then writes today's date with '?', never a guessed one.",
    inputSchema: {
      type: "object",
      required: ["rank", "origin", "what", "size", "open", "next"],
      properties: {
        rank: { type: "integer", minimum: 1 },
        origin: { type: "string", enum: ["USER", "FOUND"] },
        what: str("what it is, one line (the user's own words for a USER item)"),
        size: str("how much is left; 'unknown' is honest, an invented count is not"),
        open: str("why it is still open"),
        next: str("the concrete next action"),
        raised: str("YYYY-MM-DD, YYYY-MM-DD? or unknown; omit for today with '?'"),
      },
    },
  },
  {
    name: "backlog_close",
    description: "Close one open OPEN-WORK.md item by rank with a reason. The line stays, marked [x].",
    inputSchema: {
      type: "object",
      required: ["rank", "reason"],
      properties: { rank: { type: "integer", minimum: 1 }, reason: str("why it is closed, one line") },
    },
  },
  {
    name: "memory_add",
    description:
      "Capture or update one curated bitranox memory fact (the memory engine's add). `level` is the directory whose subtree the fact concerns (default: the session cwd); an update must target the level that owns the fact, or it is refused as SlugCollision. The hook is trigger-first ('When <situation>, <directive>'), at most 500 chars; warnings come back in the result.",
    inputSchema: {
      type: "object",
      required: ["title", "hook", "body"],
      properties: {
        title: str("short title"),
        hook: str("one line, trigger-first"),
        body: str("the fact body (multi-line allowed)"),
        level: str("directory to capture at; default the session cwd"),
        type: { type: "string", enum: ["user", "feedback", "project", "reference"] },
        slug: str("target an existing fact explicitly"),
      },
    },
  },
  {
    name: "contrib_add",
    description:
      "Queue one bitranox hook or skill contribution (contrib_queue add) instead of fixing the tool in place during unrelated work. A duplicate or an already closed intent is not re-queued; the result says why.",
    inputSchema: {
      type: "object",
      required: ["what", "target", "why"],
      properties: {
        what: str("the change, one line"),
        target: str("where it goes, e.g. hook or skill:<name>"),
        why: str("the evidence it is needed"),
      },
    },
  },
] as const;

function failure(tool: string, kind: string, message: string) {
  return { ok: false, tool, error: { kind, message } };
}

function envelopeFrom(tool: string, run: { exitCode: number; stdout: string; stderr: string }) {
  try {
    const parsed: unknown = JSON.parse(run.stdout);
    if (parsed !== null && typeof parsed === "object" && "ok" in parsed) return parsed;
  } catch {
    // not an envelope: report what the bridge printed instead
  }
  const said = (run.stderr || run.stdout).slice(0, 2000);
  return failure(tool, "BridgeFailed", `exit ${run.exitCode}: ${said}`);
}

export const register: Register = (on) => {
  on("session.start", async ($, e, next) => {
    for (const spec of TOOLS) await $.tool.register(spec as never);
    return next(e);
  });

  for (const spec of TOOLS) {
    on("tool.call", { tool: `mcp__bitranox__${spec.name}` }, async ($, e) => {
      const input = Object.fromEntries(
        Object.entries(e as Record<string, unknown>).filter(([k]) => !RESERVED.has(k)),
      );
      // On Windows a bare "bash" can resolve to the WSL stub; Claude Code's own Git Bash setting wins.
      const bash = (await $.env.get("CLAUDE_CODE_GIT_BASH_PATH")) ?? "bash";
      const root = $.plugin.root;
      try {
        const run = await $.process.run(
          [bash, `${root}/hooks/run-python.sh`, `${root}/hooks/mod_bridge.py`],
          { stdin: JSON.stringify({ tool: spec.name, input }), timeoutMs: TIMEOUT_MS },
        );
        return { result: envelopeFrom(spec.name, run) as never };
      } catch (err) {
        return { result: failure(spec.name, "BridgeFailed", String(err)) as never };
      }
    }).catch(($, e, next) =>
      next.called ? next(e) : { deny: `bitranox: the ${spec.name} tool failed before it ran.` },
    );
  }
};
