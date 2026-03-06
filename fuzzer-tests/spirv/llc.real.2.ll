; ModuleID = './llc.real.2.bc'
source_filename = "/testing/fuzzer-all-hip-files/23fc6e3146d34cb4777449148de1db7d.hip"
target datalayout = "e-i64:64-v16:16-v24:32-v32:32-v48:64-v96:128-v192:256-v256:256-v512:512-v1024:1024-n32:64-S32-G1-P4-A0"
target triple = "spirv64-amd-amdhsa"

%struct.DWordS_struct = type { i32, i8 }
%struct.QuadWordS_struct = type { i32, double }
%struct.LargeS_struct = type { i32, double, ptr addrspace(4), i32 }

@__const.__assert_fail.fmt = private unnamed_addr addrspace(1) constant [47 x i8] c"%s:%u: %s: Device-side assertion `%s' failed.\0A\00", align 16
@.str = private unnamed_addr addrspace(1) constant [4 x i8] c"abc\00", align 1
@.str.1 = private unnamed_addr addrspace(1) constant [4 x i8] c"def\00", align 1
@.str.2 = private unnamed_addr addrspace(1) constant [14 x i8] c"10 args done!\00", align 1
@__const._Z24hip_adapted_varargs_testi.s_arr = private unnamed_addr addrspace(1) constant [3 x ptr addrspace(4)] [ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str to ptr addrspace(4)), ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.1 to ptr addrspace(4)), ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.2 to ptr addrspace(4))], align 16
@__const._Z24hip_adapted_varargs_testi.ints = private unnamed_addr addrspace(1) constant [6 x i32] [i32 -127, i32 127, i32 70, i32 7, i32 164, i32 9], align 16
@__const._Z24hip_adapted_varargs_testi.doubles = private unnamed_addr addrspace(1) constant [4 x double] [double 1.060000e+01, double 6.700000e+00, double 2.400000e+00, double 3.400000e+00], align 16
@__const._Z24hip_adapted_varargs_testi.lls = private unnamed_addr addrspace(1) constant [1 x i64] [i64 12345677823423], align 8
@__const._Z24hip_adapted_varargs_testi.chars = private unnamed_addr addrspace(1) constant [1 x i8] c"a", align 1
@__const._Z24hip_adapted_varargs_testi.dw = private unnamed_addr addrspace(1) constant %struct.DWordS_struct { i32 331201, i8 97 }, align 4
@__const._Z24hip_adapted_varargs_testi.qw = private unnamed_addr addrspace(1) constant %struct.QuadWordS_struct { i32 23, double 4.600000e+00 }, align 8
@.str.3 = private unnamed_addr addrspace(1) constant [11 x i8] c"ssiciiiiis\00", align 1
@.str.4 = private unnamed_addr addrspace(1) constant [5 x i8] c"ddil\00", align 1
@.str.5 = private unnamed_addr addrspace(1) constant [4 x i8] c"DQL\00", align 1
@__const._Z24hip_adapted_varargs_testi.fmts = private unnamed_addr addrspace(1) constant [3 x ptr addrspace(4)] [ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.3 to ptr addrspace(4)), ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.4 to ptr addrspace(4)), ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.5 to ptr addrspace(4))], align 16
@.str.6 = private unnamed_addr addrspace(1) constant [20 x i8] c"[tid %d] string %s\0A\00", align 1
@.str.7 = private unnamed_addr addrspace(1) constant [17 x i8] c"[tid %d] int %d\0A\00", align 1
@.str.8 = private unnamed_addr addrspace(1) constant [20 x i8] c"[tid %d] double %f\0A\00", align 1
@.str.9 = private unnamed_addr addrspace(1) constant [25 x i8] c"[tid %d] long long %lld\0A\00", align 1
@.str.10 = private unnamed_addr addrspace(1) constant [18 x i8] c"[tid %d] char %c\0A\00", align 1
@.str.11 = private unnamed_addr addrspace(1) constant [27 x i8] c"[tid %d] DWord { %d, %c }\0A\00", align 1
@.str.12 = private unnamed_addr addrspace(1) constant [30 x i8] c"[tid %d] QuadWord { %d, %f }\0A\00", align 1
@.str.13 = private unnamed_addr addrspace(1) constant [38 x i8] c"[tid %d] LargeS { %d, %f, 0x%d, %d }\0A\00", align 1
@.str.14 = private unnamed_addr addrspace(1) constant [28 x i8] c"[tid %d] unknown format %c\0A\00", align 1
@__hip_cuid_fbd08362f22b90b4 = addrspace(1) global i8 0
@llvm.embedded.module = private addrspace(1) constant [0 x i8] zeroinitializer, section ".llvmbc", align 1
@llvm.cmdline = private addrspace(1) constant [2228 x i8] c"-cc1\00-fmessage-length=146\00-ferror-limit\0019\00-fcolor-diagnostics\00-mllvm\00-amdgpu-internalize-symbols\00-aux-triple\00x86_64-unknown-linux-gnu\00-disable-free\00-emit-llvm-bc\00-aux-target-cpu\00x86-64\00-triple\00spirv64-amd-amdhsa\00-resource-dir\00/COW/2025-12-22/trunk_22.0-0/lib/clang/22\00-iwithprefix\00/opt/rocm/include\00-isystem\00/COW/2025-12-22/trunk_22.0-0/lib/clang/22/include/cuda_wrappers\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/x86_64-linux-gnu/c++/13\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13/backward\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/x86_64-linux-gnu/c++/13\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../include/c++/13/backward\00-isystem\00/COW/2025-12-22/trunk_22.0-0/lib/clang/22/include\00-isystem\00/usr/local/include\00-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../x86_64-linux-gnu/include\00-internal-externc-isystem\00/usr/include/x86_64-linux-gnu\00-internal-externc-isystem\00/include\00-internal-externc-isystem\00/usr/include\00-internal-isystem\00/COW/2025-12-22/trunk_22.0-0/lib/clang/22/include\00-internal-isystem\00/usr/local/include\00-internal-isystem\00/usr/lib/gcc/x86_64-linux-gnu/13/../../../../x86_64-linux-gnu/include\00-internal-externc-isystem\00/usr/include/x86_64-linux-gnu\00-internal-externc-isystem\00/include\00-internal-externc-isystem\00/usr/include\00-std=gnu++17\00-cuid=d4eb2a71776bc6e2\00-fhip-new-launch-api\00-fcxx-exceptions\00-fexceptions\00-fskip-odr-check-in-gmf\00-fno-threadsafe-statics\00-pic-level\002\00-fdeprecated-macro\00-fcuda-is-device\00-fgnuc-version=4.2.1\00-fconvergent-functions\00-ffp-contract=fast-honor-pragmas\00-fno-experimental-relative-c++-abi-vtables\00-fno-file-reproducible\00-O1\00-fno-autolink\00-fembed-bitcode=marker\00-fdebug-compilation-dir=/testing\00-fcoverage-compilation-dir=/testing\00-debugger-tuning=gdb\00-disable-llvm-passes\00-mconstructor-aliases\00-clear-ast-before-backend\00-emit-llvm-uselists\00-main-file-name\0023fc6e3146d34cb4777449148de1db7d.hip\00-mframe-pointer=all\00-finline-functions\00-fno-loop-interchange\00-fdiagnostics-hotness-threshold=0\00-fdiagnostics-misexpect-tolerance=0\00-include\00__clang_hip_runtime_wrapper.h\00", section ".llvmcmd", align 1
@llvm.compiler.used = appending addrspace(1) global [3 x ptr addrspace(4)] [ptr addrspace(4) addrspacecast (ptr addrspace(1) @__hip_cuid_fbd08362f22b90b4 to ptr addrspace(4)), ptr addrspace(4) addrspacecast (ptr addrspace(1) @llvm.embedded.module to ptr addrspace(4)), ptr addrspace(4) addrspacecast (ptr addrspace(1) @llvm.cmdline to ptr addrspace(4))], section "llvm.metadata"

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
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %fmt) #7
  call addrspace(4) void @llvm.memcpy.p4.p1.i64(ptr addrspace(4) align 16 %fmt.ascast, ptr addrspace(1) align 16 @__const.__assert_fail.fmt, i64 47, i1 false)
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %msg) #7
  %call = call spir_func addrspace(4) i64 @__ockl_fprintf_stderr_begin() #8
  store i64 %call, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %len) #7
  store i32 0, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  br label %do.body

