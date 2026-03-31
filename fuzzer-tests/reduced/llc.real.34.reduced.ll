target datalayout = "e-i64:64-v16:16-v24:32-v32:32-v48:64-v96:128-v192:256-v256:256-v512:512-v1024:1024-n32:64-S32-G1-P4-A0"
target triple = "spirv64-amd-amdhsa"

define spir_func <16 x i1> @__cxa_pure_virtual() addrspace(4) {
entry:
  %C = icmp ne <16 x i1> zeroinitializer, zeroinitializer
  ret <16 x i1> %C
}
