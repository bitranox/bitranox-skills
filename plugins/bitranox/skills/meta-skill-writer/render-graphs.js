#!/usr/bin/env node

/**
 * Render graphviz diagrams from a skill's SKILL.md to SVG files.
 *
 * Usage:
 *   ./render-graphs.js <skill-directory>           # Render each diagram separately
 *   ./render-graphs.js <skill-directory> --combine # Combine all into one diagram
 *
 * Extracts all ```dot blocks from SKILL.md and renders them to SVG in <skill-directory>/diagrams/.
 * Useful for helping your human partner visualize the process flows.
 *
 * Exit status: 0 when every diagram rendered (or the file holds no ```dot block), 1 when any
 * diagram failed, graphviz is missing, or the arguments are wrong. The last line of a run reads
 * "N rendered, M failed".
 *
 * --combine merges only `digraph` blocks, and refuses (renders nothing) when two blocks share a
 * node id, because graphviz would silently fuse them into one node across the clusters. The
 * merged graph is `strict` when every block is; a mix of strict and plain blocks is refused too.
 *
 * Requires: graphviz (dot) on PATH. Runs `dot` directly, never through a shell, so it behaves the
 * same from cmd.exe, PowerShell, Git Bash and any POSIX shell.
 */

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

// A DOT ID: a quoted string, a name, or a numeral (graphviz's own lexical rules).
const DOT_ID = String.raw`"(?:[^"\\]|\\.)*"|[A-Za-z_\x80-\uffff][\w\x80-\uffff]*|-?(?:\.\d+|\d+(?:\.\d*)?)`;
// The graph header at the start of a line; DOT keywords are case-insensitive and the name optional.
const HEADER = new RegExp(
  String.raw`(?:^|\n)[ \t]*(strict\s+)?(digraph|graph)\s*(` + DOT_ID + String.raw`)?\s*\{`, 'i');
const PLAIN_NODE = new RegExp(String.raw`^node (` + DOT_ID + String.raw`|\S+) `, 'gm');
const MAX_BUFFER = 64 * 1024 * 1024;

