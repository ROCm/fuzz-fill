; ModuleID = './llc.real.34.bc'
source_filename = "/testing/hip-tests/6b50d6cf763e27442bdd9bdeb323b4ae43f019a8afc2992e663bfcc13e8236d0.hip"
target datalayout = "e-i64:64-v16:16-v24:32-v32:32-v48:64-v96:128-v192:256-v256:256-v512:512-v1024:1024-n32:64-S32-G1-P4-A0"
target triple = "spirv64-amd-amdhsa"

%struct.__hip_builtin_threadIdx_t = type { i8 }
%struct.__hip_builtin_blockIdx_t = type { i8 }

$_ZN25__hip_builtin_threadIdx_t7__get_xEv = comdat any

$_ZN24__hip_builtin_blockIdx_t7__get_xEv = comdat any

@__const.__assert_fail.fmt = private unnamed_addr addrspace(1) constant [47 x i8] c"%s:%u: %s: Device-side assertion `%s' failed.\0A\00", align 16
@.str = private unnamed_addr addrspace(1) constant [5 x i8] c"long\00", align 1
@.str.1 = private unnamed_addr addrspace(1) constant [4 x i8] c"int\00", align 1
@.str.2 = private unnamed_addr addrspace(1) constant [10 x i8] c"long long\00", align 1
@threadIdx = extern_weak addrspace(1) global %struct.__hip_builtin_threadIdx_t, align 1
@blockIdx = extern_weak addrspace(1) global %struct.__hip_builtin_blockIdx_t, align 1
@.str.3 = private unnamed_addr addrspace(1) constant [4 x i8] c"%s\0A\00", align 1
@__hip_cuid_d3a47b8e824dc663 = addrspace(1) global i8 0
@llvm.embedded.module = private addrspace(1) constant [0 x i8] zeroinitializer, section ".llvmbc", align 1
@llvm.cmdline = private addrspace(1) constant [2260 x i8] c"-cc1\00-fmessage-length=178\00-ferror-limit\0019\00-fcolor-diagnostics\00-mllvm\00-amdgpu-internalize-symbols\00-aux-triple\00x86_64-unknown-linux-gnu\00-disable-free\00-emit-llvm-bc\00-aux-target-cpu\00x86-64\00-triple\00spirv64-amd-amdhsa\00-resource-dir\00/COD/2025-11-28/trunk_22.0-0/lib/clang/22\00-iwithprefix\00/opt/rocm/include\00-isystem\00/COD/2025-11-28/trunk_22.0-0/lib/clang/22/include/cuda_wrappers\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/x86_64-linux-gnu/c++/13\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13/backward\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/x86_64-linux-gnu/c++/13\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13/backward\00-isystem\00/COD/2025-11-28/trunk_22.0-0/lib/clang/22/include\00-isystem\00/usr/local/include\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../x86_64-linux-gnu/include\00-internal-externc-isystem\00/usr/include/x86_64-linux-gnu\00-internal-externc-isystem\00/include\00-internal-externc-isystem\00/usr/include\00-internal-isystem\00/COD/2025-11-28/trunk_22.0-0/lib/clang/22/include\00-internal-isystem\00/usr/local/include\00-internal-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../x86_64-linux-gnu/include\00-internal-externc-isystem\00/usr/include/x86_64-linux-gnu\00-internal-externc-isystem\00/include\00-internal-externc-isystem\00/usr/include\00-std=gnu++17\00-cuid=10cd279744ba96ca\00-fhip-new-launch-api\00-fcxx-exceptions\00-fexceptions\00-fskip-odr-check-in-gmf\00-fno-threadsafe-statics\00-pic-level\002\00-fdeprecated-macro\00-fcuda-is-device\00-fgnuc-version=4.2.1\00-fconvergent-functions\00-ffp-contract=fast-honor-pragmas\00-fno-experimental-relative-c++-abi-vtables\00-fno-file-reproducible\00-O1\00-fno-autolink\00-fembed-bitcode=marker\00-fdebug-compilation-dir=/testing\00-fcoverage-compilation-dir=/testing\00-debugger-tuning=gdb\00-disable-llvm-passes\00-mconstructor-aliases\00-clear-ast-before-backend\00-emit-llvm-uselists\00-main-file-name\006b50d6cf763e27442bdd9bdeb323b4ae43f019a8afc2992e663bfcc13e8236d0.hip\00-mframe-pointer=all\00-finline-functions\00-fno-loop-interchange\00-fdiagnostics-hotness-threshold=0\00-fdiagnostics-misexpect-tolerance=0\00-include\00__clang_hip_runtime_wrapper.h\00", section ".llvmcmd", align 1
@llvm.compiler.used = appending addrspace(1) global [3 x ptr addrspace(4)] [ptr addrspace(4) addrspacecast (ptr addrspace(1) @__hip_cuid_d3a47b8e824dc663 to ptr addrspace(4)), ptr addrspace(4) addrspacecast (ptr addrspace(1) @llvm.embedded.module to ptr addrspace(4)), ptr addrspace(4) addrspacecast (ptr addrspace(1) @llvm.cmdline to ptr addrspace(4))], section "llvm.metadata"
@G = addrspace(1) global <16 x i1> splat (i1 true)

