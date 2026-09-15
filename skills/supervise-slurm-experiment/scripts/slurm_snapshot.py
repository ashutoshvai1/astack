#!/usr/bin/env python3
"""One bounded Slurm observation; Python 3.6+ standard library only."""

import argparse
import datetime
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile


FAILED = set("BOOT_FAIL CANCELLED DEADLINE FAILED NODE_FAIL OUT_OF_MEMORY "
             "PREEMPTED REVOKED SPECIAL_EXIT TIMEOUT".split())
ACTIVE = set("PENDING RUNNING CONFIGURING COMPLETING RESIZING REQUEUED "
             "REQUEUE_FED REQUEUE_HOLD SIGNALING STAGE_OUT STOPPED SUSPENDED".split())
TERMINAL = FAILED | {"COMPLETED"}
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
JSON_LIMIT = 16 * 1024 * 1024
ERROR_PATTERN = re.compile(r"error|exception|traceback|fail|out.of.memory|killed", re.I)


def read_json(path, limit=JSON_LIMIT):
    with open(str(path), "rb") as handle:
        raw = handle.read(min(os.fstat(handle.fileno()).st_size, limit) + 1)
    if len(raw) > limit:
        raise ValueError("JSON input exceeds {} bytes: {}".format(limit, path))
    return json.loads(raw.decode("utf-8"))


def load_jobs(path):
    value = read_json(path)
    jobs = value.get("jobs") if isinstance(value, dict) else value
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= 100:
        raise ValueError("jobs must be a list of 1 to 100 explicit jobs")
    result, seen = [], set()
    for job in jobs:
        if not isinstance(job, dict):
            raise ValueError("each job must be an object")
        if set(job) - {"job_id", "stdout", "stderr", "label", "total_steps"}:
            raise ValueError("unsupported job field")
        job = dict(job)
        job_id = str(job.get("job_id", ""))
        if not re.fullmatch(r"[1-9][0-9]*(?:_[0-9]+)?", job_id) or len(job_id) > 40:
            raise ValueError("job_id must be a job number or explicit array task (123_4)")
        if job_id in seen:
            raise ValueError("duplicate job_id: " + job_id)
        seen.add(job_id)
        job["job_id"] = job_id
        for field in ("stdout", "stderr"):
            if field in job:
                if not isinstance(job[field], str) or not job[field]:
                    raise ValueError(field + " must be a nonempty path")
                job[field] = str((path.parent / job[field]).resolve())
        if "label" in job and (not isinstance(job["label"], str) or len(job["label"]) > 120):
            raise ValueError("label must be a string of at most 120 characters")
        if "total_steps" in job and (type(job["total_steps"]) is not int or job["total_steps"] <= 0):
            raise ValueError("total_steps must be a positive integer")
        result.append(job)
    return result


def tail_log(path, limit):
    """Seek once and read at most limit bytes, including from very large logs."""
    result = {"path": path}
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise OSError("log is not a regular file")
            offset = max(0, info.st_size - limit)
            handle.seek(offset)
            raw = handle.read(limit)
        result.update(size_bytes=info.st_size, bytes_read=len(raw), truncated=offset > 0)
        # The first line may have started before the tail window.
        if offset:
            raw = raw.partition(b"\n")[2]
        result["tail"] = raw.decode("utf-8", errors="replace")
    except OSError as exc:
        result["error"] = str(exc)[:400]
    return result


def run_scheduler(command, timeout):
    try:
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 universal_newlines=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {}, str(exc)[:400]
    if process.returncode:
        return {}, "exit {}: {}".format(process.returncode, process.stderr.strip()[-400:])
    rows = {}
    for line in process.stdout.splitlines():
        fields = [part.strip() for part in line.split("|", 3)]
        if len(fields) != 4 or not fields[0] or not fields[1]:
            return {}, "malformed scheduler output: " + line[:200]
        rows[fields[0]] = fields[1:]
    return rows, None


