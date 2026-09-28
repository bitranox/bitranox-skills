"""Blind judge packets for the skill router, and the harvest of what the judges answered.

Whether a router pick was RIGHT is the one thing no log records, so it is settled by a panel:
several judges label every candidate a set of prompts drew, blind to which arm or site named it.
This module builds that panel's input and reads its output back:

  pool     every candidate any named log proposed for a prompt, keyed by the prompt's uuid, so
           the same prompt replayed by several runs (or live and replayed) is judged ONCE
  sample   a per-session cap and a total, drawn with a seed so the draw can be pre-registered
  build_packet
           one packet per judge, each in its own item order; the packet names candidates and
           their descriptions and nothing else - no arm, no log, no score, no uuid. A skill whose
           description is the variable under test takes a neutral override text, since showing
           either wording biases the verdict toward it
  extract_panel / harvest
           each judge's verdict object from its transcript, then the per-verdict majority, with
           every split listed and labels keyed by the prompt's uuid

The labels are keyed by uuid rather than by position or by prompt text, because both of those
were tried and failed: a position shifts when one item is dropped, and one prompt ("go ahead")
is typed many times, so keying by its text collapsed distinct rows into one label.

Standard library only; `classifier_eval.py packet` and `harvest` are the CLI.
"""
from __future__ import annotations

import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent.parent.parent / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

import classifier as cl  # noqa: E402 - the sys.path above is what makes this importable

VERDICTS = ("right", "defensible", "wrong")
NO_DESCRIPTION = "(no description recorded)"
# Per-field caps for what a judge reads. The prompt keeps head and tail, because a long prompt
# states its ask at either end; the context fields only need to say what the session was doing.
FIELD_CAPS = {"user_prompt": 2400, "previous_assistant_message": 600, "project": 300,
              "recent_activity": 400, "skills_already_used": 400}
MATCH_TAIL = 80

DEFAULT_INSTRUCTIONS = """\
You are labelling data for a skill router. Answer from the text in this file ONLY. Do not invoke any
skill and do not read any other file; everything you need is here, and a skill's own text would bias
the label.

Each item is one real message a developer typed to a coding assistant (Claude Code), with the
context the router had: `user_prompt` is the message (long ones are cut in the middle),
`previous_assistant_message` is what the assistant had just said, `project` is the repo,
`recent_activity` is the last tool calls, `skills_already_used` lists skills already loaded this
session. Some messages are automated notices (task notifications, hook output) rather than typed
text; judge them the same way.

Each item lists CANDIDATE SKILLS; their descriptions are in the CANDIDATE DESCRIPTIONS section. A
skill is a packaged set of instructions the assistant would load before answering. Judge each
candidate:

- "right": loading this skill is what the assistant should do for this message.
- "defensible": not the best choice, but loading it would help rather than mislead.
- "wrong": irrelevant, or it would steer the answer the wrong way. A skill already listed in
  skills_already_used and still relevant is at most "defensible" (reloading it adds little).

Also judge `needs_skill`: true if the assistant should load at least one skill (listed or not) for
this message, false if it should just carry on without one (a plain continuation, an approval, a
status question it can answer directly).

When needs_skill is true and no candidate is "right", set `better` to the one skill name from the
ALL SKILL NAMES list that would be right, or null if none would. Otherwise set `better` to null.

Return ONE JSON object and nothing else after it, keyed by item id, covering EVERY item:

{"i000": {"needs_skill": true, "verdicts": {"<candidate>": "right|defensible|wrong", ...}, "better": null}, ...}

Every candidate listed under an item must appear in its verdicts, spelled exactly as listed. An item
with no candidates still gets needs_skill and better.
"""


# ---- pooling -------------------------------------------------------------------------------

def _is_skill(name):
    return isinstance(name, str) and bool(name) and name != cl.NO_SKILL_KEY


def _runners_up(probs, winner, alternatives):
    """The `alternatives` most probable skills of a choice answer after its winner, no-match
    option excluded - the picks a lower gate or a different arm would have surfaced next."""
    ranked = sorted(((-p, n) for n, p in (probs or {}).items()
                     if _is_skill(n) and n != winner and isinstance(p, (int, float))))
    return [n for _p, n in ranked[:alternatives]]


def _choice_candidates(tag, winner, probs, alternatives):
    out = [(winner, tag + ":winner")] if _is_skill(winner) else []
    return out + [(n, tag + ":alt") for n in _runners_up(probs, winner, alternatives)]


