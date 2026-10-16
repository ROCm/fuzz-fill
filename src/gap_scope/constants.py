from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Stable LLVM targets from llvm/CMakeLists.txt LLVM_ALL_TARGETS.
LLVM_ALL_TARGETS = frozenset(
    {
        "AArch64",
        "AMDGPU",
        "ARM",
        "AVR",
        "BPF",
        "DirectX",
        "Hexagon",
        "Lanai",
        "LoongArch",
        "Mips",
        "MSP430",
        "NVPTX",
        "PowerPC",
        "RISCV",
        "Sparc",
        "SPIRV",
        "SystemZ",
        "VE",
        "WebAssembly",
        "X86",
        "XCore",
    }
)

ALLOWLIST_LLVM = SCRIPTS_DIR / "allowlist-llvm.txt"
ALLOWLIST_CLANG = SCRIPTS_DIR / "allowlist-clang.txt"
ALLOWLIST_LLVM_CLANG = SCRIPTS_DIR / "allowlist-llvm-clang.txt"

TEST_PATH_PREFIXES = (
    "llvm/test/",
    "clang/test/",
    "llvm/unittests/",
    "clang/unittests/",
)
