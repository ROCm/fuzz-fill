# Shared AMDGPU llvm-lit --filter= regex fragments for baseline coverage runs.
# Sourced by scripts/gap-filling-amdgpu.sh and
# scripts/docker/gap-finding-pr.sh (default for amdgpu allowlist).

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