do.body:                                          ; preds = %entry
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %tmp) #7
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
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %tmp) #7
  br label %do.cond

do.cond:                                          ; preds = %while.end
  br label %do.end

do.end:                                           ; preds = %do.cond
  %3 = load i64, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %arraydecay2 = getelementptr inbounds [47 x i8], ptr addrspace(4) %fmt.ascast, i64 0, i64 0
  %4 = load i32, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  %conv3 = sext i32 %4 to i64
  %call4 = call spir_func addrspace(4) i64 @__ockl_fprintf_append_string_n(i64 noundef %3, ptr addrspace(4) noundef %arraydecay2, i64 noundef %conv3, i32 noundef 0) #8
  store i64 %call4, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  br label %do.body5

do.body5:                                         ; preds = %do.end
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %tmp6) #7
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
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %tmp6) #7
  br label %do.cond16

do.cond16:                                        ; preds = %while.end11
  br label %do.end17

do.end17:                                         ; preds = %do.cond16
  %10 = load i64, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %11 = load ptr addrspace(4), ptr addrspace(4) %file.addr.ascast, align 8, !tbaa !11
  %12 = load i32, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  %conv18 = sext i32 %12 to i64
  %call19 = call spir_func addrspace(4) i64 @__ockl_fprintf_append_string_n(i64 noundef %10, ptr addrspace(4) noundef %11, i64 noundef %conv18, i32 noundef 0) #8
  store i64 %call19, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %13 = load i64, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %14 = load i32, ptr addrspace(4) %line.addr.ascast, align 4, !tbaa !7
  %conv20 = zext i32 %14 to i64
  %call21 = call spir_func addrspace(4) i64 @__ockl_fprintf_append_args(i64 noundef %13, i32 noundef 1, i64 noundef %conv20, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i64 noundef 0, i32 noundef 0) #8
  store i64 %call21, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  br label %do.body22

do.body22:                                        ; preds = %do.end17
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %tmp23) #7
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
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %tmp23) #7
  br label %do.cond33

do.cond33:                                        ; preds = %while.end28
  br label %do.end34

do.end34:                                         ; preds = %do.cond33
  %20 = load i64, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %21 = load ptr addrspace(4), ptr addrspace(4) %function.addr.ascast, align 8, !tbaa !11
  %22 = load i32, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  %conv35 = sext i32 %22 to i64
  %call36 = call spir_func addrspace(4) i64 @__ockl_fprintf_append_string_n(i64 noundef %20, ptr addrspace(4) noundef %21, i64 noundef %conv35, i32 noundef 0) #8
  store i64 %call36, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  br label %do.body37

do.body37:                                        ; preds = %do.end34
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %tmp38) #7
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
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %tmp38) #7
  br label %do.cond48

do.cond48:                                        ; preds = %while.end43
  br label %do.end49

do.end49:                                         ; preds = %do.cond48
  %28 = load i64, ptr addrspace(4) %msg.ascast, align 8, !tbaa !14
  %29 = load ptr addrspace(4), ptr addrspace(4) %assertion.addr.ascast, align 8, !tbaa !11
  %30 = load i32, ptr addrspace(4) %len.ascast, align 4, !tbaa !7
  %conv50 = sext i32 %30 to i64
  %call51 = call spir_func addrspace(4) i64 @__ockl_fprintf_append_string_n(i64 noundef %28, ptr addrspace(4) noundef %29, i64 noundef %conv50, i32 noundef 1) #8
  call addrspace(4) void @llvm.trap()
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %len) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %msg) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %fmt) #7
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