def normalized_state(raw):
    return raw.split()[0].rstrip("+").upper()


def collect(jobs, options, now):
    ids = [job["job_id"] for job in jobs]
    queued, queue_error = run_scheduler(
        ["squeue", "--noheader", "--array", "--jobs=" + ",".join(ids),
         "--format=%i|%T|%M|%R"], options["command_timeout"])
    missing = [job_id for job_id in ids if job_id not in queued
               or normalized_state(queued[job_id][0]) in TERMINAL]
    accounted, account_error = {}, None
    if missing:
        accounted, account_error = run_scheduler(
            ["sacct", "--noheader", "--parsable2", "--allocations",
             "--jobs=" + ",".join(missing), "--format=JobID%64,State%32,Elapsed,ExitCode"],
            options["command_timeout"])
    observations, log_cache = [], {}
    for job in jobs:
        job_id = job["job_id"]
        item = {"job_id": job_id, "progress": {}, "error_tail": []}
        if "label" in job:
            item["label"] = job["label"]
        row = accounted.get(job_id) or queued.get(job_id)
        if row:
            state = normalized_state(row[0])
            item.update(state=state, elapsed=row[1], source="sacct" if job_id in accounted else "squeue")
            if item["source"] == "sacct":
                item["exit_code"] = row[2]
            else:
                item["reason"] = row[2][:200]
            item["status"] = ("completed" if state == "COMPLETED" else "failed" if state in FAILED
                              else "active" if state in ACTIVE else "unknown")
        else:
            state = "SCHEDULER_ERROR" if queue_error or account_error else "MISSING"
            item.update(state=state, status=state.lower(), source=None)
        if queue_error or (account_error and job_id in missing):
            item["scheduler_errors"] = {name: error for name, error in
                (("squeue", queue_error), ("sacct", account_error if job_id in missing else None)) if error}
        logs = {}
        for name in ("stdout", "stderr"):
            if name in job:
                if job[name] not in log_cache:
                    log_cache[job[name]] = tail_log(job[name], options["tail_bytes"])
                logs[name] = log_cache[job[name]]
        for name, log in logs.items():
            lines = log.get("tail", "").splitlines()
            for line in lines:
                try:
                    value = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if isinstance(value, dict):
                    for field in options["progress_fields"]:
                        entry = value.get(field)
                        if isinstance(entry, float) and not math.isfinite(entry):
                            continue
                        if isinstance(entry, (int, float, str)) and not isinstance(entry, bool):
                            item["progress"][field] = entry[:120] if isinstance(entry, str) else entry
            errors = [line[:400] for line in lines if ERROR_PATTERN.search(line)]
            if name == "stderr" and not errors:
                errors = [line[:400] for line in lines[-options["error_lines"]:]]
            item["error_tail"].extend(errors)
        item["error_tail"] = item["error_tail"][-options["error_lines"]:]
        if "total_steps" in job:
            item["progress"]["total_steps"] = job["total_steps"]
        item["logs"] = logs
        observations.append(item)
    return {"schema_version": 1, "timestamp": now.strftime(TIME_FORMAT),
            "next_check_at": (now + datetime.timedelta(seconds=options["interval_seconds"])).strftime(TIME_FORMAT),
            "request": {"jobs": jobs, "options": options}, "jobs": observations}


def snapshot(jobs, options, previous=None, force=False, now=None):
    now = now or datetime.datetime.utcnow()
    if previous and not force:
        try:
            # Fits 100 jobs with two maximum tails, including JSON escaping.
            saved = read_json(previous, limit=128 * 1024 * 1024)
        except FileNotFoundError:
            saved = None
        if isinstance(saved, dict) and saved.get("schema_version") == 1 and saved.get("request") == {"jobs": jobs, "options": options}:
            observed = datetime.datetime.strptime(saved["timestamp"], TIME_FORMAT)
            deadline = datetime.datetime.strptime(saved["next_check_at"], TIME_FORMAT)
            if observed <= now < deadline and deadline == observed + datetime.timedelta(seconds=options["interval_seconds"]):
                return saved, True
    return collect(jobs, options, now), False


