# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Standalone validator: rerun a lit test and check the target line."""

from __future__ import annotations

import argparse
import re
import shlex
import sys
import tempfile
from pathlib import Path

from fill_line_agent.instrumented import load_instrumented
from fill_line_agent.oracle import (
    CoverageOracle,
    SymcovIndex,
    TargetLine,
    ToolName,
)
from fill_line_agent.steps import StepTracker
from fill_line_agent.tool_runner import ToolRunner

_RUN_RE = re.compile(
    r"^[;#]\s*RUN:\s*(?P<body>.+)$",
    re.MULTILINE,
)


def parse_run_line(test_text: str) -> tuple[ToolName, list[str], str]:
    """Parse the first RUN line into tool, argv, and input body."""
    match = _RUN_RE.search(test_text)
    if not match:
        raise ValueError("test has no RUN: line")
    body = match.group("body").strip()
    # Drop FileCheck redirects and trailing pipes if present.
    body = body.split("|", 1)[0].strip()
    tokens = shlex.split(body)
    if not tokens:
        raise ValueError("empty RUN: line")
    tool = tokens[0]
    if tool not in ("opt", "llc"):
        raise ValueError(f"unsupported tool in RUN: {tool!r}")
    rest = tokens[1:]
    # Remove %s placeholder and -o /dev/null (oracle supplies both).
    argv: list[str] = []
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok in ("%s", "<"):
            i += 1
            continue
        if tok in ("-o", "--o"):
            i += 2
            continue
        if tok.startswith("-o=") or tok.startswith("--o="):
            i += 1
            continue
        if tok == "/dev/null":
            i += 1
            continue
        argv.append(tok)
        i += 1
    # Strip any remaining %s that was not adjacent to -o.
    argv = [a for a in argv if a != "%s"]

    # Input body is everything after the header comments/RUN lines.
    lines = test_text.splitlines()
    start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith((";", "#")) or stripped == "":
            start = i + 1
            continue
        break
    input_text = "\n".join(lines[start:])
    if input_text and not input_text.endswith("\n"):
        input_text += "\n"
    return tool, argv, input_text  # type: ignore[return-value]


def detect_format(path: Path) -> str:
    suffix = path.suffix.lstrip(".")
    if suffix not in ("ll", "mir"):
        raise ValueError(f"test suffix must be .ll or .mir, got {path.suffix}")
    return suffix


def validate_test(
    *,
    test_path: Path,
    target: TargetLine,
    tools: dict[ToolName, Path],
    indexes: dict[ToolName, SymcovIndex],
    sancov_bin: Path,
    timeout_s: float,
    runner: ToolRunner | None = None,
) -> int:
    text = test_path.read_text(encoding="utf-8")
    tool, argv, input_text = parse_run_line(text)
    fmt = detect_format(test_path)
    if tool == "opt" and fmt == "mir":
        print("error: opt cannot run a .mir test", file=sys.stderr)
        return 1
    if tool not in tools or tool not in indexes:
        print(f"error: tool {tool} is not available", file=sys.stderr)
        return 1
    if not indexes[tool].is_instrumented(target):
        print(f"uncovered: target not instrumented in {tool} symcov", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="check-line-") as tmp:
        oracle = CoverageOracle(
            tools=tools,
            indexes=indexes,
            sancov_bin=sancov_bin,
            target=target,
            work_root=Path(tmp),
            timeout_s=timeout_s,
            runner=runner or ToolRunner(),
        )
        result = oracle.run(tool, argv, input_text, fmt)  # type: ignore[arg-type]

    assert result.measure is not None
    m = result.measure
    print(
        f"{m.status}: {target} {m.n_hit}/{m.n_points} "
        f"exit={result.exit_code} changed={result.changed}"
    )
    return 0 if m.status == "covered" else 1


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Rerun a fill-line lit test and check the target line."
    )
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--target", required=True, help="path:line")
    parser.add_argument(
        "--instrumented-bin-dir",
        type=Path,
        required=True,
        help="Directory containing instrumented opt and/or llc plus sancov",
    )
    parser.add_argument("--timeout-s", type=float, default=30.0)
    parser.add_argument(
        "--tools-runner",
        choices=("host", "docker"),
        default=None,
        help="Run opt/llc/sancov on the host or in Docker",
    )
    parser.add_argument(
        "--tools-image",
        default=None,
        help="Docker image for --tools-runner=docker",
    )
    args = parser.parse_args(argv)

    target = TargetLine.parse(args.target)
    runner = ToolRunner.from_cli(mode=args.tools_runner, image=args.tools_image)
    steps = StepTracker()
    with tempfile.TemporaryDirectory(prefix="check-line-symcov-") as tmp:
        tools, indexes, sancov = load_instrumented(
            bin_dir=args.instrumented_bin_dir,
            work_dir=Path(tmp),
            runner=runner,
            steps=steps,
        )
        raise SystemExit(
            validate_test(
                test_path=args.test,
                target=target,
                tools=tools,
                indexes=indexes,
                sancov_bin=sancov,
                timeout_s=args.timeout_s,
                runner=runner,
            )
        )


if __name__ == "__main__":
    main()
