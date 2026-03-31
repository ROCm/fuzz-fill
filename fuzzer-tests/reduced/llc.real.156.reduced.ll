target datalayout = "e-m:e-p:64:64-p1:64:64-p2:32:32-p3:32:32-p4:64:64-p5:32:32-p6:32:32-p7:160:256:256:32-p8:128:128:128:48-p9:192:256:256:32-i64:64-v16:16-v24:32-v32:32-v48:64-v96:128-v192:256-v256:256-v512:512-v1024:1024-v2048:2048-n32:64-S32-A5-G1-ni:7:8:9"
target triple = "amdgcn-amd-amdhsa"

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.start.p5(ptr addrspace(5) captures(none)) #0

define void @_Z8crc_initv(i32 %0) {
entry:
  br label %for.cond

for.cond:                                         ; preds = %for.body, %for.cond, %entry
  %cmp1 = icmp slt i32 %0, 0
  br i1 %cmp1, label %for.cond, label %BB

BB:                                               ; preds = %for.cond
  br i1 %cmp1, label %for.body, label %for.cond.cleanup

for.cond.cleanup:                                 ; preds = %BB
  ret void

for.body:                                         ; preds = %BB
  call void @llvm.lifetime.start.p5(ptr addrspace(5) poison)
  br label %for.cond
}

attributes #0 = { nocallback nofree nosync nounwind willreturn memory(argmem: readwrite) }