; Function Attrs: convergent mustprogress noreturn nounwind
define weak spir_func void @__cxa_pure_virtual() addrspace(4) #0 {
entry:
  %LGV1 = load <16 x i1>, ptr addrspace(1) @G, align 2
  %C = icmp ne <16 x i1> zeroinitializer, %LGV1
  store <16 x i1> %C, ptr addrspace(1) @G, align 2
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
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %fmt) #10
  call addrspace(4) void @llvm.memcpy.p4.p1.i64(ptr addrspace(4) align 16 %fmt.ascast, ptr addrspace(1) align 16 @__const.__assert_fail.fmt, i64 47, i1 false)
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %msg) #10
  %call = call spir_func addrspace(4) i64 @__ockl_fprintf_stderr_begin() #11
  store i64 %call, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %len) #10
  store i32 0, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  br label %do.body

do.body:                                          ; preds = %entry
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %tmp) #10
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
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %tmp) #10
  br label %do.cond

do.cond:                                          ; preds = %while.end
  br label %do.end

do.end:                                           ; preds = %do.cond
  %3 = load i64, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %arraydecay2 = getelementptr inbounds [47 x i8], ptr addrspace(4) %fmt.ascast, i64 0, i64 0
  %4 = load i32, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  %conv3 = sext i32 %4 to i64
  %call4 = call spir_func addrspace(4) i64 @__ockl_fprintf_append_string_n(i64 noundef %3, ptr addrspace(4) noundef %arraydecay2, i64 noundef %conv3, i32 noundef 0) #11
  store i64 %call4, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  br label %do.body5

do.body5:                                         ; preds = %do.end
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %tmp6) #10
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
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %tmp6) #10
  br label %do.cond16

do.cond16:                                        ; preds = %while.end11
  br label %do.end17

do.end17:                                         ; preds = %do.cond16
  %10 = load i64, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %11 = load ptr addrspace(4), ptr addrspace(4) %file.addr.ascast, align 8, !tbaa !11
  %12 = load i32, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  %conv18 = sext i32 %12 to i64
  %call19 = call spir_func addrspace(4) i64 @__ockl_fprintf_append_string_n(i64 noundef %10, ptr addrspace(4) noundef %11, i64 noundef %conv18, i32 noundef 0) #11
  store i64 %call19, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %13 = load i64, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %14 = load i32, ptr addrspace(4) %line.addr.ascast, align 4, !tbaa !7
  %conv20 = zext i32 %14 to i64
  %call21 = call spir_func addrspace(4) i64 @__ockl_fprintf_append_args(i64 noundef %13, i32 noundef 1, i64 noundef %conv20, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i32 noundef 0) #11
  store i64 %call21, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  br label %do.body22

do.body22:                                        ; preds = %do.end17
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %tmp23) #10
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
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %tmp23) #10
  br label %do.cond33

do.cond33:                                        ; preds = %while.end28
  br label %do.end34

do.end34:                                         ; preds = %do.cond33
  %20 = load i64, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %21 = load ptr addrspace(4), ptr addrspace(4) %function.addr.ascast, align 8, !tbaa !11
  %22 = load i32, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  %conv35 = sext i32 %22 to i64
  %call36 = call spir_func addrspace(4) i64 @__ockl_fprintf_append_string_n(i64 noundef %20, ptr addrspace(4) noundef %21, i64 noundef %conv35, i32 noundef 0) #11
  store i64 %call36, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  br label %do.body37

do.body37:                                        ; preds = %do.end34
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %tmp38) #10
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
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %tmp38) #10
  br label %do.cond48

do.cond48:                                        ; preds = %while.end43
  br label %do.end49

do.end49:                                         ; preds = %do.cond48
  %28 = load i64, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %29 = load ptr addrspace(4), ptr addrspace(4) %assertion.addr.ascast, align 8, !tbaa !11
  %30 = load i32, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  %conv50 = sext i32 %30 to i64
  %call51 = call spir_func addrspace(4) i64 @__ockl_fprintf_append_string_n(i64 noundef %28, ptr addrspace(4) noundef %29, i64 noundef %conv50, i32 noundef 1) #11
  call addrspace(4) void @llvm.trap()
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %len) #10
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %msg) #10
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %fmt) #10
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
define spir_func noundef ptr addrspace(4) @_Z10selectTypel(i64 noundef %0) addrspace(4) #6 {
entry:
  %retval = alloca ptr addrspace(4), align 8
  %.addr = alloca i64, align 8
  %retval.ascast = addrspacecast ptr %retval to ptr addrspace(4)
  %.addr.ascast = addrspacecast ptr %.addr to ptr addrspace(4)
  store i64 %0, ptr addrspace(4) %.addr.ascast, align 8, !tbaa !23
  ret ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str to ptr addrspace(4))
}

