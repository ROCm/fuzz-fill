; ModuleID = './llc.real.185.bc'
source_filename = "/amdgpu-dataset/llm-hip-tests/6ad3f791e7eb677394dc2f9edcbc39230c3d230d3d6c53dd88bd0db99b5d598d.hip"
target datalayout = "e-m:e-p:64:64-p1:64:64-p2:32:32-p3:32:32-p4:64:64-p5:32:32-p6:32:32-p7:160:256:256:32-p8:128:128:128:48-p9:192:256:256:32-i64:64-v16:16-v24:32-v32:32-v48:64-v96:128-v192:256-v256:256-v512:512-v1024:1024-v2048:2048-n32:64-S32-A5-G1-ni:7:8:9"
target triple = "amdgcn-amd-amdhsa"

%0 = type { i64, i64, i32, i32 }
%1 = type { [64 x [8 x i64]] }
%struct.__hip_builtin_threadIdx_t = type { i8 }
%struct.__hip_builtin_blockIdx_t = type { i8 }
%struct.__hip_builtin_blockDim_t = type { i8 }

$_ZN25__hip_builtin_threadIdx_t7__get_xEv = comdat any

$_Z13__syncthreadsv = comdat any

$_ZN24__hip_builtin_blockIdx_t7__get_xEv = comdat any

$_ZN24__hip_builtin_blockDim_t7__get_xEv = comdat any

$_Z9atomicAddPii = comdat any

@__const.__assert_fail.fmt = private unnamed_addr addrspace(4) constant [47 x i8] c"%s:%u: %s: Device-side assertion `%s' failed.\0A\00", align 16
@CRCTable = hidden addrspace(3) global [256 x i32] undef, align 16
@threadIdx = extern_weak dso_local protected addrspace(1) global %struct.__hip_builtin_threadIdx_t, align 1
@blockIdx = extern_weak dso_local protected addrspace(1) global %struct.__hip_builtin_blockIdx_t, align 1
@blockDim = extern_weak dso_local protected addrspace(1) global %struct.__hip_builtin_blockDim_t, align 1
@_ZZ15test_crc_kernelE9block_res = internal addrspace(3) global i32 undef, align 4
@.str = private unnamed_addr addrspace(4) constant [10 x i8] c"workgroup\00", align 1
@.str.1 = private unnamed_addr addrspace(4) constant [7 x i8] c"global\00", align 1
@.str.2 = private unnamed_addr addrspace(4) constant [6 x i8] c"local\00", align 1
@__hip_cuid_b312a08b1316ee1f = addrspace(1) global i8 0
@llvm.compiler.used = appending addrspace(1) global [1 x ptr] [ptr addrspacecast (ptr addrspace(1) @__hip_cuid_b312a08b1316ee1f to ptr)], section "llvm.metadata"
@__oclc_ISA_version = internal local_unnamed_addr addrspace(4) constant i32 12001, align 4
@__oclc_ABI_version = internal local_unnamed_addr addrspace(4) constant i32 600, align 4
@G = addrspace(1) global <16 x i16> splat (i16 32767)
@G.1 = addrspace(1) global <32 x i64> splat (i64 9223372036854775807)

; Function Attrs: convergent mustprogress noreturn nounwind
define weak void @__cxa_pure_virtual() #0 {
entry:
  call void @llvm.trap()
  unreachable
}

; Function Attrs: cold noreturn nounwind memory(inaccessiblemem: write)
declare void @llvm.trap() #1

; Function Attrs: convergent mustprogress noreturn nounwind
define weak void @__cxa_deleted_virtual() #0 {
entry:
  call void @llvm.trap()
  unreachable
}

; Function Attrs: convergent mustprogress noinline nounwind
define weak hidden void @__assert_fail(ptr noundef %assertion, ptr noundef %file, i32 noundef %line, ptr noundef %function) #2 {
entry:
  %assertion.addr = alloca ptr, align 8, addrspace(5)
  %file.addr = alloca ptr, align 8, addrspace(5)
  %line.addr = alloca i32, align 4, addrspace(5)
  %function.addr = alloca ptr, align 8, addrspace(5)
  %fmt = alloca [47 x i8], align 16, addrspace(5)
  %msg = alloca i64, align 8, addrspace(5)
  %len = alloca i32, align 4, addrspace(5)
  %tmp = alloca ptr, align 8, addrspace(5)
  %tmp6 = alloca ptr, align 8, addrspace(5)
  %tmp23 = alloca ptr, align 8, addrspace(5)
  %tmp38 = alloca ptr, align 8, addrspace(5)
  %assertion.addr.ascast = addrspacecast ptr addrspace(5) %assertion.addr to ptr
  %file.addr.ascast = addrspacecast ptr addrspace(5) %file.addr to ptr
  %line.addr.ascast = addrspacecast ptr addrspace(5) %line.addr to ptr
  %function.addr.ascast = addrspacecast ptr addrspace(5) %function.addr to ptr
  %fmt.ascast = addrspacecast ptr addrspace(5) %fmt to ptr
  %msg.ascast = addrspacecast ptr addrspace(5) %msg to ptr
  %len.ascast = addrspacecast ptr addrspace(5) %len to ptr
  %tmp.ascast = addrspacecast ptr addrspace(5) %tmp to ptr
  %tmp6.ascast = addrspacecast ptr addrspace(5) %tmp6 to ptr
  %tmp23.ascast = addrspacecast ptr addrspace(5) %tmp23 to ptr
  %tmp38.ascast = addrspacecast ptr addrspace(5) %tmp38 to ptr
  store ptr %assertion, ptr %assertion.addr.ascast, align 8, !tbaa !11
  store ptr %file, ptr %file.addr.ascast, align 8, !tbaa !11
  store i32 %line, ptr %line.addr.ascast, align 4, !tbaa !6
  store ptr %function, ptr %function.addr.ascast, align 8, !tbaa !11
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %fmt) #23
  call void @llvm.memcpy.p0.p4.i64(ptr align 16 %fmt.ascast, ptr addrspace(4) align 16 @__const.__assert_fail.fmt, i64 47, i1 false)
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %msg) #23
  %call = call i64 @__ockl_fprintf_stderr_begin() #24
  store i64 %call, ptr %msg.ascast, align 8, !tbaa !14
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %len) #23
  store i32 0, ptr %len.ascast, align 4, !tbaa !6
  br label %do.body

do.body:                                          ; preds = %entry
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %tmp) #23
  %arraydecay = getelementptr inbounds [47 x i8], ptr %fmt.ascast, i64 0, i64 0
  store ptr %arraydecay, ptr %tmp.ascast, align 8, !tbaa !11
  br label %while.cond

while.cond:                                       ; preds = %while.body, %do.body
  %0 = load ptr, ptr %tmp.ascast, align 8, !tbaa !11
  %incdec.ptr = getelementptr inbounds nuw i8, ptr %0, i32 1
  store ptr %incdec.ptr, ptr %tmp.ascast, align 8, !tbaa !11
  %1 = load i8, ptr %0, align 1, !tbaa !16
  %tobool = icmp ne i8 %1, 0
  br i1 %tobool, label %while.body, label %while.end

while.body:                                       ; preds = %while.cond
  br label %while.cond, !llvm.loop !17

while.end:                                        ; preds = %while.cond
  %2 = load ptr, ptr %tmp.ascast, align 8, !tbaa !11
  %arraydecay1 = getelementptr inbounds [47 x i8], ptr %fmt.ascast, i64 0, i64 0
  %sub.ptr.lhs.cast = ptrtoint ptr %2 to i64
  %sub.ptr.rhs.cast = ptrtoint ptr %arraydecay1 to i64
  %sub.ptr.sub = sub i64 %sub.ptr.lhs.cast, %sub.ptr.rhs.cast
  %conv = trunc i64 %sub.ptr.sub to i32
  store i32 %conv, ptr %len.ascast, align 4, !tbaa !6
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %tmp) #23
  br label %do.cond

do.cond:                                          ; preds = %while.end
  br label %do.end

do.end:                                           ; preds = %do.cond
  %3 = load i64, ptr %msg.ascast, align 8, !tbaa !14
  %arraydecay2 = getelementptr inbounds [47 x i8], ptr %fmt.ascast, i64 0, i64 0
  %4 = load i32, ptr %len.ascast, align 4, !tbaa !6
  %conv3 = sext i32 %4 to i64
  %call4 = call i64 @__ockl_fprintf_append_string_n(i64 noundef %3, ptr noundef %arraydecay2, i64 noundef %conv3, i32 noundef 0) #24
  store i64 %call4, ptr %msg.ascast, align 8, !tbaa !14
  br label %do.body5

do.body5:                                         ; preds = %do.end
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %tmp6) #23
  %5 = load ptr, ptr %file.addr.ascast, align 8, !tbaa !11
  store ptr %5, ptr %tmp6.ascast, align 8, !tbaa !11
  br label %while.cond7

while.cond7:                                      ; preds = %while.body10, %do.body5
  %6 = load ptr, ptr %tmp6.ascast, align 8, !tbaa !11
  %incdec.ptr8 = getelementptr inbounds nuw i8, ptr %6, i32 1
  store ptr %incdec.ptr8, ptr %tmp6.ascast, align 8, !tbaa !11
  %7 = load i8, ptr %6, align 1, !tbaa !16
  %tobool9 = icmp ne i8 %7, 0
  br i1 %tobool9, label %while.body10, label %while.end11

while.body10:                                     ; preds = %while.cond7
  br label %while.cond7, !llvm.loop !20

while.end11:                                      ; preds = %while.cond7
  %8 = load ptr, ptr %tmp6.ascast, align 8, !tbaa !11
  %9 = load ptr, ptr %file.addr.ascast, align 8, !tbaa !11
  %sub.ptr.lhs.cast12 = ptrtoint ptr %8 to i64
  %sub.ptr.rhs.cast13 = ptrtoint ptr %9 to i64
  %sub.ptr.sub14 = sub i64 %sub.ptr.lhs.cast12, %sub.ptr.rhs.cast13
  %conv15 = trunc i64 %sub.ptr.sub14 to i32
  store i32 %conv15, ptr %len.ascast, align 4, !tbaa !6
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %tmp6) #23
  br label %do.cond16

do.cond16:                                        ; preds = %while.end11
  br label %do.end17

do.end17:                                         ; preds = %do.cond16
  %10 = load i64, ptr %msg.ascast, align 8, !tbaa !14
  %11 = load ptr, ptr %file.addr.ascast, align 8, !tbaa !11
  %12 = load i32, ptr %len.ascast, align 4, !tbaa !6
  %conv18 = sext i32 %12 to i64
  %call19 = call i64 @__ockl_fprintf_append_string_n(i64 noundef %10, ptr noundef %11, i64 noundef %conv18, i32 noundef 0) #24
  store i64 %call19, ptr %msg.ascast, align 8, !tbaa !14
  %13 = load i64, ptr %msg.ascast, align 8, !tbaa !14
  %14 = load i32, ptr %line.addr.ascast, align 4, !tbaa !6
  %conv20 = zext i32 %14 to i64
  %call21 = call i64 @__ockl_fprintf_append_args(i64 noundef %13, i32 noundef 1, i64 noundef %conv20, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i32 noundef 0) #24
  store i64 %call21, ptr %msg.ascast, align 8, !tbaa !14
  br label %do.body22

do.body22:                                        ; preds = %do.end17
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %tmp23) #23
  %15 = load ptr, ptr %function.addr.ascast, align 8, !tbaa !11
  store ptr %15, ptr %tmp23.ascast, align 8, !tbaa !11
  br label %while.cond24

while.cond24:                                     ; preds = %while.body27, %do.body22
  %16 = load ptr, ptr %tmp23.ascast, align 8, !tbaa !11
  %incdec.ptr25 = getelementptr inbounds nuw i8, ptr %16, i32 1
  store ptr %incdec.ptr25, ptr %tmp23.ascast, align 8, !tbaa !11
  %17 = load i8, ptr %16, align 1, !tbaa !16
  %tobool26 = icmp ne i8 %17, 0
  br i1 %tobool26, label %while.body27, label %while.end28

while.body27:                                     ; preds = %while.cond24
  br label %while.cond24, !llvm.loop !21

while.end28:                                      ; preds = %while.cond24
  %18 = load ptr, ptr %tmp23.ascast, align 8, !tbaa !11
  %19 = load ptr, ptr %function.addr.ascast, align 8, !tbaa !11
  %sub.ptr.lhs.cast29 = ptrtoint ptr %18 to i64
  %sub.ptr.rhs.cast30 = ptrtoint ptr %19 to i64
  %sub.ptr.sub31 = sub i64 %sub.ptr.lhs.cast29, %sub.ptr.rhs.cast30
  %conv32 = trunc i64 %sub.ptr.sub31 to i32
  store i32 %conv32, ptr %len.ascast, align 4, !tbaa !6
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %tmp23) #23
  br label %do.cond33

do.cond33:                                        ; preds = %while.end28
  br label %do.end34

do.end34:                                         ; preds = %do.cond33
  %20 = load i64, ptr %msg.ascast, align 8, !tbaa !14
  %21 = load ptr, ptr %function.addr.ascast, align 8, !tbaa !11
  %22 = load i32, ptr %len.ascast, align 4, !tbaa !6
  %conv35 = sext i32 %22 to i64
  %call36 = call i64 @__ockl_fprintf_append_string_n(i64 noundef %20, ptr noundef %21, i64 noundef %conv35, i32 noundef 0) #24
  store i64 %call36, ptr %msg.ascast, align 8, !tbaa !14
  br label %do.body37

