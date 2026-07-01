; Minimal AMDGPU IR for standalone `llc -o /dev/null` coverage runs.
; Triple matches typical AMDGPU fuzz-fill / llvm-lit setups.
target datalayout = "e-p:64:64-p1:64:64-p2:32:32-p3:32:32-p4:64:64-p5:32:32-p6:32:32-p7:160:256:256:32-p8:128:128:128:48-p9:192:256:256:32-i64:64-v16:16-v24:32-v48:64-v96:128-v192:256-v256:256-v512:512-v1024:1024-v2048:2048-n32:64-A5"
target triple = "amdgcn-amd-amdhsa"

define amdgpu_kernel void @empty() #0 {
entry:
  ret void
}

attributes #0 = { "amdgpu-flat-work-group-size"="1,1024" "uniform-work-group-size"="true" }