def _replay_candidates(log, row, alternatives):
    """[(skill, origin)] from every arm of one replay row, plus the keyword matcher's picks."""
    out = [(k, log + ":keywords") for k in row.get("keyword_picks") or []]
    for name, arm in (row.get("arms") or {}).items():
        tag = "%s:%s" % (log, name)
        out += _choice_candidates(tag, arm.get("winner"), arm.get("probabilities"), alternatives)
        out += [(p, tag + ":pick") for p in arm.get("picks") or []]
        if _is_skill(arm.get("rerank_winner")):
            out.append((arm["rerank_winner"], tag + ":rerank"))
    return out


def _live_answers(row):
    results = row.get("results") or []
    return (results[0].get("answers") or {}) if results and isinstance(results[0], dict) else {}


def _live_choice(row):
    """(winner, probabilities, gate) of a live router row, from whichever answer shape it logged."""
    answers = _live_answers(row)
    pick, gate = answers.get(cl.PICK_ID), answers.get(cl.NEW_TASK_ID)
    if isinstance(pick, dict):
        probs = pick.get("probabilities")
        winner, probs = pick.get("value"), probs if isinstance(probs, dict) else {}
    else:
        winner, probs = pick, {}
    return winner, probs, gate.get("value") if isinstance(gate, dict) else gate


def _live_candidates(log, row, alternatives):
    winner, probs, _gate = _live_choice(row)
    out = [(k, log + ":keywords") for k in (row.get("regex") or {}).get("selected") or []]
    return out + _choice_candidates(log + ":jev", winner, probs, alternatives)


def _replay_origins(log, row):
    out = []
    for name, arm in (row.get("arms") or {}).items():
        winner, probs = arm.get("winner"), arm.get("probabilities") or {}
        out.append({"log": log, "arm": name, "gate": arm.get("gate"), "winner": winner,
                    "winner_p": probs.get(winner), "picks": list(arm.get("picks") or [])})
    return out


def _live_origin(log, row):
    winner, probs, gate = _live_choice(row)
    return {"log": log, "site": row.get("site"), "ts": row.get("ts"),
            "session_id": row.get("session_id"), "gate": gate, "winner": winner,
            "winner_p": probs.get(winner), "decide_path": row.get("decide_path"),
            "keywords": list((row.get("regex") or {}).get("selected") or [])}


def _prompt_tail(text):
    """The part of a prompt two rows are compared on. A live row caps a long prompt head-and-tail
    while a replay row may carry it whole, so only the tail is comparable across the two."""
    return (text or "").split(cl.CAP_MARK)[-1].strip()[-MATCH_TAIL:]


def _row_parts(log, row, alternatives, locate):
    """(uuid, state, session, transcript, candidates, origins), or (None, reason) to skip."""
    if "arms" in row:
        uuid = row.get("uuid")
        if not uuid:
            return None, "replay row carries no uuid"
        return uuid, (row.get("state") or {}, row.get("session_id") or row.get("source"),
                      row.get("source"), _replay_candidates(log, row, alternatives),
                      _replay_origins(log, row))
    if not row.get("results"):
        return None, "unanswered skill_router row"
    uuid = locate(row) if locate else None
    if not uuid:
        return None, "cannot locate its prompt in its transcript"
    states = row.get("states") or [{}]
    return uuid, (states[0], row.get("session_id"), row.get("transcript_path"),
                  _live_candidates(log, row, alternatives), [_live_origin(log, row)])


def _merge(item, uuid, parts):
    state, _session, _transcript, cands, origins = parts
    if _prompt_tail(state.get("user_prompt")) != _prompt_tail(item["state"].get("user_prompt")):
        raise ValueError("uuid %s carries two different prompts across the named logs" % uuid)
    for name, origin in cands:
        item["candidates"].setdefault(name, set()).add(origin)
    item["origins"] += origins


