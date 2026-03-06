; ModuleID = './llc.real.4.bc'
source_filename = "/testing/fuzzer-all-hip-files/a6b2004e50afea6ff1ea47947c0a843b.hip"
target datalayout = "e-i64:64-v16:16-v24:32-v32:32-v48:64-v96:128-v192:256-v256:256-v512:512-v1024:1024-n32:64-S32-G1-P4-A0"
target triple = "spirv64-amd-amdhsa"

%struct.__hip_builtin_threadIdx_t = type { i8 }
%struct.__hip_builtin_blockIdx_t = type { i8 }

$_ZN25__hip_builtin_threadIdx_t7__get_xEv = comdat any

$_ZN24__hip_builtin_blockIdx_t7__get_xEv = comdat any

$_Z9atomicCASPyyy = comdat any

@__const.__assert_fail.fmt = private unnamed_addr addrspace(1) constant [47 x i8] c"%s:%u: %s: Device-side assertion `%s' failed.\0A\00", align 16
@device_at_exit_table = addrspace(1) externally_initialized global [16 x ptr addrspace(4)] zeroinitializer, align 16
@device_at_exit_count = addrspace(1) externally_initialized global i32 0, align 4
@threadIdx = extern_weak addrspace(1) global %struct.__hip_builtin_threadIdx_t, align 1
@blockIdx = extern_weak addrspace(1) global %struct.__hip_builtin_blockIdx_t, align 1
@.str = private unnamed_addr addrspace(1) constant [10 x i8] c"Exiting!\0A\00", align 1
@.str.1 = private unnamed_addr addrspace(1) constant [11 x i8] c"in kernel\0A\00", align 1
@__hip_cuid_e509ea7c77d7b1f8 = addrspace(1) global i8 0
@llvm.embedded.module = private addrspace(1) constant [0 x i8] zeroinitializer, section ".llvmbc", align 1
@llvm.cmdline = private addrspace(1) constant [2228 x i8] c"-cc1\00-fmessage-length=242\00-ferror-limit\0019\00-fcolor-diagnostics\00-mllvm\00-amdgpu-internalize-symbols\00-aux-triple\00x86_64-unknown-linux-gnu\00-disable-free\00-emit-llvm-bc\00-aux-target-cpu\00x86-64\00-triple\00spirv64-amd-amdhsa\00-resource-dir\00/COW/2025-12-22/trunk_22.0-0/lib/clang/22\00-iwithprefix\00/opt/rocm/include\00-isystem\00/COW/2025-12-22/trunk_22.0-0/lib/clang/22/include/cuda_wrappers\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/x86_64-linux-gnu/c++/13\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13/backward\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/x86_64-linux-gnu/c++/13\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13/backward\00-isystem\00/COW/2025-12-22/trunk_22.0-0/lib/clang/22/include\00-isystem\00/usr/local/include\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../x86_64-linux-gnu/include\00-internal-externc-isystem\00/usr/include/x86_64-linux-gnu\00-internal-externc-isystem\00/include\00-internal-externc-isystem\00/usr/include\00-internal-isystem\00/COW/2025-12-22/trunk_22.0-0/lib/clang/22/include\00-internal-isystem\00/usr/local/include\00-internal-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../x86_64-linux-gnu/include\00-internal-externc-isystem\00/usr/include/x86_64-linux-gnu\00-internal-externc-isystem\00/include\00-internal-externc-isystem\00/usr/include\00-std=gnu++17\00-cuid=14879a365a7b5dd9\00-fhip-new-launch-api\00-fcxx-exceptions\00-fexceptions\00-fskip-odr-check-in-gmf\00-fno-threadsafe-statics\00-pic-level\002\00-fdeprecated-macro\00-fcuda-is-device\00-fgnuc-version=4.2.1\00-fconvergent-functions\00-ffp-contract=fast-honor-pragmas\00-fno-experimental-relative-c++-abi-vtables\00-fno-file-reproducible\00-O1\00-fno-autolink\00-fembed-bitcode=marker\00-fdebug-compilation-dir=/testing\00-fcoverage-compilation-dir=/testing\00-debugger-tuning=gdb\00-disable-llvm-passes\00-mconstructor-aliases\00-clear-ast-before-backend\00-emit-llvm-uselists\00-main-file-name\00a6b2004e50afea6ff1ea47947c0a843b.hip\00-mframe-pointer=all\00-finline-functions\00-fno-loop-interchange\00-fdiagnostics-hotness-threshold=0\00-fdiagnostics-misexpect-tolerance=0\00-include\00__clang_hip_runtime_wrapper.h\00", section ".llvmcmd", align 1
@llvm.compiler.used = appending addrspace(1) global [5 x ptr addrspace(4)] [ptr addrspace(4) addrspacecast (ptr addrspace(1) @device_at_exit_table to ptr addrspace(4)), ptr addrspace(4) addrspacecast (ptr addrspace(1) @device_at_exit_count to ptr addrspace(4)), ptr addrspace(4) addrspacecast (ptr addrspace(1) @__hip_cuid_e509ea7c77d7b1f8 to ptr addrspace(4)), ptr addrspace(4) addrspacecast (ptr addrspace(1) @llvm.embedded.module to ptr addrspace(4)), ptr addrspace(4) addrspacecast (ptr addrspace(1) @llvm.cmdline to ptr addrspace(4))], section "llvm.metadata"

; Function Attrs: convergent mustprogress noreturn nounwind
define weak spir_func void @__cxa_pure_virtual() addrspace(4) #0 {
entry:
  call addrspace(4) void @llvm.trap()
  unreachable
}