; Function Attrs: convergent mustprogress norecurse nounwind
define spir_kernel void @_Z24hip_adapted_varargs_testi(i32 noundef %seed) addrspace(4) #6 !max_work_group_size !23 {
entry:
  %seed.addr = alloca i32, align 4
  %tid = alloca i32, align 4
  %s_arr = alloca [3 x ptr addrspace(4)], align 16
  %ints = alloca [6 x i32], align 16
  %doubles = alloca [4 x double], align 16
  %lls = alloca [1 x i64], align 8
  %chars = alloca [1 x i8], align 1
  %dw = alloca %struct.DWordS_struct, align 4
  %qw = alloca %struct.QuadWordS_struct, align 8
  %ls = alloca %struct.LargeS_struct, align 8
  %fmts = alloca [3 x ptr addrspace(4)], align 16
  %scenario = alloca i32, align 4
  %fmt = alloca ptr addrspace(4), align 8
  %si = alloca i32, align 4
  %ii = alloca i32, align 4
  %di = alloca i32, align 4
  %li = alloca i32, align 4
  %ci = alloca i32, align 4
  %struct_stage = alloca i32, align 4
  %loop_break_16841 = alloca i32, align 4
  %loop_break_17053 = alloca i32, align 4
  %p = alloca ptr addrspace(4), align 8
  %cleanup.dest.slot = alloca i32, align 4
  %ch = alloca i8, align 1
  %s = alloca ptr addrspace(4), align 8
  %v = alloca i32, align 4
  %v20 = alloca double, align 8
  %v29 = alloca i64, align 8
  %v38 = alloca i8, align 1
  %local = alloca %struct.DWordS_struct, align 4
  %local55 = alloca %struct.QuadWordS_struct, align 8
  %local70 = alloca %struct.LargeS_struct, align 8
  %has_ptr = alloca i32, align 4
  %seed.addr.ascast = addrspacecast ptr %seed.addr to ptr addrspace(4)
  %tid.ascast = addrspacecast ptr %tid to ptr addrspace(4)
  %s_arr.ascast = addrspacecast ptr %s_arr to ptr addrspace(4)
  %ints.ascast = addrspacecast ptr %ints to ptr addrspace(4)
  %doubles.ascast = addrspacecast ptr %doubles to ptr addrspace(4)
  %lls.ascast = addrspacecast ptr %lls to ptr addrspace(4)
  %chars.ascast = addrspacecast ptr %chars to ptr addrspace(4)
  %dw.ascast = addrspacecast ptr %dw to ptr addrspace(4)
  %qw.ascast = addrspacecast ptr %qw to ptr addrspace(4)
  %ls.ascast = addrspacecast ptr %ls to ptr addrspace(4)
  %fmts.ascast = addrspacecast ptr %fmts to ptr addrspace(4)
  %scenario.ascast = addrspacecast ptr %scenario to ptr addrspace(4)
  %fmt.ascast = addrspacecast ptr %fmt to ptr addrspace(4)
  %si.ascast = addrspacecast ptr %si to ptr addrspace(4)
  %ii.ascast = addrspacecast ptr %ii to ptr addrspace(4)
  %di.ascast = addrspacecast ptr %di to ptr addrspace(4)
  %li.ascast = addrspacecast ptr %li to ptr addrspace(4)
  %ci.ascast = addrspacecast ptr %ci to ptr addrspace(4)
  %struct_stage.ascast = addrspacecast ptr %struct_stage to ptr addrspace(4)
  %loop_break_16841.ascast = addrspacecast ptr %loop_break_16841 to ptr addrspace(4)
  %loop_break_17053.ascast = addrspacecast ptr %loop_break_17053 to ptr addrspace(4)
  %p.ascast = addrspacecast ptr %p to ptr addrspace(4)
  %cleanup.dest.slot.ascast = addrspacecast ptr %cleanup.dest.slot to ptr addrspace(4)
  %ch.ascast = addrspacecast ptr %ch to ptr addrspace(4)
  %s.ascast = addrspacecast ptr %s to ptr addrspace(4)
  %v.ascast = addrspacecast ptr %v to ptr addrspace(4)
  %v20.ascast = addrspacecast ptr %v20 to ptr addrspace(4)
  %v29.ascast = addrspacecast ptr %v29 to ptr addrspace(4)
  %v38.ascast = addrspacecast ptr %v38 to ptr addrspace(4)
  %local.ascast = addrspacecast ptr %local to ptr addrspace(4)
  %local55.ascast = addrspacecast ptr %local55 to ptr addrspace(4)
  %local70.ascast = addrspacecast ptr %local70 to ptr addrspace(4)
  %has_ptr.ascast = addrspacecast ptr %has_ptr to ptr addrspace(4)
  store i32 %seed, ptr addrspace(4) %seed.addr.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %tid) #7
  store i32 959192, ptr addrspace(4) %tid.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %s_arr) #7
  call addrspace(4) void @llvm.memcpy.p4.p1.i64(ptr addrspace(4) align 16 %s_arr.ascast, ptr addrspace(1) align 16 @__const._Z24hip_adapted_varargs_testi.s_arr, i64 24, i1 false)
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %ints) #7
  call addrspace(4) void @llvm.memcpy.p4.p1.i64(ptr addrspace(4) align 16 %ints.ascast, ptr addrspace(1) align 16 @__const._Z24hip_adapted_varargs_testi.ints, i64 24, i1 false)
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %doubles) #7
  call addrspace(4) void @llvm.memcpy.p4.p1.i64(ptr addrspace(4) align 16 %doubles.ascast, ptr addrspace(1) align 16 @__const._Z24hip_adapted_varargs_testi.doubles, i64 32, i1 false)
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %lls) #7
  call addrspace(4) void @llvm.memcpy.p4.p1.i64(ptr addrspace(4) align 8 %lls.ascast, ptr addrspace(1) align 8 @__const._Z24hip_adapted_varargs_testi.lls, i64 8, i1 false)
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %chars) #7
  call addrspace(4) void @llvm.memcpy.p4.p1.i64(ptr addrspace(4) align 1 %chars.ascast, ptr addrspace(1) align 1 @__const._Z24hip_adapted_varargs_testi.chars, i64 1, i1 false)
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %dw) #7
  call addrspace(4) void @llvm.memcpy.p4.p1.i64(ptr addrspace(4) align 4 %dw.ascast, ptr addrspace(1) align 4 @__const._Z24hip_adapted_varargs_testi.dw, i64 8, i1 false)
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %qw) #7
  call addrspace(4) void @llvm.memcpy.p4.p1.i64(ptr addrspace(4) align 8 %qw.ascast, ptr addrspace(1) align 8 @__const._Z24hip_adapted_varargs_testi.qw, i64 16, i1 false)
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %ls) #7
  %i = getelementptr inbounds nuw %struct.LargeS_struct, ptr addrspace(4) %ls.ascast, i32 0, i32 0
  store i32 20, ptr addrspace(4) %i, align 8, !tbaa !24
  %d = getelementptr inbounds nuw %struct.LargeS_struct, ptr addrspace(4) %ls.ascast, i32 0, i32 1
  store double 6.300000e+00, ptr addrspace(4) %d, align 8, !tbaa !28
  %ptr = getelementptr inbounds nuw %struct.LargeS_struct, ptr addrspace(4) %ls.ascast, i32 0, i32 2
  store ptr addrspace(4) %dw.ascast, ptr addrspace(4) %ptr, align 8, !tbaa !29
  %j = getelementptr inbounds nuw %struct.LargeS_struct, ptr addrspace(4) %ls.ascast, i32 0, i32 3
  store i32 19, ptr addrspace(4) %j, align 8, !tbaa !30
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %fmts) #7
  call addrspace(4) void @llvm.memcpy.p4.p1.i64(ptr addrspace(4) align 16 %fmts.ascast, ptr addrspace(1) align 16 @__const._Z24hip_adapted_varargs_testi.fmts, i64 24, i1 false)
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %scenario) #7
  %0 = load i32, ptr addrspace(4) %tid.ascast, align 4, !tbaa !7
  %rem = srem i32 %0, 1
  store i32 %rem, ptr addrspace(4) %scenario.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %fmt) #7
  %1 = load i32, ptr addrspace(4) %scenario.ascast, align 4, !tbaa !7
  %idxprom = sext i32 %1 to i64
  %arrayidx = getelementptr inbounds [3 x ptr addrspace(4)], ptr addrspace(4) %fmts.ascast, i64 0, i64 %idxprom
  %2 = load ptr addrspace(4), ptr addrspace(4) %arrayidx, align 8, !tbaa !11
  store ptr addrspace(4) %2, ptr addrspace(4) %fmt.ascast, align 8, !tbaa !11
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %si) #7
  store i32 -9, ptr addrspace(4) %si.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %ii) #7
  store i32 -9, ptr addrspace(4) %ii.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %di) #7
  store i32 40, ptr addrspace(4) %di.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %li) #7
  store i32 0, ptr addrspace(4) %li.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %ci) #7
  store i32 -9, ptr addrspace(4) %ci.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %struct_stage) #7
  store i32 2, ptr addrspace(4) %struct_stage.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %loop_break_16841) #7
  store i32 -1, ptr addrspace(4) %loop_break_16841.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %loop_break_17053) #7
  store i32 0, ptr addrspace(4) %loop_break_17053.ascast, align 4, !tbaa !7
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %p) #7
  %3 = load ptr addrspace(4), ptr addrspace(4) %fmt.ascast, align 8, !tbaa !11
  store ptr addrspace(4) %3, ptr addrspace(4) %p.ascast, align 8, !tbaa !11
  br label %for.cond

for.cond:                                         ; preds = %for.inc, %entry
  %4 = load ptr addrspace(4), ptr addrspace(4) %p.ascast, align 8, !tbaa !11
  %5 = load i8, ptr addrspace(4) %4, align 1, !tbaa !16
  %conv = sext i8 %5 to i32
  %cmp = icmp ne i32 %conv, 0
  br i1 %cmp, label %for.body, label %for.cond.cleanup