do.body37:                                        ; preds = %do.end34
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %tmp38) #23
  %23 = load ptr, ptr %assertion.addr.ascast, align 8, !tbaa !11
  store ptr %23, ptr %tmp38.ascast, align 8, !tbaa !11
  br label %while.cond39

while.cond39:                                     ; preds = %while.body42, %do.body37
  %24 = load ptr, ptr %tmp38.ascast, align 8, !tbaa !11
  %incdec.ptr40 = getelementptr inbounds nuw i8, ptr %24, i32 1
  store ptr %incdec.ptr40, ptr %tmp38.ascast, align 8, !tbaa !11
  %25 = load i8, ptr %24, align 1, !tbaa !16
  %tobool41 = icmp ne i8 %25, 0
  br i1 %tobool41, label %while.body42, label %while.end43

while.body42:                                     ; preds = %while.cond39
  br label %while.cond39, !llvm.loop !22

while.end43:                                      ; preds = %while.cond39
  %26 = load ptr, ptr %tmp38.ascast, align 8, !tbaa !11
  %27 = load ptr, ptr %assertion.addr.ascast, align 8, !tbaa !11
  %sub.ptr.lhs.cast44 = ptrtoint ptr %26 to i64
  %sub.ptr.rhs.cast45 = ptrtoint ptr %27 to i64
  %sub.ptr.sub46 = sub i64 %sub.ptr.lhs.cast44, %sub.ptr.rhs.cast45
  %conv47 = trunc i64 %sub.ptr.sub46 to i32
  store i32 %conv47, ptr %len.ascast, align 4, !tbaa !6
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %tmp38) #23
  br label %do.cond48

do.cond48:                                        ; preds = %while.end43
  br label %do.end49

do.end49:                                         ; preds = %do.cond48
  %28 = load i64, ptr %msg.ascast, align 8, !tbaa !14
  %29 = load ptr, ptr %assertion.addr.ascast, align 8, !tbaa !11
  %30 = load i32, ptr %len.ascast, align 4, !tbaa !6
  %conv50 = sext i32 %30 to i64
  %call51 = call i64 @__ockl_fprintf_append_string_n(i64 noundef %28, ptr noundef %29, i64 noundef %conv50, i32 noundef 1) #24
  call void @llvm.trap()
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %len) #23
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %msg) #23
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %fmt) #23
  ret void
}

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.start.p5(ptr addrspace(5) captures(none)) #3

; Function Attrs: nocallback nofree nounwind willreturn memory(argmem: readwrite)
declare void @llvm.memcpy.p0.p4.i64(ptr noalias writeonly captures(none), ptr addrspace(4) noalias readonly captures(none), i64, i1 immarg) #4

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.end.p5(ptr addrspace(5) captures(none)) #3

; Function Attrs: convergent mustprogress noinline nounwind
define weak hidden void @__assertfail() #2 {
entry:
  call void @llvm.trap()
  ret void
}

; Function Attrs: convergent mustprogress nounwind
define hidden void @_Z8crc_initv() #5 {
entry:
  %i = alloca i32, align 4, addrspace(5)
  %cleanup.dest.slot = alloca i32, align 4, addrspace(5)
  %crc = alloca i32, align 4, addrspace(5)
  %j = alloca i32, align 4, addrspace(5)
  %i.ascast = addrspacecast ptr addrspace(5) %i to ptr
  %cleanup.dest.slot.ascast = addrspacecast ptr addrspace(5) %cleanup.dest.slot to ptr
  %crc.ascast = addrspacecast ptr addrspace(5) %crc to ptr
  %j.ascast = addrspacecast ptr addrspace(5) %j to ptr
  %call = call noundef i32 @_ZN25__hip_builtin_threadIdx_t7__get_xEv() #24
  %cmp = icmp eq i32 %call, 0
  br i1 %cmp, label %if.then, label %if.end11

if.then:                                          ; preds = %entry
  br label %do.body

do.body:                                          ; preds = %if.then
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %i) #23
  store i32 0, ptr %i.ascast, align 4, !tbaa !6
  br label %for.cond

for.cond:                                         ; preds = %for.inc8, %do.body
  %0 = load i32, ptr %i.ascast, align 4, !tbaa !6
  %cmp1 = icmp slt i32 %0, 256
  br i1 %cmp1, label %for.body, label %for.cond.cleanup

for.cond.cleanup:                                 ; preds = %for.cond
  store i32 4, ptr %cleanup.dest.slot.ascast, align 4
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %i) #23
  br label %for.end10

for.body:                                         ; preds = %for.cond
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %crc) #23
  %1 = load i32, ptr %i.ascast, align 4, !tbaa !6
  store i32 %1, ptr %crc.ascast, align 4, !tbaa !6
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %j) #23
  store i32 0, ptr %j.ascast, align 4, !tbaa !6
  br label %for.cond2

for.cond2:                                        ; preds = %for.inc, %for.body
  %2 = load i32, ptr %j.ascast, align 4, !tbaa !6
  %cmp3 = icmp slt i32 %2, 8
  br i1 %cmp3, label %for.body5, label %for.cond.cleanup4

for.cond.cleanup4:                                ; preds = %for.cond2
  store i32 7, ptr %cleanup.dest.slot.ascast, align 4
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %j) #23
  br label %for.end

for.body5:                                        ; preds = %for.cond2
  %3 = load i32, ptr %crc.ascast, align 4, !tbaa !6
  %and = and i32 %3, 1
  %tobool = icmp ne i32 %and, 0
  br i1 %tobool, label %if.then6, label %if.else

if.then6:                                         ; preds = %for.body5
  %4 = load i32, ptr %crc.ascast, align 4, !tbaa !6
  %shr = lshr i32 %4, 1
  %xor = xor i32 %shr, 33800
  store i32 %xor, ptr %crc.ascast, align 4, !tbaa !6
  br label %if.end

if.else:                                          ; preds = %for.body5
  %5 = load i32, ptr %crc.ascast, align 4, !tbaa !6
  %shr7 = lshr i32 %5, 1
  store i32 %shr7, ptr %crc.ascast, align 4, !tbaa !6
  br label %if.end

if.end:                                           ; preds = %if.else, %if.then6
  br label %for.inc

for.inc:                                          ; preds = %if.end
  %6 = load i32, ptr %j.ascast, align 4, !tbaa !6
  %inc = add nsw i32 %6, 1
  store i32 %inc, ptr %j.ascast, align 4, !tbaa !6
  br label %for.cond2, !llvm.loop !23

for.end:                                          ; preds = %for.cond.cleanup4
  %7 = load i32, ptr %crc.ascast, align 4, !tbaa !6
  %8 = load i32, ptr %i.ascast, align 4, !tbaa !6
  %idxprom = sext i32 %8 to i64
  %arrayidx = getelementptr inbounds [256 x i32], ptr addrspacecast (ptr addrspace(3) @CRCTable to ptr), i64 0, i64 %idxprom
  store i32 %7, ptr %arrayidx, align 4, !tbaa !6
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %crc) #23
  br label %for.inc8

for.inc8:                                         ; preds = %for.end
  %9 = load i32, ptr %i.ascast, align 4, !tbaa !6
  %inc9 = add nsw i32 %9, 1
  store i32 %inc9, ptr %i.ascast, align 4, !tbaa !6
  br label %for.cond, !llvm.loop !24

for.end10:                                        ; preds = %for.cond.cleanup
  br label %do.end

do.end:                                           ; preds = %for.end10
  br label %if.end11

if.end11:                                         ; preds = %do.end, %entry
  call void @_Z13__syncthreadsv() #24
  ret void
}

; Function Attrs: alwaysinline convergent mustprogress nounwind
define linkonce_odr hidden noundef i32 @_ZN25__hip_builtin_threadIdx_t7__get_xEv() #6 comdat align 2 {
entry:
  %retval = alloca i32, align 4, addrspace(5)
  %retval.ascast = addrspacecast ptr addrspace(5) %retval to ptr
  %call = call noundef i32 @_ZL22__hip_get_thread_idx_xv() #24
  ret i32 %call
}

; Function Attrs: convergent inlinehint mustprogress nounwind
define linkonce_odr hidden void @_Z13__syncthreadsv() #7 comdat {
entry:
  call void @_ZL9__barrieri(i32 noundef 3) #24
  ret void
}

; Function Attrs: convergent mustprogress nounwind
define hidden noundef i32 @_Z9crc_tablejj(i32 noundef %crc_initval, i32 noundef %data) #5 {
entry:
  %retval = alloca i32, align 4, addrspace(5)
  %crc_initval.addr = alloca i32, align 4, addrspace(5)
  %data.addr = alloca i32, align 4, addrspace(5)
  %crc = alloca i32, align 4, addrspace(5)
  %i_ = alloca i32, align 4, addrspace(5)
  %cleanup.dest.slot = alloca i32, align 4, addrspace(5)
  %cleanup.dest.slot4 = alloca i32, align 4, addrspace(5)
  %retval.ascast = addrspacecast ptr addrspace(5) %retval to ptr
  %crc_initval.addr.ascast = addrspacecast ptr addrspace(5) %crc_initval.addr to ptr
  %data.addr.ascast = addrspacecast ptr addrspace(5) %data.addr to ptr
  %crc.ascast = addrspacecast ptr addrspace(5) %crc to ptr
  %i_.ascast = addrspacecast ptr addrspace(5) %i_ to ptr
  store i32 %crc_initval, ptr %crc_initval.addr.ascast, align 4, !tbaa !6
  store i32 %data, ptr %data.addr.ascast, align 4, !tbaa !6
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %crc) #23
  %0 = load i32, ptr %crc_initval.addr.ascast, align 4, !tbaa !6
  store i32 %0, ptr %crc.ascast, align 4, !tbaa !6
  br label %do.body

do.body:                                          ; preds = %entry
  call void @_Z8crc_initv() #24
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %i_) #23
  store i32 0, ptr %i_.ascast, align 4, !tbaa !6
  br label %for.cond

for.cond:                                         ; preds = %for.inc, %do.body
  %1 = load i32, ptr %i_.ascast, align 4, !tbaa !6
  %cmp = icmp slt i32 %1, 4
  br i1 %cmp, label %for.body, label %for.cond.cleanup

for.cond.cleanup:                                 ; preds = %for.cond
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %i_) #23
  br label %for.end

for.body:                                         ; preds = %for.cond
  %2 = load i32, ptr %crc.ascast, align 4, !tbaa !6
  %shr = lshr i32 %2, 8
  %3 = load i32, ptr %crc.ascast, align 4, !tbaa !6
  %4 = load i32, ptr %data.addr.ascast, align 4, !tbaa !6
  %and = and i32 %4, 255
  %xor = xor i32 %3, %and
  %and1 = and i32 %xor, 255
  %idxprom = zext i32 %and1 to i64
  %arrayidx = getelementptr inbounds nuw [256 x i32], ptr addrspacecast (ptr addrspace(3) @CRCTable to ptr), i64 0, i64 %idxprom
  %5 = load i32, ptr %arrayidx, align 4, !tbaa !6
  %xor2 = xor i32 %shr, %5
  store i32 %xor2, ptr %crc.ascast, align 4, !tbaa !6
  %6 = load i32, ptr %data.addr.ascast, align 4, !tbaa !6
  %shr3 = lshr i32 %6, 8
  store i32 %shr3, ptr %data.addr.ascast, align 4, !tbaa !6
  br label %for.inc

for.inc:                                          ; preds = %for.body
  %7 = load i32, ptr %i_.ascast, align 4, !tbaa !6
  %inc = add nsw i32 %7, 1
  store i32 %inc, ptr %i_.ascast, align 4, !tbaa !6
  br label %for.cond, !llvm.loop !25

for.end:                                          ; preds = %for.cond.cleanup
  br label %do.cond

do.cond:                                          ; preds = %for.end
  br label %do.end

do.end:                                           ; preds = %do.cond
  %8 = load i32, ptr %crc.ascast, align 4, !tbaa !6
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %crc) #23
  ret i32 %8
}

; Function Attrs: convergent mustprogress nounwind
define hidden noundef i32 @_Z8crc_loopjj(i32 noundef %crc_initval, i32 noundef %data) #5 {
entry:
  %retval = alloca i32, align 4, addrspace(5)
  %crc_initval.addr = alloca i32, align 4, addrspace(5)
  %data.addr = alloca i32, align 4, addrspace(5)
  %crc = alloca i32, align 4, addrspace(5)
  %i_ = alloca i32, align 4, addrspace(5)
  %cleanup.dest.slot = alloca i32, align 4, addrspace(5)
  %cleanup.dest.slot4 = alloca i32, align 4, addrspace(5)
  %retval.ascast = addrspacecast ptr addrspace(5) %retval to ptr
  %crc_initval.addr.ascast = addrspacecast ptr addrspace(5) %crc_initval.addr to ptr
  %data.addr.ascast = addrspacecast ptr addrspace(5) %data.addr to ptr
  %crc.ascast = addrspacecast ptr addrspace(5) %crc to ptr
  %i_.ascast = addrspacecast ptr addrspace(5) %i_ to ptr
  store i32 %crc_initval, ptr %crc_initval.addr.ascast, align 4, !tbaa !6
  store i32 %data, ptr %data.addr.ascast, align 4, !tbaa !6
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %crc) #23
  %0 = load i32, ptr %crc_initval.addr.ascast, align 4, !tbaa !6
  store i32 %0, ptr %crc.ascast, align 4, !tbaa !6
  br label %do.body

