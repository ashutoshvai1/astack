#!/usr/bin/env python3
"""Bounded, read-only metrics for Codex rollout JSONL; Python 3.6+ stdlib."""

import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import re
import statistics
import sys


TOKEN_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens",
              "reasoning_output_tokens", "total_tokens")
CALL_TYPES = ("function_call", "custom_tool_call")
OUTPUT_TYPES = ("function_call_output", "custom_tool_call_output")
SKILL_PATH = re.compile(r"[^\s\"'`<>\\]+/SKILL\.md")


def plain_text(value):
    """Read only text fields, never serialized reasoning or encrypted payloads."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(plain_text(item) for item in value)
    if isinstance(value, dict):
        return plain_text(value.get("text", ""))
    return ""


def output_text(value, depth=0):
    """Unwrap known tool-result fields, with bounded decoding of exec JSON text."""
    if depth > 8:
        return ""
    if isinstance(value, dict):
        return "\n".join(output_text(value[key], depth + 1)
                         for key in ("output", "content", "text", "result", "value") if key in value)
    if isinstance(value, list):
        return "\n".join(output_text(item, depth + 1) for item in value[:64])
    if isinstance(value, str):
        decoded = []
        for line in value.splitlines()[:64]:
            if line.lstrip().startswith(("{", "[")):
                try:
                    decoded.append(output_text(json.loads(line), depth + 1))
                except ValueError:
                    pass
        return value + "\n" + "\n".join(decoded)
    return ""


def metadata(path):
    with path.open(encoding="utf-8") as handle:
        row = json.loads(handle.readline())
    if not isinstance(row, dict) or row.get("type") != "session_meta":
        raise ValueError("{}: first line is not session_meta".format(path))
    if not isinstance(row.get("payload"), dict) or not row["payload"].get("id"):
        raise ValueError("{}: session metadata has no identity".format(path))
    return row["payload"]


def find_session(session, sessions_dir):
    path = Path(session).expanduser()
    if path.is_file():
        return path.resolve()
    # Filename first. Metadata fallback reads one line per file, never bodies.
    paths = sorted(sessions_dir.rglob("*.jsonl"))
    matches = [p for p in paths if session in p.stem]
    if not matches:
        for candidate in paths:
            try:
                if metadata(candidate).get("id") == session:
                    matches.append(candidate)
            except (OSError, ValueError):
                continue
    if len(matches) != 1:
        raise ValueError("Session matched {} files; supply an exact path".format(len(matches)))
    return matches[0].resolve()


def select_paths(root, sessions_dir, children):
    if children == "none":
        return [root]
    selected = {metadata(root)["id"]: root}
    candidates = []
    for path in sorted(sessions_dir.rglob("*.jsonl")):
        try:
            candidates.append((path, metadata(path)))
        except (OSError, ValueError):
            continue
    while True:
        found = {m["id"]: p for p, m in candidates
                 if m.get("parent_thread_id") in selected and m.get("id") not in selected}
        selected.update(found)
        if children == "direct" or not found:
            break
    return list(selected.values())


def usage(raw):
    result = {key: max(0, int(raw.get(key, 0))) for key in TOKEN_KEYS}
    if "total_tokens" not in raw:
        result["total_tokens"] = result["input_tokens"] + result["output_tokens"]
    result["uncached_input_tokens"] = max(0, result["input_tokens"] - result["cached_input_tokens"])
    return result


def action(name, arguments):
    nested = re.findall(r"\btools\.([\w]+)\s*\(", arguments)
    names = [n.split("__")[-1] for n in nested] or [name.split(".")[-1].split("__")[-1]]
    if set(names) <= {"sleep"}:
        category = "sleep"
    elif set(names) <= {"curr_time", "get_goal"}:
        category = "clock_goal_only"
    elif set(names) <= {"write_stdin", "wait"}:
        category = "process_poll"
    elif re.search(r"\bsqueue\b|\bsacct\b|\btail\s+-|\bheartbeat\b", arguments):
        category = "status_or_logs_mixed"
    elif re.search(r"\bpytest\b|check_(?:experiment|artifact|devlog)|diff --check", arguments):
        category = "validation_mixed"
    else:
        category = "other_tool"
    return category, nested


def analyze(path):
    meta = metadata(path)
    identity = meta["id"]
    inherited = bool(meta.get("forked_from_id") or meta.get("history_base"))
    boundary = meta.get("forked_from_ordinal_exclusive")
    records, pending, calls = {}, [], {}
    tools, nested_tools, categories = Counter(), Counter(), Counter()
    outputs, compactions, instruction_refs, skill_reads = [], [], [], []
    fallback, previous = Counter(), None
    fallback_samples, resets, malformed, foreign = 0, 0, 0, 0
    baseline_omitted = False

    def owned(record, require_owner=False):
        owner = record.get("thread_id")
        if owner:
            return owner == identity
        # A child's session_id can name the root: it cannot prove child ownership.
        owner = record.get("session_id")
        return owner == identity if owner else not require_owner

    def add_record(record, line, category, call_lines):
        nonlocal foreign
        if not owned(record):
            foreign += 1
            return
        response_id = record.get("response_id")
        if not response_id or not isinstance(record.get("usage"), dict):
            return
        if response_id not in records:
            records[response_id] = {"response_id": response_id, "line": line,
                                    "usage": usage(record["usage"]),
                                    "category": category, "call_lines": call_lines}
        elif category == "compaction":
            records[response_id]["category"] = "compaction"

    with path.open(encoding="utf-8") as handle:
        for line, raw in enumerate(handle, 1):
            try:
                row = json.loads(raw)
            except ValueError:
                malformed += 1
                continue
            if not isinstance(row, dict):
                malformed += 1
                continue
            kind, payload = row.get("type"), row.get("payload", {})
            if not isinstance(payload, dict):
                continue
            ordinal = row.get("ordinal")
            if kind != "session_meta" and ((boundary is not None and ordinal is not None and ordinal < boundary)
                    or (row.get("timestamp", "~") < meta.get("timestamp", ""))):
                continue
            subtype = payload.get("type")
            if kind in ("session_meta", "turn_context"):
                for key in ("base_instructions", "developer_instructions", "user_instructions"):
                    content = plain_text(payload.get(key))
                    if content:
                        instruction_refs.append({"line": line, "field": key, "chars": len(content),
                                                 "skill_paths": sorted(set(SKILL_PATH.findall(content)))})
            if kind == "response_item" and subtype in CALL_TYPES:
                name = payload.get("name", "unknown")
                arguments = plain_text(payload.get("arguments", payload.get("input", "")))
                category, nested = action(name, arguments)
                tools[name] += 1
                nested_tools.update(nested)
                categories[category] += 1
                paths = sorted(set(SKILL_PATH.findall(arguments)))
                read_attempt = bool(paths and re.search(r"\b(cat|sed|head|tail|open|read_text)\b|skills\.read", arguments))
                call = {"line": line, "category": category, "skill_paths": paths if read_attempt else []}
                calls[payload.get("call_id", str(line))] = call
                pending.append(call)
                if read_attempt:
                    skill_reads.append({"line": line, "skill_paths": paths, "visible_skill_output": False})
            elif kind == "response_item" and subtype in OUTPUT_TYPES:
                content = plain_text(payload.get("output"))
                call = calls.get(payload.get("call_id"), {})
                truncated = bool(re.search(r"truncated output|tokens truncated|output truncated", content, re.I))
                outputs.append({"line": line, "call_line": call.get("line"), "chars": len(content), "truncated": truncated})
                skill_content = output_text(payload.get("output")) if call.get("skill_paths") else ""
                if re.search(r"(?m)^name:\s*\S+", skill_content) and "description:" in skill_content:
                    for read in reversed(skill_reads):
                        if read["line"] == call["line"]:
                            read["visible_skill_output"] = True
                            read["output_line"] = line
                            break
            elif kind == "response_item" and subtype == "message" and payload.get("role") in ("developer", "user"):
                content = plain_text(payload.get("content"))
                paths = sorted(set(SKILL_PATH.findall(content)))
                if paths:
                    instruction_refs.append({"line": line, "field": payload["role"] + "_message",
                                             "chars": len(content), "skill_paths": paths})
            elif kind == "token_usage_record":
                kinds = set(call["category"] for call in pending)
                category = next(iter(kinds)) if len(kinds) == 1 else ("mixed_tools" if kinds else "text_or_other")
                add_record(payload, line, category, [call["line"] for call in pending])
                pending = []
            elif kind == "compacted":
                record = payload.get("latest_token_usage_record") or {}
                response_id = payload.get("compaction_response_id")
                # The latest usage snapshot can belong to an ancestor or another response.
                matched = bool(response_id and record.get("response_id") == response_id and owned(record, require_owner=True))
                compactions.append({"line": line, "response_id": response_id,
                                    "owned_usage": matched, "summary_chars": len(payload.get("message", ""))})
                if matched:
                    add_record(record, line, "compaction", [])
            elif kind == "event_msg" and subtype == "token_count":
                info = payload.get("info") or {}
                total = info.get("total_token_usage")
                if not isinstance(total, dict):
                    continue
                current = usage(total)
                if previous is None:
                    # A matching last sample in an unforked file suggests a zero baseline.
                    if not inherited and info.get("last_token_usage") and usage(info["last_token_usage"]) == current:
                        fallback.update(current)
                        fallback_samples += 1
                    else:
                        baseline_omitted = True
                elif any(current[key] < previous[key] for key in TOKEN_KEYS):
                    resets += 1
                elif current["total_tokens"] > previous["total_tokens"]:
                    fallback.update({key: current[key] - previous[key] for key in current})
                    fallback_samples += 1
                previous = current

    totals, grouped = Counter(), defaultdict(Counter)
    for record in records.values():
        totals.update(record["usage"])
        grouped[record["category"]].update(record["usage"])
        grouped[record["category"]]["responses"] += 1
    inputs = [r["usage"]["input_tokens"] for r in records.values()]
    notes = ["Action-attributed tokens describe emitted actions, not proven waste or billing."]
    if inherited:
        notes.append("Forked context: inherited skills may need bounded manual inspection; ancestor totals are excluded.")
    if not records:
        totals = fallback
        notes.append("FALLBACK: monotonic token_count deltas; first baseline and reset intervals may be missing. No response-level attribution.")
    if baseline_omitted and not records:
        notes.append("Initial cumulative counter omitted: inherited baseline is uncertain; totals are observed deltas only.")
    if malformed:
        notes.append("{} malformed JSON lines skipped; evidence may be incomplete.".format(malformed))
    return {"session_id": identity, "path": str(path), "parent_thread_id": meta.get("parent_thread_id"),
            "forked_from_id": meta.get("forked_from_id"), "method": "unique_response_usage" if records else "token_count_fallback",
            "usage": dict(totals), "responses": len(records), "foreign_usage_records_ignored": foreign,
            "tool_calls": dict(tools), "nested_tool_references": dict(nested_tools), "call_categories": dict(categories),
            "action_attributed_usage": dict(grouped), "compactions": compactions,
            "input_context_tokens": {"first": inputs[0], "median": statistics.median(inputs), "max": max(inputs)} if inputs else {},
            "tool_output_chars": sum(o["chars"] for o in outputs),
            "truncated_outputs": sum(o["truncated"] for o in outputs),
            "largest_outputs": sorted(outputs, key=lambda o: o["chars"], reverse=True)[:5],
            "instruction_references": instruction_refs, "skill_read_attempts": skill_reads,
            "fallback": {"samples": fallback_samples, "resets": resets, "initial_baseline_omitted": baseline_omitted},
            "response_usage": list(records.values()), "notes": notes}


def audit(root, sessions_dir, children="none"):
    reports = [analyze(path) for path in select_paths(root, sessions_dir, children)]
    combined, seen = Counter(), set()
    for report in reports:
        for record in report["response_usage"]:
            if record["response_id"] not in seen:
                combined.update(record["usage"])
                seen.add(record["response_id"])
    return {"scope": children, "sessions": reports, "combined_unique_response_usage": dict(combined),
            "combined_usage_excludes_fallback_sessions": any(r["method"] == "token_count_fallback" for r in reports)}


def summary(report):
    lines = ["Session audit: {} session(s); child scope={}".format(len(report["sessions"]), report["scope"])]
    for session in report["sessions"]:
        counts = session["usage"]
        lines.append("{} [{}]".format(session["session_id"], session["method"]))
        lines.append("  Tokens: input={:,} (cached={:,}, uncached={:,}); output={:,} (reasoning subset={:,}); total={:,}".format(
            *(counts.get(k, 0) for k in ("input_tokens", "cached_input_tokens", "uncached_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens"))))
        lines.append("  Responses={}; tool calls={}; output chars={:,}; truncated={}; compactions={} (owned usage={})".format(
            session["responses"], sum(session["tool_calls"].values()), session["tool_output_chars"], session["truncated_outputs"],
            len(session["compactions"]), sum(c["owned_usage"] for c in session["compactions"])))
        lines.append("  Input context tokens: {}; skill read attempts={} (visible skill output={}); instruction references={}".format(
            session["input_context_tokens"], len(session["skill_read_attempts"]),
            sum(r["visible_skill_output"] for r in session["skill_read_attempts"]), len(session["instruction_references"])))
        lines.append("  Action-attributed categories (heuristic):")
        ranked = sorted(session["action_attributed_usage"].items(), key=lambda item: item[1]["total_tokens"], reverse=True)
        top = [item for index, item in enumerate(ranked)
               if index < 5 or item[0] in ("sleep", "clock_goal_only", "process_poll")]
        for name, values in top:
            refs = [r["line"] for r in session["response_usage"] if r["category"] == name][:3]
            lines.append("    {}: {} responses; {:,} tokens; usage lines {}".format(name, values["responses"], values["total_tokens"], refs))
        lines.append("  Wait/poll call categories: " + ", ".join("{}={}".format(k, session["call_categories"].get(k, 0)) for k in ("sleep", "clock_goal_only", "process_poll", "status_or_logs_mixed")))
        lines.append("  Largest output lines: {}; skill read lines: {}; source: {}".format(
            [o["line"] for o in session["largest_outputs"]], [r["line"] for r in session["skill_read_attempts"][:5]], session["path"]))
        lines.extend("  " + note for note in session["notes"])
    if len(report["sessions"]) > 1:
        lines.append("Combined unique response total={:,}; fallback sessions excluded={}".format(
            report["combined_unique_response_usage"].get("total_tokens", 0), report["combined_usage_excludes_fallback_sessions"]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True, help="Session ID (unique filename prefix accepted) or JSONL path")
    parser.add_argument("--sessions-dir", type=Path, default=Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "sessions")
    parser.add_argument("--include-children", choices=("direct", "recursive"), default="none")
    parser.add_argument("--output", type=Path, help="Explicit destination for metrics JSON; contains no transcript text")
    args = parser.parse_args(argv)
    try:
        root = find_session(args.session, args.sessions_dir.expanduser())
        report = audit(root, args.sessions_dir.expanduser(), args.include_children)
        if args.output:
            if args.output.expanduser().resolve() in {Path(r["path"]).resolve() for r in report["sessions"]}:
                raise ValueError("Output must not overwrite an input session")
            with args.output.expanduser().open("w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2)
                handle.write("\n")
        print(summary(report))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, "audit_session: {}\n".format(error))


if __name__ == "__main__":
    main()