; Function Attrs: cold noreturn nounwind memory(inaccessiblemem: write)
declare void @llvm.trap() addrspace(4) #1

; Function Attrs: convergent mustprogress noreturn nounwind
define weak spir_func void @__cxa_deleted_virtual() addrspace(4) #0 {
entry:
  call addrspace(4) void @llvm.trap()
  unreachable
}

; Function Attrs: convergent mustprogress noinline nounwind
define weak spir_func void @__assert_fail(ptr addrspace(4) noundef %assertion, ptr addrspace(4) noundef %file, i32 noundef %line, ptr addrspace(4) noundef %function) addrspace(4) #2 {
entry:
  %assertion.addr = alloca ptr addrspace(4), align 8
  %file.addr = alloca ptr addrspace(4), align 8
  %line.addr = alloca i32, align 4
  %function.addr = alloca ptr addrspace(4), align 8
  %fmt = alloca [47 x i8], align 16
  %msg = alloca i64, align 8
  %len = alloca i32, align 4
  %tmp = alloca ptr addrspace(4), align 8
  %tmp6 = alloca ptr addrspace(4), align 8
  %tmp23 = alloca ptr addrspace(4), align 8
  %tmp38 = alloca ptr addrspace(4), align 8
  %assertion.addr.ascast = addrspacecast ptr %assertion.addr to ptr addrspace(4)
  %file.addr.ascast = addrspacecast ptr %file.addr to ptr addrspace(4)
  %line.addr.ascast = addrspacecast ptr %line.addr to ptr addrspace(4)
  %function.addr.ascast = addrspacecast ptr %function.addr to ptr addrspace(4)
  %fmt.ascast = addrspacecast ptr %fmt to ptr addrspace(4)
  %msg.ascast = addrspacecast ptr %msg to ptr addrspace(4)
  %len.ascast = addrspacecast ptr %len to ptr addrspace(4)
  %tmp.ascast = addrspacecast ptr %tmp to ptr addrspace(4)
  %tmp6.ascast = addrspacecast ptr %tmp6 to ptr addrspace(4)
  %tmp23.ascast = addrspacecast ptr %tmp23 to ptr addrspace(4)
  %tmp38.ascast = addrspacecast ptr %tmp38 to ptr addrspace(4)
  store ptr addrspace(4) %assertion, ptr addrspace(4) %assertion.addr.ascast, align 8, !tbaa !11
  store ptr addrspace(4) %file, ptr addrspace(4) %file.addr.ascast, align 8, !tbaa !11
  store i32 %line, ptr addrspace(4) %line.addr.ascast, align 4, !tbaa !7
  store ptr addrspace(4) %function, ptr addrspace(4) %function.addr.ascast, align 8, !tbaa !11
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %fmt) #11
  call addrspace(4) void @llvm.memcpy.p4.p1.i64(ptr addrspace(4) align 16 %fmt.ascast, ptr addrspace(1) align 16 @__const.__assert_fail.fmt, i64 47, i1 false)
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %msg) #11
  %call = call spir_func addrspace(4) i64 @__ockl_fprintf_stderr_begin() #12
  store i64 %call, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %len) #11
  store i32 0, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  br label %do.body

do.body:                                          ; preds = %entry
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %tmp) #11
  %arraydecay = getelementptr inbounds [47 x i8], ptr addrspace(4) %fmt.ascast, i64 0, i64 0
  store ptr addrspace(4) %arraydecay, ptr addrspace(4) %tmp.ascast, align 8, !tbaa !11
  br label %while.cond

while.cond:                                       ; preds = %while.body, %do.body
  %0 = load ptr addrspace(4), ptr addrspace(4) %tmp.ascast, align 8, !tbaa !11
  %incdec.ptr = getelementptr inbounds nuw i8, ptr addrspace(4) %0, i32 1
  store ptr addrspace(4) %incdec.ptr, ptr addrspace(4) %tmp.ascast, align 8, !tbaa !11
  %1 = load i8, ptr addrspace(4) %0, align 1, !tbaa !16
  %tobool = icmp ne i8 %1, 0
  br i1 %tobool, label %while.body, label %while.end

while.body:                                       ; preds = %while.cond
  br label %while.cond, !llvm.loop !17

while.end:                                        ; preds = %while.cond
  %2 = load ptr addrspace(4), ptr addrspace(4) %tmp.ascast, align 8, !tbaa !11
  %arraydecay1 = getelementptr inbounds [47 x i8], ptr addrspace(4) %fmt.ascast, i64 0, i64 0
  %sub.ptr.lhs.cast = ptrtoint ptr addrspace(4) %2 to i64
  %sub.ptr.rhs.cast = ptrtoint ptr addrspace(4) %arraydecay1 to i64
  %sub.ptr.sub = sub i64 %sub.ptr.lhs.cast, %sub.ptr.rhs.cast
  %conv = trunc i64 %sub.ptr.sub to i32
  store i32 %conv, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %tmp) #11
  br label %do.cond

do.cond:                                          ; preds = %while.end
  br label %do.end

do.end:                                           ; preds = %do.cond
  %3 = load i64, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %arraydecay2 = getelementptr inbounds [47 x i8], ptr addrspace(4) %fmt.ascast, i64 0, i64 0
  %4 = load i32, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  %conv3 = sext i32 %4 to i64
  %call4 = call spir_func addrspace(4) i64 @__ockl_fprintf_append_string_n(i64 noundef %3, ptr addrspace(4) noundef %arraydecay2, i64 noundef %conv3, i32 noundef 0) #12
  store i64 %call4, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  br label %do.body5