for.cond.cleanup:                                 ; preds = %for.cond
  store i32 2, ptr addrspace(4) %cleanup.dest.slot.ascast, align 4
  br label %cleanup

for.body:                                         ; preds = %for.cond
  %6 = load i32, ptr addrspace(4) %loop_break_17053.ascast, align 4, !tbaa !7
  %inc = add nsw i32 %6, 1
  store i32 %inc, ptr addrspace(4) %loop_break_17053.ascast, align 4, !tbaa !7
  %7 = load i32, ptr addrspace(4) %loop_break_17053.ascast, align 4, !tbaa !7
  %cmp1 = icmp sle i32 %7, 2
  br i1 %cmp1, label %if.then, label %if.end

if.then:                                          ; preds = %for.body
  br label %for.inc

if.end:                                           ; preds = %for.body
  %8 = load i32, ptr addrspace(4) %loop_break_16841.ascast, align 4, !tbaa !7
  %inc2 = add nsw i32 %8, 1
  store i32 %inc2, ptr addrspace(4) %loop_break_16841.ascast, align 4, !tbaa !7
  %9 = load i32, ptr addrspace(4) %loop_break_16841.ascast, align 4, !tbaa !7
  %cmp3 = icmp sle i32 %9, 33701
  br i1 %cmp3, label %if.then4, label %if.end5

if.then4:                                         ; preds = %if.end
  store i32 2, ptr addrspace(4) %cleanup.dest.slot.ascast, align 4
  br label %cleanup

if.end5:                                          ; preds = %if.end
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %ch) #7
  %10 = load ptr addrspace(4), ptr addrspace(4) %p.ascast, align 8, !tbaa !11
  %11 = load i8, ptr addrspace(4) %10, align 1, !tbaa !16
  store i8 %11, ptr addrspace(4) %ch.ascast, align 1, !tbaa !16
  %12 = load i8, ptr addrspace(4) %ch.ascast, align 1, !tbaa !16
  %conv6 = sext i8 %12 to i32
  switch i32 %conv6, label %sw.default [
    i32 115, label %sw.bb
    i32 105, label %sw.bb14
    i32 100, label %sw.bb19
    i32 108, label %sw.bb28
    i32 99, label %sw.bb37
    i32 68, label %sw.bb47
    i32 81, label %sw.bb54
    i32 76, label %sw.bb69
  ]

sw.bb:                                            ; preds = %if.end5
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %s) #7
  %13 = load i32, ptr addrspace(4) %si.ascast, align 4, !tbaa !7
  %rem7 = srem i32 %13, 3
  %idxprom8 = sext i32 %rem7 to i64
  %arrayidx9 = getelementptr inbounds [3 x ptr addrspace(4)], ptr addrspace(4) %s_arr.ascast, i64 0, i64 %idxprom8
  %14 = load ptr addrspace(4), ptr addrspace(4) %arrayidx9, align 8, !tbaa !11
  store ptr addrspace(4) %14, ptr addrspace(4) %s.ascast, align 8, !tbaa !11
  %15 = load i32, ptr addrspace(4) %tid.ascast, align 4, !tbaa !7
  %16 = load ptr addrspace(4), ptr addrspace(4) %s.ascast, align 8, !tbaa !11
  %17 = call addrspace(4) i64 @__ockl_printf_begin(i64 0)
  %18 = icmp eq ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.6 to ptr addrspace(4)), null
  br i1 %18, label %strlen.join, label %strlen.while

strlen.while:                                     ; preds = %strlen.while, %sw.bb
  %19 = phi ptr addrspace(4) [ addrspacecast (ptr addrspace(1) @.str.6 to ptr addrspace(4)), %sw.bb ], [ %20, %strlen.while ]
  %20 = getelementptr i8, ptr addrspace(4) %19, i64 1
  %21 = load i8, ptr addrspace(4) %19, align 1
  %22 = icmp eq i8 %21, 0
  br i1 %22, label %strlen.while.done, label %strlen.while

strlen.while.done:                                ; preds = %strlen.while
  %23 = ptrtoint ptr addrspace(4) %19 to i64
  %24 = sub i64 %23, ptrtoint (ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.6 to ptr addrspace(4)) to i64)
  %25 = add i64 %24, 1
  br label %strlen.join

strlen.join:                                      ; preds = %strlen.while.done, %sw.bb
  %26 = phi i64 [ %25, %strlen.while.done ], [ 0, %sw.bb ]
  %27 = call addrspace(4) i64 @__ockl_printf_append_string_n(i64 %17, ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.6 to ptr addrspace(4)), i64 %26, i32 0)
  %28 = zext i32 %15 to i64
  %29 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %27, i32 1, i64 %28, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 0)
  %30 = icmp eq ptr addrspace(4) %16, null
  br i1 %30, label %strlen.join10, label %strlen.while11

strlen.while11:                                   ; preds = %strlen.while11, %strlen.join
  %31 = phi ptr addrspace(4) [ %16, %strlen.join ], [ %32, %strlen.while11 ]
  %32 = getelementptr i8, ptr addrspace(4) %31, i64 1
  %33 = load i8, ptr addrspace(4) %31, align 1
  %34 = icmp eq i8 %33, 0
  br i1 %34, label %strlen.while.done12, label %strlen.while11

strlen.while.done12:                              ; preds = %strlen.while11
  %35 = ptrtoint ptr addrspace(4) %16 to i64
  %36 = ptrtoint ptr addrspace(4) %31 to i64
  %37 = sub i64 %36, %35
  %38 = add i64 %37, 1
  br label %strlen.join10

strlen.join10:                                    ; preds = %strlen.while.done12, %strlen.join
  %39 = phi i64 [ %38, %strlen.while.done12 ], [ 0, %strlen.join ]
  %40 = call addrspace(4) i64 @__ockl_printf_append_string_n(i64 %29, ptr addrspace(4) %16, i64 %39, i32 1)
  %41 = trunc i64 %40 to i32
  %42 = load i32, ptr addrspace(4) %si.ascast, align 4, !tbaa !7
  %inc13 = add nsw i32 %42, 1
  store i32 %inc13, ptr addrspace(4) %si.ascast, align 4, !tbaa !7
  store i32 5, ptr addrspace(4) %cleanup.dest.slot.ascast, align 4
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %s) #7
  br label %sw.epilog

sw.bb14:                                          ; preds = %if.end5
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %v) #7
  store i32 -9, ptr addrspace(4) %v.ascast, align 4, !tbaa !7
  %43 = load i32, ptr addrspace(4) %tid.ascast, align 4, !tbaa !7
  %44 = load i32, ptr addrspace(4) %v.ascast, align 4, !tbaa !7
  %45 = call addrspace(4) i64 @__ockl_printf_begin(i64 0)
  %46 = icmp eq ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.7 to ptr addrspace(4)), null
  br i1 %46, label %strlen.join15, label %strlen.while16

strlen.while16:                                   ; preds = %strlen.while16, %sw.bb14
  %47 = phi ptr addrspace(4) [ addrspacecast (ptr addrspace(1) @.str.7 to ptr addrspace(4)), %sw.bb14 ], [ %48, %strlen.while16 ]
  %48 = getelementptr i8, ptr addrspace(4) %47, i64 1
  %49 = load i8, ptr addrspace(4) %47, align 1
  %50 = icmp eq i8 %49, 0
  br i1 %50, label %strlen.while.done17, label %strlen.while16

