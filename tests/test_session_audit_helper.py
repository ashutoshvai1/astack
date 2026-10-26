import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
if not SKILLS.is_dir():
    SKILLS = ROOT / "skills"
SCRIPT = SKILLS / "audit-session" / "scripts" / "audit_session.py"
SPEC = importlib.util.spec_from_file_location("audit_session", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def row(kind, payload, **extra):
    return dict(type=kind, payload=payload, **extra)


def tokens(amount, cached=0, output=10, reasoning=3):
    return dict(input_tokens=amount, cached_input_tokens=cached,
                output_tokens=output, reasoning_output_tokens=reasoning,
                total_tokens=amount + output)


def record(identity, response, amount=100, **extra):
    return dict(thread_id=identity, response_id=response,
                usage=tokens(amount, cached=amount // 2), **extra)


def rollout(directory, identity, events, **meta):
    path = directory / ("rollout-" + identity + ".jsonl")
    path.write_text("\n".join(json.dumps(r) for r in
                            [row("session_meta", dict(id=identity, **meta))] + events) + "\n",
                    encoding="utf-8")
    return path


def test_owned_dedup_cached_reasoning_and_compaction_snapshots(tmp_path):
    ordinary = record("child", "one", thread_token_usage=tokens(900000))
    compact = record("child", "compact", 200)
    inherited = record("ancestor", "old", 900000)
    path = rollout(tmp_path, "child", [
        row("response_item", dict(type="function_call", name="sleep", arguments="{}", call_id="a")),
        row("token_usage_record", ordinary), row("token_usage_record", ordinary),
        row("token_usage_record", compact),
        row("compacted", dict(compaction_response_id="compact", latest_token_usage_record=compact, message="summary")),
        row("compacted", dict(compaction_response_id="old", latest_token_usage_record=inherited)),
        row("compacted", dict(compaction_response_id="unmatched", latest_token_usage_record=ordinary)),
        row("token_usage_record", inherited),
    ], forked_from_id="ancestor", session_id="ancestor")
    result = AUDIT.analyze(path)
    assert result["usage"] == dict(tokens(300, cached=150, output=20, reasoning=6), uncached_input_tokens=150)
    assert result["responses"] == 2
    assert result["action_attributed_usage"]["compaction"]["total_tokens"] == 210
    assert result["action_attributed_usage"]["sleep"]["responses"] == 1
    assert [c["owned_usage"] for c in result["compactions"]] == [True, False, False]
    assert result["foreign_usage_records_ignored"] == 1


def test_compaction_usage_without_separate_record_is_included(tmp_path):
    compact = record("root", "compact", 200)
    result = AUDIT.analyze(rollout(tmp_path, "root", [
        row("compacted", dict(compaction_response_id="compact", latest_token_usage_record=compact))]))
    assert result["responses"] == 1
    assert result["usage"]["total_tokens"] == 210
    assert result["method"] == "unique_response_usage"


def test_shared_root_session_id_cannot_prove_child_compaction_ownership(tmp_path):
    ambiguous = dict(session_id="root", response_id="root-snapshot", usage=tokens(900000))
    result = AUDIT.analyze(rollout(tmp_path, "child", [
        row("token_usage_record", record("child", "own", session_id="root")),
        row("compacted", dict(compaction_response_id="root-snapshot", latest_token_usage_record=ambiguous)),
    ], parent_thread_id="root", session_id="root", forked_from_id="root"))
    assert result["usage"]["total_tokens"] == 110
    assert result["compactions"][0]["owned_usage"] is False


def test_direct_recursive_scope_ignores_shared_session_and_ancestor_totals(tmp_path):
    parent = rollout(tmp_path, "root", [row("token_usage_record", record("root", "r"))])
    rollout(tmp_path, "child", [row("token_usage_record", record("child", "c", 200,
            session_id="root", thread_token_usage=tokens(999999)))], parent_thread_id="root", session_id="root")
    rollout(tmp_path, "grandchild", [row("token_usage_record", record("grandchild", "g", 300))], parent_thread_id="child")
    rollout(tmp_path, "fork", [row("token_usage_record", record("fork", "f", 400))], forked_from_id="root")
    assert len(AUDIT.audit(parent, tmp_path)["sessions"]) == 1
    direct = AUDIT.audit(parent, tmp_path, "direct")
    recursive = AUDIT.audit(parent, tmp_path, "recursive")
    assert [s["session_id"] for s in direct["sessions"]] == ["root", "child"]
    assert direct["combined_unique_response_usage"]["total_tokens"] == 320
    assert recursive["combined_unique_response_usage"]["total_tokens"] == 630


def test_fallback_excludes_ambiguous_baseline_duplicates_and_resets(tmp_path):
    def counter(amount, cached, output):
        return row("event_msg", dict(type="token_count", info={"total_token_usage": tokens(amount, cached, output)}))
    path = rollout(tmp_path, "child", [
        counter(10000, 9000, 100), counter(10000, 9000, 100),
        counter(10200, 9100, 120), counter(50, 20, 10), counter(150, 60, 15),
    ], forked_from_id="parent")
    result = AUDIT.analyze(path)
    assert result["method"] == "token_count_fallback"
    assert result["usage"]["input_tokens"] == 300
    assert result["usage"]["cached_input_tokens"] == 140
    assert result["usage"]["uncached_input_tokens"] == 160
    assert result["usage"]["output_tokens"] == 25
    assert result["usage"]["total_tokens"] == 325
    assert result["fallback"] == dict(samples=2, resets=1, initial_baseline_omitted=True)
    assert "baseline is uncertain" in " ".join(result["notes"])
    combined = AUDIT.audit(path, tmp_path)
    assert combined["combined_usage_excludes_fallback_sessions"]
    assert combined["combined_unique_response_usage"] == {}


def test_fallback_zero_start_and_exact_records_take_precedence(tmp_path):
    first, second = tokens(100, 50), tokens(220, 100, 25, 8)
    events = [row("event_msg", dict(type="token_count", info=dict(total_token_usage=first, last_token_usage=first))),
              row("event_msg", dict(type="token_count", info=dict(total_token_usage=second)))]
    fallback = AUDIT.analyze(rollout(tmp_path, "fallback", events))
    assert fallback["usage"]["total_tokens"] == 245
    assert not fallback["fallback"]["initial_baseline_omitted"]
    exact = AUDIT.analyze(rollout(tmp_path, "exact", events + [row("token_usage_record", record("exact", "x"))]))
    assert exact["usage"]["total_tokens"] == 110


def test_inherited_top_level_events_are_excluded(tmp_path):
    path = rollout(tmp_path, "child", [
        row("response_item", dict(type="function_call", name="sleep", arguments="{}"), ordinal=3),
        row("token_usage_record", record("child", "old"), ordinal=4),
        row("token_usage_record", record("child", "new"), ordinal=10),
    ], forked_from_id="parent", forked_from_ordinal_exclusive=10)
    result = AUDIT.analyze(path)
    assert result["responses"] == 1
    assert result["tool_calls"] == {}


def test_skill_evidence_truncation_and_metrics_do_not_export_transcript(tmp_path):
    secret = "DO_NOT_EXPORT_PRIVATE_TRANSCRIPT"
    path = rollout(tmp_path, "root", [
        row("response_item", dict(type="reasoning", encrypted_content=secret)),
        row("response_item", dict(type="function_call", name="exec", call_id="a",
                                  arguments='text(await tools.exec_command({cmd:"cat /skills/example/SKILL.md"}));')),
        row("response_item", dict(type="function_call_output", call_id="a",
                                  output="---\nname: example\ndescription: example\n---\n" + secret + "\nWarning: truncated output")),
        row("token_usage_record", record("root", "r")),
    ], base_instructions={"text": "Available: /skills/example/SKILL.md"})
    result = AUDIT.analyze(path)
    assert len(result["instruction_references"]) == 1
    assert result["skill_read_attempts"][0]["visible_skill_output"]
    assert result["truncated_outputs"] == 1
    assert secret not in json.dumps(result)
    assert secret not in AUDIT.summary(AUDIT.audit(path, tmp_path))


def test_wrapped_exec_output_recognizes_visible_skill_content(tmp_path):
    wrapped = json.dumps({"result": {"status": "fulfilled", "value": {"output":
        "---\nname: example\ndescription: Small skill\n---\n# Example"}}})
    path = rollout(tmp_path, "root", [
        row("response_item", dict(type="custom_tool_call", name="exec", call_id="a",
                                  input='text(await tools.exec_command({cmd:"cat /skills/example/SKILL.md"}));')),
        row("response_item", dict(type="custom_tool_call_output", call_id="a", output=wrapped)),
    ])
    result = AUDIT.analyze(path)
    assert result["skill_read_attempts"][0]["visible_skill_output"]
    assert "Small skill" not in json.dumps(result)


def test_discovery_reads_first_metadata_only_and_rejects_ambiguity(tmp_path):
    path = rollout(tmp_path, "unique-id", [])
    assert AUDIT.find_session("unique", tmp_path) == path
    renamed = path.with_name("unrelated-name.jsonl")
    path.rename(renamed)
    with renamed.open("a") as handle:
        handle.write("unparseable private body\n")
    (tmp_path / "malformed.jsonl").write_text("[]\n")
    assert AUDIT.find_session("unique-id", tmp_path) == renamed
    rollout(tmp_path, "another", [])
    try:
        AUDIT.find_session("", tmp_path)
    except ValueError as error:
        assert "exact path" in str(error)
    else:
        raise AssertionError("Ambiguous selection was accepted")


def test_cli_writes_only_explicit_metrics_and_protects_input(tmp_path):
    path = rollout(tmp_path, "root", [row("token_usage_record", record("root", "r"))])
    original = path.read_bytes()
    command = [sys.executable, str(SCRIPT), "--session", str(path)]
    completed = subprocess.run(command, check=True, stdout=subprocess.PIPE, universal_newlines=True)
    assert "input=100" in completed.stdout
    assert list(tmp_path.iterdir()) == [path]
    output = tmp_path / "metrics.json"
    subprocess.run(command + ["--output", str(output)], check=True, stdout=subprocess.PIPE)
    assert json.loads(output.read_text())["sessions"][0]["usage"]["total_tokens"] == 110
    denied = subprocess.run(command + ["--output", str(path)], stderr=subprocess.PIPE)
    assert denied.returncode == 2
    assert path.read_bytes() == original


def claude_transcript(directory, identity, events):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (identity + ".jsonl")
    path.write_text("\n".join(json.dumps(r) for r in events) + "\n", encoding="utf-8")
    return path


def claude_row(kind, content, response="response", **extra):
    return dict(type=kind, sessionId="session", uuid=response + "-row", parentUuid=None,
                timestamp="2026-10-26T00:00:00Z", isSidechain=False,
                message=dict(id=response, content=content, usage=dict(input_tokens=2,
                             cache_creation_input_tokens=30, cache_read_input_tokens=100,
                             output_tokens=10)), **extra)


def tool_use(identity, name, **inputs):
    return dict(type="tool_use", id=identity, name=name, input=inputs)


def test_claude_detection_dedup_usage_attribution_and_private_content(tmp_path):
    secret = "PRIVATE_TRANSCRIPT_BODY"
    path = claude_transcript(tmp_path, "session", [
        dict(type="file-history-snapshot", snapshot={}),
        claude_row("assistant", [dict(type="thinking", thinking=secret)]),
        claude_row("assistant", [tool_use("read", "Read", file_path="/skills/example/SKILL.md")]),
        claude_row("assistant", [tool_use("read", "Read", file_path="/skills/example/SKILL.md")]),
        claude_row("user", [dict(type="tool_result", tool_use_id="read", content=[
            dict(type="text", text="name: example\ndescription: skill\n" + secret),
            dict(type="image", source=dict(type="base64", data="X" * 200))])]),
        claude_row("assistant", [dict(type="text", text=secret)], response="second"),
        claude_row("user", secret, isCompactSummary=True),
        dict(type="summary", summary=secret),
    ])
    assert AUDIT.detect_format(path) == "claude_code"
    result = AUDIT.analyze(path)
    assert result["responses"] == 2
    assert result["usage"] == dict(input_tokens=264, cached_input_tokens=200,
                                  cache_creation_input_tokens=60, uncached_input_tokens=64,
                                  output_tokens=20, total_tokens=284, reasoning_output_tokens=None)
    assert result["tool_calls"] == {"Read": 1}
    assert result["action_attributed_usage"]["read"]["total_tokens"] == 142
    assert result["action_attributed_usage"]["read"]["reasoning_output_tokens"] is None
    assert result["response_usage"][0]["call_lines"] == [3]
    assert result["largest_outputs"][0]["call_line"] == 3
    assert result["largest_outputs"][0]["category"] == "read"
    assert result["largest_outputs"][0]["image_base64_chars"] == 200
    assert result["skill_read_attempts"][0]["visible_skill_output"]
    assert len(result["compactions"]) == 2
    assert not any(c["owned_usage"] for c in result["compactions"])
    report = AUDIT.audit(path, tmp_path)
    assert report["combined_unique_response_usage"]["reasoning_output_tokens"] is None
    rendered = AUDIT.summary(report)
    assert "format=claude_code" in rendered
    assert "reasoning subset=unavailable" in rendered
    assert "Cache creation input=60" in rendered
    assert secret not in json.dumps(report) + rendered


def test_claude_waits_repeated_commands_skills_and_spills(tmp_path):
    events = []
    for index, (name, inputs) in enumerate([
        ("Bash", dict(command="sleep 600")), ("Bash", dict(command="sleep 600")),
        ("Bash", dict(command="squeue -u user")), ("Bash", dict(command="tail -f job.log")),
        ("Monitor", {}), ("ScheduleWakeup", {}), ("TaskOutput", {}),
        ("Skill", dict(skill="example")), ("Edit", {}), ("Write", {}),
        ("Grep", {}), ("Glob", {}), ("Agent", {}), ("Task", {}),
    ]):
        identity = str(index)
        events.append(claude_row("assistant", [tool_use(identity, name, **inputs)], response=identity))
        events.append(claude_row("user", [dict(type="tool_result", tool_use_id=identity,
                                              content="output truncated")]))
    path = claude_transcript(tmp_path, "session", events)
    spill_dir = tmp_path / "session" / "tool-results"
    spill_dir.mkdir(parents=True)
    (spill_dir / "result.txt").write_bytes(b"\xffPRIVATE_SPILLED_BODY")
    result = AUDIT.analyze(path)
    assert result["call_categories"] == dict(sleep=2, status_or_logs_mixed=2, process_poll=3,
                                             skill=1, edit=2, search=2, subagent=2)
    assert result["truncated_outputs"] == 14
    assert result["spilled_tool_result_files"] == 1
    assert result["repeated_commands"][0]["count"] == 2
    assert result["repeated_commands"][0]["lines"] == [1, 3]
    assert "sleep 600" not in json.dumps(result)
    assert len(result["skill_read_attempts"]) == 1


def test_claude_subagent_scope_and_shared_session_id(tmp_path):
    root = claude_transcript(tmp_path, "session", [claude_row("assistant", [], response="main")])
    agents = tmp_path / "session" / "subagents"
    child = claude_transcript(agents, "agent-child", [claude_row("assistant", [], response="child")])
    (agents / "agent-child.meta.json").write_text("not a transcript")
    claude_transcript(agents / "agent-child" / "subagents", "agent-grandchild",
                      [claude_row("assistant", [], response="grandchild")])
    assert len(AUDIT.audit(root, tmp_path)["sessions"]) == 1
    direct = AUDIT.audit(root, tmp_path, "direct")
    assert [s["session_id"] for s in direct["sessions"]] == ["session", "agent-child"]
    assert direct["combined_unique_response_usage"]["total_tokens"] == 284
    recursive = AUDIT.audit(root, tmp_path, "recursive")
    assert len(recursive["sessions"]) == 3
    assert recursive["combined_unique_response_usage"]["total_tokens"] == 426
    assert AUDIT.select_paths(child, tmp_path, "recursive")[-1].stem == "agent-grandchild"


def test_claude_id_resolution_cli_and_cross_format_ambiguity(tmp_path, monkeypatch):
    projects, codex = tmp_path / "projects", tmp_path / "codex"
    codex.mkdir()
    path = claude_transcript(projects / "project-slug", "session", [claude_row("assistant", [])])
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    assert AUDIT.claude_projects_dir() == projects
    assert AUDIT.find_session("session", codex) == path
    command = [sys.executable, str(SCRIPT), "--session", "session", "--sessions-dir", str(codex),
               "--claude-projects-dir", str(projects)]
    completed = subprocess.run(command, check=True, stdout=subprocess.PIPE, universal_newlines=True)
    assert "format=claude_code" in completed.stdout
    rollout(codex, "session", [])
    ambiguous = subprocess.run(command, stderr=subprocess.PIPE, universal_newlines=True)
    assert ambiguous.returncode == 2
    assert "exact path" in ambiguous.stderr
    assert AUDIT.find_session(str(path), codex, projects) == path


def test_codex_format_still_detected(tmp_path):
    path = rollout(tmp_path, "codex", [])
    assert AUDIT.detect_format(path) == "codex"
    assert "format=codex" in AUDIT.summary(AUDIT.audit(path, tmp_path))