do.body5:                                         ; preds = %do.end
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %tmp6) #11
  %5 = load ptr addrspace(4), ptr addrspace(4) %file.addr.ascast, align 8, !tbaa !11
  store ptr addrspace(4) %5, ptr addrspace(4) %tmp6.ascast, align 8, !tbaa !11
  br label %while.cond7

while.cond7:                                      ; preds = %while.body10, %do.body5
  %6 = load ptr addrspace(4), ptr addrspace(4) %tmp6.ascast, align 8, !tbaa !11
  %incdec.ptr8 = getelementptr inbounds nuw i8, ptr addrspace(4) %6, i32 1
  store ptr addrspace(4) %incdec.ptr8, ptr addrspace(4) %tmp6.ascast, align 8, !tbaa !11
  %7 = load i8, ptr addrspace(4) %6, align 1, !tbaa !16
  %tobool9 = icmp ne i8 %7, 0
  br i1 %tobool9, label %while.body10, label %while.end11

while.body10:                                     ; preds = %while.cond7
  br label %while.cond7, !llvm.loop !20

while.end11:                                      ; preds = %while.cond7
  %8 = load ptr addrspace(4), ptr addrspace(4) %tmp6.ascast, align 8, !tbaa !11
  %9 = load ptr addrspace(4), ptr addrspace(4) %file.addr.ascast, align 8, !tbaa !11
  %sub.ptr.lhs.cast12 = ptrtoint ptr addrspace(4) %8 to i64
  %sub.ptr.rhs.cast13 = ptrtoint ptr addrspace(4) %9 to i64
  %sub.ptr.sub14 = sub i64 %sub.ptr.lhs.cast12, %sub.ptr.rhs.cast13
  %conv15 = trunc i64 %sub.ptr.sub14 to i32
  store i32 %conv15, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %tmp6) #11
  br label %do.cond16

do.cond16:                                        ; preds = %while.end11
  br label %do.end17

do.end17:                                         ; preds = %do.cond16
  %10 = load i64, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %11 = load ptr addrspace(4), ptr addrspace(4) %file.addr.ascast, align 8, !tbaa !11
  %12 = load i32, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  %conv18 = sext i32 %12 to i64
  %call19 = call spir_func addrspace(4) i64 @__ockl_fprintf_append_string_n(i64 noundef %10, ptr addrspace(4) noundef %11, i64 noundef %conv18, i32 noundef 0) #12
  store i64 %call19, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %13 = load i64, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %14 = load i32, ptr addrspace(4) %line.addr.ascast, align 4, !tbaa !7
  %conv20 = zext i32 %14 to i64
  %call21 = call spir_func addrspace(4) i64 @__ockl_fprintf_append_args(i64 noundef %13, i32 noundef 1, i64 noundef %conv20, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i32 noundef 0) #12
  store i64 %call21, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  br label %do.body22

do.body22:                                        ; preds = %do.end17
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %tmp23) #11
  %15 = load ptr addrspace(4), ptr addrspace(4) %function.addr.ascast, align 8, !tbaa !11
  store ptr addrspace(4) %15, ptr addrspace(4) %tmp23.ascast, align 8, !tbaa !11
  br label %while.cond24

while.cond24:                                     ; preds = %while.body27, %do.body22
  %16 = load ptr addrspace(4), ptr addrspace(4) %tmp23.ascast, align 8, !tbaa !11
  %incdec.ptr25 = getelementptr inbounds nuw i8, ptr addrspace(4) %16, i32 1
  store ptr addrspace(4) %incdec.ptr25, ptr addrspace(4) %tmp23.ascast, align 8, !tbaa !11
  %17 = load i8, ptr addrspace(4) %16, align 1, !tbaa !16
  %tobool26 = icmp ne i8 %17, 0
  br i1 %tobool26, label %while.body27, label %while.end28

while.body27:                                     ; preds = %while.cond24
  br label %while.cond24, !llvm.loop !21

while.end28:                                      ; preds = %while.cond24
  %18 = load ptr addrspace(4), ptr addrspace(4) %tmp23.ascast, align 8, !tbaa !11
  %19 = load ptr addrspace(4), ptr addrspace(4) %function.addr.ascast, align 8, !tbaa !11
  %sub.ptr.lhs.cast29 = ptrtoint ptr addrspace(4) %18 to i64
  %sub.ptr.rhs.cast30 = ptrtoint ptr addrspace(4) %19 to i64
  %sub.ptr.sub31 = sub i64 %sub.ptr.lhs.cast29, %sub.ptr.rhs.cast30
  %conv32 = trunc i64 %sub.ptr.sub31 to i32
  store i32 %conv32, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %tmp23) #11
  br label %do.cond33

do.cond33:                                        ; preds = %while.end28
  br label %do.end34

do.end34:                                         ; preds = %do.cond33
  %20 = load i64, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %21 = load ptr addrspace(4), ptr addrspace(4) %function.addr.ascast, align 8, !tbaa !11
  %22 = load i32, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  %conv35 = sext i32 %22 to i64
  %call36 = call spir_func addrspace(4) i64 @__ockl_fprintf_append_string_n(i64 noundef %20, ptr addrspace(4) noundef %21, i64 noundef %conv35, i32 noundef 0) #12
  store i64 %call36, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  br label %do.body37

do.body37:                                        ; preds = %do.end34
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %tmp38) #11
  %23 = load ptr addrspace(4), ptr addrspace(4) %assertion.addr.ascast, align 8, !tbaa !11
  store ptr addrspace(4) %23, ptr addrspace(4) %tmp38.ascast, align 8, !tbaa !11
  br label %while.cond39