strlen.while.done17:                              ; preds = %strlen.while16
  %51 = ptrtoint ptr addrspace(4) %47 to i64
  %52 = sub i64 %51, ptrtoint (ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.7 to ptr addrspace(4)) to i64)
  %53 = add i64 %52, 1
  br label %strlen.join15

strlen.join15:                                    ; preds = %strlen.while.done17, %sw.bb14
  %54 = phi i64 [ %53, %strlen.while.done17 ], [ 0, %sw.bb14 ]
  %55 = call addrspace(4) i64 @__ockl_printf_append_string_n(i64 %45, ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.7 to ptr addrspace(4)), i64 %54, i32 0)
  %56 = zext i32 %43 to i64
  %57 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %55, i32 1, i64 %56, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 0)
  %58 = zext i32 %44 to i64
  %59 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %57, i32 1, i64 %58, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 1)
  %60 = trunc i64 %59 to i32
  %61 = load i32, ptr addrspace(4) %ii.ascast, align 4, !tbaa !7
  %inc18 = add nsw i32 %61, 1
  store i32 %inc18, ptr addrspace(4) %ii.ascast, align 4, !tbaa !7
  store i32 5, ptr addrspace(4) %cleanup.dest.slot.ascast, align 4
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %v) #7
  br label %sw.epilog

sw.bb19:                                          ; preds = %if.end5
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %v20) #7
  %62 = load i32, ptr addrspace(4) %di.ascast, align 4, !tbaa !7
  %rem21 = srem i32 %62, 4
  %idxprom22 = sext i32 %rem21 to i64
  %arrayidx23 = getelementptr inbounds [4 x double], ptr addrspace(4) %doubles.ascast, i64 0, i64 %idxprom22
  %63 = load double, ptr addrspace(4) %arrayidx23, align 8, !tbaa !31
  store double %63, ptr addrspace(4) %v20.ascast, align 8, !tbaa !31
  %64 = load i32, ptr addrspace(4) %tid.ascast, align 4, !tbaa !7
  %65 = load double, ptr addrspace(4) %v20.ascast, align 8, !tbaa !31
  %66 = call addrspace(4) i64 @__ockl_printf_begin(i64 0)
  %67 = icmp eq ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.8 to ptr addrspace(4)), null
  br i1 %67, label %strlen.join24, label %strlen.while25

strlen.while25:                                   ; preds = %strlen.while25, %sw.bb19
  %68 = phi ptr addrspace(4) [ addrspacecast (ptr addrspace(1) @.str.8 to ptr addrspace(4)), %sw.bb19 ], [ %69, %strlen.while25 ]
  %69 = getelementptr i8, ptr addrspace(4) %68, i64 1
  %70 = load i8, ptr addrspace(4) %68, align 1
  %71 = icmp eq i8 %70, 0
  br i1 %71, label %strlen.while.done26, label %strlen.while25

strlen.while.done26:                              ; preds = %strlen.while25
  %72 = ptrtoint ptr addrspace(4) %68 to i64
  %73 = sub i64 %72, ptrtoint (ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.8 to ptr addrspace(4)) to i64)
  %74 = add i64 %73, 1
  br label %strlen.join24

strlen.join24:                                    ; preds = %strlen.while.done26, %sw.bb19
  %75 = phi i64 [ %74, %strlen.while.done26 ], [ 0, %sw.bb19 ]
  %76 = call addrspace(4) i64 @__ockl_printf_append_string_n(i64 %66, ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.8 to ptr addrspace(4)), i64 %75, i32 0)
  %77 = zext i32 %64 to i64
  %78 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %76, i32 1, i64 %77, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 0)
  %79 = bitcast double %65 to i64
  %80 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %78, i32 1, i64 %79, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 1)
  %81 = trunc i64 %80 to i32
  %82 = load i32, ptr addrspace(4) %di.ascast, align 4, !tbaa !7
  %inc27 = add nsw i32 %82, 1
  store i32 %inc27, ptr addrspace(4) %di.ascast, align 4, !tbaa !7
  store i32 5, ptr addrspace(4) %cleanup.dest.slot.ascast, align 4
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %v20) #7
  br label %sw.epilog

sw.bb28:                                          ; preds = %if.end5
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %v29) #7
  %83 = load i32, ptr addrspace(4) %li.ascast, align 4, !tbaa !7
  %rem30 = srem i32 %83, 1
  %idxprom31 = sext i32 %rem30 to i64
  %arrayidx32 = getelementptr inbounds [1 x i64], ptr addrspace(4) %lls.ascast, i64 0, i64 %idxprom31
  %84 = load i64, ptr addrspace(4) %arrayidx32, align 8, !tbaa !14
  store i64 %84, ptr addrspace(4) %v29.ascast, align 8, !tbaa !14
  %85 = load i32, ptr addrspace(4) %tid.ascast, align 4, !tbaa !7
  %86 = load i64, ptr addrspace(4) %v29.ascast, align 8, !tbaa !14
  %87 = call addrspace(4) i64 @__ockl_printf_begin(i64 0)
  %88 = icmp eq ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.9 to ptr addrspace(4)), null
  br i1 %88, label %strlen.join33, label %strlen.while34

strlen.while34:                                   ; preds = %strlen.while34, %sw.bb28
  %89 = phi ptr addrspace(4) [ addrspacecast (ptr addrspace(1) @.str.9 to ptr addrspace(4)), %sw.bb28 ], [ %90, %strlen.while34 ]
  %90 = getelementptr i8, ptr addrspace(4) %89, i64 1
  %91 = load i8, ptr addrspace(4) %89, align 1
  %92 = icmp eq i8 %91, 0
  br i1 %92, label %strlen.while.done35, label %strlen.while34

strlen.while.done35:                              ; preds = %strlen.while34
  %93 = ptrtoint ptr addrspace(4) %89 to i64
  %94 = sub i64 %93, ptrtoint (ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.9 to ptr addrspace(4)) to i64)
  %95 = add i64 %94, 1
  br label %strlen.join33

strlen.join33:                                    ; preds = %strlen.while.done35, %sw.bb28
  %96 = phi i64 [ %95, %strlen.while.done35 ], [ 0, %sw.bb28 ]
  %97 = call addrspace(4) i64 @__ockl_printf_append_string_n(i64 %87, ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.9 to ptr addrspace(4)), i64 %96, i32 0)
  %98 = zext i32 %85 to i64
  %99 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %97, i32 1, i64 %98, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 0)
  %100 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %99, i32 1, i64 %86, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 1)
  %101 = trunc i64 %100 to i32
  %102 = load i32, ptr addrspace(4) %li.ascast, align 4, !tbaa !7
  %inc36 = add nsw i32 %102, 1
  store i32 %inc36, ptr addrspace(4) %li.ascast, align 4, !tbaa !7
  store i32 5, ptr addrspace(4) %cleanup.dest.slot.ascast, align 4
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %v29) #7
  br label %sw.epilog