; Function Attrs: convergent mustprogress nounwind
define spir_func noundef ptr addrspace(4) @_Z10selectTypei(i32 noundef %0) addrspace(4) #6 {
entry:
  %retval = alloca ptr addrspace(4), align 8
  %.addr = alloca i32, align 4
  %retval.ascast = addrspacecast ptr %retval to ptr addrspace(4)
  %.addr.ascast = addrspacecast ptr %.addr to ptr addrspace(4)
  store i32 %0, ptr addrspace(4) %.addr.ascast, align 4, !tbaa !7
  ret ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.1 to ptr addrspace(4))
}

; Function Attrs: convergent mustprogress nounwind
define spir_func noundef ptr addrspace(4) @_Z10selectTypex(i64 noundef %0) addrspace(4) #6 {
entry:
  %retval = alloca ptr addrspace(4), align 8
  %.addr = alloca i64, align 8
  %retval.ascast = addrspacecast ptr %retval to ptr addrspace(4)
  %.addr.ascast = addrspacecast ptr %.addr to ptr addrspace(4)
  store i64 %0, ptr addrspace(4) %.addr.ascast, align 8, !tbaa !14
  ret ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.2 to ptr addrspace(4))
}

; Function Attrs: convergent mustprogress norecurse nounwind
define spir_kernel void @type_selection_kernel() addrspace(4) #7 !max_work_group_size !25 {
entry:
  %i = alloca i32, align 4
  %expr = alloca i64, align 8
  %result = alloca ptr addrspace(4), align 8
  %i.ascast = addrspacecast ptr %i to ptr addrspace(4)
  %expr.ascast = addrspacecast ptr %expr to ptr addrspace(4)
  %result.ascast = addrspacecast ptr %result to ptr addrspace(4)
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %i) #10
  %call = call spir_func noundef addrspace(4) i32 @_ZN25__hip_builtin_threadIdx_t7__get_xEv() #11
  %call1 = call spir_func noundef addrspace(4) i32 @_ZN24__hip_builtin_blockIdx_t7__get_xEv() #11
  %add = add i32 %call, %call1
  store i32 %add, ptr addrspace(4) %i.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %expr) #10
  %0 = load i32, ptr addrspace(4) %i.ascast, align 4, !tbaa !7
  %conv = sext i32 %0 to i64
  %add2 = add nsw i64 %conv, 44
  store i64 %add2, ptr addrspace(4) %expr.ascast, align 8, !tbaa !23
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %result) #10
  %1 = load i64, ptr addrspace(4) %expr.ascast, align 8, !tbaa !23
  %call3 = call spir_func noundef addrspace(4) ptr addrspace(4) @_Z10selectTypel(i64 noundef %1) #11
  store ptr addrspace(4) %call3, ptr addrspace(4) %result.ascast, align 8, !tbaa !11
  %2 = load ptr addrspace(4), ptr addrspace(4) %result.ascast, align 8, !tbaa !11
  %3 = call addrspace(4) i64 @__ockl_printf_begin(i64 0)
  %4 = icmp eq ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.3 to ptr addrspace(4)), null
  br i1 %4, label %strlen.join, label %strlen.while

strlen.while:                                     ; preds = %strlen.while, %entry
  %5 = phi ptr addrspace(4) [ addrspacecast (ptr addrspace(1) @.str.3 to ptr addrspace(4)), %entry ], [ %6, %strlen.while ]
  %6 = getelementptr i8, ptr addrspace(4) %5, i64 1
  %7 = load i8, ptr addrspace(4) %5, align 1
  %8 = icmp eq i8 %7, 0
  br i1 %8, label %strlen.while.done, label %strlen.while

strlen.while.done:                                ; preds = %strlen.while
  %9 = ptrtoint ptr addrspace(4) %5 to i64
  %10 = sub i64 %9, ptrtoint (ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.3 to ptr addrspace(4)) to i64)
  %11 = add i64 %10, 1
  br label %strlen.join

strlen.join:                                      ; preds = %strlen.while.done, %entry
  %12 = phi i64 [ %11, %strlen.while.done ], [ 0, %entry ]
  %13 = call addrspace(4) i64 @__ockl_printf_append_string_n(i64 %3, ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.3 to ptr addrspace(4)), i64 %12, i32 0)
  %14 = icmp eq ptr addrspace(4) %2, null
  br i1 %14, label %strlen.join4, label %strlen.while5