def pool(logs, *, alternatives, locate=None, always=()):
    """({uuid: item}, skipped) over every row of every named log, in first-seen order.

    `logs` is [(log name, rows)]. A replay row is keyed by its recorded uuid; a live shadow row by
    `locate(row)`, the prompt uuid its transcript holds. A row that cannot be keyed is skipped and
    reported rather than judged on a guessed identity. Raises ValueError when one uuid carries two
    different prompts, which means the logs are not about the same prompts at all.
    """
    items, skipped = {}, []
    for log, rows in logs:
        for index, row in enumerate(rows):
            if "arms" not in row and row.get("site") != "skill_router":
                continue    # another site's row: never a candidate, so not a skip either
            uuid, parts = _row_parts(log, row, alternatives, locate)
            if uuid is None:
                skipped.append({"log": log, "index": index, "reason": parts})
                continue
            item = items.get(uuid)
            if item is None:
                item = items[uuid] = {"uuid": uuid, "state": parts[0], "session_id": parts[1],
                                      "transcript": parts[2], "candidates": {}, "origins": []}
            _merge(item, uuid, parts)
    for item in items.values():
        for name in always:
            item["candidates"].setdefault(name, set()).add("always")
        item["candidates"] = {k: sorted(v) for k, v in sorted(item["candidates"].items())}
    return items, skipped


def sample(pooled, *, per_session=None, limit=None, seed=0):
    """At most `per_session` items per session and `limit` in all, drawn with `seed`, kept in
    their pooled order. The cap exists because one long session otherwise dominates a sample and
    the panel ends up judging that session's habits rather than the router."""
    rng = random.Random(seed)
    by_session = {}
    for uuid, item in pooled.items():
        by_session.setdefault(str(item.get("session_id")), []).append(uuid)
    kept = []
    for session in sorted(by_session):
        group = by_session[session]
        kept += rng.sample(group, min(per_session, len(group))) if per_session else group
    if limit is not None and len(kept) > limit:
        kept = rng.sample(kept, limit)
    chosen = set(kept)
    return {u: it for u, it in pooled.items() if u in chosen}


# ---- the packet ----------------------------------------------------------------------------

def _clip(text, cap):
    text = " ".join(str(text or "").split()) if cap < 1000 else str(text or "")
    if len(text) <= cap:
        return text
    half = cap // 2
    return text[:half] + "\n[... %d chars cut ...]\n" % (len(text) - cap) + text[-half:]


def _describe(name, descriptions, overrides):
    bare = name.rsplit(":", 1)[-1]
    if bare in overrides:
        return overrides[bare]
    text = descriptions.get(name) or descriptions.get(bare) or next(
        (d for k, d in descriptions.items() if k.endswith(":" + bare) and d), None)
    return " ".join(text.split()) if text else NO_DESCRIPTION


def build_packet(pooled, *, descriptions, all_names, overrides=None, judges=5, seed=0,
                 instructions=DEFAULT_INSTRUCTIONS):
    """{"items", "key", "packets"} for `judges` blind judges.

    Item ids are assigned in a seeded shuffle, so an id says nothing about which log or position a
    prompt came from, and each packet lists the items in its own order so no judge's fatigue lands
    on the same items as another's. The key maps each id back to its uuid and origins; it is the
    only file that names an arm, and it never goes to a judge.
    """
    overrides = overrides or {}
    order = list(pooled)
    random.Random(seed).shuffle(order)
    items, key, glossary = {}, {}, {}
    for n, uuid in enumerate(order):
        item, iid = pooled[uuid], "i%03d" % n
        fields = {f: _clip(item["state"].get(f), cap) for f, cap in FIELD_CAPS.items()
                  if item["state"].get(f)}
        items[iid] = {**fields, "candidates": sorted(item["candidates"])}
        key[iid] = {"uuid": uuid, "session_id": item.get("session_id"),
                    "transcript": item.get("transcript"), "candidates": item["candidates"],
                    "origins": item["origins"]}
        for name in item["candidates"]:
            glossary[name] = _describe(name, descriptions, overrides)
    head = [instructions.rstrip("\n"), "", "ALL SKILL NAMES INSTALLED (for `better`):",
            ", ".join(sorted(all_names)), "", "CANDIDATE DESCRIPTIONS:"]
    head += ["- %s: %s" % (name, glossary[name]) for name in sorted(glossary)]
    head += ["", "ITEMS:"]
    packets = []
    for j in range(judges):
        ids = list(items)
        random.Random(seed * 1000 + 100 + j).shuffle(ids)
        body = []
        for iid in ids:
            body += ["", "=== %s ===" % iid, json.dumps(items[iid], ensure_ascii=False, indent=1)]
        packets.append("\n".join(head + body) + "\n")
    return {"items": items, "key": key, "packets": packets}


# ---- harvest -------------------------------------------------------------------------------

_OBJECT_START = re.compile(r'\{\s*"')


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from _strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _strings(value)