do.body:                                          ; preds = %entry
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %i_) #23
  store i32 0, ptr %i_.ascast, align 4, !tbaa !6
  br label %for.cond

for.cond:                                         ; preds = %for.inc, %do.body
  %1 = load i32, ptr %i_.ascast, align 4, !tbaa !6
  %cmp = icmp slt i32 %1, 4
  br i1 %cmp, label %for.body, label %for.cond.cleanup

for.cond.cleanup:                                 ; preds = %for.cond
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %i_) #23
  br label %for.end

for.body:                                         ; preds = %for.cond
  %2 = load i32, ptr %crc.ascast, align 4, !tbaa !6
  %3 = load i32, ptr %data.addr.ascast, align 4, !tbaa !6
  %xor = xor i32 %2, %3
  %and = and i32 %xor, 1
  %tobool = icmp ne i32 %and, 0
  br i1 %tobool, label %if.then, label %if.else

if.then:                                          ; preds = %for.body
  %4 = load i32, ptr %crc.ascast, align 4, !tbaa !6
  %shr = lshr i32 %4, 1
  %xor1 = xor i32 %shr, 33800
  store i32 %xor1, ptr %crc.ascast, align 4, !tbaa !6
  br label %if.end

if.else:                                          ; preds = %for.body
  %5 = load i32, ptr %crc.ascast, align 4, !tbaa !6
  %shr2 = lshr i32 %5, 1
  store i32 %shr2, ptr %crc.ascast, align 4, !tbaa !6
  br label %if.end

if.end:                                           ; preds = %if.else, %if.then
  %6 = load i32, ptr %data.addr.ascast, align 4, !tbaa !6
  %shr3 = lshr i32 %6, 1
  store i32 %shr3, ptr %data.addr.ascast, align 4, !tbaa !6
  br label %for.inc

for.inc:                                          ; preds = %if.end
  %7 = load i32, ptr %i_.ascast, align 4, !tbaa !6
  %inc = add nsw i32 %7, 1
  store i32 %inc, ptr %i_.ascast, align 4, !tbaa !6
  br label %for.cond, !llvm.loop !26

for.end:                                          ; preds = %for.cond.cleanup
  br label %do.cond

do.cond:                                          ; preds = %for.end
  br label %do.end

do.end:                                           ; preds = %do.cond
  %8 = load i32, ptr %crc.ascast, align 4, !tbaa !6
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %crc) #23
  ret i32 %8
}

; Function Attrs: convergent mustprogress nounwind
define hidden void @_Z13VERIFY_RESULTjjPi(i32 noundef %in_crc_init, i32 noundef %in_data, ptr noundef %res) #5 {
entry:
  %A = alloca <8 x half>, align 16, addrspace(5)
  store <8 x half> poison, ptr addrspace(5) %A, align 16
  %LGV2 = load <32 x i64>, ptr addrspace(1) @G.1, align 256
  %LGV = load <16 x i16>, ptr addrspace(1) @G, align 32
  %in_crc_init.addr = alloca i32, align 4, addrspace(5)
  %L1 = load <4 x half>, ptr addrspace(5) %in_crc_init.addr, align 8
  %in_data.addr = alloca i32, align 4, addrspace(5)
  %res.addr = alloca ptr, align 8, addrspace(5)
  %ct = alloca i32, align 4, addrspace(5)
  %cl = alloca i32, align 4, addrspace(5)
  %in_crc_init.addr.ascast = addrspacecast ptr addrspace(5) %in_crc_init.addr to ptr
  %L = load <4 x half>, ptr %in_crc_init.addr.ascast, align 8
  %in_data.addr.ascast = addrspacecast ptr addrspace(5) %in_data.addr to ptr
  %res.addr.ascast = addrspacecast ptr addrspace(5) %res.addr to ptr
  %ct.ascast = addrspacecast ptr addrspace(5) %ct to ptr
  %cl.ascast = addrspacecast ptr addrspace(5) %cl to ptr
  store i32 %in_crc_init, ptr %in_crc_init.addr.ascast, align 4, !tbaa !6
  store i32 %in_data, ptr %in_data.addr.ascast, align 4, !tbaa !6
  store ptr %res, ptr %res.addr.ascast, align 8, !tbaa !27
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %ct) #23
  %0 = load i32, ptr %in_crc_init.addr.ascast, align 4, !tbaa !6
  %1 = load i32, ptr %in_data.addr.ascast, align 4, !tbaa !6
  %call = call noundef i32 @_Z9crc_tablejj(i32 noundef %0, i32 noundef %1) #24
  store i32 %call, ptr %ct.ascast, align 4, !tbaa !6
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %cl) #23
  %2 = load i32, ptr %in_crc_init.addr.ascast, align 4, !tbaa !6
  %3 = load i32, ptr %in_data.addr.ascast, align 4, !tbaa !6
  %call1 = call noundef i32 @_Z8crc_loopjj(i32 noundef %2, i32 noundef %3) #24
  %C = call <8 x half> @f(<4 x half> splat (half 0xH7BFF), <16 x i16> %LGV, <4 x half> splat (half 0xH7C00), <32 x i64> %LGV2)
  store i32 %call1, ptr %cl.ascast, align 4, !tbaa !6
  %4 = load i32, ptr %ct.ascast, align 4, !tbaa !6
  %5 = load i32, ptr %cl.ascast, align 4, !tbaa !6
  %cmp = icmp ne i32 %4, %5
  store <8 x half> %C, ptr addrspace(5) %A, align 16
  br i1 %cmp, label %if.then, label %if.end

if.then:                                          ; preds = %entry
  %6 = load ptr, ptr %res.addr.ascast, align 8, !tbaa !27
  store i32 1, ptr %6, align 4, !tbaa !6
  br label %if.end

if.end:                                           ; preds = %if.then, %entry
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %cl) #23
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %ct) #23
  ret void
}

; Function Attrs: convergent mustprogress norecurse nounwind
define protected amdgpu_kernel void @test_crc_kernel(ptr addrspace(1) noundef %result.coerce) #8 {
entry:
  %result = alloca ptr, align 8, addrspace(5)
  %result.addr = alloca ptr, align 8, addrspace(5)
  %crc_initval = alloca i32, align 4, addrspace(5)
  %data = alloca i32, align 4, addrspace(5)
  %local_res = alloca i32, align 4, addrspace(5)
  %result.ascast = addrspacecast ptr addrspace(5) %result to ptr
  %result.addr.ascast = addrspacecast ptr addrspace(5) %result.addr to ptr
  %crc_initval.ascast = addrspacecast ptr addrspace(5) %crc_initval to ptr
  %data.ascast = addrspacecast ptr addrspace(5) %data to ptr
  %local_res.ascast = addrspacecast ptr addrspace(5) %local_res to ptr
  store ptr addrspace(1) %result.coerce, ptr %result.ascast, align 8
  %result1 = load ptr, ptr %result.ascast, align 8, !tbaa !27
  store ptr %result1, ptr %result.addr.ascast, align 8, !tbaa !27
  call void @_Z8crc_initv() #24
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %crc_initval) #23
  %call = call noundef i32 @_ZN25__hip_builtin_threadIdx_t7__get_xEv() #24
  %call2 = call noundef i32 @_ZN24__hip_builtin_blockIdx_t7__get_xEv() #24
  %call3 = call noundef i32 @_ZN24__hip_builtin_blockDim_t7__get_xEv() #24
  %mul = mul i32 %call2, %call3
  %add = add i32 %call, %mul
  %xor = xor i32 -1, %add
  store i32 %xor, ptr %crc_initval.ascast, align 4, !tbaa !6
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %data) #23
  %call4 = call noundef i32 @_ZN25__hip_builtin_threadIdx_t7__get_xEv() #24
  %mul5 = mul i32 %call4, 16843009
  %xor6 = xor i32 -1515870811, %mul5
  store i32 %xor6, ptr %data.ascast, align 4, !tbaa !6
  %call7 = call noundef i32 @_ZN25__hip_builtin_threadIdx_t7__get_xEv() #24
  %cmp = icmp eq i32 %call7, 0
  br i1 %cmp, label %if.then, label %if.end

if.then:                                          ; preds = %entry
  store i32 0, ptr addrspacecast (ptr addrspace(3) @_ZZ15test_crc_kernelE9block_res to ptr), align 4, !tbaa !6
  br label %if.end

if.end:                                           ; preds = %if.then, %entry
  call void @_Z13__syncthreadsv() #24
  call void @llvm.lifetime.start.p5(ptr addrspace(5) %local_res) #23
  store i32 0, ptr %local_res.ascast, align 4, !tbaa !6
  %0 = load i32, ptr %crc_initval.ascast, align 4, !tbaa !6
  %1 = load i32, ptr %data.ascast, align 4, !tbaa !6
  call void @_Z13VERIFY_RESULTjjPi(i32 noundef %0, i32 noundef %1, ptr noundef %local_res.ascast) #24
  %2 = load i32, ptr %local_res.ascast, align 4, !tbaa !6
  %cmp8 = icmp ne i32 %2, 0
  br i1 %cmp8, label %if.then9, label %if.end11

if.then9:                                         ; preds = %if.end
  %call10 = call noundef i32 @_Z9atomicAddPii(ptr noundef addrspacecast (ptr addrspace(3) @_ZZ15test_crc_kernelE9block_res to ptr), i32 noundef 1) #24
  br label %if.end11

if.end11:                                         ; preds = %if.then9, %if.end
  call void @_Z13__syncthreadsv() #24
  %call12 = call noundef i32 @_ZN25__hip_builtin_threadIdx_t7__get_xEv() #24
  %cmp13 = icmp eq i32 %call12, 0
  br i1 %cmp13, label %if.then14, label %if.end16

if.then14:                                        ; preds = %if.end11
  %3 = load ptr, ptr %result.addr.ascast, align 8, !tbaa !27
  %4 = load i32, ptr addrspacecast (ptr addrspace(3) @_ZZ15test_crc_kernelE9block_res to ptr), align 4, !tbaa !6
  %call15 = call noundef i32 @_Z9atomicAddPii(ptr noundef %3, i32 noundef %4) #24
  br label %if.end16

if.end16:                                         ; preds = %if.then14, %if.end11
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %local_res) #23
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %data) #23
  call void @llvm.lifetime.end.p5(ptr addrspace(5) %crc_initval) #23
  ret void
}

; Function Attrs: alwaysinline convergent mustprogress nounwind
define linkonce_odr hidden noundef i32 @_ZN24__hip_builtin_blockIdx_t7__get_xEv() #6 comdat align 2 {
entry:
  %retval = alloca i32, align 4, addrspace(5)
  %retval.ascast = addrspacecast ptr addrspace(5) %retval to ptr
  %call = call noundef i32 @_ZL21__hip_get_block_idx_xv() #24
  ret i32 %call
}

; Function Attrs: alwaysinline convergent mustprogress nounwind
define linkonce_odr hidden noundef i32 @_ZN24__hip_builtin_blockDim_t7__get_xEv() #6 comdat align 2 {
entry:
  %retval = alloca i32, align 4, addrspace(5)
  %retval.ascast = addrspacecast ptr addrspace(5) %retval to ptr
  %call = call noundef i32 @_ZL21__hip_get_block_dim_xv() #24
  ret i32 %call
}

; Function Attrs: convergent inlinehint mustprogress nounwind
define linkonce_odr hidden noundef i32 @_Z9atomicAddPii(ptr noundef %address, i32 noundef %val) #7 comdat {
entry:
  %retval = alloca i32, align 4, addrspace(5)
  %address.addr = alloca ptr, align 8, addrspace(5)
  %val.addr = alloca i32, align 4, addrspace(5)
  %.atomictmp = alloca i32, align 4, addrspace(5)
  %atomic-temp = alloca i32, align 4, addrspace(5)
  %retval.ascast = addrspacecast ptr addrspace(5) %retval to ptr
  %address.addr.ascast = addrspacecast ptr addrspace(5) %address.addr to ptr
  %val.addr.ascast = addrspacecast ptr addrspace(5) %val.addr to ptr
  %.atomictmp.ascast = addrspacecast ptr addrspace(5) %.atomictmp to ptr
  %atomic-temp.ascast = addrspacecast ptr addrspace(5) %atomic-temp to ptr
  store ptr %address, ptr %address.addr.ascast, align 8, !tbaa !27
  store i32 %val, ptr %val.addr.ascast, align 4, !tbaa !6
  %0 = load ptr, ptr %address.addr.ascast, align 8, !tbaa !27
  %1 = load i32, ptr %val.addr.ascast, align 4, !tbaa !6
  store i32 %1, ptr %.atomictmp.ascast, align 4, !tbaa !6
  %2 = load i32, ptr %.atomictmp.ascast, align 4
  %3 = atomicrmw add ptr %0, i32 %2 syncscope("agent") monotonic, align 4, !noalias.addrspace !29, !amdgpu.no.fine.grained.memory !30, !amdgpu.no.remote.memory !30
  store i32 %3, ptr %atomic-temp.ascast, align 4
  %4 = load i32, ptr %atomic-temp.ascast, align 4, !tbaa !6
  ret i32 %4
}

