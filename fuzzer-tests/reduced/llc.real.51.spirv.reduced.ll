target datalayout = "e-i64:64-v16:16-v24:32-v32:32-v48:64-v96:128-v192:256-v256:256-v512:512-v1024:1024-n32:64-S32-G1-P4-A0"
target triple = "spirv64-amd-amdhsa"

define spir_kernel void @type_selection_kernel() addrspace(4) {
entry:
  %call3 = call spir_func addrspace(4) ptr addrspace(4) inttoptr (i64 336 to ptr addrspace(4))(i64 0)
  ret void
}