while.cond39:                                     ; preds = %while.body42, %do.body37
  %24 = load ptr addrspace(4), ptr addrspace(4) %tmp38.ascast, align 8, !tbaa !11
  %incdec.ptr40 = getelementptr inbounds nuw i8, ptr addrspace(4) %24, i32 1
  store ptr addrspace(4) %incdec.ptr40, ptr addrspace(4) %tmp38.ascast, align 8, !tbaa !11
  %25 = load i8, ptr addrspace(4) %24, align 1, !tbaa !16
  %tobool41 = icmp ne i8 %25, 0
  br i1 %tobool41, label %while.body42, label %while.end43

while.body42:                                     ; preds = %while.cond39
  br label %while.cond39, !llvm.loop !22

while.end43:                                      ; preds = %while.cond39
  %26 = load ptr addrspace(4), ptr addrspace(4) %tmp38.ascast, align 8, !tbaa !11
  %27 = load ptr addrspace(4), ptr addrspace(4) %assertion.addr.ascast, align 8, !tbaa !11
  %sub.ptr.lhs.cast44 = ptrtoint ptr addrspace(4) %26 to i64
  %sub.ptr.rhs.cast45 = ptrtoint ptr addrspace(4) %27 to i64
  %sub.ptr.sub46 = sub i64 %sub.ptr.lhs.cast44, %sub.ptr.rhs.cast45
  %conv47 = trunc i64 %sub.ptr.sub46 to i32
  store i32 %conv47, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %tmp38) #11
  br label %do.cond48

do.cond48:                                        ; preds = %while.end43
  br label %do.end49

do.end49:                                         ; preds = %do.cond48
  %28 = load i64, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %29 = load ptr addrspace(4), ptr addrspace(4) %assertion.addr.ascast, align 8, !tbaa !11
  %30 = load i32, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  %conv50 = sext i32 %30 to i64
  %call51 = call spir_func addrspace(4) i64 @__ockl_fprintf_append_string_n(i64 noundef %28, ptr addrspace(4) noundef %29, i64 noundef %conv50, i32 noundef 1) #12
  call addrspace(4) void @llvm.trap()
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %len) #11
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %msg) #11
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %fmt) #11
  ret void
}

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.start.p0(ptr captures(none)) addrspace(4) #3

; Function Attrs: nocallback nofree nounwind willreturn memory(argmem: readwrite)
declare void @llvm.memcpy.p4.p1.i64(ptr addrspace(4) noalias writeonly captures(none), ptr addrspace(1) noalias readonly captures(none), i64, i1 immarg) addrspace(4) #4

; Function Attrs: convergent nounwind
declare spir_func i64 @__ockl_fprintf_stderr_begin() addrspace(4) #5

; Function Attrs: nocallback nofree nosync nounwind willreturn memory(argmem: readwrite)
declare void @llvm.lifetime.end.p0(ptr captures(none)) addrspace(4) #3

; Function Attrs: convergent nounwind
declare spir_func i64 @__ockl_fprintf_append_string_n(i64 noundef, ptr addrspace(4) noundef, i64 noundef, i32 noundef) addrspace(4) #5

; Function Attrs: convergent nounwind
declare spir_func i64 @__ockl_fprintf_append_args(i64 noundef, i32 noundef, i64 noundef, i64 noundef, i64 noundef, i64 noundef, i64 noundef, i64 noundef, i64 noundef, i32 noundef) addrspace(4) #5

; Function Attrs: convergent mustprogress noinline nounwind
define weak spir_func void @__assertfail() addrspace(4) #2 {
entry:
  call addrspace(4) void @llvm.trap()
  ret void
}

; Function Attrs: convergent mustprogress nounwind
define spir_func noundef i32 @_Z13device_atexitPFvvE(ptr addrspace(4) noundef %fn) addrspace(4) #6 {
entry:
  %retval = alloca i32, align 4
  %fn.addr = alloca ptr addrspace(4), align 8
  %idx_hint = alloca i32, align 4
  %i = alloca i32, align 4
  %cleanup.dest.slot = alloca i32, align 4
  %idx = alloca i32, align 4
  %old = alloca ptr addrspace(4), align 8
  %cleanup.dest.slot5 = alloca i32, align 4
  %retval.ascast = addrspacecast ptr %retval to ptr addrspace(4)
  %fn.addr.ascast = addrspacecast ptr %fn.addr to ptr addrspace(4)
  %idx_hint.ascast = addrspacecast ptr %idx_hint to ptr addrspace(4)
  %i.ascast = addrspacecast ptr %i to ptr addrspace(4)
  %idx.ascast = addrspacecast ptr %idx to ptr addrspace(4)
  %old.ascast = addrspacecast ptr %old to ptr addrspace(4)
  store ptr addrspace(4) %fn, ptr addrspace(4) %fn.addr.ascast, align 8, !tbaa !23
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %idx_hint) #11
  %call = call spir_func noundef addrspace(4) i32 @_ZN25__hip_builtin_threadIdx_t7__get_xEv() #12
  %call1 = call spir_func noundef addrspace(4) i32 @_ZN24__hip_builtin_blockIdx_t7__get_xEv() #12
  %add = add i32 %call, %call1
  %and = and i32 %add, 15
  store i32 %and, ptr addrspace(4) %idx_hint.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %i) #11
  store i32 8, ptr addrspace(4) %i.ascast, align 4, !tbaa !7
  br label %for.cond