; Function Attrs: alwaysinline convergent mustprogress nounwind
define internal noundef i32 @_ZL22__hip_get_thread_idx_xv() #6 {
entry:
  %retval = alloca i32, align 4, addrspace(5)
  %retval.ascast = addrspacecast ptr addrspace(5) %retval to ptr
  %call = call i64 @__ockl_get_local_id(i32 noundef 0) #25
  %conv = trunc i64 %call to i32
  ret i32 %conv
}

; Function Attrs: convergent inlinehint mustprogress nounwind
define internal void @_ZL9__barrieri(i32 noundef %n) #7 {
entry:
  %n.addr = alloca i32, align 4, addrspace(5)
  %n.addr.ascast = addrspacecast ptr addrspace(5) %n.addr to ptr
  store i32 %n, ptr %n.addr.ascast, align 4, !tbaa !6
  %0 = load i32, ptr %n.addr.ascast, align 4, !tbaa !6
  call void @_ZL20__work_group_barrierj(i32 noundef %0) #24
  ret void
}

; Function Attrs: convergent inlinehint mustprogress nounwind
define internal void @_ZL20__work_group_barrierj(i32 noundef %flags) #7 {
entry:
  %flags.addr = alloca i32, align 4, addrspace(5)
  %flags.addr.ascast = addrspacecast ptr addrspace(5) %flags.addr to ptr
  store i32 %flags, ptr %flags.addr.ascast, align 4, !tbaa !6
  %0 = load i32, ptr %flags.addr.ascast, align 4, !tbaa !6
  %cmp = icmp eq i32 %0, 3
  br i1 %cmp, label %if.then, label %if.else

if.then:                                          ; preds = %entry
  fence syncscope("workgroup") release
  call void @llvm.amdgcn.s.barrier()
  fence syncscope("workgroup") acquire
  br label %if.end8

if.else:                                          ; preds = %entry
  %1 = load i32, ptr %flags.addr.ascast, align 4, !tbaa !6
  %and = and i32 %1, 2
  %tobool = icmp ne i32 %and, 0
  br i1 %tobool, label %if.then1, label %if.else2

if.then1:                                         ; preds = %if.else
  fence syncscope("workgroup") release, !mmra !31
  call void @llvm.amdgcn.s.barrier()
  fence syncscope("workgroup") acquire, !mmra !31
  br label %if.end7

if.else2:                                         ; preds = %if.else
  %2 = load i32, ptr %flags.addr.ascast, align 4, !tbaa !6
  %and3 = and i32 %2, 1
  %tobool4 = icmp ne i32 %and3, 0
  br i1 %tobool4, label %if.then5, label %if.else6

if.then5:                                         ; preds = %if.else2
  fence syncscope("workgroup") release, !mmra !32
  call void @llvm.amdgcn.s.barrier()
  fence syncscope("workgroup") acquire, !mmra !32
  br label %if.end

if.else6:                                         ; preds = %if.else2
  call void @llvm.amdgcn.s.barrier()
  br label %if.end

if.end:                                           ; preds = %if.else6, %if.then5
  br label %if.end7

if.end7:                                          ; preds = %if.end, %if.then1
  br label %if.end8

if.end8:                                          ; preds = %if.end7, %if.then
  ret void
}

; Function Attrs: convergent nocallback nofree nounwind willreturn
declare void @llvm.amdgcn.s.barrier() #9

; Function Attrs: alwaysinline convergent mustprogress nounwind
define internal noundef i32 @_ZL21__hip_get_block_idx_xv() #6 {
entry:
  %retval = alloca i32, align 4, addrspace(5)
  %retval.ascast = addrspacecast ptr addrspace(5) %retval to ptr
  %call = call i64 @__ockl_get_group_id(i32 noundef 0) #25
  %conv = trunc i64 %call to i32
  ret i32 %conv
}

; Function Attrs: alwaysinline convergent mustprogress nounwind
define internal noundef i32 @_ZL21__hip_get_block_dim_xv() #6 {
entry:
  %retval = alloca i32, align 4, addrspace(5)
  %retval.ascast = addrspacecast ptr addrspace(5) %retval to ptr
  %call = call i64 @__ockl_get_local_size(i32 noundef 0) #25
  %conv = trunc i64 %call to i32
  ret i32 %conv
}

; Function Attrs: convergent mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define internal range(i64 0, 1024) i64 @__ockl_get_local_id(i32 noundef %0) #10 {
  switch i32 %0, label %8 [
    i32 0, label %2
    i32 1, label %4
    i32 2, label %6
  ]

2:                                                ; preds = %1
  %3 = tail call noundef range(i32 0, 1024) i32 @llvm.amdgcn.workitem.id.x()
  br label %8

4:                                                ; preds = %1
  %5 = tail call noundef range(i32 0, 1024) i32 @llvm.amdgcn.workitem.id.y()
  br label %8

6:                                                ; preds = %1
  %7 = tail call noundef range(i32 0, 1024) i32 @llvm.amdgcn.workitem.id.z()
  br label %8

8:                                                ; preds = %6, %4, %2, %1
  %9 = phi i32 [ %7, %6 ], [ %5, %4 ], [ %3, %2 ], [ 0, %1 ]
  %10 = zext nneg i32 %9 to i64
  ret i64 %10
}

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare noundef range(i32 0, 1024) i32 @llvm.amdgcn.workitem.id.x() #11

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare noundef range(i32 0, 1024) i32 @llvm.amdgcn.workitem.id.y() #11

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare noundef range(i32 0, 1024) i32 @llvm.amdgcn.workitem.id.z() #11

; Function Attrs: convergent norecurse nounwind
define internal i64 @__ockl_fprintf_stderr_begin() #12 {
  %1 = tail call <2 x i64> @__ockl_hostcall_preview(i32 noundef 2, i64 noundef 33, i64 noundef 1, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0) #24
  %2 = extractelement <2 x i64> %1, i64 0
  ret i64 %2
}

; Function Attrs: cold convergent norecurse nounwind
define internal <2 x i64> @__ockl_hostcall_preview(i32 noundef %0, i64 noundef %1, i64 noundef %2, i64 noundef %3, i64 noundef %4, i64 noundef %5, i64 noundef %6, i64 noundef %7, i64 noundef %8) local_unnamed_addr #13 {
  %10 = load i32, ptr addrspace(4) @__oclc_ABI_version, align 4, !tbaa !33
  %11 = icmp slt i32 %10, 500
  %12 = tail call ptr addrspace(4) @llvm.amdgcn.implicitarg.ptr()
  %13 = select i1 %11, i64 24, i64 80
  %14 = getelementptr inbounds nuw i8, ptr addrspace(4) %12, i64 %13
  %15 = load i64, ptr addrspace(4) %14, align 8, !tbaa !37
  %16 = inttoptr i64 %15 to ptr addrspace(1)
  %17 = addrspacecast ptr addrspace(1) %16 to ptr
  %18 = tail call <2 x i64> @__ockl_hostcall_internal(ptr noundef %17, i32 noundef %0, i64 noundef %1, i64 noundef %2, i64 noundef %3, i64 noundef %4, i64 noundef %5, i64 noundef %6, i64 noundef %7, i64 noundef %8) #26
  ret <2 x i64> %18
}

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare noundef align 4 ptr addrspace(4) @llvm.amdgcn.implicitarg.ptr() #11

; Function Attrs: convergent norecurse nounwind
define internal <2 x i64> @__ockl_hostcall_internal(ptr noundef captures(none) %0, i32 noundef %1, i64 noundef %2, i64 noundef %3, i64 noundef %4, i64 noundef %5, i64 noundef %6, i64 noundef %7, i64 noundef %8, i64 noundef %9) local_unnamed_addr #12 {
  %11 = tail call i32 @__ockl_lane_u32() #24
  %12 = tail call i32 @llvm.amdgcn.readfirstlane.i32(i32 %11)
  %13 = addrspacecast ptr %0 to ptr addrspace(1)
  %14 = icmp eq i32 %11, %12
  br i1 %14, label %15, label %37

15:                                               ; preds = %10
  %16 = getelementptr inbounds nuw i8, ptr addrspace(1) %13, i64 24
  %17 = load atomic i64, ptr addrspace(1) %16 syncscope("one-as") acquire, align 8
  %18 = getelementptr i8, ptr addrspace(1) %13, i64 40
  %19 = load ptr addrspace(1), ptr addrspace(1) %13, align 8, !tbaa !39
  %20 = load i64, ptr addrspace(1) %18, align 8, !tbaa !43
  %21 = and i64 %20, %17
  %22 = getelementptr inbounds nuw %0, ptr addrspace(1) %19, i64 %21
  %23 = load atomic i64, ptr addrspace(1) %22 syncscope("one-as") monotonic, align 8
  %24 = cmpxchg ptr addrspace(1) %16, i64 %17, i64 %23 syncscope("one-as") acquire monotonic, align 8
  %25 = extractvalue { i64, i1 } %24, 1
  %26 = extractvalue { i64, i1 } %24, 0
  br i1 %25, label %37, label %27

27:                                               ; preds = %27, %15
  %28 = phi i64 [ %36, %27 ], [ %26, %15 ]
  tail call void @llvm.amdgcn.s.sleep(i32 1)
  %29 = load ptr addrspace(1), ptr addrspace(1) %13, align 8, !tbaa !39
  %30 = load i64, ptr addrspace(1) %18, align 8, !tbaa !43
  %31 = and i64 %30, %28
  %32 = getelementptr inbounds nuw %0, ptr addrspace(1) %29, i64 %31
  %33 = load atomic i64, ptr addrspace(1) %32 syncscope("one-as") monotonic, align 8
  %34 = cmpxchg ptr addrspace(1) %16, i64 %28, i64 %33 syncscope("one-as") acquire monotonic, align 8
  %35 = extractvalue { i64, i1 } %34, 1
  %36 = extractvalue { i64, i1 } %34, 0
  br i1 %35, label %37, label %27

37:                                               ; preds = %27, %15, %10
  %38 = phi i64 [ 0, %10 ], [ %26, %15 ], [ %36, %27 ]
  %39 = tail call i64 @llvm.amdgcn.readfirstlane.i64(i64 %38)
  %40 = load ptr addrspace(1), ptr addrspace(1) %13, align 8, !tbaa !39
  %41 = getelementptr i8, ptr addrspace(1) %13, i64 40
  %42 = load i64, ptr addrspace(1) %41, align 8, !tbaa !43
  %43 = and i64 %42, %39
  %44 = getelementptr inbounds nuw %0, ptr addrspace(1) %40, i64 %43
  %45 = getelementptr i8, ptr addrspace(1) %13, i64 8
  %46 = load ptr addrspace(1), ptr addrspace(1) %45, align 8, !tbaa !44
  %47 = getelementptr inbounds nuw %1, ptr addrspace(1) %46, i64 %43
  %48 = tail call i64 @llvm.amdgcn.ballot.i64(i1 true)
  br i1 %14, label %49, label %53

49:                                               ; preds = %37
  %50 = getelementptr inbounds nuw i8, ptr addrspace(1) %44, i64 16
  %51 = getelementptr inbounds nuw i8, ptr addrspace(1) %44, i64 8
  %52 = getelementptr inbounds nuw i8, ptr addrspace(1) %44, i64 20
  store i32 %1, ptr addrspace(1) %50, align 8, !tbaa !45
  store i64 %48, ptr addrspace(1) %51, align 8, !tbaa !47
  store i32 1, ptr addrspace(1) %52, align 4, !tbaa !48
  br label %53

53:                                               ; preds = %49, %37
  %54 = zext i32 %11 to i64
  %55 = getelementptr inbounds nuw [64 x [8 x i64]], ptr addrspace(1) %47, i64 0, i64 %54
  store i64 %2, ptr addrspace(1) %55, align 8, !tbaa !37
  %56 = getelementptr inbounds nuw i8, ptr addrspace(1) %55, i64 8
  store i64 %3, ptr addrspace(1) %56, align 8, !tbaa !37
  %57 = getelementptr inbounds nuw i8, ptr addrspace(1) %55, i64 16
  store i64 %4, ptr addrspace(1) %57, align 8, !tbaa !37
  %58 = getelementptr inbounds nuw i8, ptr addrspace(1) %55, i64 24
  store i64 %5, ptr addrspace(1) %58, align 8, !tbaa !37
  %59 = getelementptr inbounds nuw i8, ptr addrspace(1) %55, i64 32
  store i64 %6, ptr addrspace(1) %59, align 8, !tbaa !37
  %60 = getelementptr inbounds nuw i8, ptr addrspace(1) %55, i64 40
  store i64 %7, ptr addrspace(1) %60, align 8, !tbaa !37
  %61 = getelementptr inbounds nuw i8, ptr addrspace(1) %55, i64 48
  store i64 %8, ptr addrspace(1) %61, align 8, !tbaa !37
  %62 = getelementptr inbounds nuw i8, ptr addrspace(1) %55, i64 56
  store i64 %9, ptr addrspace(1) %62, align 8, !tbaa !37
  br i1 %14, label %63, label %79

63:                                               ; preds = %53
  %64 = getelementptr inbounds nuw i8, ptr addrspace(1) %13, i64 32
  %65 = load atomic i64, ptr addrspace(1) %64 syncscope("one-as") monotonic, align 8
  %66 = load i64, ptr addrspace(1) %41, align 8, !tbaa !43
  %67 = and i64 %66, %39
  %68 = getelementptr inbounds nuw %0, ptr addrspace(1) %40, i64 %67
  store i64 %65, ptr addrspace(1) %68, align 8, !tbaa !49
  %69 = cmpxchg ptr addrspace(1) %64, i64 %65, i64 %39 syncscope("one-as") release monotonic, align 8
  %70 = extractvalue { i64, i1 } %69, 1
  br i1 %70, label %76, label %71