strlen.while5:                                    ; preds = %strlen.while5, %strlen.join
  %15 = phi ptr addrspace(4) [ %2, %strlen.join ], [ %16, %strlen.while5 ]
  %16 = getelementptr i8, ptr addrspace(4) %15, i64 1
  %17 = load i8, ptr addrspace(4) %15, align 1
  %18 = icmp eq i8 %17, 0
  br i1 %18, label %strlen.while.done6, label %strlen.while5

strlen.while.done6:                               ; preds = %strlen.while5
  %19 = ptrtoint ptr addrspace(4) %2 to i64
  %20 = ptrtoint ptr addrspace(4) %15 to i64
  %21 = sub i64 %20, %19
  %22 = add i64 %21, 1
  br label %strlen.join4

strlen.join4:                                     ; preds = %strlen.while.done6, %strlen.join
  %23 = phi i64 [ %22, %strlen.while.done6 ], [ 0, %strlen.join ]
  %24 = call addrspace(4) i64 @__ockl_printf_append_string_n(i64 %13, ptr addrspace(4) %2, i64 %23, i32 1)
  %25 = trunc i64 %24 to i32
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %result) #10
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %expr) #10
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %i) #10
  ret void
}

; Function Attrs: alwaysinline convergent mustprogress nounwind
define linkonce_odr spir_func noundef i32 @_ZN25__hip_builtin_threadIdx_t7__get_xEv() addrspace(4) #8 comdat align 2 {
entry:
  %retval = alloca i32, align 4
  %retval.ascast = addrspacecast ptr %retval to ptr addrspace(4)
  %call = call spir_func noundef addrspace(4) i32 @_ZL22__hip_get_thread_idx_xv() #11
  ret i32 %call
}

; Function Attrs: alwaysinline convergent mustprogress nounwind
define linkonce_odr spir_func noundef i32 @_ZN24__hip_builtin_blockIdx_t7__get_xEv() addrspace(4) #8 comdat align 2 {
entry:
  %retval = alloca i32, align 4
  %retval.ascast = addrspacecast ptr %retval to ptr addrspace(4)
  %call = call spir_func noundef addrspace(4) i32 @_ZL21__hip_get_block_idx_xv() #11
  ret i32 %call
}

declare i64 @__ockl_printf_begin(i64) addrspace(4)

declare i64 @__ockl_printf_append_string_n(i64, ptr addrspace(4), i64, i32) addrspace(4)

; Function Attrs: alwaysinline convergent mustprogress nounwind
define internal spir_func noundef i32 @_ZL22__hip_get_thread_idx_xv() addrspace(4) #8 {
entry:
  %retval = alloca i32, align 4
  %retval.ascast = addrspacecast ptr %retval to ptr addrspace(4)
  %call = call spir_func addrspace(4) i64 @__ockl_get_local_id(i32 noundef 0) #12
  %conv = trunc i64 %call to i32
  ret i32 %conv
}

; Function Attrs: convergent nounwind willreturn memory(none)
declare spir_func i64 @__ockl_get_local_id(i32 noundef) addrspace(4) #9

; Function Attrs: alwaysinline convergent mustprogress nounwind
define internal spir_func noundef i32 @_ZL21__hip_get_block_idx_xv() addrspace(4) #8 {
entry:
  %retval = alloca i32, align 4
  %retval.ascast = addrspacecast ptr %retval to ptr addrspace(4)
  %call = call spir_func addrspace(4) i64 @__ockl_get_group_id(i32 noundef 0) #12
  %conv = trunc i64 %call to i32
  ret i32 %conv
}

; Function Attrs: convergent nounwind willreturn memory(none)
declare spir_func i64 @__ockl_get_group_id(i32 noundef) addrspace(4) #9

attributes #0 = { convergent mustprogress noreturn nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #1 = { cold noreturn nounwind memory(inaccessiblemem: write) }
attributes #2 = { convergent mustprogress noinline nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #3 = { nocallback nofree nosync nounwind willreturn memory(argmem: readwrite) }
attributes #4 = { nocallback nofree nounwind willreturn memory(argmem: readwrite) }
attributes #5 = { convergent nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #6 = { convergent mustprogress nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #7 = { convergent mustprogress norecurse nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" "uniform-work-group-size"="true" }
attributes #8 = { alwaysinline convergent mustprogress nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #9 = { convergent nounwind willreturn memory(none) "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #10 = { nounwind }
attributes #11 = { convergent nounwind }
attributes #12 = { convergent nounwind willreturn memory(none) }

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
!6 = !{!"clang version 22.0.0git (https://github.com/llvm/llvm-project 6f7ea34933649d16845b1635d1e97f9ccb35ffea+PATCHED)"}
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
!23 = !{!24, !24, i64 0}
!24 = !{!"long", !9, i64 0}
!25 = !{i32 1024, i32 1, i32 1}