function unquote(id) {
  return id.startsWith('"') ? id.slice(1, -1).replace(/\\"/g, '"') : id;
}

function quoteId(text) {
  return `"${text.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
}

function fileStem(name) {
  return name.replace(/[^A-Za-z0-9_]/g, '_') || 'graph';
}

// Where a construct that may hold a brace ends: a quoted string (backslash escapes), an HTML
// string (nested < >), a // or /* */ comment, or a # line (C preprocessor output, column 0).
// Each returns the index just past it, or the text's length when it never ends.
function skipQuoted(text, i) {
  for (let j = i + 1; j < text.length; j += 1) {
    if (text[j] === '\\') j += 1;
    else if (text[j] === '"') return j + 1;
  }
  return text.length;
}

function skipHtml(text, i) {
  let depth = 0;
  for (let j = i; j < text.length; j += 1) {
    if (text[j] === '<') depth += 1;
    else if (text[j] === '>' && --depth === 0) return j + 1;
  }
  return text.length;
}

function skipToLineEnd(text, i) {
  const end = text.indexOf('\n', i);
  return end < 0 ? text.length : end;
}

function skipBlockComment(text, i) {
  const end = text.indexOf('*/', i + 2);
  return end < 0 ? text.length : end + 2;
}

function skipNonCode(text, i) {
  const ch = text[i];
  if (ch === '"') return skipQuoted(text, i);
  if (ch === '<') return skipHtml(text, i);
  if (text.startsWith('//', i)) return skipToLineEnd(text, i);
  if (text.startsWith('/*', i)) return skipBlockComment(text, i);
  if (ch === '#' && (i === 0 || text[i - 1] === '\n')) return skipToLineEnd(text, i);
  return i;
}

// The index of the `}` that closes the brace opened just before `start`, or -1. Taking the LAST
// `}` in the block instead read a trailing comment holding one into the body, which broke the
// combined render.
function closingBrace(text, start) {
  let depth = 1;
  let i = start;
  while (i < text.length) {
    const next = skipNonCode(text, i);
    if (next !== i) {
      i = next;
      continue;
    }
    if (text[i] === '{') depth += 1;
    else if (text[i] === '}' && --depth === 0) return i;
    i += 1;
  }
  return -1;
}

function parseBlock(content, index) {
  const fallback = `graph_${index + 1}`;
  const header = HEADER.exec(content);
  if (!header) return { index, content, name: fallback, kind: null, strict: false, body: '' };
  const bodyStart = header.index + header[0].length;
  const bodyEnd = closingBrace(content, bodyStart);
  return {
    index,
    content,
    name: header[3] ? unquote(header[3]) : fallback,
    kind: header[2].toLowerCase(),
    strict: Boolean(header[1]),
    body: bodyEnd > bodyStart ? content.slice(bodyStart, bodyEnd).trim() : '',
  };
}

function extractDotBlocks(markdown) {
  const regex = /```dot[ \t]*\n([\s\S]*?)```/g;
  const blocks = [];
  let match;
  while ((match = regex.exec(markdown)) !== null) {
    blocks.push(parseBlock(match[1].trim(), blocks.length));
  }
  return blocks;
}

// Two blocks with one name would write one file twice; the later block gets the first free
// "<stem>_N" that no block claims as its own name, so no diagram is ever overwritten.
function assignStems(blocks) {
  const natural = new Set(blocks.map(b => fileStem(b.name)));
  const taken = new Set();
  for (const block of blocks) {
    let stem = fileStem(block.name);
    if (taken.has(stem)) {
      let n = 2;
      while (taken.has(`${stem}_${n}`) || natural.has(`${stem}_${n}`)) n += 1;
      console.error(`  Note: block ${block.index + 1} repeats the name "${block.name}"; ` +
                    `naming it ${stem}_${n} so neither diagram is overwritten`);
      stem = `${stem}_${n}`;
    }
    taken.add(stem);
    block.stem = stem;
    block.label = stem === fileStem(block.name) ? block.name : stem;
  }
}

function runDot(format, input) {
  const result = spawnSync('dot', [`-T${format}`], {
    input, encoding: 'utf-8', maxBuffer: MAX_BUFFER, stdio: ['pipe', 'pipe', 'pipe'],
  });
  if (result.error) return { ok: false, error: `could not run dot: ${result.error.message}` };
  const stderr = (result.stderr || '').trim();
  if (result.status !== 0) return { ok: false, error: stderr || `dot exited ${result.status}` };
  return { ok: true, out: result.stdout, warnings: stderr };
}

function dotAvailable() {
  const probe = spawnSync('dot', ['-V'], { stdio: ['ignore', 'pipe', 'pipe'] });
  return !probe.error && probe.status === 0;
}

function indent(text) {
  return text.split('\n').map(line => `    ${line}`).join('\n');
}

function reportFailure(what, error) {
  console.error(`  Failed: ${what}`);
  console.error(indent(error));
}

function reportWarnings(what, warnings) {
  if (warnings) console.error(`  Warning from dot for ${what}:\n${indent(warnings)}`);
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function renderSeparately(blocks, outputDir) {
  let rendered = 0;
  let failed = 0;
  for (const block of blocks) {
    const result = runDot('svg', block.content);
    if (!result.ok) {
      failed += 1;
      reportFailure(`block ${block.index + 1} (${block.label})`, result.error);
      continue;
    }
    reportWarnings(block.label, result.warnings);
    ensureDir(outputDir);
    fs.writeFileSync(path.join(outputDir, `${block.stem}.svg`), result.out);
    console.log(`  Rendered: ${block.stem}.svg`);
    rendered += 1;
  }
  return { rendered, failed };
}

// What --combine cannot merge, decided from the source alone before anything is written.
function combineProblems(blocks) {
  const problems = [];
  for (const block of blocks) {
    const where = `block ${block.index + 1} (${block.label})`;
    if (block.kind === null) {
      problems.push(`${where} has no "digraph <name> { ... }" wrapper, so there is no graph body ` +
                    'to merge. Wrap it in a digraph, or fence an illustration as text.');
    } else if (block.kind === 'graph') {
      problems.push(`${where} is an undirected graph; --combine merges only digraph blocks, ` +
                    'because its -- edges are invalid inside a digraph. Render without --combine.');
    } else if (!block.body) {
      problems.push(`${where} yielded an empty graph body, so its cluster would be empty.`);
    }
  }
  // `strict` belongs to a whole graph, never a cluster: the merged graph is strict when every
  // block is, and a mix would either draw a strict block's duplicate edges or merge a plain one's.
  const strict = blocks.filter(b => b.kind === 'digraph' && b.strict).map(b => b.label);
  if (strict.length > 0 && strict.length < blocks.length) {
    problems.push(`blocks mix strict and plain digraphs (strict: ${strict.join(', ')}); ` +
                  'one merged graph is strict or not as a whole. Render without --combine.');
  }
  return problems;
}

function combineGraphs(blocks, graphName) {
  const clusters = blocks.map((block, i) => {
    // rankdir is set once at the top level; inside a cluster it would be ignored anyway.
    const body = block.body.replace(/^\s*rankdir\s*=\s*\w+\s*;?\s*$/gim, '').trim();
    return [
      `  subgraph cluster_${i} {`,
      `    label=${quoteId(block.label)};`,
      ...body.split('\n').map(line => `    ${line}`),
      '  }',
    ].join('\n');
  });
  const strict = blocks.every(block => block.strict) ? 'strict ' : '';
  return [
    `${strict}digraph ${quoteId(`${graphName}_combined`)} {`,
    '  rankdir=TB;',
    '  compound=true;',
    '  newrank=true;',
    '',
    clusters.join('\n\n'),
    '}',
    '',
  ].join('\n');
}

// Node ids as graphviz itself resolves them ("a" and a are one node), per block.
function nodeIdsByBlock(blocks) {
  const owners = new Map();
  let failed = 0;
  for (const block of blocks) {
    const result = runDot('plain', block.content);
    if (!result.ok) {
      failed += 1;
      reportFailure(`block ${block.index + 1} (${block.label})`, result.error);
      continue;
    }
    for (const match of result.out.matchAll(PLAIN_NODE)) {
      const id = unquote(match[1]);
      if (!owners.has(id)) owners.set(id, new Set());
      owners.get(id).add(block.label);
    }
  }
  return { owners, failed };
}

function reportSharedIds(owners) {
  const shared = [...owners].filter(([, labels]) => labels.size > 1);
  if (shared.length === 0) return false;
  console.error('  Failed: --combine would fuse node ids shared between blocks into one node:');
  for (const [id, labels] of shared) console.error(`    ${id}: ${[...labels].join(', ')}`);
  console.error('  Rename them apart in SKILL.md, or render without --combine.');
  return true;
}

function renderCombined(blocks, skillDir, outputDir) {
  const failure = { rendered: 0, failed: 1 };
  const problems = combineProblems(blocks);
  if (problems.length > 0) {
    for (const problem of problems) console.error(`  Failed: ${problem}`);
    return failure;
  }

  const graphName = path.basename(skillDir);
  const stem = `${fileStem(graphName)}_combined`;
  const combined = combineGraphs(blocks, graphName);
  // Written before rendering, so the merged source is there to read when the render fails.
  ensureDir(outputDir);
  fs.writeFileSync(path.join(outputDir, `${stem}.dot`), combined);
  console.log(`  Source: ${stem}.dot`);

  const { owners, failed } = nodeIdsByBlock(blocks);
  if (failed > 0 || reportSharedIds(owners)) return failure;

  const result = runDot('svg', combined);
  if (!result.ok) {
    reportFailure(`combined diagram (source: ${stem}.dot)`, result.error);
    return failure;
  }
  reportWarnings(`${stem}.dot`, result.warnings);
  fs.writeFileSync(path.join(outputDir, `${stem}.svg`), result.out);
  console.log(`  Rendered: ${stem}.svg`);
  return { rendered: 1, failed: 0 };
}

function usage() {
  console.error('Usage: render-graphs.js <skill-directory> [--combine]');
  console.error('');
  console.error('Options:');
  console.error('  --combine    Combine all diagrams into one SVG');
  console.error('');
  console.error('Example:');
  console.error('  ./render-graphs.js ../subagent-driven-development');
  console.error('  ./render-graphs.js ../subagent-driven-development --combine');
  process.exit(1);
}

function main() {
  const args = process.argv.slice(2);
  const combine = args.includes('--combine');
  const skillDirArg = args.find(a => !a.startsWith('--'));
  if (!skillDirArg) usage();

  const skillDir = path.resolve(skillDirArg);
  const skillFile = path.join(skillDir, 'SKILL.md');
  if (!fs.existsSync(skillFile)) {
    console.error(`Error: ${skillFile} not found`);
    process.exit(1);
  }

  if (!dotAvailable()) {
    console.error('Error: graphviz (dot) not found on PATH. Install it with:');
    console.error('  brew install graphviz    # macOS');
    console.error('  apt install graphviz     # Debian/Ubuntu Linux');
    console.error('  Windows: the installer from https://graphviz.org/download/ with "add to PATH",');
    console.error('           then open a new shell so dot is found');
    process.exit(1);
  }

  // A Windows checkout with core.autocrlf=true gives SKILL.md CRLF line endings.
  const markdown = fs.readFileSync(skillFile, 'utf-8').replace(/\r\n/g, '\n');
  const blocks = extractDotBlocks(markdown);
  if (blocks.length === 0) {
    console.log('No ```dot blocks found in', skillFile);
    process.exit(0);
  }

  console.log(`Found ${blocks.length} diagram(s) in ${path.basename(skillDir)}/SKILL.md`);
  assignStems(blocks);

  const outputDir = path.join(skillDir, 'diagrams');
  const { rendered, failed } = combine
    ? renderCombined(blocks, skillDir, outputDir)
    : renderSeparately(blocks, outputDir);

  if (fs.existsSync(outputDir)) console.log(`\nOutput: ${outputDir}${path.sep}`);
  console.log(`${rendered} rendered, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}

main();