71:                                               ; preds = %71, %63
  %72 = phi { i64, i1 } [ %74, %71 ], [ %69, %63 ]
  %73 = extractvalue { i64, i1 } %72, 0
  tail call void @llvm.amdgcn.s.sleep(i32 1)
  store i64 %73, ptr addrspace(1) %68, align 8, !tbaa !49
  %74 = cmpxchg ptr addrspace(1) %64, i64 %73, i64 %39 syncscope("one-as") release monotonic, align 8
  %75 = extractvalue { i64, i1 } %74, 1
  br i1 %75, label %76, label %71

76:                                               ; preds = %71, %63
  %77 = getelementptr inbounds nuw i8, ptr addrspace(1) %13, i64 16
  %78 = load i64, ptr addrspace(1) %77, align 8
  tail call void @__ockl_hsa_signal_add(i64 %78, i64 noundef 1, i32 noundef 3) #24
  br label %79

79:                                               ; preds = %76, %53
  %80 = getelementptr inbounds nuw i8, ptr addrspace(1) %44, i64 20
  br label %81

81:                                               ; preds = %89, %79
  br i1 %14, label %82, label %85

82:                                               ; preds = %81
  %83 = load atomic i32, ptr addrspace(1) %80 syncscope("one-as") acquire, align 4
  %84 = and i32 %83, 1
  br label %85

85:                                               ; preds = %82, %81
  %86 = phi i32 [ %84, %82 ], [ 1, %81 ]
  %87 = tail call i32 @llvm.amdgcn.readfirstlane.i32(i32 %86)
  %88 = icmp eq i32 %87, 0
  br i1 %88, label %90, label %89

89:                                               ; preds = %85
  tail call void @llvm.amdgcn.s.sleep(i32 1)
  br label %81

90:                                               ; preds = %85
  %91 = load i64, ptr addrspace(1) %55, align 8, !tbaa !37
  %92 = load i64, ptr addrspace(1) %56, align 8, !tbaa !37
  br i1 %14, label %93, label %111

93:                                               ; preds = %90
  %94 = load i64, ptr addrspace(1) %41, align 8, !tbaa !43
  %95 = add i64 %94, 1
  %96 = add i64 %95, %39
  %97 = icmp eq i64 %96, 0
  %98 = select i1 %97, i64 %95, i64 %96
  %99 = getelementptr inbounds nuw i8, ptr addrspace(1) %13, i64 24
  %100 = load atomic i64, ptr addrspace(1) %99 syncscope("one-as") monotonic, align 8
  %101 = load ptr addrspace(1), ptr addrspace(1) %13, align 8, !tbaa !39
  %102 = and i64 %98, %94
  %103 = getelementptr inbounds nuw %0, ptr addrspace(1) %101, i64 %102
  store i64 %100, ptr addrspace(1) %103, align 8, !tbaa !49
  %104 = cmpxchg ptr addrspace(1) %99, i64 %100, i64 %98 syncscope("one-as") release monotonic, align 8
  %105 = extractvalue { i64, i1 } %104, 1
  br i1 %105, label %111, label %106

106:                                              ; preds = %106, %93
  %107 = phi { i64, i1 } [ %109, %106 ], [ %104, %93 ]
  %108 = extractvalue { i64, i1 } %107, 0
  tail call void @llvm.amdgcn.s.sleep(i32 1)
  store i64 %108, ptr addrspace(1) %103, align 8, !tbaa !49
  %109 = cmpxchg ptr addrspace(1) %99, i64 %108, i64 %98 syncscope("one-as") release monotonic, align 8
  %110 = extractvalue { i64, i1 } %109, 1
  br i1 %110, label %111, label %106

111:                                              ; preds = %106, %93, %90
  %112 = insertelement <2 x i64> poison, i64 %91, i64 0
  %113 = insertelement <2 x i64> %112, i64 %92, i64 1
  ret <2 x i64> %113
}

; Function Attrs: alwaysinline convergent mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define internal i32 @__ockl_lane_u32() local_unnamed_addr #14 {
  %1 = tail call i32 @llvm.amdgcn.mbcnt.lo(i32 -1, i32 0)
  %2 = tail call i32 @llvm.amdgcn.mbcnt.hi(i32 -1, i32 %1)
  ret i32 %2
}

; Function Attrs: convergent nocallback nocreateundeforpoison nofree nounwind willreturn memory(none)
declare i32 @llvm.amdgcn.readfirstlane.i32(i32) #15

; Function Attrs: nocallback nofree nosync nounwind willreturn
declare void @llvm.amdgcn.s.sleep(i32 immarg) #16

; Function Attrs: convergent nocallback nocreateundeforpoison nofree nounwind willreturn memory(none)
declare i64 @llvm.amdgcn.readfirstlane.i64(i64) #15

; Function Attrs: convergent nocallback nocreateundeforpoison nofree nounwind willreturn memory(none)
declare i64 @llvm.amdgcn.ballot.i64(i1) #15

; Function Attrs: convergent norecurse nounwind
define internal void @__ockl_hsa_signal_add(i64 %0, i64 noundef %1, i32 noundef %2) local_unnamed_addr #17 {
  %4 = inttoptr i64 %0 to ptr addrspace(1)
  %5 = getelementptr inbounds nuw i8, ptr addrspace(1) %4, i64 8
  switch i32 %2, label %6 [
    i32 1, label %8
    i32 2, label %8
    i32 3, label %10
    i32 4, label %12
    i32 5, label %14
  ]

6:                                                ; preds = %3
  %7 = atomicrmw add ptr addrspace(1) %5, i64 %1 syncscope("one-as") monotonic, align 8
  br label %16

8:                                                ; preds = %3, %3
  %9 = atomicrmw add ptr addrspace(1) %5, i64 %1 syncscope("one-as") acquire, align 8
  br label %16

10:                                               ; preds = %3
  %11 = atomicrmw add ptr addrspace(1) %5, i64 %1 syncscope("one-as") release, align 8
  br label %16

12:                                               ; preds = %3
  %13 = atomicrmw add ptr addrspace(1) %5, i64 %1 syncscope("one-as") acq_rel, align 8
  br label %16

14:                                               ; preds = %3
  %15 = atomicrmw add ptr addrspace(1) %5, i64 %1 seq_cst, align 8
  br label %16

16:                                               ; preds = %14, %12, %10, %8, %6
  %17 = getelementptr inbounds nuw i8, ptr addrspace(1) %4, i64 16
  %18 = load i64, ptr addrspace(1) %17, align 16, !tbaa !50
  %19 = icmp eq i64 %18, 0
  br i1 %19, label %34, label %20

20:                                               ; preds = %16
  %21 = inttoptr i64 %18 to ptr addrspace(1)
  %22 = getelementptr inbounds nuw i8, ptr addrspace(1) %4, i64 24
  %23 = load i32, ptr addrspace(1) %22, align 8, !tbaa !52
  %24 = zext i32 %23 to i64
  store atomic i64 %24, ptr addrspace(1) %21 syncscope("one-as") release, align 8
  %25 = load i32, ptr addrspace(4) @__oclc_ISA_version, align 4, !tbaa !33
  %26 = icmp slt i32 %25, 9000
  %27 = icmp samesign ult i32 %25, 10000
  %28 = icmp samesign ult i32 %25, 11000
  %29 = select i1 %28, i32 8388607, i32 16777215
  %30 = select i1 %27, i32 16777215, i32 %29
  %31 = select i1 %26, i32 255, i32 %30
  %32 = and i32 %31, %23
  %33 = tail call i32 @llvm.amdgcn.readfirstlane.i32(i32 %32)
  tail call void @llvm.amdgcn.s.sendmsg(i32 1, i32 %33)
  br label %34

34:                                               ; preds = %20, %16
  ret void
}

; Function Attrs: nocallback nounwind willreturn
declare void @llvm.amdgcn.s.sendmsg(i32 immarg, i32) #18

; Function Attrs: nocallback nocreateundeforpoison nofree nosync nounwind willreturn memory(none)
declare i32 @llvm.amdgcn.mbcnt.lo(i32, i32) #19

; Function Attrs: nocallback nocreateundeforpoison nofree nosync nounwind willreturn memory(none)
declare i32 @llvm.amdgcn.mbcnt.hi(i32, i32) #19

; Function Attrs: convergent norecurse nounwind
define internal i64 @__ockl_fprintf_append_args(i64 noundef %0, i32 noundef %1, i64 noundef %2, i64 noundef %3, i64 noundef %4, i64 noundef %5, i64 noundef %6, i64 noundef %7, i64 noundef %8, i32 noundef %9) #12 {
  %11 = icmp eq i32 %9, 0
  %12 = or i64 %0, 2
  %13 = select i1 %11, i64 %0, i64 %12
  %14 = and i64 %13, -225
  %15 = zext i32 %1 to i64
  %16 = shl nuw nsw i64 %15, 5
  %17 = or i64 %14, %16
  %18 = tail call <2 x i64> @__ockl_hostcall_preview(i32 noundef 2, i64 noundef %17, i64 noundef %2, i64 noundef %3, i64 noundef %4, i64 noundef %5, i64 noundef %6, i64 noundef %7, i64 noundef %8) #24
  %19 = extractelement <2 x i64> %18, i64 0
  ret i64 %19
}

; Function Attrs: convergent norecurse nounwind
define internal i64 @__ockl_fprintf_append_string_n(i64 noundef %0, ptr noundef readonly %1, i64 noundef %2, i32 noundef %3) #12 {
  %5 = icmp eq i32 %3, 0
  %6 = or i64 %0, 2
  %7 = select i1 %5, i64 %0, i64 %6
  %8 = icmp eq ptr %1, null
  br i1 %8, label %9, label %13

9:                                                ; preds = %4
  %10 = and i64 %7, -225
  %11 = or disjoint i64 %10, 32
  %12 = tail call <2 x i64> @__ockl_hostcall_preview(i32 noundef 2, i64 noundef %11, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0) #24
  br label %452

13:                                               ; preds = %4
  %14 = and i64 %7, 2
  %15 = and i64 %7, -3
  %16 = insertelement <2 x i64> <i64 poison, i64 0>, i64 %15, i64 0
  br label %17

17:                                               ; preds = %440, %13
  %18 = phi i64 [ %2, %13 ], [ %449, %440 ]
  %19 = phi ptr [ %1, %13 ], [ %450, %440 ]
  %20 = phi <2 x i64> [ %16, %13 ], [ %448, %440 ]
  %21 = icmp ugt i64 %18, 56
  %22 = extractelement <2 x i64> %20, i64 0
  %23 = tail call i64 @llvm.umin.i64(i64 %18, i64 56)
  %24 = trunc nuw nsw i64 %23 to i32
  %25 = select i1 %21, i64 0, i64 %14
  %26 = icmp ugt i64 %18, 7
  br i1 %26, label %29, label %27

27:                                               ; preds = %17
  %28 = icmp eq i64 %18, 0
  br i1 %28, label %82, label %69

29:                                               ; preds = %17
  %30 = load i8, ptr %19, align 1, !tbaa !53
  %31 = zext i8 %30 to i64
  %32 = getelementptr inbounds nuw i8, ptr %19, i64 1
  %33 = load i8, ptr %32, align 1, !tbaa !53
  %34 = zext i8 %33 to i64
  %35 = shl nuw nsw i64 %34, 8
  %36 = or disjoint i64 %35, %31
  %37 = getelementptr inbounds nuw i8, ptr %19, i64 2
  %38 = load i8, ptr %37, align 1, !tbaa !53
  %39 = zext i8 %38 to i64
  %40 = shl nuw nsw i64 %39, 16
  %41 = or disjoint i64 %36, %40
  %42 = getelementptr inbounds nuw i8, ptr %19, i64 3
  %43 = load i8, ptr %42, align 1, !tbaa !53
  %44 = zext i8 %43 to i64
  %45 = shl nuw nsw i64 %44, 24
  %46 = or disjoint i64 %41, %45
  %47 = getelementptr inbounds nuw i8, ptr %19, i64 4
  %48 = load i8, ptr %47, align 1, !tbaa !53
  %49 = zext i8 %48 to i64
  %50 = shl nuw nsw i64 %49, 32
  %51 = or disjoint i64 %46, %50
  %52 = getelementptr inbounds nuw i8, ptr %19, i64 5
  %53 = load i8, ptr %52, align 1, !tbaa !53
  %54 = zext i8 %53 to i64
  %55 = shl nuw nsw i64 %54, 40
  %56 = or i64 %51, %55
  %57 = getelementptr inbounds nuw i8, ptr %19, i64 6
  %58 = load i8, ptr %57, align 1, !tbaa !53
  %59 = zext i8 %58 to i64
  %60 = shl nuw nsw i64 %59, 48
  %61 = or i64 %56, %60
  %62 = getelementptr inbounds nuw i8, ptr %19, i64 7
  %63 = load i8, ptr %62, align 1, !tbaa !53
  %64 = zext i8 %63 to i64
  %65 = shl nuw i64 %64, 56
  %66 = or i64 %61, %65
  %67 = add nsw i32 %24, -8
  %68 = getelementptr inbounds nuw i8, ptr %19, i64 8
  br label %82

