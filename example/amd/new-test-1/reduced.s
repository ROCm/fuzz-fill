	.amdgcn_target "amdgcn-amd-amdhsa--gfx700"
	.amdhsa_code_object_version 6
	.text
	.globl	__ockl_fprintf_append_args      ; -- Begin function __ockl_fprintf_append_args
	.p2align	7
	.type	__ockl_fprintf_append_args,@function
__ockl_fprintf_append_args:             ; @__ockl_fprintf_append_args
; %bb.0:
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	v_dual_mov_b32 v0, 0 :: v_dual_mov_b32 v1, 0
	global_load_i8 v0, v[0:1], off
	s_wait_loadcnt 0x0
	v_cvt_f32_i32_e32 v1, v0
	v_ashrrev_i32_e32 v0, 30, v0
	s_delay_alu instid0(VALU_DEP_2) | instskip(NEXT) | instid1(VALU_DEP_1)
	v_rcp_iflag_f32_e32 v2, v1
	v_or_b32_e32 v0, 1, v0
	s_delay_alu instid0(TRANS32_DEP_1) | instskip(NEXT) | instid1(VALU_DEP_1)
	v_trunc_f32_e32 v2, v2
	v_xor_b32_e32 v3, 0x80000000, v2
	v_cvt_i32_f32_e32 v2, v2
	s_delay_alu instid0(VALU_DEP_2) | instskip(SKIP_1) | instid1(VALU_DEP_2)
	v_fma_f32 v3, v3, v1, 1.0
	v_and_b32_e32 v1, 0x7fffffff, v1
	v_and_b32_e32 v3, 0x7fffffff, v3
	s_delay_alu instid0(VALU_DEP_1) | instskip(SKIP_2) | instid1(VALU_DEP_1)
	v_cmp_ge_f32_e32 vcc_lo, v3, v1
	s_wait_alu depctr_va_vcc(0)
	v_cndmask_b32_e32 v0, 0, v0, vcc_lo
	v_add_nc_u32_e32 v0, v2, v0
	s_delay_alu instid0(VALU_DEP_1)
	v_bfe_i32 v0, v0, 0, 8
	s_setpc_b64 s[30:31]
.Lfunc_end0:
	.size	__ockl_fprintf_append_args, .Lfunc_end0-__ockl_fprintf_append_args
                                        ; -- End function
	.set .L__ockl_fprintf_append_args.num_vgpr, 4
	.set .L__ockl_fprintf_append_args.num_agpr, 0
	.set .L__ockl_fprintf_append_args.numbered_sgpr, 32
	.set .L__ockl_fprintf_append_args.num_named_barrier, 0
	.set .L__ockl_fprintf_append_args.private_seg_size, 0
	.set .L__ockl_fprintf_append_args.uses_vcc, 1
	.set .L__ockl_fprintf_append_args.uses_flat_scratch, 0
	.set .L__ockl_fprintf_append_args.has_dyn_sized_stack, 0
	.set .L__ockl_fprintf_append_args.has_recursion, 0
	.set .L__ockl_fprintf_append_args.has_indirect_call, 0
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 148
; TotalNumSgprs: 34
; NumVgprs: 4
; ScratchSize: 0
; MemoryBound: 0
	.section	.AMDGPU.gpr_maximums,"",@progbits
	.set amdgpu.max_num_vgpr, 4
	.set amdgpu.max_num_agpr, 0
	.set amdgpu.max_num_sgpr, 32
	.set amdgpu.max_num_named_barrier, 0
	.section	.AMDGPU.csdata,"",@progbits
	.section	".note.GNU-stack","",@progbits
	.amdgpu_metadata
---
amdhsa.kernels:  []
amdhsa.target:   amdgcn-amd-amdhsa--gfx700
amdhsa.version:
  - 1
  - 2
...

	.end_amdgpu_metadata
