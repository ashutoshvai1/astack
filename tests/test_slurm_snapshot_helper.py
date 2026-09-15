"""Exercise the portable skill helper without contacting a scheduler."""

import datetime
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from unittest import mock

import pytest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills" if (ROOT / ".agents" / "skills").is_dir() else ROOT / "skills"
HELPER = SKILLS / "supervise-slurm-experiment" / "scripts" / "slurm_snapshot.py"
# LUMI sets sys.executable to a shell wrapper; use the running interpreter for
# fake executables so tests do not recursively start the module container.
PYTHON = str(Path("/proc/self/exe").resolve()) if Path("/proc/self/exe").exists() else sys.executable


@pytest.fixture
def helper():
    spec = importlib.util.spec_from_file_location("slurm_snapshot", HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def scheduler(tmp_path, monkeypatch):
    binary = tmp_path / "bin"
    binary.mkdir()
    responses = tmp_path / "responses.json"
    calls = tmp_path / "calls.jsonl"
    source = "#!{}\n".format(PYTHON) + '''import json, os, sys
name = os.path.basename(sys.argv[0])
with open(os.environ["MOCK_CALLS"], "a") as handle:
    handle.write(json.dumps([name] + sys.argv[1:]) + "\\n")
with open(os.environ["MOCK_RESPONSES"]) as handle:
    response = json.load(handle)[name]
sys.stdout.write(response.get("stdout", ""))
sys.stderr.write(response.get("stderr", ""))
sys.exit(response.get("returncode", 0))
'''
    for name in ("squeue", "sacct"):
        executable = binary / name
        executable.write_text(source)
        executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(binary))
    monkeypatch.setenv("MOCK_CALLS", str(calls))
    monkeypatch.setenv("MOCK_RESPONSES", str(responses))

    def configure(queue="", accounting="", queue_error=None, accounting_error=None):
        value = {"squeue": {"stdout": queue}, "sacct": {"stdout": accounting}}
        for name, error in (("squeue", queue_error), ("sacct", accounting_error)):
            if error:
                value[name].update(returncode=1, stderr=error)
        responses.write_text(json.dumps(value))
        return calls
    return configure


def run_helper(helper, tmp_path, capsys, jobs, *args):
    inputs = tmp_path / "jobs.json"
    inputs.write_text(json.dumps(jobs))
    assert helper.main(["--jobs-file", str(inputs)] + list(args)) == 0
    return json.loads(capsys.readouterr().out)