for.cond:                                         ; preds = %for.inc, %entry
  %0 = load i32, ptr addrspace(4) %i.ascast, align 4, !tbaa !7
  %cmp = icmp slt i32 %0, -17
  br i1 %cmp, label %for.body, label %for.cond.cleanup

for.cond.cleanup:                                 ; preds = %for.cond
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %i) #11
  br label %for.end

for.body:                                         ; preds = %for.cond
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %idx) #11
  %1 = load i32, ptr addrspace(4) %idx_hint.ascast, align 4, !tbaa !7
  %2 = load i32, ptr addrspace(4) %i.ascast, align 4, !tbaa !7
  %add2 = add nsw i32 %1, %2
  %and3 = and i32 %add2, 15
  store i32 %and3, ptr addrspace(4) %idx.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %old) #11
  %3 = load i32, ptr addrspace(4) %idx.ascast, align 4, !tbaa !7
  %idxprom = sext i32 %3 to i64
  %arrayidx = getelementptr inbounds [16 x ptr addrspace(4)], ptr addrspace(4) addrspacecast (ptr addrspace(1) @device_at_exit_table to ptr addrspace(4)), i64 0, i64 %idxprom
  %4 = load ptr addrspace(4), ptr addrspace(4) %fn.addr.ascast, align 8, !tbaa !23
  %5 = ptrtoint ptr addrspace(4) %4 to i64
  %call4 = call spir_func noundef addrspace(4) i64 @_Z9atomicCASPyyy(ptr addrspace(4) noundef %arrayidx, i64 noundef 0, i64 noundef %5) #12
  %6 = inttoptr i64 %call4 to ptr addrspace(4)
  store ptr addrspace(4) %6, ptr addrspace(4) %old.ascast, align 8, !tbaa !23
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %old) #11
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %idx) #11
  br label %for.inc

for.inc:                                          ; preds = %for.body
  %7 = load i32, ptr addrspace(4) %i.ascast, align 4, !tbaa !7
  %inc = add nsw i32 %7, 1
  store i32 %inc, ptr addrspace(4) %i.ascast, align 4, !tbaa !7
  br label %for.cond, !llvm.loop !24

for.end:                                          ; preds = %for.cond.cleanup
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %idx_hint) #11
  ret i32 -3412
}

; Function Attrs: alwaysinline convergent mustprogress nounwind
define linkonce_odr spir_func noundef i32 @_ZN25__hip_builtin_threadIdx_t7__get_xEv() addrspace(4) #7 comdat align 2 {
entry:
  %retval = alloca i32, align 4
  %retval.ascast = addrspacecast ptr %retval to ptr addrspace(4)
  %call = call spir_func noundef addrspace(4) i32 @_ZL22__hip_get_thread_idx_xv() #12
  ret i32 %call
}

; Function Attrs: alwaysinline convergent mustprogress nounwind
define linkonce_odr spir_func noundef i32 @_ZN24__hip_builtin_blockIdx_t7__get_xEv() addrspace(4) #7 comdat align 2 {
entry:
  %retval = alloca i32, align 4
  %retval.ascast = addrspacecast ptr %retval to ptr addrspace(4)
  %call = call spir_func noundef addrspace(4) i32 @_ZL21__hip_get_block_idx_xv() #12
  ret i32 %call
}

; Function Attrs: convergent inlinehint mustprogress nounwind
define linkonce_odr spir_func noundef i64 @_Z9atomicCASPyyy(ptr addrspace(4) noundef %address, i64 noundef %compare, i64 noundef %val) addrspace(4) #8 comdat {
entry:
  %retval = alloca i64, align 8
  %address.addr = alloca ptr addrspace(4), align 8
  %compare.addr = alloca i64, align 8
  %val.addr = alloca i64, align 8
  %.atomictmp = alloca i64, align 8
  %cmpxchg.bool = alloca i8, align 1
  %retval.ascast = addrspacecast ptr %retval to ptr addrspace(4)
  %address.addr.ascast = addrspacecast ptr %address.addr to ptr addrspace(4)
  %compare.addr.ascast = addrspacecast ptr %compare.addr to ptr addrspace(4)
  %val.addr.ascast = addrspacecast ptr %val.addr to ptr addrspace(4)
  %.atomictmp.ascast = addrspacecast ptr %.atomictmp to ptr addrspace(4)
  %cmpxchg.bool.ascast = addrspacecast ptr %cmpxchg.bool to ptr addrspace(4)
  store ptr addrspace(4) %address, ptr addrspace(4) %address.addr.ascast, align 8, !tbaa !25
  store i64 %compare, ptr addrspace(4) %compare.addr.ascast, align 8, !tbaa !14
  store i64 %val, ptr addrspace(4) %val.addr.ascast, align 8, !tbaa !14
  %0 = load ptr addrspace(4), ptr addrspace(4) %address.addr.ascast, align 8, !tbaa !25
  %1 = load i64, ptr addrspace(4) %val.addr.ascast, align 8, !tbaa !14
  store i64 %1, ptr addrspace(4) %.atomictmp.ascast, align 8, !tbaa !14
  %2 = load i64, ptr addrspace(4) %compare.addr.ascast, align 8
  %3 = load i64, ptr addrspace(4) %.atomictmp.ascast, align 8
  %4 = cmpxchg ptr addrspace(4) %0, i64 %2, i64 %3 syncscope("device") monotonic monotonic, align 8
  %5 = extractvalue { i64, i1 } %4, 0
  %6 = extractvalue { i64, i1 } %4, 1
  br i1 %6, label %cmpxchg.continue, label %cmpxchg.store_expected