sw.bb37:                                          ; preds = %if.end5
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %v38) #7
  %103 = load i32, ptr addrspace(4) %ci.ascast, align 4, !tbaa !7
  %rem39 = srem i32 %103, 1
  %idxprom40 = sext i32 %rem39 to i64
  %arrayidx41 = getelementptr inbounds [1 x i8], ptr addrspace(4) %chars.ascast, i64 0, i64 %idxprom40
  %104 = load i8, ptr addrspace(4) %arrayidx41, align 1, !tbaa !16
  store i8 %104, ptr addrspace(4) %v38.ascast, align 1, !tbaa !16
  %105 = load i32, ptr addrspace(4) %tid.ascast, align 4, !tbaa !7
  %106 = load i8, ptr addrspace(4) %v38.ascast, align 1, !tbaa !16
  %conv42 = sext i8 %106 to i32
  %107 = call addrspace(4) i64 @__ockl_printf_begin(i64 0)
  %108 = icmp eq ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.10 to ptr addrspace(4)), null
  br i1 %108, label %strlen.join43, label %strlen.while44

strlen.while44:                                   ; preds = %strlen.while44, %sw.bb37
  %109 = phi ptr addrspace(4) [ addrspacecast (ptr addrspace(1) @.str.10 to ptr addrspace(4)), %sw.bb37 ], [ %110, %strlen.while44 ]
  %110 = getelementptr i8, ptr addrspace(4) %109, i64 1
  %111 = load i8, ptr addrspace(4) %109, align 1
  %112 = icmp eq i8 %111, 0
  br i1 %112, label %strlen.while.done45, label %strlen.while44

strlen.while.done45:                              ; preds = %strlen.while44
  %113 = ptrtoint ptr addrspace(4) %109 to i64
  %114 = sub i64 %113, ptrtoint (ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.10 to ptr addrspace(4)) to i64)
  %115 = add i64 %114, 1
  br label %strlen.join43

strlen.join43:                                    ; preds = %strlen.while.done45, %sw.bb37
  %116 = phi i64 [ %115, %strlen.while.done45 ], [ 0, %sw.bb37 ]
  %117 = call addrspace(4) i64 @__ockl_printf_append_string_n(i64 %107, ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.10 to ptr addrspace(4)), i64 %116, i32 0)
  %118 = zext i32 %105 to i64
  %119 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %117, i32 1, i64 %118, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 0)
  %120 = zext i32 %conv42 to i64
  %121 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %119, i32 1, i64 %120, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 1)
  %122 = trunc i64 %121 to i32
  %123 = load i32, ptr addrspace(4) %ci.ascast, align 4, !tbaa !7
  %inc46 = add nsw i32 %123, 1
  store i32 %inc46, ptr addrspace(4) %ci.ascast, align 4, !tbaa !7
  store i32 5, ptr addrspace(4) %cleanup.dest.slot.ascast, align 4
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %v38) #7
  br label %sw.epilog

sw.bb47:                                          ; preds = %if.end5
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %local) #7
  call addrspace(4) void @llvm.memcpy.p4.p4.i64(ptr addrspace(4) align 4 %local.ascast, ptr addrspace(4) align 4 %dw.ascast, i64 8, i1 false), !tbaa.struct !32
  %124 = load i32, ptr addrspace(4) %tid.ascast, align 4, !tbaa !7
  %i48 = getelementptr inbounds nuw %struct.DWordS_struct, ptr addrspace(4) %local.ascast, i32 0, i32 0
  %125 = load i32, ptr addrspace(4) %i48, align 4, !tbaa !33
  %c = getelementptr inbounds nuw %struct.DWordS_struct, ptr addrspace(4) %local.ascast, i32 0, i32 1
  %126 = load i8, ptr addrspace(4) %c, align 4, !tbaa !35
  %conv49 = sext i8 %126 to i32
  %127 = call addrspace(4) i64 @__ockl_printf_begin(i64 0)
  %128 = icmp eq ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.11 to ptr addrspace(4)), null
  br i1 %128, label %strlen.join50, label %strlen.while51

strlen.while51:                                   ; preds = %strlen.while51, %sw.bb47
  %129 = phi ptr addrspace(4) [ addrspacecast (ptr addrspace(1) @.str.11 to ptr addrspace(4)), %sw.bb47 ], [ %130, %strlen.while51 ]
  %130 = getelementptr i8, ptr addrspace(4) %129, i64 1
  %131 = load i8, ptr addrspace(4) %129, align 1
  %132 = icmp eq i8 %131, 0
  br i1 %132, label %strlen.while.done52, label %strlen.while51

strlen.while.done52:                              ; preds = %strlen.while51
  %133 = ptrtoint ptr addrspace(4) %129 to i64
  %134 = sub i64 %133, ptrtoint (ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.11 to ptr addrspace(4)) to i64)
  %135 = add i64 %134, 1
  br label %strlen.join50

strlen.join50:                                    ; preds = %strlen.while.done52, %sw.bb47
  %136 = phi i64 [ %135, %strlen.while.done52 ], [ 0, %sw.bb47 ]
  %137 = call addrspace(4) i64 @__ockl_printf_append_string_n(i64 %127, ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.11 to ptr addrspace(4)), i64 %136, i32 0)
  %138 = zext i32 %124 to i64
  %139 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %137, i32 1, i64 %138, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 0)
  %140 = zext i32 %125 to i64
  %141 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %139, i32 1, i64 %140, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 0)
  %142 = zext i32 %conv49 to i64
  %143 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %141, i32 1, i64 %142, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 1)
  %144 = trunc i64 %143 to i32
  %145 = load i32, ptr addrspace(4) %struct_stage.ascast, align 4, !tbaa !7
  %inc53 = add nsw i32 %145, 1
  store i32 %inc53, ptr addrspace(4) %struct_stage.ascast, align 4, !tbaa !7
  store i32 5, ptr addrspace(4) %cleanup.dest.slot.ascast, align 4
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %local) #7
  br label %sw.epilog

sw.bb54:                                          ; preds = %if.end5
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %local55) #7
  call addrspace(4) void @llvm.memcpy.p4.p4.i64(ptr addrspace(4) align 8 %local55.ascast, ptr addrspace(4) align 8 %qw.ascast, i64 16, i1 false), !tbaa.struct !36
  %146 = load i32, ptr addrspace(4) %tid.ascast, align 4, !tbaa !7
  %rem56 = srem i32 %146, -11
  %conv57 = sitofp i32 %rem56 to double
  %d58 = getelementptr inbounds nuw %struct.QuadWordS_struct, ptr addrspace(4) %local55.ascast, i32 0, i32 1
  %147 = load double, ptr addrspace(4) %d58, align 8, !tbaa !37
  %add = fadd contract double %147, %conv57
  store double %add, ptr addrspace(4) %d58, align 8, !tbaa !37
  %148 = load i32, ptr addrspace(4) %tid.ascast, align 4, !tbaa !7
  %rem59 = srem i32 %148, 30
  %conv60 = sitofp i32 %rem59 to double
  %d61 = getelementptr inbounds nuw %struct.QuadWordS_struct, ptr addrspace(4) %local55.ascast, i32 0, i32 1
  %149 = load double, ptr addrspace(4) %d61, align 8, !tbaa !37
  %add62 = fadd contract double %149, %conv60
  store double %add62, ptr addrspace(4) %d61, align 8, !tbaa !37
  %150 = load i32, ptr addrspace(4) %tid.ascast, align 4, !tbaa !7
  %i63 = getelementptr inbounds nuw %struct.QuadWordS_struct, ptr addrspace(4) %local55.ascast, i32 0, i32 0
  %151 = load i32, ptr addrspace(4) %i63, align 8, !tbaa !39
  %d64 = getelementptr inbounds nuw %struct.QuadWordS_struct, ptr addrspace(4) %local55.ascast, i32 0, i32 1
  %152 = load double, ptr addrspace(4) %d64, align 8, !tbaa !37
  %153 = call addrspace(4) i64 @__ockl_printf_begin(i64 0)
  %154 = icmp eq ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.12 to ptr addrspace(4)), null
  br i1 %154, label %strlen.join65, label %strlen.while66