def _verdict_objects(text, item_ids):
    """Every JSON object in `text` whose keys are all item ids, in order."""
    decoder, pos = json.JSONDecoder(), 0
    while True:
        match = _OBJECT_START.search(text, pos)
        if not match:
            return
        try:
            obj, end = decoder.raw_decode(text, match.start())
        except ValueError:
            pos = match.start() + 1
            continue
        if isinstance(obj, dict) and obj and set(obj) <= item_ids:
            yield obj
            pos = end
        else:
            pos = match.start() + 1


def extract_panel(path, item_ids):
    """The last verdict object an ASSISTANT record of this transcript wrote, else None.

    Read from the transcript, never from the message a judge delivered, because the delivery can
    be reworded or arrive twice; and from assistant records only, because the packet itself sits
    in the judge's first user record and carries ids too.
    """
    item_ids, found = set(item_ids), None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict) or record.get("type") != "assistant":
                continue
            for text in _strings((record.get("message") or {}).get("content")):
                for obj in _verdict_objects(text, item_ids):
                    found = obj
    return found


def _majority(votes):
    """(label, unresolved): the unique most common vote, or None when the top is tied."""
    top = votes.most_common(2)
    if not top:
        return None, False
    if len(top) == 2 and top[0][1] == top[1][1]:
        return None, True
    return top[0][0], False


def _collect(key, panels):
    """({item: {"needs": Counter, cand: Counter, "better": Counter, "judges": n}}, unjudged,
    invalid) - every vote cast, with each vote that could not be counted reported instead."""
    tallies, unjudged, invalid = {}, [], []
    for iid, entry in key.items():
        tally = tallies[iid] = {"needs": Counter(), "better": Counter(), "judges": 0,
                                "cands": {c: Counter() for c in entry["candidates"]}}
        for j, panel in enumerate(panels):
            answer = panel.get(iid)
            if not isinstance(answer, dict):
                unjudged.append({"judge": j, "item": iid})
                continue
            tally["judges"] += 1
            need = answer.get("needs_skill")
            if isinstance(need, bool):
                tally["needs"][need] += 1
            else:
                invalid.append({"judge": j, "item": iid, "candidate": "needs_skill", "value": need})
            verdicts = answer.get("verdicts") if isinstance(answer.get("verdicts"), dict) else {}
            for cand, counter in tally["cands"].items():
                value = verdicts.get(cand)
                if value in VERDICTS:
                    counter[value] += 1
                else:
                    invalid.append({"judge": j, "item": iid, "candidate": cand, "value": value})
            if isinstance(answer.get("better"), str) and answer["better"]:
                tally["better"][answer["better"]] += 1
    return tallies, unjudged, invalid


def _split(uuid, iid, cand, votes, unresolved):
    return {"uuid": uuid, "item": iid, "candidate": cand, "votes": votes, "unresolved": unresolved}


def harvest(key, panels):
    """{"labels" (keyed by uuid), "splits", "unjudged", "invalid", "judges"}.

    A verdict is the unique most common vote; a tie is left None and listed as unresolved, for a
    human to adjudicate against the prompt, because breaking it by dict order would put an
    arbitrary label in the ground truth. `should_pick` is the candidates a majority called right,
    and only when the majority says a skill is needed at all.
    """
    tallies, unjudged, invalid = _collect(key, panels)
    labels, splits = {}, []
    for iid in sorted(key):
        uuid, tally = key[iid]["uuid"], tallies[iid]
        need, tied = _majority(tally["needs"])
        need_votes = {str(k).lower(): v for k, v in tally["needs"].items()}
        if len(tally["needs"]) > 1:
            splits.append(_split(uuid, iid, "needs_skill", need_votes, tied))
        verdicts, votes = {}, {"needs_skill": need_votes}
        for cand, counter in tally["cands"].items():
            verdicts[cand], tied = _majority(counter)
            votes[cand] = dict(counter)
            if len(counter) > 1:
                splits.append(_split(uuid, iid, cand, dict(counter), tied))
        better = sorted(tally["better"].items(), key=lambda kv: (-kv[1], kv[0]))
        labels[uuid] = {"item": iid, "needs_skill": need, "verdicts": verdicts,
                        "should_pick": [c for c, v in verdicts.items() if v == "right"]
                        if need is True else [],
                        "better": [list(kv) for kv in better], "votes": votes,
                        "judges": tally["judges"]}
    return {"labels": labels, "splits": splits, "unjudged": unjudged, "invalid": invalid,
            "judges": len(panels)}