69:                                               ; preds = %69, %27
  %70 = phi i32 [ %80, %69 ], [ 0, %27 ]
  %71 = phi i64 [ %79, %69 ], [ 0, %27 ]
  %72 = zext nneg i32 %70 to i64
  %73 = getelementptr inbounds nuw i8, ptr %19, i64 %72
  %74 = load i8, ptr %73, align 1, !tbaa !53
  %75 = zext i8 %74 to i64
  %76 = shl i32 %70, 3
  %77 = zext nneg i32 %76 to i64
  %78 = shl nuw i64 %75, %77
  %79 = or i64 %78, %71
  %80 = add nuw nsw i32 %70, 1
  %81 = icmp eq i32 %80, %24
  br i1 %81, label %82, label %69

82:                                               ; preds = %69, %29, %27
  %83 = phi ptr [ %68, %29 ], [ %19, %27 ], [ %19, %69 ]
  %84 = phi i32 [ %67, %29 ], [ 0, %27 ], [ 0, %69 ]
  %85 = phi i64 [ %66, %29 ], [ 0, %27 ], [ %79, %69 ]
  %86 = icmp ugt i32 %84, 7
  br i1 %86, label %89, label %87

87:                                               ; preds = %82
  %88 = icmp eq i32 %84, 0
  br i1 %88, label %142, label %129

89:                                               ; preds = %82
  %90 = load i8, ptr %83, align 1, !tbaa !53
  %91 = zext i8 %90 to i64
  %92 = getelementptr inbounds nuw i8, ptr %83, i64 1
  %93 = load i8, ptr %92, align 1, !tbaa !53
  %94 = zext i8 %93 to i64
  %95 = shl nuw nsw i64 %94, 8
  %96 = or disjoint i64 %95, %91
  %97 = getelementptr inbounds nuw i8, ptr %83, i64 2
  %98 = load i8, ptr %97, align 1, !tbaa !53
  %99 = zext i8 %98 to i64
  %100 = shl nuw nsw i64 %99, 16
  %101 = or disjoint i64 %96, %100
  %102 = getelementptr inbounds nuw i8, ptr %83, i64 3
  %103 = load i8, ptr %102, align 1, !tbaa !53
  %104 = zext i8 %103 to i64
  %105 = shl nuw nsw i64 %104, 24
  %106 = or disjoint i64 %101, %105
  %107 = getelementptr inbounds nuw i8, ptr %83, i64 4
  %108 = load i8, ptr %107, align 1, !tbaa !53
  %109 = zext i8 %108 to i64
  %110 = shl nuw nsw i64 %109, 32
  %111 = or disjoint i64 %106, %110
  %112 = getelementptr inbounds nuw i8, ptr %83, i64 5
  %113 = load i8, ptr %112, align 1, !tbaa !53
  %114 = zext i8 %113 to i64
  %115 = shl nuw nsw i64 %114, 40
  %116 = or i64 %111, %115
  %117 = getelementptr inbounds nuw i8, ptr %83, i64 6
  %118 = load i8, ptr %117, align 1, !tbaa !53
  %119 = zext i8 %118 to i64
  %120 = shl nuw nsw i64 %119, 48
  %121 = or i64 %116, %120
  %122 = getelementptr inbounds nuw i8, ptr %83, i64 7
  %123 = load i8, ptr %122, align 1, !tbaa !53
  %124 = zext i8 %123 to i64
  %125 = shl nuw i64 %124, 56
  %126 = or i64 %121, %125
  %127 = add nsw i32 %84, -8
  %128 = getelementptr inbounds nuw i8, ptr %83, i64 8
  br label %142

129:                                              ; preds = %129, %87
  %130 = phi i32 [ %140, %129 ], [ 0, %87 ]
  %131 = phi i64 [ %139, %129 ], [ 0, %87 ]
  %132 = zext nneg i32 %130 to i64
  %133 = getelementptr inbounds nuw i8, ptr %83, i64 %132
  %134 = load i8, ptr %133, align 1, !tbaa !53
  %135 = zext i8 %134 to i64
  %136 = shl i32 %130, 3
  %137 = zext nneg i32 %136 to i64
  %138 = shl nuw i64 %135, %137
  %139 = or i64 %138, %131
  %140 = add nuw nsw i32 %130, 1
  %141 = icmp eq i32 %140, %84
  br i1 %141, label %142, label %129

142:                                              ; preds = %129, %89, %87
  %143 = phi ptr [ %128, %89 ], [ %83, %87 ], [ %83, %129 ]
  %144 = phi i32 [ %127, %89 ], [ 0, %87 ], [ 0, %129 ]
  %145 = phi i64 [ %126, %89 ], [ 0, %87 ], [ %139, %129 ]
  %146 = icmp ugt i32 %144, 7
  br i1 %146, label %149, label %147

147:                                              ; preds = %142
  %148 = icmp eq i32 %144, 0
  br i1 %148, label %202, label %189

149:                                              ; preds = %142
  %150 = load i8, ptr %143, align 1, !tbaa !53
  %151 = zext i8 %150 to i64
  %152 = getelementptr inbounds nuw i8, ptr %143, i64 1
  %153 = load i8, ptr %152, align 1, !tbaa !53
  %154 = zext i8 %153 to i64
  %155 = shl nuw nsw i64 %154, 8
  %156 = or disjoint i64 %155, %151
  %157 = getelementptr inbounds nuw i8, ptr %143, i64 2
  %158 = load i8, ptr %157, align 1, !tbaa !53
  %159 = zext i8 %158 to i64
  %160 = shl nuw nsw i64 %159, 16
  %161 = or disjoint i64 %156, %160
  %162 = getelementptr inbounds nuw i8, ptr %143, i64 3
  %163 = load i8, ptr %162, align 1, !tbaa !53
  %164 = zext i8 %163 to i64
  %165 = shl nuw nsw i64 %164, 24
  %166 = or disjoint i64 %161, %165
  %167 = getelementptr inbounds nuw i8, ptr %143, i64 4
  %168 = load i8, ptr %167, align 1, !tbaa !53
  %169 = zext i8 %168 to i64
  %170 = shl nuw nsw i64 %169, 32
  %171 = or disjoint i64 %166, %170
  %172 = getelementptr inbounds nuw i8, ptr %143, i64 5
  %173 = load i8, ptr %172, align 1, !tbaa !53
  %174 = zext i8 %173 to i64
  %175 = shl nuw nsw i64 %174, 40
  %176 = or i64 %171, %175
  %177 = getelementptr inbounds nuw i8, ptr %143, i64 6
  %178 = load i8, ptr %177, align 1, !tbaa !53
  %179 = zext i8 %178 to i64
  %180 = shl nuw nsw i64 %179, 48
  %181 = or i64 %176, %180
  %182 = getelementptr inbounds nuw i8, ptr %143, i64 7
  %183 = load i8, ptr %182, align 1, !tbaa !53
  %184 = zext i8 %183 to i64
  %185 = shl nuw i64 %184, 56
  %186 = or i64 %181, %185
  %187 = add nsw i32 %144, -8
  %188 = getelementptr inbounds nuw i8, ptr %143, i64 8
  br label %202

189:                                              ; preds = %189, %147
  %190 = phi i32 [ %200, %189 ], [ 0, %147 ]
  %191 = phi i64 [ %199, %189 ], [ 0, %147 ]
  %192 = zext nneg i32 %190 to i64
  %193 = getelementptr inbounds nuw i8, ptr %143, i64 %192
  %194 = load i8, ptr %193, align 1, !tbaa !53
  %195 = zext i8 %194 to i64
  %196 = shl i32 %190, 3
  %197 = zext nneg i32 %196 to i64
  %198 = shl nuw i64 %195, %197
  %199 = or i64 %198, %191
  %200 = add nuw nsw i32 %190, 1
  %201 = icmp eq i32 %200, %144
  br i1 %201, label %202, label %189

202:                                              ; preds = %189, %149, %147
  %203 = phi ptr [ %188, %149 ], [ %143, %147 ], [ %143, %189 ]
  %204 = phi i32 [ %187, %149 ], [ 0, %147 ], [ 0, %189 ]
  %205 = phi i64 [ %186, %149 ], [ 0, %147 ], [ %199, %189 ]
  %206 = icmp ugt i32 %204, 7
  br i1 %206, label %209, label %207

207:                                              ; preds = %202
  %208 = icmp eq i32 %204, 0
  br i1 %208, label %262, label %249

209:                                              ; preds = %202
  %210 = load i8, ptr %203, align 1, !tbaa !53
  %211 = zext i8 %210 to i64
  %212 = getelementptr inbounds nuw i8, ptr %203, i64 1
  %213 = load i8, ptr %212, align 1, !tbaa !53
  %214 = zext i8 %213 to i64
  %215 = shl nuw nsw i64 %214, 8
  %216 = or disjoint i64 %215, %211
  %217 = getelementptr inbounds nuw i8, ptr %203, i64 2
  %218 = load i8, ptr %217, align 1, !tbaa !53
  %219 = zext i8 %218 to i64
  %220 = shl nuw nsw i64 %219, 16
  %221 = or disjoint i64 %216, %220
  %222 = getelementptr inbounds nuw i8, ptr %203, i64 3
  %223 = load i8, ptr %222, align 1, !tbaa !53
  %224 = zext i8 %223 to i64
  %225 = shl nuw nsw i64 %224, 24
  %226 = or disjoint i64 %221, %225
  %227 = getelementptr inbounds nuw i8, ptr %203, i64 4
  %228 = load i8, ptr %227, align 1, !tbaa !53
  %229 = zext i8 %228 to i64
  %230 = shl nuw nsw i64 %229, 32
  %231 = or disjoint i64 %226, %230
  %232 = getelementptr inbounds nuw i8, ptr %203, i64 5
  %233 = load i8, ptr %232, align 1, !tbaa !53
  %234 = zext i8 %233 to i64
  %235 = shl nuw nsw i64 %234, 40
  %236 = or i64 %231, %235
  %237 = getelementptr inbounds nuw i8, ptr %203, i64 6
  %238 = load i8, ptr %237, align 1, !tbaa !53
  %239 = zext i8 %238 to i64
  %240 = shl nuw nsw i64 %239, 48
  %241 = or i64 %236, %240
  %242 = getelementptr inbounds nuw i8, ptr %203, i64 7
  %243 = load i8, ptr %242, align 1, !tbaa !53
  %244 = zext i8 %243 to i64
  %245 = shl nuw i64 %244, 56
  %246 = or i64 %241, %245
  %247 = add nsw i32 %204, -8
  %248 = getelementptr inbounds nuw i8, ptr %203, i64 8
  br label %262

249:                                              ; preds = %249, %207
  %250 = phi i32 [ %260, %249 ], [ 0, %207 ]
  %251 = phi i64 [ %259, %249 ], [ 0, %207 ]
  %252 = zext nneg i32 %250 to i64
  %253 = getelementptr inbounds nuw i8, ptr %203, i64 %252
  %254 = load i8, ptr %253, align 1, !tbaa !53
  %255 = zext i8 %254 to i64
  %256 = shl i32 %250, 3
  %257 = zext nneg i32 %256 to i64
  %258 = shl nuw i64 %255, %257
  %259 = or i64 %258, %251
  %260 = add nuw nsw i32 %250, 1
  %261 = icmp eq i32 %260, %204
  br i1 %261, label %262, label %249

262:                                              ; preds = %249, %209, %207
  %263 = phi ptr [ %248, %209 ], [ %203, %207 ], [ %203, %249 ]
  %264 = phi i32 [ %247, %209 ], [ 0, %207 ], [ 0, %249 ]
  %265 = phi i64 [ %246, %209 ], [ 0, %207 ], [ %259, %249 ]
  %266 = icmp ugt i32 %264, 7
  br i1 %266, label %269, label %267

267:                                              ; preds = %262
  %268 = icmp eq i32 %264, 0
  br i1 %268, label %322, label %309

269:                                              ; preds = %262
  %270 = load i8, ptr %263, align 1, !tbaa !53
  %271 = zext i8 %270 to i64
  %272 = getelementptr inbounds nuw i8, ptr %263, i64 1
  %273 = load i8, ptr %272, align 1, !tbaa !53
  %274 = zext i8 %273 to i64
  %275 = shl nuw nsw i64 %274, 8
  %276 = or disjoint i64 %275, %271
  %277 = getelementptr inbounds nuw i8, ptr %263, i64 2
  %278 = load i8, ptr %277, align 1, !tbaa !53
  %279 = zext i8 %278 to i64
  %280 = shl nuw nsw i64 %279, 16
  %281 = or disjoint i64 %276, %280
  %282 = getelementptr inbounds nuw i8, ptr %263, i64 3
  %283 = load i8, ptr %282, align 1, !tbaa !53
  %284 = zext i8 %283 to i64
  %285 = shl nuw nsw i64 %284, 24
  %286 = or disjoint i64 %281, %285
  %287 = getelementptr inbounds nuw i8, ptr %263, i64 4
  %288 = load i8, ptr %287, align 1, !tbaa !53
  %289 = zext i8 %288 to i64
  %290 = shl nuw nsw i64 %289, 32
  %291 = or disjoint i64 %286, %290
  %292 = getelementptr inbounds nuw i8, ptr %263, i64 5
  %293 = load i8, ptr %292, align 1, !tbaa !53
  %294 = zext i8 %293 to i64
  %295 = shl nuw nsw i64 %294, 40
  %296 = or i64 %291, %295
  %297 = getelementptr inbounds nuw i8, ptr %263, i64 6
  %298 = load i8, ptr %297, align 1, !tbaa !53
  %299 = zext i8 %298 to i64
  %300 = shl nuw nsw i64 %299, 48
  %301 = or i64 %296, %300
  %302 = getelementptr inbounds nuw i8, ptr %263, i64 7
  %303 = load i8, ptr %302, align 1, !tbaa !53
  %304 = zext i8 %303 to i64
  %305 = shl nuw i64 %304, 56
  %306 = or i64 %301, %305
  %307 = add nsw i32 %264, -8
  %308 = getelementptr inbounds nuw i8, ptr %263, i64 8
  br label %322