strlen.while66:                                   ; preds = %strlen.while66, %sw.bb54
  %155 = phi ptr addrspace(4) [ addrspacecast (ptr addrspace(1) @.str.12 to ptr addrspace(4)), %sw.bb54 ], [ %156, %strlen.while66 ]
  %156 = getelementptr i8, ptr addrspace(4) %155, i64 1
  %157 = load i8, ptr addrspace(4) %155, align 1
  %158 = icmp eq i8 %157, 0
  br i1 %158, label %strlen.while.done67, label %strlen.while66

strlen.while.done67:                              ; preds = %strlen.while66
  %159 = ptrtoint ptr addrspace(4) %155 to i64
  %160 = sub i64 %159, ptrtoint (ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.12 to ptr addrspace(4)) to i64)
  %161 = add i64 %160, 1
  br label %strlen.join65

strlen.join65:                                    ; preds = %strlen.while.done67, %sw.bb54
  %162 = phi i64 [ %161, %strlen.while.done67 ], [ 0, %sw.bb54 ]
  %163 = call addrspace(4) i64 @__ockl_printf_append_string_n(i64 %153, ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.12 to ptr addrspace(4)), i64 %162, i32 0)
  %164 = zext i32 %150 to i64
  %165 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %163, i32 1, i64 %164, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 0)
  %166 = zext i32 %151 to i64
  %167 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %165, i32 1, i64 %166, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 0)
  %168 = bitcast double %152 to i64
  %169 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %167, i32 1, i64 %168, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 1)
  %170 = trunc i64 %169 to i32
  %171 = load i32, ptr addrspace(4) %struct_stage.ascast, align 4, !tbaa !7
  %inc68 = add nsw i32 %171, 1
  store i32 %inc68, ptr addrspace(4) %struct_stage.ascast, align 4, !tbaa !7
  store i32 5, ptr addrspace(4) %cleanup.dest.slot.ascast, align 4
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %local55) #7
  br label %sw.epilog

sw.bb69:                                          ; preds = %if.end5
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %local70) #7
  call addrspace(4) void @llvm.memcpy.p4.p4.i64(ptr addrspace(4) align 8 %local70.ascast, ptr addrspace(4) align 8 %ls.ascast, i64 32, i1 false), !tbaa.struct !40
  %172 = load i32, ptr addrspace(4) %tid.ascast, align 4, !tbaa !7
  %and = and i32 %172, 255
  %i71 = getelementptr inbounds nuw %struct.LargeS_struct, ptr addrspace(4) %local70.ascast, i32 0, i32 0
  %173 = load i32, ptr addrspace(4) %i71, align 8, !tbaa !24
  %add72 = add nsw i32 %173, %and
  store i32 %add72, ptr addrspace(4) %i71, align 8, !tbaa !24
  %174 = load i32, ptr addrspace(4) %tid.ascast, align 4, !tbaa !7
  %and73 = and i32 %174, 255
  %i74 = getelementptr inbounds nuw %struct.LargeS_struct, ptr addrspace(4) %local70.ascast, i32 0, i32 0
  %175 = load i32, ptr addrspace(4) %i74, align 8, !tbaa !24
  %add75 = add nsw i32 %175, %and73
  store i32 %add75, ptr addrspace(4) %i74, align 8, !tbaa !24
  call addrspace(4) void @llvm.lifetime.start.p0(ptr %has_ptr) #7
  store i32 -9, ptr addrspace(4) %has_ptr.ascast, align 4, !tbaa !7
  %176 = load i32, ptr addrspace(4) %tid.ascast, align 4, !tbaa !7
  %i76 = getelementptr inbounds nuw %struct.LargeS_struct, ptr addrspace(4) %local70.ascast, i32 0, i32 0
  %177 = load i32, ptr addrspace(4) %i76, align 8, !tbaa !24
  %d77 = getelementptr inbounds nuw %struct.LargeS_struct, ptr addrspace(4) %local70.ascast, i32 0, i32 1
  %178 = load double, ptr addrspace(4) %d77, align 8, !tbaa !28
  %179 = load i32, ptr addrspace(4) %has_ptr.ascast, align 4, !tbaa !7
  %j78 = getelementptr inbounds nuw %struct.LargeS_struct, ptr addrspace(4) %local70.ascast, i32 0, i32 3
  %180 = load i32, ptr addrspace(4) %j78, align 8, !tbaa !30
  %181 = call addrspace(4) i64 @__ockl_printf_begin(i64 0)
  %182 = icmp eq ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.13 to ptr addrspace(4)), null
  br i1 %182, label %strlen.join79, label %strlen.while80

strlen.while80:                                   ; preds = %strlen.while80, %sw.bb69
  %183 = phi ptr addrspace(4) [ addrspacecast (ptr addrspace(1) @.str.13 to ptr addrspace(4)), %sw.bb69 ], [ %184, %strlen.while80 ]
  %184 = getelementptr i8, ptr addrspace(4) %183, i64 1
  %185 = load i8, ptr addrspace(4) %183, align 1
  %186 = icmp eq i8 %185, 0
  br i1 %186, label %strlen.while.done81, label %strlen.while80

strlen.while.done81:                              ; preds = %strlen.while80
  %187 = ptrtoint ptr addrspace(4) %183 to i64
  %188 = sub i64 %187, ptrtoint (ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.13 to ptr addrspace(4)) to i64)
  %189 = add i64 %188, 1
  br label %strlen.join79

strlen.join79:                                    ; preds = %strlen.while.done81, %sw.bb69
  %190 = phi i64 [ %189, %strlen.while.done81 ], [ 0, %sw.bb69 ]
  %191 = call addrspace(4) i64 @__ockl_printf_append_string_n(i64 %181, ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.13 to ptr addrspace(4)), i64 %190, i32 0)
  %192 = zext i32 %176 to i64
  %193 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %191, i32 1, i64 %192, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 0)
  %194 = zext i32 %177 to i64
  %195 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %193, i32 1, i64 %194, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 0)
  %196 = bitcast double %178 to i64
  %197 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %195, i32 1, i64 %196, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 0)
  %198 = zext i32 %179 to i64
  %199 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %197, i32 1, i64 %198, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 0)
  %200 = zext i32 %180 to i64
  %201 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %199, i32 1, i64 %200, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 1)
  %202 = trunc i64 %201 to i32
  %203 = load i32, ptr addrspace(4) %struct_stage.ascast, align 4, !tbaa !7
  %inc82 = add nsw i32 %203, 1
  store i32 %inc82, ptr addrspace(4) %struct_stage.ascast, align 4, !tbaa !7
  store i32 5, ptr addrspace(4) %cleanup.dest.slot.ascast, align 4
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %has_ptr) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %local70) #7
  br label %sw.epilog

sw.default:                                       ; preds = %if.end5
  %204 = load i32, ptr addrspace(4) %tid.ascast, align 4, !tbaa !7
  %205 = load i8, ptr addrspace(4) %ch.ascast, align 1, !tbaa !16
  %conv83 = sext i8 %205 to i32
  %206 = call addrspace(4) i64 @__ockl_printf_begin(i64 0)
  %207 = icmp eq ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.14 to ptr addrspace(4)), null
  br i1 %207, label %strlen.join84, label %strlen.while85

