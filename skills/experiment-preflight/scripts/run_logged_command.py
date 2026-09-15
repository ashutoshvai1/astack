#!/usr/bin/env python3
"""Run an authorized command once, retaining its output and reporting a summary."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def bounded_tail(path, byte_limit, line_limit):
    with path.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(max(0, size - byte_limit))
        data = stream.read(byte_limit)
    return "\n".join(data.decode("utf-8", errors="replace").splitlines()[-line_limit:])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, type=Path,
                        help="New log file; existing files are never overwritten")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--env-script", type=Path,
                        help="Explicit trusted Bash environment setup; relative to cwd")
    parser.add_argument("--tail-bytes", type=int, default=4096)
    parser.add_argument("--tail-lines", type=int, default=20)
    parser.add_argument("command", nargs=argparse.REMAINDER,
                        help="Command and literal arguments after --; no shell expansion")
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required after --")
    if not 1 <= args.tail_bytes <= 65536 or not 1 <= args.tail_lines <= 200:
        parser.error("tail bounds must be 1..65536 bytes and 1..200 lines")
    cwd = args.cwd.resolve()
    if not cwd.is_dir():
        parser.error("cwd must be an existing directory")
    log = args.log.resolve()
    if args.env_script:
        profile = args.env_script
        profile = (cwd / profile).resolve() if not profile.is_absolute() else profile.resolve()
        if not profile.is_file():
            parser.error("env-script must be an existing file")
        command = ["bash", "--noprofile", "--norc", "-c",
                   'set -e; source "$1"; shift; exec "$@"',
                   "run-logged-command", str(profile)] + command
    started = time.monotonic()
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("xb") as stream:
            try:
                result = subprocess.run(command, cwd=str(cwd), stdout=stream,
                                        stderr=subprocess.STDOUT)
                code = result.returncode
            except OSError as exc:
                stream.write((str(exc) + "\n").encode("utf-8"))
                code = 127
    except OSError as exc:
        print(json.dumps({"status": "not_started", "log": str(log), "error": str(exc)}))
        return 2
    code = code if code >= 0 else 128 - code
    summary = {"status": "passed" if code == 0 else "failed", "exit_code": code,
               "elapsed_seconds": round(time.monotonic() - started, 3), "log": str(log)}
    if code:
        summary["error_tail"] = bounded_tail(log, args.tail_bytes, args.tail_lines)
    print(json.dumps(summary, ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