def read_calls(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_batches_explicit_array_ids_and_only_accounts_missing_or_terminal(helper, scheduler, tmp_path, capsys):
    calls = scheduler("123_4|RUNNING|00:12|nid01\n125|FAILED|00:04|(NonZeroExitCode)\n",
                      "123_5|COMPLETED|00:08|0:0\n125|FAILED|00:04|1:0\n")
    result = run_helper(helper, tmp_path, capsys,
                        {"jobs": [{"job_id": "123_4"}, {"job_id": "123_5"}, {"job_id": 125}]})
    assert [job["status"] for job in result["jobs"]] == ["active", "completed", "failed"]
    assert result["jobs"][1]["exit_code"] == "0:0"
    commands = read_calls(calls)
    assert [command[0] for command in commands] == ["squeue", "sacct"]
    assert "--jobs=123_4,123_5,125" in commands[0]
    assert "--array" in commands[0]
    assert "--jobs=123_5,125" in commands[1]
    assert "--allocations" in commands[1]


def test_large_log_read_is_bounded_and_stdout_omits_full_tails(helper, scheduler, tmp_path, capsys):
    scheduler("123|RUNNING|00:12|nid01\n")
    log = tmp_path / "run.out"
    with log.open("wb") as handle:
        handle.write(b"ERROR old unrelated failure\n")
        handle.seek(10 * 1024 * 1024)
        handle.write(b'\nordinary output\n{"step":20,"loss":1.5,"huge":"omit"}\nERROR current failure\n')
    state = tmp_path / "snapshot.json"
    real_fdopen = helper.os.fdopen
    read_sizes = []

    class BoundedReader:
        def __init__(self, wrapped):
            self.wrapped = wrapped

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.wrapped.close()

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

        def read(self, size=-1):
            assert 0 <= size <= 256
            read_sizes.append(size)
            return self.wrapped.read(size)

    with mock.patch.object(helper.os, "fdopen", side_effect=lambda *a, **kw: BoundedReader(real_fdopen(*a, **kw))):
        result = run_helper(helper, tmp_path, capsys,
                            [{"job_id": 123, "stdout": "run.out", "total_steps": 100}],
                            "--tail-bytes", "256", "--output", str(state))
    assert read_sizes == [256]
    job = result["jobs"][0]
    assert job["progress"] == {"step": 20, "loss": 1.5, "total_steps": 100}
    assert job["error_tail"] == ["ERROR current failure"]
    assert "logs" not in job
    detail = json.loads(state.read_text())["jobs"][0]["logs"]["stdout"]
    assert detail["bytes_read"] == 256 and detail["truncated"]
    assert "ordinary output" in detail["tail"]
    assert "old unrelated" not in detail["tail"]


def test_cached_deadline_reuses_observation_without_commands_or_log_reads(helper, scheduler, tmp_path, capsys):
    scheduler("123|RUNNING|00:12|nid01\n")
    state = tmp_path / "snapshot.json"
    first = run_helper(helper, tmp_path, capsys, [{"job_id": 123, "stdout": "missing.out"}],
                       "--previous", str(state), "--output", str(state))
    saved = json.loads(state.read_text())
    request = saved["request"]
    observed = datetime.datetime.strptime(saved["timestamp"], helper.TIME_FORMAT)
    assert saved["next_check_at"] == (observed + datetime.timedelta(seconds=600)).strftime(helper.TIME_FORMAT)
    with mock.patch.object(helper, "run_scheduler", side_effect=AssertionError("early scheduler read")), \
            mock.patch.object(helper, "tail_log", side_effect=AssertionError("early log read")):
        cached, reused = helper.snapshot(request["jobs"], request["options"], state,
                                         now=observed + datetime.timedelta(seconds=599))
        second = run_helper(helper, tmp_path, capsys, [{"job_id": 123, "stdout": "missing.out"}],
                            "--previous", str(state), "--output", str(state))
    assert reused and cached == saved
    assert second["cached"] and not first["cached"]
    assert second["timestamp"] == first["timestamp"]
    assert second["next_check_at"] == first["next_check_at"]
    with mock.patch.object(helper, "collect", return_value={"fresh": True}) as collect:
        helper.snapshot(request["jobs"], request["options"], state, now=observed + datetime.timedelta(seconds=600))
        helper.snapshot(request["jobs"], request["options"], state, force=True, now=observed)
        helper.snapshot([{"job_id": "124"}], request["options"], state, now=observed)
    assert collect.call_count == 3


@pytest.mark.parametrize("queue_error,accounting_error,expected,commands", [
    ("controller unavailable", None, "scheduler_error", ["squeue", "sacct"]),
    (None, "accounting unavailable", "scheduler_error", ["squeue", "sacct"]),
    (None, None, "missing", ["squeue", "sacct"]),
])
def test_unavailable_or_absent_jobs_are_not_completed(helper, scheduler, tmp_path, capsys,
                                                    queue_error, accounting_error, expected, commands):
    calls = scheduler(queue_error=queue_error, accounting_error=accounting_error)
    result = run_helper(helper, tmp_path, capsys, [{"job_id": 123, "stderr": "absent.err"}])
    job = result["jobs"][0]
    assert job["status"] == expected
    assert "stderr" in job["log_errors"]
    assert [command[0] for command in read_calls(calls)] == commands
    if queue_error or accounting_error:
        assert any((queue_error or accounting_error) in error for error in job["scheduler_errors"].values())


def test_disappeared_job_is_confirmed_by_accounting_after_squeue_error(helper, scheduler, tmp_path, capsys):
    calls = scheduler(queue_error="slurm_load_jobs error: Invalid job id specified",
                      accounting="123|COMPLETED|00:08|0:0\n")
    result = run_helper(helper, tmp_path, capsys, [{"job_id": 123}])
    job = result["jobs"][0]
    assert job["status"] == "completed" and job["source"] == "sacct"
    assert "Invalid job id" in job["scheduler_errors"]["squeue"]
    assert [command[0] for command in read_calls(calls)] == ["squeue", "sacct"]


def test_unrecognized_state_is_unknown_and_timeout_is_reported(helper, scheduler, tmp_path, capsys):
    scheduler("123|NEW_STATE|00:12|nid01\n")
    result = run_helper(helper, tmp_path, capsys, [{"job_id": 123}])
    assert result["jobs"][0]["status"] == "unknown"
    with mock.patch.object(helper.subprocess, "run", side_effect=subprocess.TimeoutExpired("squeue", 15)):
        result = run_helper(helper, tmp_path, capsys, [{"job_id": 123}])
    assert result["jobs"][0]["status"] == "scheduler_error"
    assert "timed out" in result["jobs"][0]["scheduler_errors"]["squeue"]


def test_custom_progress_fields_and_error_tail_are_small(helper, scheduler, tmp_path, capsys):
    scheduler("123|RUNNING|00:12|nid01\n")
    (tmp_path / "out").write_text('{"iteration":22,"lr":0.01,"loss":7}\n')
    (tmp_path / "err").write_text("ERROR one\nERROR two\nERROR three\n")
    result = run_helper(helper, tmp_path, capsys, [{"job_id": 123, "stdout": "out", "stderr": "err"}],
                        "--progress-fields", "iteration,lr", "--error-lines", "2")
    assert result["jobs"][0]["progress"] == {"iteration": 22, "lr": 0.01}
    assert result["jobs"][0]["error_tail"] == ["ERROR two", "ERROR three"]


@pytest.mark.parametrize("jobs", [[{"job_id": "123_[1-9]"}], [{"job_id": "123;echo bad"}],
                                 [{"job_id": 123}, {"job_id": "123"}]])
def test_invalid_identities_fail_before_scheduler_calls(helper, tmp_path, capsys, jobs):
    with mock.patch.object(helper, "run_scheduler", side_effect=AssertionError("invalid scheduler call")):
        with pytest.raises(SystemExit) as exc:
            run_helper(helper, tmp_path, capsys, jobs)
    assert exc.value.code == 2


def test_cli_runs_with_mock_executables_and_rejects_log_overwrite(scheduler, tmp_path):
    scheduler("123|RUNNING|00:12|nid01\n")
    inputs = tmp_path / "jobs.json"
    log = tmp_path / "run.log"
    log.write_text("preserve me\n")
    inputs.write_text(json.dumps([{"job_id": "123", "stdout": str(log)}]))
    result = subprocess.run([PYTHON, str(HELPER), "--jobs-file", str(inputs)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["jobs"][0]["state"] == "RUNNING"
    result = subprocess.run([PYTHON, str(HELPER), "--jobs-file", str(inputs), "--output", str(log)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    assert result.returncode == 2
    assert log.read_text() == "preserve me\n"
