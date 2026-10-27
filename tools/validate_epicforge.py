#!/usr/bin/env python3
"""EpicForge built-in MIDI verification runner."""

import argparse
import csv
import os
import pathlib
import subprocess
import sys
import tempfile
import time

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=pathlib.Path, default=pathlib.Path("."))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--report", type=pathlib.Path,
                        default=pathlib.Path("validation_results.csv"))
    args = parser.parse_args()

    root = args.source.resolve()
    engine = root / "engine"
    programs = sorted(
        (root / "programs").rglob("EFG_*.py"),
        key=lambda p: p.name
    )

    if args.limit is not None:
        programs = programs[:args.limit]

    if not (engine / "epic_analysis.json").is_file():
        sys.exit("ERROR: Missing engine/epic_analysis.json")

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(engine), str(root), env.get("PYTHONPATH", "")]
    )

    results = []

    with tempfile.TemporaryDirectory(prefix="epicforge_") as tmp:
        for index, script in enumerate(programs, 1):
            output = pathlib.Path(tmp) / script.stem
            output.mkdir()

            start = time.monotonic()
            result_status = "FAIL"
            detail = ""
            return_code = ""

            try:
                run = subprocess.run(
                    [sys.executable, str(script), str(output)],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=args.timeout
                )

                return_code = run.returncode
                message = run.stdout + run.stderr
                midi = output / (script.stem + ".mid")

                if (
                    run.returncode == 0
                    and midi.is_file()
                    and midi.stat().st_size > 0
                    and "identical to dataset file" in run.stdout
                ):
                    result_status = "PASS"
                else:
                    detail = message[-1000:]

            except subprocess.TimeoutExpired:
                result_status = "TIMEOUT"
                detail = "Execution exceeded timeout"

            except Exception as exc:
                detail = str(exc)

            results.append({
                "program": script.name,
                "status": result_status,
                "return_code": return_code,
                "elapsed_seconds": round(time.monotonic() - start, 3),
                "detail": detail
            })

            print(
                f"[{index}/{len(programs)}] "
                f"{script.name}: {result_status}",
                flush=True
            )

    args.report.parent.mkdir(parents=True, exist_ok=True)

    with args.report.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "program", "status", "return_code",
                "elapsed_seconds", "detail"
            ]
        )
        writer.writeheader()
        writer.writerows(results)

    passed = sum(r["status"] == "PASS" for r in results)

    print(f"\nRESULT: {passed}/{len(results)} passed")
    print(f"Report: {args.report}")

    sys.exit(0 if programs and passed == len(programs) else 1)

if __name__ == "__main__":
    main()
