"""Typed LLVM tool paths resolved from CLI flags and environment variables."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fuzz_fill.env import (
    FUZZ_FILL_LLC,
    FUZZ_FILL_LLVM_DIS,
    FUZZ_FILL_LLVM_LIT,
    FUZZ_FILL_LLVM_REDUCE,
    FUZZ_FILL_OPT,
    FUZZ_FILL_SANCOV,
    executable_from_flag_or_env,
)


@dataclass(frozen=True)
class BaselineTools:
    sancov: Path
    llvm_lit: Path
    llc: Path
    opt: Path


@dataclass(frozen=True)
class CandidateTestTools:
    llc: Path


@dataclass(frozen=True)
class IncrementalTools:
    sancov: Path


@dataclass(frozen=True)
class ReduceTools:
    llc: Path
    llvm_reduce: Path
    llvm_dis: Path | None


def baseline_tools_from_args(
    *,
    sancov: Path | None,
    llvm_lit: Path | None,
    llc: Path | None,
    opt: Path | None,
) -> BaselineTools:
    return BaselineTools(
        sancov=executable_from_flag_or_env(
            sancov, FUZZ_FILL_SANCOV, flag_name="--sancov"
        ),
        llvm_lit=executable_from_flag_or_env(
            llvm_lit, FUZZ_FILL_LLVM_LIT, flag_name="--llvm-lit"
        ),
        llc=executable_from_flag_or_env(llc, FUZZ_FILL_LLC, flag_name="--llc"),
        opt=executable_from_flag_or_env(opt, FUZZ_FILL_OPT, flag_name="--opt"),
    )


def candidate_test_tools_from_args(*, llc: Path | None) -> CandidateTestTools:
    return CandidateTestTools(
        llc=executable_from_flag_or_env(llc, FUZZ_FILL_LLC, flag_name="--llc"),
    )


def incremental_tools_from_args(*, sancov: Path | None) -> IncrementalTools:
    return IncrementalTools(
        sancov=executable_from_flag_or_env(
            sancov, FUZZ_FILL_SANCOV, flag_name="--sancov"
        ),
    )


def reduce_tools_from_args(
    *,
    llc: Path | None,
    llvm_reduce: Path | None,
    llvm_dis: Path | None,
) -> ReduceTools:
    dis: Path | None = None
    if llvm_dis is not None:
        dis = executable_from_flag_or_env(
            llvm_dis, FUZZ_FILL_LLVM_DIS, flag_name="--llvm-dis"
        )
    return ReduceTools(
        llc=executable_from_flag_or_env(llc, FUZZ_FILL_LLC, flag_name="--llc"),
        llvm_reduce=executable_from_flag_or_env(
            llvm_reduce, FUZZ_FILL_LLVM_REDUCE, flag_name="--llvm-reduce"
        ),
        llvm_dis=dis,
    )
