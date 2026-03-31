target datalayout = "e-i64:64-v16:16-v24:32-v32:32-v48:64-v96:128-v192:256-v256:256-v512:512-v1024:1024-n32:64-S32-G1-P4-A0"
target triple = "spirv64-amd-amdhsa"

define spir_func i32 @_Z13device_atexitPFvvE(ptr addrspace(4) %fn) addrspace(4) {
entry:
  ret i32 0
}

declare spir_func void @_Z10device_foov() addrspace(4)

define spir_kernel void @_Z11test_kernelv() addrspace(4) {
entry:
  %call = call spir_func addrspace(4) i32 @_Z13device_atexitPFvvE(ptr addrspace(4) @_Z10device_foov)
  ret void
}
