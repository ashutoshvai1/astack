import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / (".agents/skills" if (ROOT / ".agents/skills").is_dir() else "skills")
HELPER = SKILLS / "experiment-preflight/scripts/run_logged_command.py"


def run_helper(tmp_path, command, *options):
    return subprocess.run(
        [sys.executable, str(HELPER), "--log", str(tmp_path / "command.log"),
         "--cwd", str(tmp_path), *options, "--", *command],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
    )


def test_success_keeps_large_output_out_of_summary(tmp_path):
    result = run_helper(tmp_path, [sys.executable, "-c", "print('payload' * 20000)"])
    summary = json.loads(result.stdout)
    assert result.returncode == 0
    assert summary["status"] == "passed"
    assert len(result.stdout) < 500
    assert (tmp_path / "command.log").stat().st_size > 100000


def test_failure_preserves_exit_and_bounds_tail(tmp_path):
    result = run_helper(tmp_path, [sys.executable, "-c",
                        "import sys; print('x' * 9000); print('failure detail'); sys.exit(7)"],
                        "--tail-bytes", "100", "--tail-lines", "2")
    summary = json.loads(result.stdout)
    assert result.returncode == summary["exit_code"] == 7
    assert len(summary["error_tail"]) <= 100
    assert summary["error_tail"].endswith("failure detail")
    assert (tmp_path / "command.log").stat().st_size > 9000


def test_environment_setup_preserves_literal_arguments_and_cwd(tmp_path):
    profile = tmp_path / "environment with spaces.sh"
    profile.write_text("export HELPER_TEST_SETTING='environment ready'\n")
    literal = "literal ; $(touch unexpected) `touch unexpected2` $HOME"
    result = run_helper(tmp_path, [sys.executable, "-c",
                        "import os, sys; print(os.environ['HELPER_TEST_SETTING']); "
                        "print(os.getcwd()); print(sys.argv[1])", literal],
                        "--env-script", profile.name)
    assert result.returncode == 0
    assert (tmp_path / "command.log").read_text().splitlines() == [
        "environment ready", str(tmp_path), literal]
    assert not (tmp_path / "unexpected").exists()
    assert not (tmp_path / "unexpected2").exists()


def test_environment_failure_stops_command(tmp_path):
    (tmp_path / "bad.sh").write_text("false\nexport SHOULD_NOT_CONTINUE=1\n")
    result = run_helper(tmp_path, [sys.executable, "-c", "print('should not run')"],
                        "--env-script", "bad.sh")
    assert result.returncode != 0
    assert "should not run" not in (tmp_path / "command.log").read_text()


def test_existing_log_is_preserved_and_command_not_started(tmp_path):
    (tmp_path / "command.log").write_text("keep me")
    result = run_helper(tmp_path, [sys.executable, "-c", "open('side-effect', 'w').close()"])
    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "not_started"
    assert (tmp_path / "command.log").read_text() == "keep me"
    assert not (tmp_path / "side-effect").exists()


def test_missing_executable_reports_failure(tmp_path):
    result = run_helper(tmp_path, [str(tmp_path / "missing-program")])
    assert result.returncode == 127
    assert json.loads(result.stdout)["error_tail"]