strlen.while85:                                   ; preds = %strlen.while85, %sw.default
  %208 = phi ptr addrspace(4) [ addrspacecast (ptr addrspace(1) @.str.14 to ptr addrspace(4)), %sw.default ], [ %209, %strlen.while85 ]
  %209 = getelementptr i8, ptr addrspace(4) %208, i64 1
  %210 = load i8, ptr addrspace(4) %208, align 1
  %211 = icmp eq i8 %210, 0
  br i1 %211, label %strlen.while.done86, label %strlen.while85

strlen.while.done86:                              ; preds = %strlen.while85
  %212 = ptrtoint ptr addrspace(4) %208 to i64
  %213 = sub i64 %212, ptrtoint (ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.14 to ptr addrspace(4)) to i64)
  %214 = add i64 %213, 1
  br label %strlen.join84

strlen.join84:                                    ; preds = %strlen.while.done86, %sw.default
  %215 = phi i64 [ %214, %strlen.while.done86 ], [ 0, %sw.default ]
  %216 = call addrspace(4) i64 @__ockl_printf_append_string_n(i64 %206, ptr addrspace(4) addrspacecast (ptr addrspace(1) @.str.14 to ptr addrspace(4)), i64 %215, i32 0)
  %217 = zext i32 %204 to i64
  %218 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %216, i32 1, i64 %217, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 0)
  %219 = zext i32 %conv83 to i64
  %220 = call addrspace(4) i64 @__ockl_printf_append_args(i64 %218, i32 1, i64 %219, i64 0, i64 0, i64 0, i64 0, i64 0, i64 0, i32 1)
  %221 = trunc i64 %220 to i32
  br label %sw.epilog

sw.epilog:                                        ; preds = %strlen.join84, %strlen.join79, %strlen.join65, %strlen.join50, %strlen.join43, %strlen.join33, %strlen.join24, %strlen.join15, %strlen.join10
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %ch) #7
  br label %for.inc

for.inc:                                          ; preds = %sw.epilog, %if.then
  %222 = load ptr addrspace(4), ptr addrspace(4) %p.ascast, align 8, !tbaa !11
  %incdec.ptr = getelementptr inbounds i8, ptr addrspace(4) %222, i32 -1
  store ptr addrspace(4) %incdec.ptr, ptr addrspace(4) %p.ascast, align 8, !tbaa !11
  br label %for.cond, !llvm.loop !42

cleanup:                                          ; preds = %if.then4, %for.cond.cleanup
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %p) #7
  br label %for.end

for.end:                                          ; preds = %cleanup
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %loop_break_17053) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %loop_break_16841) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %struct_stage) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %ci) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %li) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %di) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %ii) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %si) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %fmt) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %scenario) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %fmts) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %ls) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %qw) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %dw) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %chars) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %lls) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %doubles) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %ints) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %s_arr) #7
  call addrspace(4) void @llvm.lifetime.end.p0(ptr %tid) #7
  ret void
}

declare i64 @__ockl_printf_begin(i64) addrspace(4)

declare i64 @__ockl_printf_append_string_n(i64, ptr addrspace(4), i64, i32) addrspace(4)

declare i64 @__ockl_printf_append_args(i64, i32, i64, i64, i64, i64, i64, i64, i64, i32) addrspace(4)

; Function Attrs: nocallback nofree nounwind willreturn memory(argmem: readwrite)
declare void @llvm.memcpy.p4.p4.i64(ptr addrspace(4) noalias writeonly captures(none), ptr addrspace(4) noalias readonly captures(none), i64, i1 immarg) addrspace(4) #4

attributes #0 = { convergent mustprogress noreturn nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #1 = { cold noreturn nounwind memory(inaccessiblemem: write) }
attributes #2 = { convergent mustprogress noinline nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #3 = { nocallback nofree nosync nounwind willreturn memory(argmem: readwrite) }
attributes #4 = { nocallback nofree nounwind willreturn memory(argmem: readwrite) }
attributes #5 = { convergent nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" }
attributes #6 = { convergent mustprogress norecurse nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-features"="+16-bit-insts,+ashr-pk-insts,+atomic-buffer-global-pk-add-f16-insts,+atomic-buffer-pk-add-bf16-inst,+atomic-ds-pk-add-16-insts,+atomic-fadd-rtn-insts,+atomic-flat-pk-add-16-insts,+atomic-global-pk-add-bf16-inst,+bf16-cvt-insts,+bf16-trans-insts,+bf8-cvt-scale-insts,+bitop3-insts,+ci-insts,+dl-insts,+dot1-insts,+dot10-insts,+dot11-insts,+dot12-insts,+dot13-insts,+dot2-insts,+dot3-insts,+dot4-insts,+dot5-insts,+dot6-insts,+dot7-insts,+dot8-insts,+dot9-insts,+dpp,+f16bf16-to-fp6bf6-cvt-scale-insts,+f32-to-f16bf16-cvt-sr-insts,+fp4-cvt-scale-insts,+fp6bf6-cvt-scale-insts,+fp8-conversion-insts,+fp8-cvt-scale-insts,+fp8-insts,+fp8e5m3-insts,+gfx10-3-insts,+gfx10-insts,+gfx11-insts,+gfx12-insts,+gfx1250-insts,+gfx8-insts,+gfx9-insts,+gfx90a-insts,+gfx940-insts,+gfx950-insts,+gws,+image-insts,+mai-insts,+permlane16-swap,+permlane32-swap,+prng-inst,+s-memrealtime,+s-memtime-inst,+setprio-inc-wg-inst,+tanh-insts,+tensor-cvt-lut-insts,+transpose-load-f4f6-insts,+vmem-pref-insts,+vmem-to-lds-load-insts,+wavefrontsize32,+wavefrontsize64" "uniform-work-group-size"="true" }
attributes #7 = { nounwind }
attributes #8 = { convergent nounwind }

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
!23 = !{i32 1024, i32 1, i32 1}
!24 = !{!25, !8, i64 0}
!25 = !{!"_ZTS13LargeS_struct", !8, i64 0, !26, i64 8, !27, i64 16, !8, i64 24}
!26 = !{!"double", !9, i64 0}
!27 = !{!"p1 _ZTS13DWordS_struct", !13, i64 0}
!28 = !{!25, !26, i64 8}
!29 = !{!25, !27, i64 16}
!30 = !{!25, !8, i64 24}
!31 = !{!26, !26, i64 0}
!32 = !{i64 0, i64 4, !7, i64 4, i64 1, !16}
!33 = !{!34, !8, i64 0}
!34 = !{!"_ZTS13DWordS_struct", !8, i64 0, !9, i64 4}
!35 = !{!34, !9, i64 4}
!36 = !{i64 0, i64 4, !7, i64 8, i64 8, !31}
!37 = !{!38, !26, i64 8}
!38 = !{!"_ZTS16QuadWordS_struct", !8, i64 0, !26, i64 8}
!39 = !{!38, !8, i64 0}
!40 = !{i64 0, i64 4, !7, i64 8, i64 8, !31, i64 16, i64 8, !41, i64 24, i64 4, !7}
!41 = !{!27, !27, i64 0}
!42 = distinct !{!42, !18, !19}