309:                                              ; preds = %309, %267
  %310 = phi i32 [ %320, %309 ], [ 0, %267 ]
  %311 = phi i64 [ %319, %309 ], [ 0, %267 ]
  %312 = zext nneg i32 %310 to i64
  %313 = getelementptr inbounds nuw i8, ptr %263, i64 %312
  %314 = load i8, ptr %313, align 1, !tbaa !53
  %315 = zext i8 %314 to i64
  %316 = shl i32 %310, 3
  %317 = zext nneg i32 %316 to i64
  %318 = shl nuw i64 %315, %317
  %319 = or i64 %318, %311
  %320 = add nuw nsw i32 %310, 1
  %321 = icmp eq i32 %320, %264
  br i1 %321, label %322, label %309

322:                                              ; preds = %309, %269, %267
  %323 = phi ptr [ %308, %269 ], [ %263, %267 ], [ %263, %309 ]
  %324 = phi i32 [ %307, %269 ], [ 0, %267 ], [ 0, %309 ]
  %325 = phi i64 [ %306, %269 ], [ 0, %267 ], [ %319, %309 ]
  %326 = icmp ugt i32 %324, 7
  br i1 %326, label %329, label %327

327:                                              ; preds = %322
  %328 = icmp eq i32 %324, 0
  br i1 %328, label %382, label %369

329:                                              ; preds = %322
  %330 = load i8, ptr %323, align 1, !tbaa !53
  %331 = zext i8 %330 to i64
  %332 = getelementptr inbounds nuw i8, ptr %323, i64 1
  %333 = load i8, ptr %332, align 1, !tbaa !53
  %334 = zext i8 %333 to i64
  %335 = shl nuw nsw i64 %334, 8
  %336 = or disjoint i64 %335, %331
  %337 = getelementptr inbounds nuw i8, ptr %323, i64 2
  %338 = load i8, ptr %337, align 1, !tbaa !53
  %339 = zext i8 %338 to i64
  %340 = shl nuw nsw i64 %339, 16
  %341 = or disjoint i64 %336, %340
  %342 = getelementptr inbounds nuw i8, ptr %323, i64 3
  %343 = load i8, ptr %342, align 1, !tbaa !53
  %344 = zext i8 %343 to i64
  %345 = shl nuw nsw i64 %344, 24
  %346 = or disjoint i64 %341, %345
  %347 = getelementptr inbounds nuw i8, ptr %323, i64 4
  %348 = load i8, ptr %347, align 1, !tbaa !53
  %349 = zext i8 %348 to i64
  %350 = shl nuw nsw i64 %349, 32
  %351 = or disjoint i64 %346, %350
  %352 = getelementptr inbounds nuw i8, ptr %323, i64 5
  %353 = load i8, ptr %352, align 1, !tbaa !53
  %354 = zext i8 %353 to i64
  %355 = shl nuw nsw i64 %354, 40
  %356 = or i64 %351, %355
  %357 = getelementptr inbounds nuw i8, ptr %323, i64 6
  %358 = load i8, ptr %357, align 1, !tbaa !53
  %359 = zext i8 %358 to i64
  %360 = shl nuw nsw i64 %359, 48
  %361 = or i64 %356, %360
  %362 = getelementptr inbounds nuw i8, ptr %323, i64 7
  %363 = load i8, ptr %362, align 1, !tbaa !53
  %364 = zext i8 %363 to i64
  %365 = shl nuw i64 %364, 56
  %366 = or i64 %361, %365
  %367 = add nsw i32 %324, -8
  %368 = getelementptr inbounds nuw i8, ptr %323, i64 8
  br label %382

369:                                              ; preds = %369, %327
  %370 = phi i32 [ %380, %369 ], [ 0, %327 ]
  %371 = phi i64 [ %379, %369 ], [ 0, %327 ]
  %372 = zext nneg i32 %370 to i64
  %373 = getelementptr inbounds nuw i8, ptr %323, i64 %372
  %374 = load i8, ptr %373, align 1, !tbaa !53
  %375 = zext i8 %374 to i64
  %376 = shl i32 %370, 3
  %377 = zext nneg i32 %376 to i64
  %378 = shl nuw i64 %375, %377
  %379 = or i64 %378, %371
  %380 = add nuw nsw i32 %370, 1
  %381 = icmp eq i32 %380, %324
  br i1 %381, label %382, label %369

382:                                              ; preds = %369, %329, %327
  %383 = phi ptr [ %368, %329 ], [ %323, %327 ], [ %323, %369 ]
  %384 = phi i32 [ %367, %329 ], [ 0, %327 ], [ 0, %369 ]
  %385 = phi i64 [ %366, %329 ], [ 0, %327 ], [ %379, %369 ]
  %386 = icmp ugt i32 %384, 7
  br i1 %386, label %389, label %387

387:                                              ; preds = %382
  %388 = icmp eq i32 %384, 0
  br i1 %388, label %440, label %427

389:                                              ; preds = %382
  %390 = load i8, ptr %383, align 1, !tbaa !53
  %391 = zext i8 %390 to i64
  %392 = getelementptr inbounds nuw i8, ptr %383, i64 1
  %393 = load i8, ptr %392, align 1, !tbaa !53
  %394 = zext i8 %393 to i64
  %395 = shl nuw nsw i64 %394, 8
  %396 = or disjoint i64 %395, %391
  %397 = getelementptr inbounds nuw i8, ptr %383, i64 2
  %398 = load i8, ptr %397, align 1, !tbaa !53
  %399 = zext i8 %398 to i64
  %400 = shl nuw nsw i64 %399, 16
  %401 = or disjoint i64 %396, %400
  %402 = getelementptr inbounds nuw i8, ptr %383, i64 3
  %403 = load i8, ptr %402, align 1, !tbaa !53
  %404 = zext i8 %403 to i64
  %405 = shl nuw nsw i64 %404, 24
  %406 = or disjoint i64 %401, %405
  %407 = getelementptr inbounds nuw i8, ptr %383, i64 4
  %408 = load i8, ptr %407, align 1, !tbaa !53
  %409 = zext i8 %408 to i64
  %410 = shl nuw nsw i64 %409, 32
  %411 = or disjoint i64 %406, %410
  %412 = getelementptr inbounds nuw i8, ptr %383, i64 5
  %413 = load i8, ptr %412, align 1, !tbaa !53
  %414 = zext i8 %413 to i64
  %415 = shl nuw nsw i64 %414, 40
  %416 = or i64 %411, %415
  %417 = getelementptr inbounds nuw i8, ptr %383, i64 6
  %418 = load i8, ptr %417, align 1, !tbaa !53
  %419 = zext i8 %418 to i64
  %420 = shl nuw nsw i64 %419, 48
  %421 = or i64 %416, %420
  %422 = getelementptr inbounds nuw i8, ptr %383, i64 7
  %423 = load i8, ptr %422, align 1, !tbaa !53
  %424 = zext i8 %423 to i64
  %425 = shl nuw i64 %424, 56
  %426 = or i64 %421, %425
  br label %440

427:                                              ; preds = %427, %387
  %428 = phi i32 [ %438, %427 ], [ 0, %387 ]
  %429 = phi i64 [ %437, %427 ], [ 0, %387 ]
  %430 = zext nneg i32 %428 to i64
  %431 = getelementptr inbounds nuw i8, ptr %383, i64 %430
  %432 = load i8, ptr %431, align 1, !tbaa !53
  %433 = zext i8 %432 to i64
  %434 = shl i32 %428, 3
  %435 = zext nneg i32 %434 to i64
  %436 = shl nuw i64 %433, %435
  %437 = or i64 %436, %429
  %438 = add nuw nsw i32 %428, 1
  %439 = icmp eq i32 %438, %384
  br i1 %439, label %440, label %427

440:                                              ; preds = %427, %389, %387
  %441 = phi i64 [ %426, %389 ], [ 0, %387 ], [ %437, %427 ]
  %442 = shl nuw nsw i64 %23, 2
  %443 = add nuw nsw i64 %442, 28
  %444 = and i64 %443, 480
  %445 = and i64 %22, -225
  %446 = or i64 %445, %25
  %447 = or i64 %446, %444
  %448 = tail call <2 x i64> @__ockl_hostcall_preview(i32 noundef 2, i64 noundef %447, i64 noundef %85, i64 noundef %145, i64 noundef %205, i64 noundef %265, i64 noundef %325, i64 noundef %385, i64 noundef %441) #24
  %449 = sub i64 %18, %23
  %450 = getelementptr inbounds nuw i8, ptr %19, i64 %23
  %451 = icmp eq i64 %449, 0
  br i1 %451, label %452, label %17

452:                                              ; preds = %440, %9
  %453 = phi <2 x i64> [ %12, %9 ], [ %448, %440 ]
  %454 = extractelement <2 x i64> %453, i64 0
  ret i64 %454
}

; Function Attrs: nocallback nocreateundeforpoison nofree nosync nounwind speculatable willreturn memory(none)
declare i64 @llvm.umin.i64(i64, i64) #20

; Function Attrs: convergent mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define internal range(i64 0, 65536) i64 @__ockl_get_local_size(i32 noundef %0) #21 {
  switch i32 %0, label %17 [
    i32 0, label %2
    i32 1, label %7
    i32 2, label %12
  ]

2:                                                ; preds = %1
  %3 = load i32, ptr addrspace(4) @__oclc_ABI_version, align 4, !tbaa !33
  %4 = icmp slt i32 %3, 500
  br i1 %4, label %5, label %6

5:                                                ; preds = %2
  br label %17

6:                                                ; preds = %2
  br label %17

7:                                                ; preds = %1
  %8 = load i32, ptr addrspace(4) @__oclc_ABI_version, align 4, !tbaa !33
  %9 = icmp slt i32 %8, 500
  br i1 %9, label %10, label %11

10:                                               ; preds = %7
  br label %17

11:                                               ; preds = %7
  br label %17

12:                                               ; preds = %1
  %13 = load i32, ptr addrspace(4) @__oclc_ABI_version, align 4, !tbaa !33
  %14 = icmp slt i32 %13, 500
  br i1 %14, label %15, label %16

15:                                               ; preds = %12
  br label %17

16:                                               ; preds = %12
  br label %17

17:                                               ; preds = %16, %15, %11, %10, %6, %5, %1
  %E = extractelement <2 x i64> splat (i64 1), i32 %0
  ret i64 %E
}

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare noundef nonnull align 4 ptr addrspace(4) @llvm.amdgcn.dispatch.ptr() #11

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare noundef i32 @llvm.amdgcn.workgroup.id.x() #11

; Function Attrs: nocallback nocreateundeforpoison nofree nosync nounwind speculatable willreturn memory(none)
declare i32 @llvm.umin.i32(i32, i32) #20

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare noundef i32 @llvm.amdgcn.workgroup.id.y() #11

; Function Attrs: nocallback nofree nosync nounwind speculatable willreturn memory(none)
declare noundef i32 @llvm.amdgcn.workgroup.id.z() #11

; Function Attrs: convergent mustprogress nofree norecurse nosync nounwind willreturn memory(none)
define internal range(i64 0, 4294967296) i64 @__ockl_get_group_id(i32 noundef %0) #22 {
  switch i32 %0, label %8 [
    i32 0, label %2
    i32 1, label %4
    i32 2, label %6
  ]

2:                                                ; preds = %1
  %3 = tail call i32 @llvm.amdgcn.workgroup.id.x()
  br label %8

4:                                                ; preds = %1
  %5 = tail call i32 @llvm.amdgcn.workgroup.id.y()
  br label %8

6:                                                ; preds = %1
  %7 = tail call i32 @llvm.amdgcn.workgroup.id.z()
  br label %8

8:                                                ; preds = %6, %4, %2, %1
  %9 = phi i32 [ %7, %6 ], [ %5, %4 ], [ %3, %2 ], [ 0, %1 ]
  %10 = zext i32 %9 to i64
  ret i64 %10
}

declare <8 x half> @f(<4 x half>, <16 x i16>, <4 x half>, <32 x i64>)

