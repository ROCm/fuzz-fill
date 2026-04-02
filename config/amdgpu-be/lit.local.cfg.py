# -*- Python -*-
import os

if not "AMDGPU" in config.root.targets:
    config.unsupported = True

# Forward these from the shell that runs llvm-lit into every test in this tree,
# but only if they are set (empty values are skipped). Edit the list as needed.
_env_from_host = (
    "UBSAN_OPTIONS",  # e.g. export LLVM_LIT_AMDGPU_EXAMPLE=1 for local runs
)
for _name in _env_from_host:
    _val = os.environ.get(_name)
    if _val:
        config.environment[_name] = _val
