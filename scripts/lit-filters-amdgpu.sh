# Shared AMDGPU LIT --lit-filter prefixes for baseline coverage runs.
# Sourced by scripts/test_coverage_amdgpu_workflow1.sh and
# scripts/docker/pr-cov-gaps-detection.sh (default for amdgpu allowlist).

AMDGPU_LIT_FILTERS=(
    CodeGen/AMDGPU
    Analysis/*/AMDGPU
    Transforms/*/AMDGPU
    Verifier/*/AMDGPU
    Instrumentation/*/AMDGPU
    CodeGen/MIR/AMDGPU
    MachineVerifier/AMDGPU
    DebugInfo/AMDGPU
    MachineVerifier/*/AMDGPU
    tools/llvm-objdump/ELF/AMDGPU
    ThinLTO/AMDGPU
    LTO/AMDGPU
)
