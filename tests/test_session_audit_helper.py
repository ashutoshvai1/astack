import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
if not SKILLS.is_dir():
    SKILLS = ROOT / "skills"
SCRIPT = SKILLS / "audit-codex-session" / "scripts" / "audit_session.py"
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