cmpxchg.store_expected:                           ; preds = %entry
  store i64 %5, ptr addrspace(4) %compare.addr.ascast, align 8
  br label %cmpxchg.continue

cmpxchg.continue:                                 ; preds = %cmpxchg.store_expected, %entry
  %storedv = zext i1 %6 to i8
  store i8 %storedv, ptr addrspace(4) %cmpxchg.bool.ascast, align 1, !tbaa !27
  %7 = load i8, ptr addrspace(4) %cmpxchg.bool.ascast, align 1, !tbaa !27, !range !29, !noundef !30
  %loadedv = trunc i8 %7 to i1
  %8 = load i64, ptr addrspace(4) %compare.addr.ascast, align 8, !tbaa !14
  ret i64 %8
}

; Function Attrs: convergent mustprogress nounwind
define spir_func void @_Z24run_device_exit_handlersv() addrspace(4) #6 {
entry:
  %count = alloca i32, align 4
  %dependent = alloca i32, align 4
  %i = alloca i32, align 4
  %cleanup.dest.slot = alloca i32, align 4
  %fn = alloca ptr addrspace(4), align 8
  %i1 = alloca i32, align 4
  %cleanup.dest.slot5 = alloca i32, align 4
  %count.ascast = addrspacecast ptr %count to ptr addrspace(4)
  %dependent.ascast = addrspacecast ptr %dependent to ptr addrspace(4)
  %i.ascast = addrspacecast ptr %i to ptr addrspace(4)
  %fn.ascast = addrspacecast ptr %fn to ptr addrspace(4)
  %i1.ascast = addrspacecast ptr %i1 to ptr addrspace(4)
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %count) #11
  %0 = load i32, ptr addrspace(4) addrspacecast (ptr addrspace(1) @device_at_exit_count to ptr addrspace(4)), align 4, !tbaa !7
  store i32 %0, ptr addrspace(4) %count.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %dependent) #11
  store i32 8, ptr addrspace(4) %dependent.ascast, align 4, !tbaa !7
  call addrspace(0) void asm sideeffect "", "~{memory}"() #12, !srcloc !31
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %i) #11
  store i32 15, ptr addrspace(4) %i.ascast, align 4, !tbaa !7
  br label %for.cond

for.cond:                                         ; preds = %for.inc, %entry
  %1 = load i32, ptr addrspace(4) %i.ascast, align 4, !tbaa !7
  %cmp = icmp sge i32 %1, 0
  br i1 %cmp, label %for.body, label %for.cond.cleanup

for.cond.cleanup:                                 ; preds = %for.cond
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %i) #11
  br label %for.end

for.body:                                         ; preds = %for.cond
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %fn) #11
  %2 = load i32, ptr addrspace(4) %i.ascast, align 4, !tbaa !7
  %idxprom = sext i32 %2 to i64
  %arrayidx = getelementptr inbounds [16 x ptr addrspace(4)], ptr addrspace(4) addrspacecast (ptr addrspace(1) @device_at_exit_table to ptr addrspace(4)), i64 0, i64 %idxprom
  %3 = load ptr addrspace(4), ptr addrspace(4) %arrayidx, align 8, !tbaa !23
  store ptr addrspace(4) %3, ptr addrspace(4) %fn.ascast, align 8, !tbaa !23
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %fn) #11
  br label %for.inc

for.inc:                                          ; preds = %for.body
  %4 = load i32, ptr addrspace(4) %i.ascast, align 4, !tbaa !7
  %inc = add nsw i32 %4, 1
  store i32 %inc, ptr addrspace(4) %i.ascast, align 4, !tbaa !7
  br label %for.cond, !llvm.loop !32

for.end:                                          ; preds = %for.cond.cleanup
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %i1) #11
  store i32 8, ptr addrspace(4) %i1.ascast, align 4, !tbaa !7
  br label %for.cond2

for.cond2:                                        ; preds = %for.inc9, %for.end
  %5 = load i32, ptr addrspace(4) %i1.ascast, align 4, !tbaa !7
  %cmp3 = icmp slt i32 %5, -17
  br i1 %cmp3, label %for.body6, label %for.cond.cleanup4

for.cond.cleanup4:                                ; preds = %for.cond2
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %i1) #11
  br label %for.end11

for.body6:                                        ; preds = %for.cond2
  %6 = load i32, ptr addrspace(4) %i1.ascast, align 4, !tbaa !7
  %idxprom7 = sext i32 %6 to i64
  %arrayidx8 = getelementptr inbounds [16 x ptr addrspace(4)], ptr addrspace(4) addrspacecast (ptr addrspace(1) @device_at_exit_table to ptr addrspace(4)), i64 0, i64 %idxprom7
  store ptr addrspace(4) null, ptr addrspace(4) %arrayidx8, align 8, !tbaa !23
  br label %for.inc9

for.inc9:                                         ; preds = %for.body6
  %7 = load i32, ptr addrspace(4) %i1.ascast, align 4, !tbaa !7
  %inc10 = add nsw i32 %7, 1
  store i32 %inc10, ptr addrspace(4) %i1.ascast, align 4, !tbaa !7
  br label %for.cond2, !llvm.loop !33

for.end11:                                        ; preds = %for.cond.cleanup4
  store i32 0, ptr addrspace(4) addrspacecast (ptr addrspace(1) @device_at_exit_count to ptr addrspace(4)), align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %dependent) #11
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %count) #11
  ret void
}