def write_snapshot(path, value):
    """Publish disposable monitor state atomically; never patch experiment records."""
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(path.parent),
                                     prefix="." + path.name + ".", delete=False) as handle:
        temporary = handle.name
        try:
            json.dump(value, handle, separators=(",", ":"))
            handle.write("\n")
            handle.close()
            os.replace(temporary, str(path))
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def bounded_integer(minimum, maximum):
    def parse(value):
        number = int(value)
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError("must be between {} and {}".format(minimum, maximum))
        return number
    return parse


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Input: [{"job_id":"123_4","stdout":"logs/run.out","stderr":"logs/run.err",
         "label":"seed 0","total_steps":1000}] or {"jobs":[...]}.
Only job_id is required. Paths are relative to the jobs file. Use explicit array
task IDs, not array ranges or parent IDs for whole arrays. Up to 100 jobs.
Progress is selected from top-level scalar JSON fields in complete tail lines;
unstructured progress is not guessed. Each log read is bounded, even with --output.
Stdout is a compact JSON summary. --output writes full bounded tails and cache
state to a disposable file, outside canonical evidence. A matching --previous
before its deadline makes no Slurm/log reads; missing previous state is allowed.
This is one observation, with no polling or sleep. Scheduler/log failures appear
in JSON and do not establish completion. Exit 2 means invalid input or state I/O.''')
    parser.add_argument("--jobs-file", required=True, type=Path)
    parser.add_argument("--previous", type=Path, help="reuse this snapshot before its deadline")
    parser.add_argument("--output", type=Path, help="atomically save full snapshot (may equal --previous)")
    parser.add_argument("--force", action="store_true", help="explicit early-check override")
    parser.add_argument("--interval-seconds", type=bounded_integer(1, 86400), default=600)
    parser.add_argument("--tail-bytes", type=bounded_integer(1, 65536), default=8192, help="maximum bytes read per log (default: 8192)")
    parser.add_argument("--error-lines", type=bounded_integer(1, 10), default=3)
    parser.add_argument("--progress-fields", default="step,total_steps,epoch,loss", help="comma-separated top-level JSON keys (up to 12)")
    parser.add_argument("--command-timeout", type=bounded_integer(1, 30), default=15, help="seconds per scheduler command (default: 15)")
    args = parser.parse_args(argv)
    try:
        fields = [field.strip() for field in args.progress_fields.split(",")]
        if not 1 <= len(fields) <= 12 or any(not field or len(field) > 64 for field in fields):
            raise ValueError("select 1 to 12 nonempty progress fields of at most 64 characters")
        jobs = load_jobs(args.jobs_file.resolve())
        options = {"interval_seconds": args.interval_seconds, "tail_bytes": args.tail_bytes,
                   "error_lines": args.error_lines, "progress_fields": fields,
                   "command_timeout": args.command_timeout}
        if args.output and args.output.resolve() in {args.jobs_file.resolve()} | {
                Path(job[name]) for job in jobs for name in ("stdout", "stderr") if name in job}:
            raise ValueError("output must not overwrite the jobs file or an input log")
        value, reused = snapshot(jobs, options, args.previous, args.force)
        if args.output:
            write_snapshot(args.output, value)
        summary = {key: value[key] for key in ("timestamp", "next_check_at")}
        summary["cached"] = reused
        summary["jobs"] = [{key: entry for key, entry in job.items() if key != "logs"} for job in value["jobs"]]
        for job, full in zip(summary["jobs"], value["jobs"]):
            errors = {name: log["error"] for name, log in full["logs"].items() if "error" in log}
            if errors:
                job["log_errors"] = errors
        print(json.dumps(summary, separators=(",", ":")))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
