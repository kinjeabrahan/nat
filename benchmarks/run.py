"""Process-level microbenchmark; source compilation is timed separately.

The same nested loops and dependent byte transitions are used in every port.
These are startup-inclusive wall times, not isolated CPU kernel timings.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent


def run(command):
    start = time.perf_counter_ns()
    result = subprocess.run(command, capture_output=True, timeout=120)
    elapsed = (time.perf_counter_ns() - start) / 1e9
    if result.returncode:
        raise RuntimeError(f"Command failed {command!r}: {result.stderr.decode(errors='replace')}")
    return result, elapsed


def version(command):
    result = subprocess.run(command + ["--version"], capture_output=True, text=True)
    return (result.stdout or result.stderr).splitlines()[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "nat.c")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--label", default="working-tree")
    parser.add_argument("--repetitions", type=int, default=9)
    parser.add_argument("--warmups", type=int, default=2)
    args = parser.parse_args()
    if args.repetitions < 3 or args.warmups < 0:
        parser.error("Use at least 3 repetitions and nonnegative warmups")
    compiler = shutil.which("gcc") or shutil.which("cc")
    if not compiler:
        parser.error("A C compiler is required to build Nat")
    flags = ["-std=c11", "-O2", "-Wall", "-Wextra", "-Wpedantic"]
    cpu = platform.processor()
    if Path("/proc/cpuinfo").exists():
        cpu = next((line.split(":", 1)[1].strip()
                    for line in Path("/proc/cpuinfo").read_text().splitlines()
                    if line.startswith("model name")), cpu)
    report = {
        "label": args.label,
        "date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "environment": {"platform": platform.platform(), "machine": platform.machine(),
                        "cpu": cpu, "logical_cpus": os.cpu_count()},
        "method": {"workload": "digit_walk", "transitions": 9**4,
                   "repetitions": args.repetitions, "warmups": args.warmups,
                   "clock": "perf_counter_ns", "includes_process_startup": True,
                   "schedule": "shuffled interleaved rounds; seed=0",
                   "limitations": ["One small byte/string microbenchmark only",
                       "Compiler may optimize code while preserving its observable output",
                       "C/C++ use one-byte scalar states; Python/Nat use strings",
                       "Rust integer parsing differs internally from C strtol",
                       "No CPU pinning, frequency control or isolated host",
                       "No performance ranking or memory-safety conclusion follows"]},
        "sources_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(HERE.glob("digit_walk.*"))},
        "implementations": {},
    }
    with tempfile.TemporaryDirectory(prefix="nat-benchmark-") as directory:
        build = Path(directory)
        implementations = report["implementations"]
        commands = {}

        def compiled(name, tool, compile_args, suffix):
            if not tool:
                implementations[name] = {"status": "unavailable"}
                return
            binary = build / suffix
            command = [tool, *compile_args, "-o", str(binary)]
            _, elapsed = run(command)
            implementations[name] = {"status": "measured", "version": version([tool]),
                                     "compile_command": command, "compile_seconds": elapsed}
            commands[name] = [str(binary)]

        compiled("Nat", compiler, [*flags, str(args.source.resolve())], "nat")
        implementations["Nat"]["compile_scope"] = "C interpreter build; Nat source is interpreted during execution"
        commands["Nat"].append(str(HERE / "digit_walk.nat"))
        compiled("C", compiler, [*flags, str(HERE / "digit_walk.c")], "walk-c")
        compiled("C++", shutil.which("g++"),
                 ["-x", "c++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Wpedantic",
                  str(HERE / "digit_walk.c")], "walk-cpp")
        compiled("Rust", shutil.which("rustc"),
                 ["-C", "opt-level=2", "--edition=2021", str(HERE / "digit_walk.rs")], "walk-rust")
        implementations["Python"] = {"status": "measured", "version": sys.version,
                                     "compile_seconds": None,
                                     "compile_scope": "source compilation is included in process execution"}
        commands["Python"] = [sys.executable, str(HERE / "digit_walk.py")]
        for name, command in commands.items():
            implementations[name]["run_command"] = command
            implementations[name]["samples_seconds"] = []
            for _ in range(args.warmups):
                result, _ = run(command)
                if result.stdout != b"1\n" or result.stderr:
                    raise RuntimeError(f"Incorrect warmup result for {name}: {result!r}")
        rng = random.Random(0)
        for _ in range(args.repetitions):
            order = list(commands)
            rng.shuffle(order)
            for name in order:
                result, elapsed = run(commands[name])
                if result.stdout != b"1\n" or result.stderr:
                    raise RuntimeError(f"Incorrect benchmark result for {name}: {result!r}")
                implementations[name]["samples_seconds"].append(elapsed)
        for name in commands:
            item = implementations[name]
            samples = item["samples_seconds"]
            item.update({"median_seconds": statistics.median(samples),
                         "mean_seconds": statistics.mean(samples),
                         "stdev_seconds": statistics.stdev(samples),
                         "min_seconds": min(samples), "max_seconds": max(samples),
                         "verified_stdout": "1\n"})
            print(f"{name}: median={item['median_seconds'] * 1000:.3f} ms, "
                  f"stdev={item['stdev_seconds'] * 1000:.3f} ms")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Results: {args.output}")


if __name__ == "__main__":
    main()