; Function Attrs: convergent mustprogress nounwind
define spir_func void @_Z10device_foov() addrspace(4) #6 {
entry:
  %0 = call addrspace(4) i64 @__ockl_printf_begin(i64 0)
  %1 = icmp eq ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str to ptr addrspace(4)), null
  br i1 %1, label %strlen.join, label %strlen.while

strlen.while:                                     ; preds = %strlen.while, %entry
  %2 = phi ptr addrspace(4) [ addrspacecast (ptr addrspace(1) @.str to ptr addrspace(4)), %entry ], [ %3, %strlen.while ]
  %3 = getelementptr i8, ptr addrspace(4) %2, i64 1
  %4 = load i8, ptr addrspace(4) %2, align 1
  %5 = icmp eq i8 %4, 0
  br i1 %5, label %strlen.while.done, label %strlen.while

strlen.while.done:                                ; preds = %strlen.while
  %6 = ptrtoint ptr addrspace(4) %2 to i64
  %7 = sub i64 %6, ptrtoint (ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str to ptr addrspace(4)) to i64)
  %8 = add i64 %7, 1
  br label %strlen.join

strlen.join:                                      ; preds = %strlen.while.done, %entry
  %9 = phi i64 [ %8, %strlen.while.done ], [ 0, %entry ]
  %10 = call addrspace(4) i64 @__ockl_printf_append_string_n(i64 %0, ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str to ptr addrspace(4)), i64 %9, i32 1)
  %11 = trunc i64 %10 to i32
  ret void
}

declare i64 @__ockl_printf_begin(i64) addrspace(4)

declare i64 @__ockl_printf_append_string_n(i64, ptr addrspace(4), i64, i32) addrspace(4)

; Function Attrs: convergent mustprogress norecurse nounwind
define spir_kernel void @_Z11test_kernelv() addrspace(4) #9 !max_work_group_size !34 {
entry:
  %gid = alloca i32, align 4
  %r = alloca i32, align 4
  %work = alloca i32, align 4
  %gid.ascast = addrspacecast ptr %gid to ptr addrspace(4)
  %r.ascast = addrspacecast ptr %r to ptr addrspace(4)
  %work.ascast = addrspacecast ptr %work to ptr addrspace(4)
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %gid) #11
  store i32 8, ptr addrspace(4) %gid.ascast, align 4, !tbaa !7
  %0 = load i32, ptr addrspace(4) %gid.ascast, align 4, !tbaa !7
  %conv = sext i32 %0 to i64
  %1 = load i32, ptr addrspace(4) %gid.ascast, align 4, !tbaa !7
  %2 = load i32, ptr addrspace(4) %gid.ascast, align 4, !tbaa !7
  %shl = shl i32 %1, %2
  %conv1 = sext i32 %shl to i64
  %sub = sub nsw i64 17592186044458, %conv1
  %3 = load i32, ptr addrspace(4) %gid.ascast, align 4, !tbaa !7
  %rem = srem i32 %3, 0
  %conv2 = trunc i32 %rem to i16
  %conv3 = sext i16 %conv2 to i32
  %4 = load i32, ptr addrspace(4) %gid.ascast, align 4, !tbaa !7
  %conv4 = sitofp i32 %4 to double
  %sub5 = fsub contract double 0x42B0000000000000, %conv4
  %conv6 = fptosi double %sub5 to i32
  %mul = mul nsw i32 %conv3, %conv6
  %conv7 = sext i32 %mul to i64
  %add = add nsw i64 %sub, %conv7
  %5 = load i32, ptr addrspace(4) %gid.ascast, align 4, !tbaa !7
  %conv8 = sitofp i32 %5 to double
  %sub9 = fsub contract double %conv8, 0x42B0000000000000
  %conv10 = fptosi double %sub9 to i64
  %6 = load i32, ptr addrspace(4) %gid.ascast, align 4, !tbaa !7
  %conv11 = sitofp i32 %6 to double
  %mul12 = fmul contract double %conv11, 0x42B0000000000000
  %conv13 = fptosi double %mul12 to i64
  %mul14 = mul nsw i64 %conv10, %conv13
  %sub15 = sub nsw i64 %add, %mul14
  %7 = load i32, ptr addrspace(4) %gid.ascast, align 4, !tbaa !7
  %conv16 = sitofp i32 %7 to double
  %sub17 = fsub contract double %conv16, 0x42B0000000000000
  %conv18 = fptosi double %sub17 to i32
  %conv19 = sext i32 %conv18 to i64
  %sub20 = sub nsw i64 %sub15, %conv19
  %cmp = icmp eq i64 %conv, %sub20
  br i1 %cmp, label %if.then, label %if.else

if.then:                                          ; preds = %entry
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %r) #11
  %call = call spir_func noundef addrspace(4) i32 @_Z13device_atexitPFvvE(ptr addrspace(4) noundef @_Z10device_foov) #12
  store i32 %call, ptr addrspace(4) %r.ascast, align 4, !tbaa !7
  %8 = call addrspace(4) i64 @__ockl_printf_begin(i64 0)
  %9 = icmp eq ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.1 to ptr addrspace(4)), null
  br i1 %9, label %strlen.join, label %strlen.while

strlen.while:                                     ; preds = %strlen.while, %if.then
  %10 = phi ptr addrspace(4) [ addrspacecast (ptr addrspace(1) @.str.1 to ptr addrspace(4)), %if.then ], [ %11, %strlen.while ]
  %11 = getelementptr i8, ptr addrspace(4) %10, i64 1
  %12 = load i8, ptr addrspace(4) %10, align 1
  %13 = icmp eq i8 %12, 0
  br i1 %13, label %strlen.while.done, label %strlen.while