attributes #0 = { convergent mustprogress noreturn nounwind "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="gfx1201" "target-features"="+16-bit-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-fmin-fmax-global-f32,+atomic-global-pk-add-bf16-inst,+ci-insts,+cube-insts,+cvt-pknorm-vop2-insts,+dl-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+fp8-conversion-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx8-insts,+gfx9-insts,+lerp-inst,+qsad-insts,+sad-insts,+wavefrontsize32" }
attributes #1 = { cold noreturn nounwind memory(inaccessiblemem: write) }
attributes #2 = { convergent mustprogress noinline nounwind "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="gfx1201" "target-features"="+16-bit-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-fmin-fmax-global-f32,+atomic-global-pk-add-bf16-inst,+ci-insts,+cube-insts,+cvt-pknorm-vop2-insts,+dl-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+fp8-conversion-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx8-insts,+gfx9-insts,+lerp-inst,+qsad-insts,+sad-insts,+wavefrontsize32" }
attributes #3 = { nocallback nofree nosync nounwind willreturn memory(argmem: readwrite) }
attributes #4 = { nocallback nofree nounwind willreturn memory(argmem: readwrite) }
attributes #5 = { convergent mustprogress nounwind "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="gfx1201" "target-features"="+16-bit-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-fmin-fmax-global-f32,+atomic-global-pk-add-bf16-inst,+ci-insts,+cube-insts,+cvt-pknorm-vop2-insts,+dl-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+fp8-conversion-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx8-insts,+gfx9-insts,+lerp-inst,+qsad-insts,+sad-insts,+wavefrontsize32" }
attributes #6 = { alwaysinline convergent mustprogress nounwind "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="gfx1201" "target-features"="+16-bit-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-fmin-fmax-global-f32,+atomic-global-pk-add-bf16-inst,+ci-insts,+cube-insts,+cvt-pknorm-vop2-insts,+dl-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+fp8-conversion-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx8-insts,+gfx9-insts,+lerp-inst,+qsad-insts,+sad-insts,+wavefrontsize32" }
attributes #7 = { convergent inlinehint mustprogress nounwind "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="gfx1201" "target-features"="+16-bit-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-fmin-fmax-global-f32,+atomic-global-pk-add-bf16-inst,+ci-insts,+cube-insts,+cvt-pknorm-vop2-insts,+dl-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+fp8-conversion-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx8-insts,+gfx9-insts,+lerp-inst,+qsad-insts,+sad-insts,+wavefrontsize32" }
attributes #8 = { convergent mustprogress norecurse nounwind "amdgpu-flat-work-group-size"="1,1024" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="gfx1201" "target-features"="+16-bit-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-fmin-fmax-global-f32,+atomic-global-pk-add-bf16-inst,+ci-insts,+cube-insts,+cvt-pknorm-vop2-insts,+dl-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+fp8-conversion-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx8-insts,+gfx9-insts,+lerp-inst,+qsad-insts,+sad-insts,+wavefrontsize32" "uniform-work-group-size"="true" }
attributes #9 = { convergent nocallback nofree nounwind willreturn }
attributes #10 = { convergent mustprogress nofree norecurse nosync nounwind willreturn memory(none) "amdgpu-no-agpr" "amdgpu-no-completion-action" "amdgpu-no-default-queue" "amdgpu-no-dispatch-id" "amdgpu-no-dispatch-ptr" "amdgpu-no-flat-scratch-init" "amdgpu-no-heap-ptr" "amdgpu-no-hostcall-ptr" "amdgpu-no-implicitarg-ptr" "amdgpu-no-lds-kernel-id" "amdgpu-no-multigrid-sync-arg" "amdgpu-no-queue-ptr" "amdgpu-no-workgroup-id-x" "amdgpu-no-workgroup-id-y" "amdgpu-no-workgroup-id-z" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="gfx1201" "target-features"="+16-bit-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-fmin-fmax-global-f32,+atomic-global-pk-add-bf16-inst,+ci-insts,+cube-insts,+cvt-pknorm-vop2-insts,+dl-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+fp8-conversion-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx8-insts,+gfx9-insts,+image-insts,+lerp-inst,+qsad-insts,+sad-insts,+wavefrontsize32" "uniform-work-group-size"="false" }
attributes #11 = { nocallback nofree nosync nounwind speculatable willreturn memory(none) }
attributes #12 = { convergent norecurse nounwind "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="gfx1201" "target-features"="+16-bit-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-fmin-fmax-global-f32,+atomic-global-pk-add-bf16-inst,+ci-insts,+cube-insts,+cvt-pknorm-vop2-insts,+dl-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+fp8-conversion-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx8-insts,+gfx9-insts,+image-insts,+lerp-inst,+qsad-insts,+sad-insts,+wavefrontsize32" "uniform-work-group-size"="false" }
attributes #13 = { cold convergent norecurse nounwind "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="gfx1201" "target-features"="+16-bit-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-fmin-fmax-global-f32,+atomic-global-pk-add-bf16-inst,+ci-insts,+cube-insts,+cvt-pknorm-vop2-insts,+dl-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+fp8-conversion-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx8-insts,+gfx9-insts,+image-insts,+lerp-inst,+qsad-insts,+sad-insts,+wavefrontsize32" "uniform-work-group-size"="false" }
attributes #14 = { alwaysinline convergent mustprogress nofree norecurse nosync nounwind willreturn memory(none) "amdgpu-no-agpr" "amdgpu-no-completion-action" "amdgpu-no-default-queue" "amdgpu-no-dispatch-id" "amdgpu-no-dispatch-ptr" "amdgpu-no-flat-scratch-init" "amdgpu-no-heap-ptr" "amdgpu-no-hostcall-ptr" "amdgpu-no-implicitarg-ptr" "amdgpu-no-lds-kernel-id" "amdgpu-no-multigrid-sync-arg" "amdgpu-no-queue-ptr" "amdgpu-no-workgroup-id-x" "amdgpu-no-workgroup-id-y" "amdgpu-no-workgroup-id-z" "amdgpu-no-workitem-id-x" "amdgpu-no-workitem-id-y" "amdgpu-no-workitem-id-z" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="gfx1201" "target-features"="+16-bit-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-fmin-fmax-global-f32,+atomic-global-pk-add-bf16-inst,+ci-insts,+cube-insts,+cvt-pknorm-vop2-insts,+dl-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+fp8-conversion-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx8-insts,+gfx9-insts,+image-insts,+lerp-inst,+qsad-insts,+sad-insts,+wavefrontsize32" "uniform-work-group-size"="false" }
attributes #15 = { convergent nocallback nocreateundeforpoison nofree nounwind willreturn memory(none) }
attributes #16 = { nocallback nofree nosync nounwind willreturn }
attributes #17 = { convergent norecurse nounwind "amdgpu-no-agpr" "amdgpu-no-completion-action" "amdgpu-no-default-queue" "amdgpu-no-dispatch-id" "amdgpu-no-dispatch-ptr" "amdgpu-no-flat-scratch-init" "amdgpu-no-heap-ptr" "amdgpu-no-hostcall-ptr" "amdgpu-no-implicitarg-ptr" "amdgpu-no-lds-kernel-id" "amdgpu-no-multigrid-sync-arg" "amdgpu-no-queue-ptr" "amdgpu-no-workgroup-id-x" "amdgpu-no-workgroup-id-y" "amdgpu-no-workgroup-id-z" "amdgpu-no-workitem-id-x" "amdgpu-no-workitem-id-y" "amdgpu-no-workitem-id-z" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="gfx1201" "target-features"="+16-bit-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-fmin-fmax-global-f32,+atomic-global-pk-add-bf16-inst,+ci-insts,+cube-insts,+cvt-pknorm-vop2-insts,+dl-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+fp8-conversion-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx8-insts,+gfx9-insts,+image-insts,+lerp-inst,+qsad-insts,+sad-insts,+wavefrontsize32" "uniform-work-group-size"="false" }
attributes #18 = { nocallback nounwind willreturn }
attributes #19 = { nocallback nocreateundeforpoison nofree nosync nounwind willreturn memory(none) }
attributes #20 = { nocallback nocreateundeforpoison nofree nosync nounwind speculatable willreturn memory(none) }
attributes #21 = { convergent mustprogress nofree norecurse nosync nounwind willreturn memory(none) "amdgpu-no-agpr" "amdgpu-no-completion-action" "amdgpu-no-default-queue" "amdgpu-no-dispatch-id" "amdgpu-no-flat-scratch-init" "amdgpu-no-heap-ptr" "amdgpu-no-hostcall-ptr" "amdgpu-no-lds-kernel-id" "amdgpu-no-multigrid-sync-arg" "amdgpu-no-queue-ptr" "amdgpu-no-workitem-id-x" "amdgpu-no-workitem-id-y" "amdgpu-no-workitem-id-z" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="gfx1201" "target-features"="+16-bit-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-fmin-fmax-global-f32,+atomic-global-pk-add-bf16-inst,+ci-insts,+cube-insts,+cvt-pknorm-vop2-insts,+dl-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+fp8-conversion-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx8-insts,+gfx9-insts,+image-insts,+lerp-inst,+qsad-insts,+sad-insts,+wavefrontsize32" "uniform-work-group-size"="false" }
attributes #22 = { convergent mustprogress nofree norecurse nosync nounwind willreturn memory(none) "amdgpu-no-agpr" "amdgpu-no-completion-action" "amdgpu-no-default-queue" "amdgpu-no-dispatch-id" "amdgpu-no-dispatch-ptr" "amdgpu-no-flat-scratch-init" "amdgpu-no-heap-ptr" "amdgpu-no-hostcall-ptr" "amdgpu-no-implicitarg-ptr" "amdgpu-no-lds-kernel-id" "amdgpu-no-multigrid-sync-arg" "amdgpu-no-queue-ptr" "amdgpu-no-workitem-id-x" "amdgpu-no-workitem-id-y" "amdgpu-no-workitem-id-z" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="gfx1201" "target-features"="+16-bit-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-fmin-fmax-global-f32,+atomic-global-pk-add-bf16-inst,+ci-insts,+cube-insts,+cvt-pknorm-vop2-insts,+dl-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+fp8-conversion-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx8-insts,+gfx9-insts,+image-insts,+lerp-inst,+qsad-insts,+sad-insts,+wavefrontsize32" "uniform-work-group-size"="false" }
attributes #23 = { nounwind }
attributes #24 = { convergent nounwind }
attributes #25 = { convergent nounwind willreturn memory(none) }
attributes #26 = { cold convergent nounwind }

!llvm.module.flags = !{!0, !1, !2, !3}
!llvm.ident = !{!4, !5}
!llvm.errno.tbaa = !{!6}
!opencl.ocl.version = !{!10}

!0 = !{i32 1, !"amdhsa_code_object_version", i32 600}
!1 = !{i32 1, !"amdgpu_printf_kind", !"hostcall"}
!2 = !{i32 1, !"wchar_size", i32 4}
!3 = !{i32 8, !"PIC Level", i32 2}
!4 = !{!"clang version 22.0.0git (https://github.com/llvm/llvm-project 86b9f90b9574b3a7d15d28a91f6316459dcfa046+PATCHED)"}
!5 = !{!"AMD clang version 20.0.0git (https://github.com/RadeonOpenCompute/llvm-project roc-7.1.1 25444 27682a16360e33e37c4f3cc6adf9a620733f8fe1)"}
!6 = !{!7, !7, i64 0}
!7 = !{!"int", !8, i64 0}
!8 = !{!"omnipotent char", !9, i64 0}
!9 = !{!"Simple C++ TBAA"}
!10 = !{i32 2, i32 0}
!11 = !{!12, !12, i64 0}
!12 = !{!"p1 omnipotent char", !13, i64 0}
!13 = !{!"any pointer", !8, i64 0}
!14 = !{!15, !15, i64 0}
!15 = !{!"long long", !8, i64 0}
!16 = !{!8, !8, i64 0}
!17 = distinct !{!17, !18, !19}
!18 = !{!"llvm.loop.mustprogress"}
!19 = !{!"llvm.loop.unroll.disable"}
!20 = distinct !{!20, !18, !19}
!21 = distinct !{!21, !18, !19}
!22 = distinct !{!22, !18, !19}
!23 = distinct !{!23, !18, !19}
!24 = distinct !{!24, !18, !19}
!25 = distinct !{!25, !18, !19}
!26 = distinct !{!26, !18, !19}
!27 = !{!28, !28, i64 0}
!28 = !{!"p1 int", !13, i64 0}
!29 = !{i32 5, i32 6}
!30 = !{}
!31 = !{!"amdgpu-synchronize-as", !"global"}
!32 = !{!"amdgpu-synchronize-as", !"local"}
!33 = !{!34, !34, i64 0}
!34 = !{!"int", !35, i64 0}
!35 = !{!"omnipotent char", !36, i64 0}
!36 = !{!"Simple C/C++ TBAA"}
!37 = !{!38, !38, i64 0}
!38 = !{!"long", !35, i64 0}
!39 = !{!40, !41, i64 0}
!40 = !{!"", !41, i64 0, !41, i64 8, !42, i64 16, !38, i64 24, !38, i64 32, !38, i64 40}
!41 = !{!"any pointer", !35, i64 0}
!42 = !{!"hsa_signal_s", !38, i64 0}
!43 = !{!40, !38, i64 40}
!44 = !{!40, !41, i64 8}
!45 = !{!46, !34, i64 16}
!46 = !{!"", !38, i64 0, !38, i64 8, !34, i64 16, !34, i64 20}
!47 = !{!46, !38, i64 8}
!48 = !{!46, !34, i64 20}
!49 = !{!46, !38, i64 0}
!50 = !{!51, !38, i64 16}
!51 = !{!"amd_signal_s", !38, i64 0, !35, i64 8, !38, i64 16, !34, i64 24, !34, i64 28, !38, i64 32, !38, i64 40, !35, i64 48, !35, i64 56}
!52 = !{!51, !34, i64 24}
!53 = !{!35, !35, i64 0}
