"""Probe for backlog [55]: which .claude/rules files reach the model, and when.

Builds a scratch tree (non-git ancestor T, git repo T/proj = cwd, nested git repo T/proj/nested),
puts a unique token in each CLAUDE.md and rules file, runs headless `claude -p` through
capture_proxy.py, and reports which tokens appear in each captured request body. Evidence is the
request body only, never the model's answer.

Usage: python3 run_probe.py [<workdir>]   (default: a fresh dir under ~/.cache)
Env: PROBE_ONLY=<scenario> runs one scenario; PROBE_ARGS replaces "--setting-sources project,local".

Two traps the first run hit, both of which make every token read as absent:
- a tree under Claude Code's own temp dir (/tmp/claude-<uid>/...) loads no CLAUDE.md and no rules
  at all, so the script refuses one;
- the parent session's CLAUDE* variables reach the child, so they are stripped.
TOKEN_PROJ_CLAUDEMD in the first request is the liveness control: without it, nothing else counts.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

FILES = {
    "CLAUDE.md": "Probe marker TOKEN_ANC_CLAUDEMD.\n",
    ".claude/rules/anc-always.md": "Probe marker TOKEN_ANC_ALWAYS.\n",
    ".claude/rules/anc-py.md": '---\npaths:\n  - "**/*.py"\n---\nProbe marker TOKEN_ANC_PY.\n',
    "proj/CLAUDE.md": "Probe marker TOKEN_PROJ_CLAUDEMD.\n",
    "proj/.claude/rules/proj-always.md": "Probe marker TOKEN_PROJ_ALWAYS.\n",
    "proj/.claude/rules/proj-py.md": '---\npaths:\n  - "**/*.py"\n---\nProbe marker TOKEN_PROJ_PY.\n',
    "proj/src/a.py": "x = 1\n",
    "proj/src/c.py": "z = 3\n",
    "proj/nested/.claude/rules/nested-always.md": "Probe marker TOKEN_NESTED_ALWAYS.\n",
    "proj/nested/.claude/rules/nested-py.md": '---\npaths:\n  - "**/*.py"\n---\nProbe marker TOKEN_NESTED_PY.\n',
    "proj/nested/CLAUDE.md": "Probe marker TOKEN_NESTED_CLAUDEMD.\n",
    "proj/nested/b.py": "y = 2\n",
}
TOKENS = sorted({line.split()[-1].rstrip(".") for text in FILES.values() for line in text.splitlines() if "TOKEN_" in line})

SCENARIOS = {
    "S0_no_read": "Reply with the single word OK and nothing else. Do not use any tool.",
    "S1_read_proj_py": "Call the Read tool on src/a.py, then reply with the exact first line of that file and nothing else.",
    "S3_bash_cat_py": "Run the Bash command `cat src/a.py` (do not use the Read tool), then reply with its output and nothing else.",
    "S4_grep_py": "Use the Grep tool (not Read, not Bash) to search for the pattern \"x =\" in the src directory with output mode content, then reply with the matching line and nothing else.",
    "S5_three_reads_py": "Call the Read tool on src/a.py, then on src/c.py, then on src/a.py again (three separate Read calls), then reply with the first line of each read, one per line.",
    "S2_read_nested_py": "Call the Read tool on nested/b.py, then reply with the exact first line of that file and nothing else.",
}

# A chain is one session across several claude -p calls (--resume); C1 asks whether a paths: rule
# loaded before a /compact is still in the request after it.
CHAINS = {
    "C1_compact": [
        "Call the Read tool on src/a.py, then reply with the exact first line of that file and nothing else.",
        "/compact",
        "Reply with the single word OK and nothing else. Do not use any tool.",
    ],
    # C2: one read per resumed turn, so re-send is measured across turns (a single turn batches
    # the reads), then whether the rule comes back on the first matching read after a /compact.
    "C2_resend_then_compact": [
        "Call the Read tool on src/a.py, then reply with the exact first line of that file and nothing else.",
        "Call the Read tool on src/c.py, then reply with the exact first line of that file and nothing else.",
        "Call the Read tool on src/a.py again, then reply with the exact first line of that file and nothing else.",
        "/compact",
        "Call the Read tool on src/c.py, then reply with the exact first line of that file and nothing else.",
    ],
}


def build(tree: Path) -> None:
    for rel, text in FILES.items():
        p = tree / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    for repo in (tree / "proj", tree / "proj" / "nested"):
        subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run(name: str, prompt: str, tree: Path, out: Path, resume: str | None = None) -> dict[str, object]:
    cap = out / name
    port = free_port()
    proxy = subprocess.Popen([sys.executable, str(HERE / "capture_proxy.py"), str(port), str(cap)])
    time.sleep(1.0)
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
    env["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{port}"
    try:
        res = subprocess.run(
            ["claude", "-p", "--model", "haiku", *os.environ.get("PROBE_ARGS", "--setting-sources project,local").split(),
             *(["--resume", resume] if resume else []),
             "--allowedTools", "Read", "Bash(cat:*)", "Grep", "--output-format", "json", prompt],
            cwd=tree / "proj", env=env, capture_output=True, text=True, timeout=300,
        )
    finally:
        proxy.terminate()
        proxy.wait()
    try:
        doc_out = json.loads(res.stdout)
        answer, session = doc_out.get("result"), doc_out.get("session_id")
    except json.JSONDecodeError:
        answer, session = f"rc={res.returncode} stdout={res.stdout[:200]!r} stderr={res.stderr[:300]!r}", None
    requests = []
    for body in sorted(cap.glob("*.json")):
        text = body.read_text(encoding="utf-8", errors="replace")
        try:
            doc = json.loads(text)
            kind = f"model={doc.get('model')} tools={len(doc.get('tools') or [])} msgs={len(doc.get('messages') or [])}"
        except json.JSONDecodeError:
            kind = "non-json"
        requests.append({"req": body.stem, "path": (cap / f"{body.stem}.path").read_text(), "kind": kind,
                         "tokens": {t: text.count(t) for t in TOKENS if t in text},
                         "rule_attachments": text.count("rules/proj-py.md")})
    return {"scenario": name, "answer": answer, "session": session, "requests": requests}


def run_chain(name: str, prompts: list[str], tree: Path, out: Path) -> list[dict[str, object]]:
    """Run prompts as ONE session: the first starts it, each later one resumes it."""
    steps, session = [], None
    for i, prompt in enumerate(prompts):
        step = run(f"{name}_step{i}", prompt, tree, out, resume=session)
        session = step["session"] or session
        steps.append(step)
    return steps


def main() -> None:
    if len(sys.argv) > 1:
        work = Path(sys.argv[1]).resolve()
    else:
        (Path.home() / ".cache").mkdir(exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix="rules-probe-", dir=Path.home() / ".cache"))
    if str(work).startswith(f"/tmp/claude-{os.getuid()}"):
        sys.exit(f"refused: {work} is under Claude Code's temp dir, where no CLAUDE.md or rule loads")
    print(f"workdir {work}")
    tree, out = work / "T", work / "captures"
    build(tree)
    only = os.environ.get("PROBE_ONLY")
    report = [run(n, p, tree, out) for n, p in SCENARIOS.items() if not only or n == only]
    for n, prompts in CHAINS.items():
        if not only or n == only:
            report.extend(run_chain(n, prompts, tree, out))
    (work / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for r in report:
        print(f"== {r['scenario']}: answer={r['answer']!r}")
        for q in r["requests"]:
            print(f"   {q['req']} {q['path']} {q['kind']} proj-py attachments={q['rule_attachments']}\n      {q['tokens']}")


if __name__ == "__main__":
    main()