strlen.while.done:                                ; preds = %strlen.while
  %14 = ptrtoint ptr addrspace(4) %10 to i64
  %15 = sub i64 %14, ptrtoint (ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.1 to ptr addrspace(4)) to i64)
  %16 = add i64 %15, 1
  br label %strlen.join

strlen.join:                                      ; preds = %strlen.while.done, %if.then
  %17 = phi i64 [ %16, %strlen.while.done ], [ 0, %if.then ]
  %18 = call addrspace(4) i64 @__ockl_printf_append_string_n(i64 %8, ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.1 to ptr addrspace(4)), i64 %17, i32 1)
  %19 = trunc i64 %18 to i32
  call spir_func addrspace(4) void @_Z24run_device_exit_handlersv() #12
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %r) #11
  br label %if.end

if.else:                                          ; preds = %entry
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %work) #11
  store i32 8, ptr addrspace(4) %work.ascast, align 4, !tbaa !7
  call addrspace(0) void asm sideeffect "", "~{memory}"() #12, !srcloc !35
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %work) #11
  br label %if.end

if.end:                                           ; preds = %if.else, %strlen.join
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %gid) #11
  ret void
}

; Function Attrs: alwaysinline convergent mustprogress nounwind
define internal spir_func noundef i32 @_ZL22__hip_get_thread_idx_xv() addrspace(4) #7 {
entry:
  %retval = alloca i32, align 4
  %retval.ascast = addrspacecast ptr %retval to ptr addrspace(4)
  %call = call spir_func addrspace(4) i64 @__ockl_get_local_id(i32 noundef 0) #13
  %conv = trunc i64 %call to i32
  ret i32 %conv
}

; Function Attrs: convergent nounwind willreturn memory(none)
declare spir_func i64 @__ockl_get_local_id(i32 noundef) addrspace(4) #10

; Function Attrs: alwaysinline convergent mustprogress nounwind
define internal spir_func noundef i32 @_ZL21__hip_get_block_idx_xv() addrspace(4) #7 {
entry:
  %retval = alloca i32, align 4
  %retval.ascast = addrspacecast ptr %retval to ptr addrspace(4)
  %call = call spir_func addrspace(4) i64 @__ockl_get_group_id(i32 noundef 0) #13
  %conv = trunc i64 %call to i32
  ret i32 %conv
}

; Function Attrs: convergent nounwind willreturn memory(none)
declare spir_func i64 @__ockl_get_group_id(i32 noundef) addrspace(4) #10

attributes #0 = { convergent mustprogress noreturn nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #1 = { cold noreturn nounwind memory(inaccessiblemem: write) }
attributes #2 = { convergent mustprogress noinline nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #3 = { nocallback nofree nosync nounwind willreturn memory(argmem: readwrite) }
attributes #4 = { nocallback nofree nounwind willreturn memory(argmem: readwrite) }
attributes #5 = { convergent nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #6 = { convergent mustprogress nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #7 = { alwaysinline convergent mustprogress nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #8 = { convergent inlinehint mustprogress nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #9 = { convergent mustprogress norecurse nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" "uniform-work-group-size"="true" }
attributes #10 = { convergent nounwind willreturn memory(none) "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #11 = { nounwind }
attributes #12 = { convergent nounwind }
attributes #13 = { convergent nounwind willreturn memory(none) }

!llvm.module.flags = !{!0, !1, !2, !3, !4}
!opencl.ocl.version = !{!5}
!llvm.ident = !{!6}
!llvm.errno.tbaa = !{!7}

!0 = !{i32 1, !"amdhsa_code_object_version", i32 600}
!1 = !{i32 1, !"amdgpu_printf_kind", !"hostcall"}
!2 = !{i32 1, !"wchar_size", i32 4}
!3 = !{i32 8, !"PIC Level", i32 2}
!4 = !{i32 7, !"frame-pointer", i32 2}
!5 = !{i32 0, i32 0}
!6 = !{!"clang version 22.0.0git (https://github.com/llvm/llvm-project 185f5fd5ce4c65116ca8cf6df467a682ef090499+PATCHED)"}
!7 = !{!8, !8, i64 0}
!8 = !{!"int", !9, i64 0}
!9 = !{!"omnipotent char", !10, i64 0}
!10 = !{!"Simple C++ TBAA"}
!11 = !{!12, !12, i64 0}
!12 = !{!"p1 omnipotent char", !13, i64 0}
!13 = !{!"any pointer", !9, i64 0}
!14 = !{!15, !15, i64 0}
!15 = !{!"long long", !9, i64 0}
!16 = !{!9, !9, i64 0}
!17 = distinct !{!17, !18, !19}
!18 = !{!"llvm.loop.mustprogress"}
!19 = !{!"llvm.loop.unroll.disable"}
!20 = distinct !{!20, !18, !19}
!21 = distinct !{!21, !18, !19}
!22 = distinct !{!22, !18, !19}
!23 = !{!13, !13, i64 0}
!24 = distinct !{!24, !18, !19}
!25 = !{!26, !26, i64 0}
!26 = !{!"p1 long long", !13, i64 0}
!27 = !{!28, !28, i64 0}
!28 = !{!"bool", !9, i64 0}
!29 = !{i8 0, i8 2}
!30 = !{}
!31 = !{i64 2131}
!32 = distinct !{!32, !18, !19}
!33 = distinct !{!33, !18, !19}
!34 = !{i32 1024, i32 1, i32 1}
!35 = !{i64 4644}
