# Shared AMDGPU llvm-lit --filter= regex fragments for baseline coverage runs.
# Sourced by scripts/lib/lit-filters.sh (via --backend-tests amdgpu) and referenced
# by scripts/docker/gap-finding-pr.sh for default amdgpu allowlist filters.

AMDGPU_LIT_FILTERS=(
    CodeGen/AMDGPU
    Analysis/[^/]+/AMDGPU
    Transforms/[^/]+/AMDGPU
    Verifier/[^/]+/AMDGPU
    Instrumentation/[^/]+/AMDGPU
    CodeGen/MIR/AMDGPU
    MachineVerifier/AMDGPU
    DebugInfo/AMDGPU
    MachineVerifier/[^/]+/AMDGPU
    tools/llvm-objdump/ELF/AMDGPU
    ThinLTO/AMDGPU
    LTO/AMDGPU
)
