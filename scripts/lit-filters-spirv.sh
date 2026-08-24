# Shared SPIRV llvm-lit --filter= regex fragments for baseline coverage runs.
# Sourced by scripts/lib/lit-filters.sh (via --backend-tests spirv) and referenced
# by scripts/docker/gap-finding-pr.sh for default spirv allowlist filters.

SPIRV_LIT_FILTERS=(
    CodeGen/SPIRV
    Transforms/[^/]+/SPIRV
)
