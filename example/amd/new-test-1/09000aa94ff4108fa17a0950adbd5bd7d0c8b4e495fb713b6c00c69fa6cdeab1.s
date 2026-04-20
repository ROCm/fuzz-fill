	.amdgcn_target "amdgcn-amd-amdhsa--gfx700"
	.amdhsa_code_object_version 6
	.text
	.weak	__cxa_pure_virtual              ; -- Begin function __cxa_pure_virtual
	.p2align	7
	.type	__cxa_pure_virtual,@function
__cxa_pure_virtual:                     ; @__cxa_pure_virtual
; %bb.0:                                ; %entry
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_trap 2
.Lfunc_end0:
	.size	__cxa_pure_virtual, .Lfunc_end0-__cxa_pure_virtual
                                        ; -- End function
	.set __cxa_pure_virtual.num_vgpr, 0
	.set __cxa_pure_virtual.num_agpr, 0
	.set __cxa_pure_virtual.numbered_sgpr, 0
	.set __cxa_pure_virtual.num_named_barrier, 0
	.set __cxa_pure_virtual.private_seg_size, 0
	.set __cxa_pure_virtual.uses_vcc, 0
	.set __cxa_pure_virtual.uses_flat_scratch, 0
	.set __cxa_pure_virtual.has_dyn_sized_stack, 0
	.set __cxa_pure_virtual.has_recursion, 0
	.set __cxa_pure_virtual.has_indirect_call, 0
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 24
; TotalNumSgprs: 0
; NumVgprs: 0
; ScratchSize: 0
; MemoryBound: 0
	.text
	.weak	__cxa_deleted_virtual           ; -- Begin function __cxa_deleted_virtual
	.p2align	7
	.type	__cxa_deleted_virtual,@function
__cxa_deleted_virtual:                  ; @__cxa_deleted_virtual
; %bb.0:                                ; %entry
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_trap 2
.Lfunc_end1:
	.size	__cxa_deleted_virtual, .Lfunc_end1-__cxa_deleted_virtual
                                        ; -- End function
	.set __cxa_deleted_virtual.num_vgpr, 0
	.set __cxa_deleted_virtual.num_agpr, 0
	.set __cxa_deleted_virtual.numbered_sgpr, 0
	.set __cxa_deleted_virtual.num_named_barrier, 0
	.set __cxa_deleted_virtual.private_seg_size, 0
	.set __cxa_deleted_virtual.uses_vcc, 0
	.set __cxa_deleted_virtual.uses_flat_scratch, 0
	.set __cxa_deleted_virtual.has_dyn_sized_stack, 0
	.set __cxa_deleted_virtual.has_recursion, 0
	.set __cxa_deleted_virtual.has_indirect_call, 0
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 24
; TotalNumSgprs: 0
; NumVgprs: 0
; ScratchSize: 0
; MemoryBound: 0
	.text
	.p2align	7                               ; -- Begin function __ockl_hsa_signal_add
	.type	__ockl_hsa_signal_add,@function
__ockl_hsa_signal_add:                  ; @__ockl_hsa_signal_add
; %bb.0:
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_mov_b32 s0, 0
	s_mov_b32 s1, 0
	s_mov_b32 s2, exec_lo
	v_cmpx_lt_i32_e32 3, v4
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s2, exec_lo, s2
	s_cbranch_execz .LBB2_8
; %bb.1:                                ; %NodeBlock12
	s_mov_b32 s3, 0
	s_mov_b32 s1, exec_lo
	v_cmpx_lt_i32_e32 4, v4
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s1, exec_lo, s1
	s_cbranch_execz .LBB2_5
; %bb.2:                                ; %LeafBlock10
	s_mov_b32 s3, -1
	s_mov_b32 s4, exec_lo
	v_cmpx_eq_u32_e32 5, v4
	s_cbranch_execz .LBB2_4
; %bb.3:
	global_wb scope:SCOPE_SYS
	s_wait_storecnt 0x0
	global_atomic_add_u64 v[0:1], v[2:3], off offset:8 scope:SCOPE_SYS
	s_wait_storecnt 0x0
	global_inv scope:SCOPE_SYS
	s_xor_b32 s3, exec_lo, -1
.LBB2_4:                                ; %Flow17
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s4
	s_delay_alu instid0(SALU_CYCLE_1)
	s_and_b32 s3, s3, exec_lo
.LBB2_5:                                ; %Flow16
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_saveexec_b32 s1, s1
	s_cbranch_execz .LBB2_7
; %bb.6:
	global_wb scope:SCOPE_SYS
	s_wait_loadcnt 0x0
	s_wait_storecnt 0x0
	global_atomic_add_u64 v[0:1], v[2:3], off offset:8 scope:SCOPE_SYS
	s_wait_storecnt 0x0
	global_inv scope:SCOPE_SYS
.LBB2_7:                                ; %Flow18
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s1
	s_delay_alu instid0(SALU_CYCLE_1)
	s_and_b32 s1, s3, exec_lo
                                        ; implicit-def: $vgpr4
.LBB2_8:                                ; %Flow
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_saveexec_b32 s2, s2
	s_cbranch_execz .LBB2_14
; %bb.9:                                ; %NodeBlock
	s_mov_b32 s0, exec_lo
	v_cmpx_lt_i32_e32 2, v4
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s0, exec_lo, s0
	s_cbranch_execz .LBB2_11
; %bb.10:
	global_wb scope:SCOPE_SYS
	s_wait_loadcnt 0x0
	s_wait_storecnt 0x0
	global_atomic_add_u64 v[0:1], v[2:3], off offset:8 scope:SCOPE_SYS
                                        ; implicit-def: $vgpr4
.LBB2_11:                               ; %Flow20
	s_wait_alu depctr_sa_sdst(0)
	s_or_saveexec_b32 s3, s0
	s_mov_b32 s0, 0
	s_mov_b32 s4, s1
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 exec_lo, exec_lo, s3
; %bb.12:                               ; %LeafBlock
	v_cmp_gt_i32_e32 vcc_lo, 1, v4
	s_and_not1_b32 s4, s1, exec_lo
	s_mov_b32 s0, exec_lo
	s_and_b32 s5, vcc_lo, exec_lo
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 s4, s4, s5
; %bb.13:                               ; %Flow21
	s_or_b32 exec_lo, exec_lo, s3
	s_delay_alu instid0(SALU_CYCLE_1)
	s_and_not1_b32 s1, s1, exec_lo
	s_wait_alu depctr_sa_sdst(0)
	s_and_b32 s3, s4, exec_lo
	s_and_b32 s0, s0, exec_lo
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 s1, s1, s3
.LBB2_14:                               ; %Flow19
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s2
	s_and_saveexec_b32 s2, s1
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s1, exec_lo, s2
	s_cbranch_execz .LBB2_16
; %bb.15:
	global_atomic_add_u64 v[0:1], v[2:3], off offset:8 scope:SCOPE_SYS
	s_and_not1_b32 s0, s0, exec_lo
.LBB2_16:                               ; %Flow22
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s1
	s_and_saveexec_b32 s1, s0
	s_cbranch_execz .LBB2_18
; %bb.17:
	global_atomic_add_u64 v[0:1], v[2:3], off offset:8 scope:SCOPE_SYS
	s_wait_storecnt 0x0
	global_inv scope:SCOPE_SYS
.LBB2_18:
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s1
	global_load_b64 v[2:3], v[0:1], off offset:16
	s_mov_b32 s0, exec_lo
	s_wait_loadcnt 0x0
	v_cmpx_ne_u64_e32 0, v[2:3]
	s_cbranch_execz .LBB2_20
; %bb.19:
	global_load_b32 v0, v[0:1], off offset:24
	s_wait_loadcnt 0x0
	v_dual_mov_b32 v1, 0 :: v_dual_and_b32 v4, 0xffffff, v0
	global_wb scope:SCOPE_SYS
	s_wait_storecnt 0x0
	global_store_b64 v[2:3], v[0:1], off scope:SCOPE_SYS
	v_readfirstlane_b32 s1, v4
	s_mov_b32 m0, s1
	s_sendmsg sendmsg(MSG_INTERRUPT)
.LBB2_20:                               ; %UnifiedReturnBlock
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s0
	s_wait_kmcnt 0x0
	s_setpc_b64 s[30:31]
.Lfunc_end2:
	.size	__ockl_hsa_signal_add, .Lfunc_end2-__ockl_hsa_signal_add
                                        ; -- End function
	.set .L__ockl_hsa_signal_add.num_vgpr, 5
	.set .L__ockl_hsa_signal_add.num_agpr, 0
	.set .L__ockl_hsa_signal_add.numbered_sgpr, 32
	.set .L__ockl_hsa_signal_add.num_named_barrier, 0
	.set .L__ockl_hsa_signal_add.private_seg_size, 0
	.set .L__ockl_hsa_signal_add.uses_vcc, 1
	.set .L__ockl_hsa_signal_add.uses_flat_scratch, 0
	.set .L__ockl_hsa_signal_add.has_dyn_sized_stack, 0
	.set .L__ockl_hsa_signal_add.has_recursion, 0
	.set .L__ockl_hsa_signal_add.has_indirect_call, 0
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 576
; TotalNumSgprs: 34
; NumVgprs: 5
; ScratchSize: 0
; MemoryBound: 0
	.text
	.p2align	7                               ; -- Begin function __ockl_hostcall_internal
	.type	__ockl_hostcall_internal,@function
__ockl_hostcall_internal:               ; @__ockl_hostcall_internal
; %bb.0:
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_mov_b32 s10, s33
	s_mov_b32 s33, s32
	s_xor_saveexec_b32 s0, -1
	scratch_store_b32 off, v32, s33         ; 4-byte Folded Spill
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s0
	v_mov_b32_e32 v23, v0
	v_mbcnt_lo_u32_b32 v0, -1, 0
	v_dual_mov_b32 v21, v2 :: v_dual_mov_b32 v24, v1
	v_writelane_b32 v32, s30, 0
	s_add_co_i32 s32, s32, 16
	s_delay_alu instid0(VALU_DEP_3) | instskip(SKIP_3) | instid1(VALU_DEP_4)
	v_mbcnt_hi_u32_b32 v2, -1, v0
	v_mov_b32_e32 v0, 0
	v_mov_b32_e32 v1, 0
	v_writelane_b32 v32, s31, 1
	v_readfirstlane_b32 s0, v2
	s_wait_alu depctr_va_sdst(0)
	s_delay_alu instid0(VALU_DEP_1)
	v_cmp_eq_u32_e64 s6, s0, v2
	s_and_saveexec_b32 s0, s6
	s_cbranch_execz .LBB3_6
; %bb.1:
	global_load_b64 v[27:28], v[23:24], off offset:24 scope:SCOPE_SYS
	s_wait_loadcnt 0x0
	global_inv scope:SCOPE_SYS
	s_clause 0x1
	global_load_b64 v[0:1], v[23:24], off offset:40
	global_load_b64 v[19:20], v[23:24], off
	s_mov_b32 s1, exec_lo
	s_wait_loadcnt 0x1
	v_and_b32_e32 v0, v0, v27
	s_wait_loadcnt 0x0
	s_delay_alu instid0(VALU_DEP_1) | instskip(SKIP_1) | instid1(VALU_DEP_1)
	v_mad_co_u64_u32 v[29:30], null, v0, 24, v[19:20]
	v_and_b32_e32 v0, v1, v28
	v_mad_co_u64_u32 v[30:31], null, v0, 24, v[30:31]
	global_load_b64 v[25:26], v[29:30], off scope:SCOPE_SYS
	s_wait_loadcnt 0x0
	global_atomic_cmpswap_b64 v[0:1], v[23:24], v[25:28], off offset:24 th:TH_ATOMIC_RETURN scope:SCOPE_SYS
	s_wait_loadcnt 0x0
	global_inv scope:SCOPE_SYS
	v_cmpx_ne_u64_e64 v[0:1], v[27:28]
	s_cbranch_execz .LBB3_5
; %bb.2:                                ; %.preheader3
	s_mov_b32 s2, 0
.LBB3_3:                                ; =>This Inner Loop Header: Depth=1
	s_sleep 1
	s_clause 0x1
	global_load_b64 v[19:20], v[23:24], off offset:40
	global_load_b64 v[25:26], v[23:24], off
	v_dual_mov_b32 v28, v1 :: v_dual_mov_b32 v27, v0
	s_wait_loadcnt 0x1
	s_delay_alu instid0(VALU_DEP_1) | instskip(SKIP_1) | instid1(VALU_DEP_1)
	v_and_b32_e32 v0, v19, v27
	s_wait_loadcnt 0x0
	v_mad_co_u64_u32 v[29:30], null, v0, 24, v[25:26]
	v_and_b32_e32 v0, v20, v28
	s_delay_alu instid0(VALU_DEP_1)
	v_mad_co_u64_u32 v[30:31], null, v0, 24, v[30:31]
	global_load_b64 v[25:26], v[29:30], off scope:SCOPE_SYS
	s_wait_loadcnt 0x0
	global_atomic_cmpswap_b64 v[0:1], v[23:24], v[25:28], off offset:24 th:TH_ATOMIC_RETURN scope:SCOPE_SYS
	s_wait_loadcnt 0x0
	global_inv scope:SCOPE_SYS
	v_cmp_eq_u64_e32 vcc_lo, v[0:1], v[27:28]
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 s2, vcc_lo, s2
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s2
	s_cbranch_execnz .LBB3_3
; %bb.4:                                ; %Flow19
	s_or_b32 exec_lo, exec_lo, s2
.LBB3_5:                                ; %Flow21
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s1
.LBB3_6:
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s0
	s_clause 0x1
	global_load_b64 v[19:20], v[23:24], off offset:40
	global_load_b128 v[25:28], v[23:24], off
	v_readfirstlane_b32 s7, v0
	v_readfirstlane_b32 s8, v1
	s_mov_b64 s[0:1], exec
	s_wait_loadcnt 0x1
	s_wait_alu depctr_va_sdst(0)
	v_and_b32_e32 v0, s7, v19
	v_and_b32_e32 v1, s8, v20
	s_wait_loadcnt 0x0
	s_delay_alu instid0(VALU_DEP_2) | instskip(NEXT) | instid1(VALU_DEP_1)
	v_mad_co_u64_u32 v[29:30], null, v0, 24, v[25:26]
	v_mad_co_u64_u32 v[30:31], null, v1, 24, v[30:31]
	s_and_saveexec_b32 s2, s6
	s_cbranch_execz .LBB3_8
; %bb.7:
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v20, s1 :: v_dual_mov_b32 v19, s0
	v_mov_b32_e32 v22, 1
	global_store_b128 v[29:30], v[19:22], off offset:8
.LBB3_8:
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s2
	v_lshlrev_b64_e32 v[0:1], 12, v[0:1]
	v_lshlrev_b32_e32 v2, 6, v2
	s_delay_alu instid0(VALU_DEP_2) | instskip(SKIP_1) | instid1(VALU_DEP_3)
	v_add_co_u32 v0, vcc_lo, v27, v0
	s_wait_alu depctr_va_vcc(0)
	v_add_co_ci_u32_e64 v1, null, v28, v1, vcc_lo
	s_delay_alu instid0(VALU_DEP_2) | instskip(SKIP_1) | instid1(VALU_DEP_2)
	v_add_co_u32 v19, vcc_lo, v0, v2
	s_wait_alu depctr_va_vcc(0)
	v_add_co_ci_u32_e64 v20, null, 0, v1, vcc_lo
	s_clause 0x3
	global_store_b128 v[19:20], v[3:6], off
	global_store_b128 v[19:20], v[7:10], off offset:16
	global_store_b128 v[19:20], v[11:14], off offset:32
	global_store_b128 v[19:20], v[15:18], off offset:48
	s_and_saveexec_b32 s9, s6
	s_cbranch_execz .LBB3_13
; %bb.9:
	s_clause 0x1
	global_load_b64 v[8:9], v[23:24], off offset:32 scope:SCOPE_SYS
	global_load_b64 v[0:1], v[23:24], off offset:40
	s_mov_b32 s0, exec_lo
	s_wait_loadcnt 0x0
	v_dual_mov_b32 v7, s8 :: v_dual_and_b32 v0, s7, v0
	s_delay_alu instid0(VALU_DEP_1) | instskip(SKIP_1) | instid1(VALU_DEP_1)
	v_mad_co_u64_u32 v[4:5], null, v0, 24, v[25:26]
	v_and_b32_e32 v0, s8, v1
	v_mad_co_u64_u32 v[5:6], null, v0, 24, v[5:6]
	v_mov_b32_e32 v6, s7
	global_store_b64 v[4:5], v[8:9], off
	global_wb scope:SCOPE_SYS
	s_wait_storecnt 0x0
	global_atomic_cmpswap_b64 v[2:3], v[23:24], v[6:9], off offset:32 th:TH_ATOMIC_RETURN scope:SCOPE_SYS
	s_wait_loadcnt 0x0
	v_cmpx_ne_u64_e64 v[2:3], v[8:9]
	s_cbranch_execz .LBB3_12
; %bb.10:                               ; %.preheader1
	s_mov_b32 s1, 0
.LBB3_11:                               ; =>This Inner Loop Header: Depth=1
	v_dual_mov_b32 v0, s7 :: v_dual_mov_b32 v1, s8
	s_sleep 1
	global_store_b64 v[4:5], v[2:3], off
	global_wb scope:SCOPE_SYS
	s_wait_storecnt 0x0
	global_atomic_cmpswap_b64 v[0:1], v[23:24], v[0:3], off offset:32 th:TH_ATOMIC_RETURN scope:SCOPE_SYS
	s_wait_loadcnt 0x0
	v_cmp_eq_u64_e32 vcc_lo, v[0:1], v[2:3]
	v_dual_mov_b32 v3, v1 :: v_dual_mov_b32 v2, v0
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 s1, vcc_lo, s1
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s1
	s_cbranch_execnz .LBB3_11
.LBB3_12:                               ; %Flow17
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s0
	global_load_b64 v[0:1], v[23:24], off offset:16
	v_dual_mov_b32 v2, 1 :: v_dual_mov_b32 v3, 0
	v_mov_b32_e32 v4, 3
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_hsa_signal_add@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_hsa_signal_add@rel32@hi+24
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
.LBB3_13:                               ; %Flow18
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s9
	s_branch .LBB3_17
.LBB3_14:                               ;   in Loop: Header=BB3_17 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s0
	s_delay_alu instid0(VALU_DEP_1)
	v_readfirstlane_b32 s0, v0
	s_cmp_eq_u32 s0, 0
	s_cbranch_scc1 .LBB3_16
; %bb.15:                               ;   in Loop: Header=BB3_17 Depth=1
	s_sleep 1
	s_cbranch_execnz .LBB3_17
	s_branch .LBB3_19
.LBB3_16:
	s_branch .LBB3_19
.LBB3_17:                               ; =>This Inner Loop Header: Depth=1
	v_mov_b32_e32 v0, 1
	s_and_saveexec_b32 s0, s6
	s_cbranch_execz .LBB3_14
; %bb.18:                               ;   in Loop: Header=BB3_17 Depth=1
	global_load_b32 v0, v[29:30], off offset:20 scope:SCOPE_SYS
	s_wait_loadcnt 0x0
	global_inv scope:SCOPE_SYS
	v_and_b32_e32 v0, 1, v0
	s_branch .LBB3_14
.LBB3_19:
	global_load_b128 v[0:3], v[19:20], off
	s_and_saveexec_b32 s0, s6
	s_cbranch_execz .LBB3_23
; %bb.20:
	s_clause 0x2
	global_load_b64 v[6:7], v[23:24], off offset:40
	global_load_b64 v[11:12], v[23:24], off offset:24 scope:SCOPE_SYS
	global_load_b64 v[8:9], v[23:24], off
	s_wait_loadcnt 0x2
	v_add_co_u32 v10, vcc_lo, v6, 1
	s_wait_alu depctr_va_vcc(0)
	v_add_co_ci_u32_e64 v13, null, 0, v7, vcc_lo
	s_delay_alu instid0(VALU_DEP_2) | instskip(SKIP_1) | instid1(VALU_DEP_2)
	v_add_co_u32 v4, vcc_lo, v10, s7
	s_wait_alu depctr_va_vcc(0)
	v_add_co_ci_u32_e64 v5, null, s8, v13, vcc_lo
	s_delay_alu instid0(VALU_DEP_1) | instskip(SKIP_2) | instid1(VALU_DEP_1)
	v_cmp_eq_u64_e32 vcc_lo, 0, v[4:5]
	s_wait_alu depctr_va_vcc(0)
	v_dual_cndmask_b32 v5, v5, v13 :: v_dual_cndmask_b32 v4, v4, v10
	v_and_b32_e32 v6, v4, v6
	s_wait_loadcnt 0x0
	s_delay_alu instid0(VALU_DEP_1) | instskip(NEXT) | instid1(VALU_DEP_3)
	v_mad_co_u64_u32 v[8:9], null, v6, 24, v[8:9]
	v_and_b32_e32 v6, v5, v7
	v_mov_b32_e32 v7, v12
	s_delay_alu instid0(VALU_DEP_2)
	v_mad_co_u64_u32 v[9:10], null, v6, 24, v[9:10]
	v_mov_b32_e32 v6, v11
	global_store_b64 v[8:9], v[11:12], off
	global_wb scope:SCOPE_SYS
	s_wait_storecnt 0x0
	global_atomic_cmpswap_b64 v[6:7], v[23:24], v[4:7], off offset:24 th:TH_ATOMIC_RETURN scope:SCOPE_SYS
	s_wait_loadcnt 0x0
	v_cmp_ne_u64_e32 vcc_lo, v[6:7], v[11:12]
	s_and_b32 exec_lo, exec_lo, vcc_lo
	s_cbranch_execz .LBB3_23
; %bb.21:                               ; %.preheader
	s_mov_b32 s1, 0
.LBB3_22:                               ; =>This Inner Loop Header: Depth=1
	s_sleep 1
	global_store_b64 v[8:9], v[6:7], off
	global_wb scope:SCOPE_SYS
	s_wait_storecnt 0x0
	global_atomic_cmpswap_b64 v[10:11], v[23:24], v[4:7], off offset:24 th:TH_ATOMIC_RETURN scope:SCOPE_SYS
	s_wait_loadcnt 0x0
	v_cmp_eq_u64_e32 vcc_lo, v[10:11], v[6:7]
	v_dual_mov_b32 v6, v10 :: v_dual_mov_b32 v7, v11
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 s1, vcc_lo, s1
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s1
	s_cbranch_execnz .LBB3_22
.LBB3_23:
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s0
	v_readlane_b32 s31, v32, 1
	v_readlane_b32 s30, v32, 0
	s_mov_b32 s32, s33
	s_xor_saveexec_b32 s0, -1
	scratch_load_b32 v32, off, s33          ; 4-byte Folded Reload
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s0
	s_mov_b32 s33, s10
	s_wait_loadcnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	s_setpc_b64 s[30:31]
.Lfunc_end3:
	.size	__ockl_hostcall_internal, .Lfunc_end3-__ockl_hostcall_internal
                                        ; -- End function
	.set .L__ockl_hostcall_internal.num_vgpr, max(33, .L__ockl_hsa_signal_add.num_vgpr)
	.set .L__ockl_hostcall_internal.num_agpr, max(0, .L__ockl_hsa_signal_add.num_agpr)
	.set .L__ockl_hostcall_internal.numbered_sgpr, max(34, .L__ockl_hsa_signal_add.numbered_sgpr)
	.set .L__ockl_hostcall_internal.num_named_barrier, max(0, .L__ockl_hsa_signal_add.num_named_barrier)
	.set .L__ockl_hostcall_internal.private_seg_size, 16+max(.L__ockl_hsa_signal_add.private_seg_size)
	.set .L__ockl_hostcall_internal.uses_vcc, or(1, .L__ockl_hsa_signal_add.uses_vcc)
	.set .L__ockl_hostcall_internal.uses_flat_scratch, or(0, .L__ockl_hsa_signal_add.uses_flat_scratch)
	.set .L__ockl_hostcall_internal.has_dyn_sized_stack, or(0, .L__ockl_hsa_signal_add.has_dyn_sized_stack)
	.set .L__ockl_hostcall_internal.has_recursion, or(0, .L__ockl_hsa_signal_add.has_recursion)
	.set .L__ockl_hostcall_internal.has_indirect_call, or(0, .L__ockl_hsa_signal_add.has_indirect_call)
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 1476
; TotalNumSgprs: 36
; NumVgprs: 33
; ScratchSize: 16
; MemoryBound: 0
	.section	.text.unlikely.,"ax",@progbits
	.p2align	7                               ; -- Begin function __ockl_hostcall_preview
	.type	__ockl_hostcall_preview,@function
__ockl_hostcall_preview:                ; @__ockl_hostcall_preview
; %bb.0:
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_xor_saveexec_b32 s0, -1
	scratch_store_b32 off, v33, s32         ; 4-byte Folded Spill
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s0
	s_load_b64 s[2:3], s[8:9], 0x50
	v_writelane_b32 v33, s30, 0
	v_dual_mov_b32 v18, v16 :: v_dual_mov_b32 v17, v15
	v_dual_mov_b32 v16, v14 :: v_dual_mov_b32 v15, v13
	v_writelane_b32 v33, s31, 1
	v_dual_mov_b32 v14, v12 :: v_dual_mov_b32 v13, v11
	v_dual_mov_b32 v12, v10 :: v_dual_mov_b32 v11, v9
	v_writelane_b32 v33, s33, 2
	v_dual_mov_b32 v10, v8 :: v_dual_mov_b32 v9, v7
	v_dual_mov_b32 v8, v6 :: v_dual_mov_b32 v7, v5
	v_dual_mov_b32 v6, v4 :: v_dual_mov_b32 v5, v3
	v_dual_mov_b32 v4, v2 :: v_dual_mov_b32 v3, v1
	s_wait_kmcnt 0x0
	v_dual_mov_b32 v2, v0 :: v_dual_mov_b32 v1, s3
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_hostcall_internal@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_hostcall_internal@rel32@hi+24
	v_mov_b32_e32 v0, s2
	v_readlane_b32 s33, v33, 2
	v_readlane_b32 s31, v33, 1
	v_readlane_b32 s30, v33, 0
	s_xor_saveexec_b32 s2, -1
	scratch_load_b32 v33, off, s32          ; 4-byte Folded Reload
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s2
	s_setpc_b64 s[0:1]
.Lfunc_end4:
	.size	__ockl_hostcall_preview, .Lfunc_end4-__ockl_hostcall_preview
                                        ; -- End function
	.set .L__ockl_hostcall_preview.num_vgpr, max(34, .L__ockl_hostcall_internal.num_vgpr)
	.set .L__ockl_hostcall_preview.num_agpr, max(0, .L__ockl_hostcall_internal.num_agpr)
	.set .L__ockl_hostcall_preview.numbered_sgpr, max(34, .L__ockl_hostcall_internal.numbered_sgpr)
	.set .L__ockl_hostcall_preview.num_named_barrier, max(0, .L__ockl_hostcall_internal.num_named_barrier)
	.set .L__ockl_hostcall_preview.private_seg_size, 8+max(.L__ockl_hostcall_internal.private_seg_size)
	.set .L__ockl_hostcall_preview.uses_vcc, or(1, .L__ockl_hostcall_internal.uses_vcc)
	.set .L__ockl_hostcall_preview.uses_flat_scratch, or(0, .L__ockl_hostcall_internal.uses_flat_scratch)
	.set .L__ockl_hostcall_preview.has_dyn_sized_stack, or(0, .L__ockl_hostcall_internal.has_dyn_sized_stack)
	.set .L__ockl_hostcall_preview.has_recursion, or(0, .L__ockl_hostcall_internal.has_recursion)
	.set .L__ockl_hostcall_preview.has_indirect_call, or(0, .L__ockl_hostcall_internal.has_indirect_call)
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 240
; TotalNumSgprs: 36
; NumVgprs: 34
; ScratchSize: 24
; MemoryBound: 0
	.text
	.p2align	7                               ; -- Begin function __ockl_fprintf_stderr_begin
	.type	__ockl_fprintf_stderr_begin,@function
__ockl_fprintf_stderr_begin:            ; @__ockl_fprintf_stderr_begin
; %bb.0:
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_mov_b32 s16, s33
	s_mov_b32 s33, s32
	s_xor_saveexec_b32 s0, -1
	scratch_store_b32 off, v34, s33         ; 4-byte Folded Spill
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s0
	v_writelane_b32 v34, s30, 0
	v_dual_mov_b32 v0, 2 :: v_dual_mov_b32 v1, 33
	v_dual_mov_b32 v2, 0 :: v_dual_mov_b32 v3, 1
	v_dual_mov_b32 v4, 0 :: v_dual_mov_b32 v5, 0
	v_dual_mov_b32 v6, 0 :: v_dual_mov_b32 v7, 0
	v_dual_mov_b32 v8, 0 :: v_dual_mov_b32 v9, 0
	v_dual_mov_b32 v10, 0 :: v_dual_mov_b32 v11, 0
	v_dual_mov_b32 v12, 0 :: v_dual_mov_b32 v13, 0
	v_dual_mov_b32 v14, 0 :: v_dual_mov_b32 v15, 0
	v_mov_b32_e32 v16, 0
	s_add_co_i32 s32, s32, 16
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_hostcall_preview@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_hostcall_preview@rel32@hi+24
	v_writelane_b32 v34, s31, 1
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	s_delay_alu instid0(VALU_DEP_1)
	v_readlane_b32 s31, v34, 1
	v_readlane_b32 s30, v34, 0
	s_mov_b32 s32, s33
	s_xor_saveexec_b32 s0, -1
	scratch_load_b32 v34, off, s33          ; 4-byte Folded Reload
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s0
	s_mov_b32 s33, s16
	s_wait_loadcnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	s_setpc_b64 s[30:31]
.Lfunc_end5:
	.size	__ockl_fprintf_stderr_begin, .Lfunc_end5-__ockl_fprintf_stderr_begin
                                        ; -- End function
	.set .L__ockl_fprintf_stderr_begin.num_vgpr, max(35, .L__ockl_hostcall_preview.num_vgpr)
	.set .L__ockl_fprintf_stderr_begin.num_agpr, max(0, .L__ockl_hostcall_preview.num_agpr)
	.set .L__ockl_fprintf_stderr_begin.numbered_sgpr, max(34, .L__ockl_hostcall_preview.numbered_sgpr)
	.set .L__ockl_fprintf_stderr_begin.num_named_barrier, max(0, .L__ockl_hostcall_preview.num_named_barrier)
	.set .L__ockl_fprintf_stderr_begin.private_seg_size, 16+max(.L__ockl_hostcall_preview.private_seg_size)
	.set .L__ockl_fprintf_stderr_begin.uses_vcc, or(1, .L__ockl_hostcall_preview.uses_vcc)
	.set .L__ockl_fprintf_stderr_begin.uses_flat_scratch, or(0, .L__ockl_hostcall_preview.uses_flat_scratch)
	.set .L__ockl_fprintf_stderr_begin.has_dyn_sized_stack, or(0, .L__ockl_hostcall_preview.has_dyn_sized_stack)
	.set .L__ockl_fprintf_stderr_begin.has_recursion, or(0, .L__ockl_hostcall_preview.has_recursion)
	.set .L__ockl_fprintf_stderr_begin.has_indirect_call, or(0, .L__ockl_hostcall_preview.has_indirect_call)
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 244
; TotalNumSgprs: 36
; NumVgprs: 35
; ScratchSize: 40
; MemoryBound: 0
	.text
	.p2align	7                               ; -- Begin function __ockl_fprintf_append_string_n
	.type	__ockl_fprintf_append_string_n,@function
__ockl_fprintf_append_string_n:         ; @__ockl_fprintf_append_string_n
; %bb.0:
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_mov_b32 s26, s33
	s_mov_b32 s33, s32
	s_or_saveexec_b32 s0, -1
	scratch_store_b32 off, v40, s33         ; 4-byte Folded Spill
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s0
	v_mov_b32_e32 v36, v2
	v_mov_b32_e32 v2, v1
	v_or_b32_e32 v1, 2, v0
	v_cmp_eq_u32_e64 s0, 0, v6
	v_writelane_b32 v40, s30, 0
	v_dual_mov_b32 v38, v31 :: v_dual_mov_b32 v35, v5
	v_dual_mov_b32 v34, v4 :: v_dual_mov_b32 v37, v3
	s_wait_alu depctr_va_sdst(0)
	v_cndmask_b32_e64 v1, v1, v0, s0
	s_mov_b64 s[16:17], s[10:11]
	s_mov_b64 s[18:19], s[8:9]
	s_mov_b64 s[20:21], s[6:7]
	s_mov_b64 s[22:23], s[4:5]
	s_mov_b32 s25, 0
	s_add_co_i32 s32, s32, 16
	v_writelane_b32 v40, s31, 1
	s_mov_b32 s0, exec_lo
	v_cmpx_ne_u64_e32 0, v[36:37]
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s24, exec_lo, s0
                                        ; implicit-def: $vgpr0
	s_cbranch_execz .LBB6_60
; %bb.1:
	v_and_b32_e32 v39, 2, v1
	v_dual_mov_b32 v49, 0 :: v_dual_and_b32 v0, -3, v1
.LBB6_2:                                ; =>This Loop Header: Depth=1
                                        ;     Child Loop BB6_5 Depth 2
                                        ;     Child Loop BB6_13 Depth 2
                                        ;     Child Loop BB6_21 Depth 2
                                        ;     Child Loop BB6_29 Depth 2
                                        ;     Child Loop BB6_37 Depth 2
                                        ;     Child Loop BB6_45 Depth 2
                                        ;     Child Loop BB6_53 Depth 2
	v_cmp_gt_u64_e32 vcc_lo, 56, v[34:35]
	s_mov_b32 s1, exec_lo
                                        ; implicit-def: $vgpr3_vgpr4
	s_wait_alu depctr_va_vcc(0)
	v_cndmask_b32_e32 v50, 56, v34, vcc_lo
	v_cmpx_gt_u64_e32 8, v[34:35]
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s1, exec_lo, s1
	s_cbranch_execz .LBB6_8
; %bb.3:                                ;   in Loop: Header=BB6_2 Depth=1
	v_mov_b32_e32 v3, 0
	v_mov_b32_e32 v4, 0
	s_mov_b32 s2, exec_lo
	v_cmpx_ne_u64_e32 0, v[34:35]
	s_cbranch_execz .LBB6_7
; %bb.4:                                ; %.preheader11
                                        ;   in Loop: Header=BB6_2 Depth=1
	v_mov_b32_e32 v3, 0
	v_mov_b32_e32 v4, 0
	s_mov_b32 s3, 0
	s_mov_b32 s4, 0
.LBB6_5:                                ;   Parent Loop BB6_2 Depth=1
                                        ; =>  This Inner Loop Header: Depth=2
	s_wait_alu depctr_sa_sdst(0)
	v_add_co_u32 v5, s0, v36, s4
	s_wait_alu depctr_va_sdst(0)
	v_add_co_ci_u32_e64 v6, null, 0, v37, s0
	v_mov_b16_e32 v48.h, 0
	s_lshl_b32 s0, s4, 3
	s_add_co_i32 s4, s4, 1
	flat_load_d16_u8 v48, v[5:6]
	s_wait_loadcnt_dscnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	v_lshlrev_b64_e32 v[5:6], s0, v[48:49]
	v_cmp_eq_u32_e64 s0, s4, v50
	s_or_b32 s3, s0, s3
	v_or_b32_e32 v4, v6, v4
	v_or_b32_e32 v3, v5, v3
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s3
	s_cbranch_execnz .LBB6_5
; %bb.6:                                ; %Flow41
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_or_b32 exec_lo, exec_lo, s3
.LBB6_7:                                ; %Flow42
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s2
.LBB6_8:                                ; %Flow43
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_saveexec_b32 s1, s1
	v_mov_b32_e32 v17, v36
	v_dual_mov_b32 v1, 0 :: v_dual_mov_b32 v18, v37
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 exec_lo, exec_lo, s1
	s_cbranch_execz .LBB6_10
; %bb.9:                                ;   in Loop: Header=BB6_2 Depth=1
	flat_load_b64 v[3:4], v[36:37]
	v_add_co_u32 v17, s0, v36, 8
	s_wait_alu depctr_va_sdst(0)
	v_add_co_ci_u32_e64 v18, null, 0, v37, s0
	s_wait_loadcnt_dscnt 0x0
	v_and_b32_e32 v1, 0xff, v4
	v_and_b32_e32 v5, 0xff00, v4
	v_and_b32_e32 v6, 0xff0000, v4
	v_and_b32_e32 v4, 0xff000000, v4
	v_or3_b32 v3, v3, 0, 0
	s_delay_alu instid0(VALU_DEP_4) | instskip(SKIP_1) | instid1(VALU_DEP_2)
	v_or_b32_e32 v5, v1, v5
	v_add_nc_u32_e32 v1, -8, v50
	v_or3_b32 v4, v5, v6, v4
.LBB6_10:                               ;   in Loop: Header=BB6_2 Depth=1
	s_or_b32 exec_lo, exec_lo, s1
	s_delay_alu instid0(SALU_CYCLE_1) | instskip(NEXT) | instid1(VALU_DEP_1)
	s_mov_b32 s1, exec_lo
                                        ; implicit-def: $vgpr5_vgpr6
	v_cmpx_gt_u32_e32 8, v1
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s1, exec_lo, s1
	s_cbranch_execz .LBB6_16
; %bb.11:                               ;   in Loop: Header=BB6_2 Depth=1
	v_mov_b32_e32 v5, 0
	v_mov_b32_e32 v6, 0
	s_mov_b32 s2, exec_lo
	v_cmpx_ne_u32_e32 0, v1
	s_cbranch_execz .LBB6_15
; %bb.12:                               ; %.preheader9
                                        ;   in Loop: Header=BB6_2 Depth=1
	v_mov_b32_e32 v5, 0
	v_mov_b32_e32 v6, 0
	s_mov_b32 s3, 0
	s_mov_b32 s4, 0
.LBB6_13:                               ;   Parent Loop BB6_2 Depth=1
                                        ; =>  This Inner Loop Header: Depth=2
	s_wait_alu depctr_sa_sdst(0)
	v_add_co_u32 v7, s0, v17, s4
	s_wait_alu depctr_va_sdst(0)
	v_add_co_ci_u32_e64 v8, null, 0, v18, s0
	v_mov_b16_e32 v48.h, 0
	s_lshl_b32 s0, s4, 3
	s_add_co_i32 s4, s4, 1
	flat_load_d16_u8 v48, v[7:8]
	s_wait_loadcnt_dscnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	v_lshlrev_b64_e32 v[7:8], s0, v[48:49]
	v_cmp_eq_u32_e64 s0, s4, v1
	s_or_b32 s3, s0, s3
	v_or_b32_e32 v6, v8, v6
	v_or_b32_e32 v5, v7, v5
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s3
	s_cbranch_execnz .LBB6_13
; %bb.14:                               ; %Flow38
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_or_b32 exec_lo, exec_lo, s3
.LBB6_15:                               ; %Flow39
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s2
                                        ; implicit-def: $vgpr1
.LBB6_16:                               ; %Flow40
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_saveexec_b32 s1, s1
	v_mov_b32_e32 v9, 0
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 exec_lo, exec_lo, s1
	s_cbranch_execz .LBB6_18
; %bb.17:                               ;   in Loop: Header=BB6_2 Depth=1
	flat_load_b64 v[5:6], v[17:18]
	v_add_co_u32 v17, s0, v17, 8
	v_add_nc_u32_e32 v9, -8, v1
	s_wait_alu depctr_va_sdst(0)
	v_add_co_ci_u32_e64 v18, null, 0, v18, s0
	s_wait_loadcnt_dscnt 0x0
	v_and_b32_e32 v7, 0xff, v6
	v_and_b32_e32 v8, 0xff00, v6
	v_and_b32_e32 v10, 0xff0000, v6
	v_and_b32_e32 v6, 0xff000000, v6
	v_or3_b32 v5, v5, 0, 0
	s_delay_alu instid0(VALU_DEP_4) | instskip(NEXT) | instid1(VALU_DEP_1)
	v_or_b32_e32 v7, v7, v8
	v_or3_b32 v6, v7, v10, v6
.LBB6_18:                               ;   in Loop: Header=BB6_2 Depth=1
	s_or_b32 exec_lo, exec_lo, s1
	s_delay_alu instid0(SALU_CYCLE_1)
	s_mov_b32 s1, exec_lo
                                        ; implicit-def: $vgpr7_vgpr8
	v_cmpx_gt_u32_e32 8, v9
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s1, exec_lo, s1
	s_cbranch_execz .LBB6_24
; %bb.19:                               ;   in Loop: Header=BB6_2 Depth=1
	v_mov_b32_e32 v7, 0
	v_mov_b32_e32 v8, 0
	s_mov_b32 s2, exec_lo
	v_cmpx_ne_u32_e32 0, v9
	s_cbranch_execz .LBB6_23
; %bb.20:                               ; %.preheader7
                                        ;   in Loop: Header=BB6_2 Depth=1
	v_mov_b32_e32 v7, 0
	v_mov_b32_e32 v8, 0
	s_mov_b32 s3, 0
	s_mov_b32 s4, 0
.LBB6_21:                               ;   Parent Loop BB6_2 Depth=1
                                        ; =>  This Inner Loop Header: Depth=2
	s_wait_alu depctr_sa_sdst(0)
	v_add_co_u32 v10, s0, v17, s4
	s_wait_alu depctr_va_sdst(0)
	v_add_co_ci_u32_e64 v11, null, 0, v18, s0
	v_mov_b16_e32 v48.h, 0
	s_lshl_b32 s0, s4, 3
	s_add_co_i32 s4, s4, 1
	flat_load_d16_u8 v48, v[10:11]
	s_wait_loadcnt_dscnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	v_lshlrev_b64_e32 v[10:11], s0, v[48:49]
	v_cmp_eq_u32_e64 s0, s4, v9
	s_or_b32 s3, s0, s3
	v_or_b32_e32 v8, v11, v8
	v_or_b32_e32 v7, v10, v7
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s3
	s_cbranch_execnz .LBB6_21
; %bb.22:                               ; %Flow35
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_or_b32 exec_lo, exec_lo, s3
.LBB6_23:                               ; %Flow36
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s2
                                        ; implicit-def: $vgpr9
.LBB6_24:                               ; %Flow37
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_saveexec_b32 s1, s1
	v_mov_b32_e32 v1, 0
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 exec_lo, exec_lo, s1
	s_cbranch_execz .LBB6_26
; %bb.25:                               ;   in Loop: Header=BB6_2 Depth=1
	flat_load_b64 v[7:8], v[17:18]
	v_add_co_u32 v17, s0, v17, 8
	s_wait_alu depctr_va_sdst(0)
	v_add_co_ci_u32_e64 v18, null, 0, v18, s0
	s_wait_loadcnt_dscnt 0x0
	v_and_b32_e32 v1, 0xff, v8
	v_and_b32_e32 v10, 0xff00, v8
	v_and_b32_e32 v11, 0xff0000, v8
	v_and_b32_e32 v8, 0xff000000, v8
	v_or3_b32 v7, v7, 0, 0
	s_delay_alu instid0(VALU_DEP_4) | instskip(SKIP_1) | instid1(VALU_DEP_2)
	v_or_b32_e32 v10, v1, v10
	v_add_nc_u32_e32 v1, -8, v9
	v_or3_b32 v8, v10, v11, v8
.LBB6_26:                               ;   in Loop: Header=BB6_2 Depth=1
	s_or_b32 exec_lo, exec_lo, s1
	s_delay_alu instid0(SALU_CYCLE_1) | instskip(NEXT) | instid1(VALU_DEP_1)
	s_mov_b32 s1, exec_lo
                                        ; implicit-def: $vgpr9_vgpr10
	v_cmpx_gt_u32_e32 8, v1
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s1, exec_lo, s1
	s_cbranch_execz .LBB6_32
; %bb.27:                               ;   in Loop: Header=BB6_2 Depth=1
	v_mov_b32_e32 v9, 0
	v_mov_b32_e32 v10, 0
	s_mov_b32 s2, exec_lo
	v_cmpx_ne_u32_e32 0, v1
	s_cbranch_execz .LBB6_31
; %bb.28:                               ; %.preheader5
                                        ;   in Loop: Header=BB6_2 Depth=1
	v_mov_b32_e32 v9, 0
	v_mov_b32_e32 v10, 0
	s_mov_b32 s3, 0
	s_mov_b32 s4, 0
.LBB6_29:                               ;   Parent Loop BB6_2 Depth=1
                                        ; =>  This Inner Loop Header: Depth=2
	s_wait_alu depctr_sa_sdst(0)
	v_add_co_u32 v11, s0, v17, s4
	s_wait_alu depctr_va_sdst(0)
	v_add_co_ci_u32_e64 v12, null, 0, v18, s0
	v_mov_b16_e32 v48.h, 0
	s_lshl_b32 s0, s4, 3
	s_add_co_i32 s4, s4, 1
	flat_load_d16_u8 v48, v[11:12]
	s_wait_loadcnt_dscnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	v_lshlrev_b64_e32 v[11:12], s0, v[48:49]
	v_cmp_eq_u32_e64 s0, s4, v1
	s_or_b32 s3, s0, s3
	v_or_b32_e32 v10, v12, v10
	v_or_b32_e32 v9, v11, v9
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s3
	s_cbranch_execnz .LBB6_29
; %bb.30:                               ; %Flow32
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_or_b32 exec_lo, exec_lo, s3
.LBB6_31:                               ; %Flow33
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s2
                                        ; implicit-def: $vgpr1
.LBB6_32:                               ; %Flow34
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_saveexec_b32 s1, s1
	v_mov_b32_e32 v13, 0
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 exec_lo, exec_lo, s1
	s_cbranch_execz .LBB6_34
; %bb.33:                               ;   in Loop: Header=BB6_2 Depth=1
	flat_load_b64 v[9:10], v[17:18]
	v_add_co_u32 v17, s0, v17, 8
	v_add_nc_u32_e32 v13, -8, v1
	s_wait_alu depctr_va_sdst(0)
	v_add_co_ci_u32_e64 v18, null, 0, v18, s0
	s_wait_loadcnt_dscnt 0x0
	v_and_b32_e32 v11, 0xff, v10
	v_and_b32_e32 v12, 0xff00, v10
	v_and_b32_e32 v14, 0xff0000, v10
	v_and_b32_e32 v10, 0xff000000, v10
	v_or3_b32 v9, v9, 0, 0
	s_delay_alu instid0(VALU_DEP_4) | instskip(NEXT) | instid1(VALU_DEP_1)
	v_or_b32_e32 v11, v11, v12
	v_or3_b32 v10, v11, v14, v10
.LBB6_34:                               ;   in Loop: Header=BB6_2 Depth=1
	s_or_b32 exec_lo, exec_lo, s1
	s_delay_alu instid0(SALU_CYCLE_1)
	s_mov_b32 s1, exec_lo
                                        ; implicit-def: $vgpr11_vgpr12
	v_cmpx_gt_u32_e32 8, v13
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s1, exec_lo, s1
	s_cbranch_execz .LBB6_40
; %bb.35:                               ;   in Loop: Header=BB6_2 Depth=1
	v_mov_b32_e32 v11, 0
	v_mov_b32_e32 v12, 0
	s_mov_b32 s2, exec_lo
	v_cmpx_ne_u32_e32 0, v13
	s_cbranch_execz .LBB6_39
; %bb.36:                               ; %.preheader3
                                        ;   in Loop: Header=BB6_2 Depth=1
	v_mov_b32_e32 v11, 0
	v_mov_b32_e32 v12, 0
	s_mov_b32 s3, 0
	s_mov_b32 s4, 0
.LBB6_37:                               ;   Parent Loop BB6_2 Depth=1
                                        ; =>  This Inner Loop Header: Depth=2
	s_wait_alu depctr_sa_sdst(0)
	v_add_co_u32 v14, s0, v17, s4
	s_wait_alu depctr_va_sdst(0)
	v_add_co_ci_u32_e64 v15, null, 0, v18, s0
	v_mov_b16_e32 v48.h, 0
	s_lshl_b32 s0, s4, 3
	s_add_co_i32 s4, s4, 1
	flat_load_d16_u8 v48, v[14:15]
	s_wait_loadcnt_dscnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	v_lshlrev_b64_e32 v[14:15], s0, v[48:49]
	v_cmp_eq_u32_e64 s0, s4, v13
	s_or_b32 s3, s0, s3
	v_or_b32_e32 v12, v15, v12
	v_or_b32_e32 v11, v14, v11
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s3
	s_cbranch_execnz .LBB6_37
; %bb.38:                               ; %Flow29
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_or_b32 exec_lo, exec_lo, s3
.LBB6_39:                               ; %Flow30
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s2
                                        ; implicit-def: $vgpr13
.LBB6_40:                               ; %Flow31
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_saveexec_b32 s1, s1
	v_mov_b32_e32 v1, 0
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 exec_lo, exec_lo, s1
	s_cbranch_execz .LBB6_42
; %bb.41:                               ;   in Loop: Header=BB6_2 Depth=1
	flat_load_b64 v[11:12], v[17:18]
	v_add_co_u32 v17, s0, v17, 8
	s_wait_alu depctr_va_sdst(0)
	v_add_co_ci_u32_e64 v18, null, 0, v18, s0
	s_wait_loadcnt_dscnt 0x0
	v_and_b32_e32 v1, 0xff, v12
	v_and_b32_e32 v14, 0xff00, v12
	v_and_b32_e32 v15, 0xff0000, v12
	v_and_b32_e32 v12, 0xff000000, v12
	v_or3_b32 v11, v11, 0, 0
	s_delay_alu instid0(VALU_DEP_4) | instskip(SKIP_1) | instid1(VALU_DEP_2)
	v_or_b32_e32 v14, v1, v14
	v_add_nc_u32_e32 v1, -8, v13
	v_or3_b32 v12, v14, v15, v12
.LBB6_42:                               ;   in Loop: Header=BB6_2 Depth=1
	s_or_b32 exec_lo, exec_lo, s1
	s_delay_alu instid0(SALU_CYCLE_1) | instskip(NEXT) | instid1(VALU_DEP_1)
	s_mov_b32 s1, exec_lo
                                        ; implicit-def: $vgpr13_vgpr14
	v_cmpx_gt_u32_e32 8, v1
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s1, exec_lo, s1
	s_cbranch_execz .LBB6_48
; %bb.43:                               ;   in Loop: Header=BB6_2 Depth=1
	v_mov_b32_e32 v13, 0
	v_mov_b32_e32 v14, 0
	s_mov_b32 s2, exec_lo
	v_cmpx_ne_u32_e32 0, v1
	s_cbranch_execz .LBB6_47
; %bb.44:                               ; %.preheader1
                                        ;   in Loop: Header=BB6_2 Depth=1
	v_mov_b32_e32 v13, 0
	v_mov_b32_e32 v14, 0
	s_mov_b32 s3, 0
	s_mov_b32 s4, 0
.LBB6_45:                               ;   Parent Loop BB6_2 Depth=1
                                        ; =>  This Inner Loop Header: Depth=2
	s_wait_alu depctr_sa_sdst(0)
	v_add_co_u32 v15, s0, v17, s4
	s_wait_alu depctr_va_sdst(0)
	v_add_co_ci_u32_e64 v16, null, 0, v18, s0
	v_mov_b16_e32 v48.h, 0
	s_lshl_b32 s0, s4, 3
	s_add_co_i32 s4, s4, 1
	flat_load_d16_u8 v48, v[15:16]
	s_wait_loadcnt_dscnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	v_lshlrev_b64_e32 v[15:16], s0, v[48:49]
	v_cmp_eq_u32_e64 s0, s4, v1
	s_or_b32 s3, s0, s3
	v_or_b32_e32 v14, v16, v14
	v_or_b32_e32 v13, v15, v13
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s3
	s_cbranch_execnz .LBB6_45
; %bb.46:                               ; %Flow26
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_or_b32 exec_lo, exec_lo, s3
.LBB6_47:                               ; %Flow27
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s2
                                        ; implicit-def: $vgpr1
.LBB6_48:                               ; %Flow28
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_saveexec_b32 s1, s1
	v_mov_b32_e32 v19, 0
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 exec_lo, exec_lo, s1
	s_cbranch_execz .LBB6_50
; %bb.49:                               ;   in Loop: Header=BB6_2 Depth=1
	flat_load_b64 v[13:14], v[17:18]
	v_add_co_u32 v17, s0, v17, 8
	v_add_nc_u32_e32 v19, -8, v1
	s_wait_alu depctr_va_sdst(0)
	v_add_co_ci_u32_e64 v18, null, 0, v18, s0
	s_wait_loadcnt_dscnt 0x0
	v_and_b32_e32 v15, 0xff, v14
	v_and_b32_e32 v16, 0xff00, v14
	v_and_b32_e32 v20, 0xff0000, v14
	v_and_b32_e32 v14, 0xff000000, v14
	v_or3_b32 v13, v13, 0, 0
	s_delay_alu instid0(VALU_DEP_4) | instskip(NEXT) | instid1(VALU_DEP_1)
	v_or_b32_e32 v15, v15, v16
	v_or3_b32 v14, v15, v20, v14
.LBB6_50:                               ;   in Loop: Header=BB6_2 Depth=1
	s_or_b32 exec_lo, exec_lo, s1
                                        ; implicit-def: $vgpr15_vgpr16
	s_delay_alu instid0(SALU_CYCLE_1)
	s_mov_b32 s1, exec_lo
	v_cmpx_gt_u32_e32 8, v19
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s4, exec_lo, s1
	s_cbranch_execz .LBB6_56
; %bb.51:                               ;   in Loop: Header=BB6_2 Depth=1
	v_mov_b32_e32 v15, 0
	v_mov_b32_e32 v16, 0
	s_mov_b32 s5, exec_lo
	v_cmpx_ne_u32_e32 0, v19
	s_cbranch_execz .LBB6_55
; %bb.52:                               ; %.preheader
                                        ;   in Loop: Header=BB6_2 Depth=1
	v_mov_b32_e32 v15, 0
	v_mov_b32_e32 v16, 0
	s_mov_b64 s[2:3], 0
	s_mov_b32 s6, 0
.LBB6_53:                               ;   Parent Loop BB6_2 Depth=1
                                        ; =>  This Inner Loop Header: Depth=2
	flat_load_d16_u8 v48, v[17:18]
	s_wait_loadcnt_dscnt 0x0
	v_mov_b16_e32 v48.h, 0
	v_add_nc_u32_e32 v19, -1, v19
	v_add_co_u32 v17, s0, v17, 1
	s_wait_alu depctr_va_sdst(0)
	v_add_co_ci_u32_e64 v18, null, 0, v18, s0
	s_delay_alu instid0(VALU_DEP_3) | instskip(SKIP_4) | instid1(VALU_DEP_1)
	v_cmp_eq_u32_e64 s1, 0, v19
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 s6, s1, s6
	v_lshlrev_b64_e32 v[20:21], s2, v[48:49]
	s_add_nc_u64 s[2:3], s[2:3], 8
	v_or_b32_e32 v16, v21, v16
	s_delay_alu instid0(VALU_DEP_2)
	v_or_b32_e32 v15, v20, v15
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s6
	s_cbranch_execnz .LBB6_53
; %bb.54:                               ; %Flow
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_or_b32 exec_lo, exec_lo, s6
.LBB6_55:                               ; %Flow24
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s5
                                        ; implicit-def: $vgpr17_vgpr18
.LBB6_56:                               ; %Flow25
                                        ;   in Loop: Header=BB6_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_saveexec_b32 s0, s4
	s_cbranch_execz .LBB6_58
; %bb.57:                               ;   in Loop: Header=BB6_2 Depth=1
	flat_load_b64 v[15:16], v[17:18]
	s_wait_loadcnt_dscnt 0x0
	v_and_b32_e32 v1, 0xff, v16
	v_and_b32_e32 v17, 0xff00, v16
	v_and_b32_e32 v18, 0xff0000, v16
	v_and_b32_e32 v16, 0xff000000, v16
	v_or3_b32 v15, v15, 0, 0
	s_delay_alu instid0(VALU_DEP_4) | instskip(NEXT) | instid1(VALU_DEP_1)
	v_or_b32_e32 v1, v1, v17
	v_or3_b32 v16, v1, v18, v16
.LBB6_58:                               ;   in Loop: Header=BB6_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s0
	v_cmp_gt_u64_e64 s0, 57, v[34:35]
	v_dual_mov_b32 v31, v38 :: v_dual_and_b32 v0, 0xffffff1f, v0
	v_lshl_add_u32 v17, v50, 2, 28
	s_mov_b64 s[4:5], s[22:23]
	s_mov_b64 s[6:7], s[20:21]
	v_cndmask_b32_e64 v1, 0, v39, s0
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_hostcall_preview@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_hostcall_preview@rel32@hi+24
	s_mov_b64 s[8:9], s[18:19]
	s_mov_b64 s[10:11], s[16:17]
	v_cndmask_b32_e32 v48, 0, v35, vcc_lo
	v_or_b32_e32 v0, v0, v1
	s_delay_alu instid0(VALU_DEP_1)
	v_and_or_b32 v1, 0x1e0, v17, v0
	v_mov_b32_e32 v0, 2
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	v_sub_co_u32 v34, vcc_lo, v34, v50
	s_wait_alu depctr_va_vcc(0)
	v_sub_co_ci_u32_e64 v35, null, v35, v48, vcc_lo
	v_add_co_u32 v36, s0, v36, v50
	v_mov_b32_e32 v2, v1
	s_delay_alu instid0(VALU_DEP_3)
	v_cmp_eq_u64_e32 vcc_lo, 0, v[34:35]
	s_wait_alu depctr_va_sdst(0)
	v_add_co_ci_u32_e64 v37, null, v37, v48, s0
	s_or_b32 s25, vcc_lo, s25
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s25
	s_cbranch_execnz .LBB6_2
; %bb.59:                               ; %Flow44
	s_or_b32 exec_lo, exec_lo, s25
                                        ; implicit-def: $vgpr1
                                        ; implicit-def: $vgpr38
.LBB6_60:                               ; %Flow45
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_saveexec_b32 s24, s24
	s_cbranch_execnz .LBB6_62
.LBB6_61:
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s24
	s_delay_alu instid0(VALU_DEP_1)
	v_mov_b32_e32 v1, v2
	v_readlane_b32 s31, v40, 1
	v_readlane_b32 s30, v40, 0
	s_mov_b32 s32, s33
	s_or_saveexec_b32 s0, -1
	scratch_load_b32 v40, off, s33          ; 4-byte Folded Reload
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s0
	s_mov_b32 s33, s26
	s_wait_loadcnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	s_setpc_b64 s[30:31]
.LBB6_62:
	v_and_or_b32 v1, 0xffffff1f, v1, 32
	v_dual_mov_b32 v31, v38 :: v_dual_mov_b32 v0, 2
	v_dual_mov_b32 v3, 0 :: v_dual_mov_b32 v4, 0
	v_dual_mov_b32 v5, 0 :: v_dual_mov_b32 v6, 0
	v_dual_mov_b32 v7, 0 :: v_dual_mov_b32 v8, 0
	v_dual_mov_b32 v9, 0 :: v_dual_mov_b32 v10, 0
	v_dual_mov_b32 v11, 0 :: v_dual_mov_b32 v12, 0
	v_dual_mov_b32 v13, 0 :: v_dual_mov_b32 v14, 0
	v_dual_mov_b32 v15, 0 :: v_dual_mov_b32 v16, 0
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_hostcall_preview@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_hostcall_preview@rel32@hi+24
	s_mov_b64 s[4:5], s[22:23]
	s_mov_b64 s[6:7], s[20:21]
	s_mov_b64 s[8:9], s[18:19]
	s_mov_b64 s[10:11], s[16:17]
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	v_mov_b32_e32 v2, v1
	s_branch .LBB6_61
.Lfunc_end6:
	.size	__ockl_fprintf_append_string_n, .Lfunc_end6-__ockl_fprintf_append_string_n
                                        ; -- End function
	.set .L__ockl_fprintf_append_string_n.num_vgpr, max(51, .L__ockl_hostcall_preview.num_vgpr)
	.set .L__ockl_fprintf_append_string_n.num_agpr, max(0, .L__ockl_hostcall_preview.num_agpr)
	.set .L__ockl_fprintf_append_string_n.numbered_sgpr, max(34, .L__ockl_hostcall_preview.numbered_sgpr)
	.set .L__ockl_fprintf_append_string_n.num_named_barrier, max(0, .L__ockl_hostcall_preview.num_named_barrier)
	.set .L__ockl_fprintf_append_string_n.private_seg_size, 16+max(.L__ockl_hostcall_preview.private_seg_size)
	.set .L__ockl_fprintf_append_string_n.uses_vcc, or(1, .L__ockl_hostcall_preview.uses_vcc)
	.set .L__ockl_fprintf_append_string_n.uses_flat_scratch, or(0, .L__ockl_hostcall_preview.uses_flat_scratch)
	.set .L__ockl_fprintf_append_string_n.has_dyn_sized_stack, or(0, .L__ockl_hostcall_preview.has_dyn_sized_stack)
	.set .L__ockl_fprintf_append_string_n.has_recursion, or(0, .L__ockl_hostcall_preview.has_recursion)
	.set .L__ockl_fprintf_append_string_n.has_indirect_call, or(0, .L__ockl_hostcall_preview.has_indirect_call)
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 2596
; TotalNumSgprs: 36
; NumVgprs: 51
; ScratchSize: 40
; MemoryBound: 0
	.text
	.p2align	7                               ; -- Begin function __ockl_fprintf_append_args
	.type	__ockl_fprintf_append_args,@function
__ockl_fprintf_append_args:             ; @__ockl_fprintf_append_args
; %bb.0:
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_mov_b32 s16, s33
	s_mov_b32 s33, s32
	s_xor_saveexec_b32 s0, -1
	scratch_store_b32 off, v34, s33         ; 4-byte Folded Spill
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s0
	v_or_b32_e32 v19, 2, v0
	v_cmp_eq_u32_e32 vcc_lo, 0, v17
	v_dual_mov_b32 v18, v3 :: v_dual_mov_b32 v3, 0
	v_writelane_b32 v34, s30, 0
	s_add_co_i32 s32, s32, 16
	s_wait_alu depctr_va_vcc(0)
	v_cndmask_b32_e32 v0, v19, v0, vcc_lo
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_hostcall_preview@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_hostcall_preview@rel32@hi+24
	v_lshlrev_b64_e32 v[19:20], 5, v[2:3]
	v_mov_b32_e32 v3, v18
	v_writelane_b32 v34, s31, 1
	v_and_b32_e32 v0, 0xffffff1f, v0
	s_delay_alu instid0(VALU_DEP_4) | instskip(NEXT) | instid1(VALU_DEP_2)
	v_or_b32_e32 v2, v1, v20
	v_or_b32_e32 v1, v0, v19
	v_mov_b32_e32 v0, 2
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	v_readlane_b32 s31, v34, 1
	v_readlane_b32 s30, v34, 0
	s_mov_b32 s32, s33
	s_xor_saveexec_b32 s0, -1
	scratch_load_b32 v34, off, s33          ; 4-byte Folded Reload
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s0
	s_mov_b32 s33, s16
	s_wait_loadcnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	s_setpc_b64 s[30:31]
.Lfunc_end7:
	.size	__ockl_fprintf_append_args, .Lfunc_end7-__ockl_fprintf_append_args
                                        ; -- End function
	.set .L__ockl_fprintf_append_args.num_vgpr, max(35, .L__ockl_hostcall_preview.num_vgpr)
	.set .L__ockl_fprintf_append_args.num_agpr, max(0, .L__ockl_hostcall_preview.num_agpr)
	.set .L__ockl_fprintf_append_args.numbered_sgpr, max(34, .L__ockl_hostcall_preview.numbered_sgpr)
	.set .L__ockl_fprintf_append_args.num_named_barrier, max(0, .L__ockl_hostcall_preview.num_named_barrier)
	.set .L__ockl_fprintf_append_args.private_seg_size, 16+max(.L__ockl_hostcall_preview.private_seg_size)
	.set .L__ockl_fprintf_append_args.uses_vcc, or(1, .L__ockl_hostcall_preview.uses_vcc)
	.set .L__ockl_fprintf_append_args.uses_flat_scratch, or(0, .L__ockl_hostcall_preview.uses_flat_scratch)
	.set .L__ockl_fprintf_append_args.has_dyn_sized_stack, or(0, .L__ockl_hostcall_preview.has_dyn_sized_stack)
	.set .L__ockl_fprintf_append_args.has_recursion, or(0, .L__ockl_hostcall_preview.has_recursion)
	.set .L__ockl_fprintf_append_args.has_indirect_call, or(0, .L__ockl_hostcall_preview.has_indirect_call)
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 228
; TotalNumSgprs: 36
; NumVgprs: 35
; ScratchSize: 40
; MemoryBound: 0
	.text
	.hidden	__assert_fail                   ; -- Begin function __assert_fail
	.weak	__assert_fail
	.p2align	7
	.type	__assert_fail,@function
__assert_fail:                          ; @__assert_fail
; %bb.0:                                ; %entry
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_mov_b32 s76, s33
	s_mov_b32 s33, s32
	s_or_saveexec_b32 s0, -1
	scratch_store_b32 off, v41, s33 offset:120 ; 4-byte Folded Spill
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s0
	s_mov_b64 s[46:47], src_private_base
	s_addk_co_i32 s32, 0x80
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s73, s47
	v_mov_b32_e32 v35, 0
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, .L__const.__assert_fail.fmt@rel32@lo+43
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, .L__const.__assert_fail.fmt@rel32@hi+55
	s_mov_b64 s[44:45], s[4:5]
	s_mov_b64 s[42:43], s[6:7]
	s_mov_b32 s63, s47
	global_load_b128 v[7:10], v35, s[0:1]
	s_add_co_i32 s0, s33, 16
	s_mov_b32 s61, s47
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s72, s0
	s_add_co_i32 s0, s33, 24
	v_writelane_b32 v41, s30, 0
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s62, s0
	s_add_co_i32 s0, s33, 32
	scratch_store_b32 off, v40, s33         ; 4-byte Folded Spill
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s60, s0
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, .L__const.__assert_fail.fmt@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, .L__const.__assert_fail.fmt@rel32@hi+24
	s_getpc_b64 s[4:5]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s5, s5
	s_add_co_u32 s4, s4, .L__const.__assert_fail.fmt@rel32@lo+28
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s5, s5, .L__const.__assert_fail.fmt@rel32@hi+40
	s_add_co_i32 s2, s33, 48
	v_mov_b32_e32 v19, s72
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s18, s2
	s_add_co_i32 s2, s33, 0x60
	v_mov_b32_e32 v20, s73
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s56, s2
	s_add_co_i32 s2, s33, 0x68
	s_add_co_i32 s16, s33, 0x70
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s58, s2
	s_clause 0x1
	s_load_b128 s[0:3], s[0:1], 0x0
	s_load_b128 s[4:7], s[4:5], 0x0
	s_mov_b32 s20, s16
	s_getpc_b64 s[16:17]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s17, s17
	s_add_co_u32 s16, s16, __ockl_fprintf_stderr_begin@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s17, s17, __ockl_fprintf_stderr_begin@rel32@hi+24
	s_add_co_i32 s19, s33, 8
	v_writelane_b32 v41, s31, 1
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s46, s19
	v_mov_b32_e32 v51, v31
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v11, s46 :: v_dual_mov_b32 v12, s47
	s_mov_b32 s19, s47
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v21, s62 :: v_dual_mov_b32 v26, s19
	v_dual_mov_b32 v23, s60 :: v_dual_mov_b32 v28, s19
	v_dual_mov_b32 v22, s63 :: v_dual_mov_b32 v27, s18
	flat_store_b64 v[11:12], v[0:1]
	v_dual_mov_b32 v24, s61 :: v_dual_mov_b32 v25, s18
	v_mov_b32_e32 v30, s19
	s_wait_kmcnt 0x0
	v_dual_mov_b32 v14, s3 :: v_dual_mov_b32 v13, s2
	v_dual_mov_b32 v18, s7 :: v_dual_mov_b32 v29, s18
	v_dual_mov_b32 v12, s1 :: v_dual_mov_b32 v11, s0
	v_dual_mov_b32 v16, s5 :: v_dual_mov_b32 v17, s6
	v_mov_b32_e32 v15, s4
	s_mov_b64 s[4:5], s[44:45]
	s_mov_b64 s[6:7], s[42:43]
	s_mov_b64 s[28:29], s[10:11]
	s_mov_b64 s[40:41], s[8:9]
	s_mov_b32 s57, s47
	s_mov_b32 s59, s47
	s_mov_b32 s21, s47
	flat_store_b64 v[19:20], v[2:3]
	flat_store_b32 v[21:22], v4
	flat_store_b64 v[23:24], v[5:6]
	s_clause 0x1
	flat_store_b128 v[25:26], v[11:14]
	flat_store_b128 v[27:28], v[15:18] offset:16
	s_wait_loadcnt 0x0
	flat_store_b128 v[29:30], v[7:10] offset:31
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[16:17]
	v_dual_mov_b32 v2, s56 :: v_dual_mov_b32 v3, s57
	v_dual_mov_b32 v4, s58 :: v_dual_mov_b32 v5, s59
	v_dual_mov_b32 v6, s18 :: v_dual_mov_b32 v7, s19
	flat_store_b64 v[2:3], v[0:1]
	v_dual_mov_b32 v2, s20 :: v_dual_mov_b32 v3, s21
	v_dual_mov_b32 v0, s20 :: v_dual_mov_b32 v1, s21
	s_mov_b32 s2, 0
	s_mov_b64 s[0:1], s[18:19]
	flat_store_b32 v[4:5], v35
	flat_store_b64 v[2:3], v[6:7]
.LBB8_1:                                ; %while.cond
                                        ; =>This Inner Loop Header: Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_add_nc_u64 s[4:5], s[0:1], 1
	v_dual_mov_b32 v5, s1 :: v_dual_mov_b32 v4, s0
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v2, s4 :: v_dual_mov_b32 v3, s5
	s_mov_b64 s[0:1], s[4:5]
	flat_store_b64 v[0:1], v[2:3]
	flat_load_d16_u8 v3, v[4:5]
	s_wait_loadcnt_dscnt 0x0
	v_cmp_eq_u16_e32 vcc_lo, 0, v3.l
	s_or_b32 s2, vcc_lo, s2
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s2
	s_cbranch_execnz .LBB8_1
; %bb.2:                                ; %while.end
	s_or_b32 exec_lo, exec_lo, s2
	s_add_co_i32 s0, s33, 48
	v_dual_mov_b32 v0, s58 :: v_dual_mov_b32 v1, s59
	s_wait_alu depctr_sa_sdst(0)
	v_subrev_nc_u32_e32 v2, s0, v2
	v_dual_mov_b32 v52, s56 :: v_dual_mov_b32 v53, s57
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_fprintf_append_string_n@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_fprintf_append_string_n@rel32@hi+24
	s_add_co_i32 s2, s33, 0x70
	flat_store_b32 v[0:1], v2
	flat_load_b32 v4, v[0:1]
	flat_load_b64 v[0:1], v[52:53]
	s_mov_b64 s[74:75], src_private_base
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s74, s2
	s_add_co_i32 s2, s33, 48
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v31, v51 :: v_dual_mov_b32 v2, s2
	v_dual_mov_b32 v3, s19 :: v_dual_mov_b32 v6, 0
	s_mov_b64 s[4:5], s[44:45]
	s_mov_b64 s[6:7], s[42:43]
	s_mov_b64 s[8:9], s[40:41]
	s_mov_b64 s[10:11], s[28:29]
	s_mov_b32 s27, 0
	s_wait_loadcnt_dscnt 0x101
	v_ashrrev_i32_e32 v5, 31, v4
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	v_dual_mov_b32 v2, s72 :: v_dual_mov_b32 v3, s73
	flat_store_b64 v[52:53], v[0:1]
	v_dual_mov_b32 v4, s74 :: v_dual_mov_b32 v5, s75
	flat_load_b64 v[0:1], v[2:3]
	v_dual_mov_b32 v2, s74 :: v_dual_mov_b32 v3, s75
	s_wait_loadcnt_dscnt 0x0
	flat_store_b64 v[4:5], v[0:1]
.LBB8_3:                                ; %while.cond7
                                        ; =>This Inner Loop Header: Depth=1
	v_dual_mov_b32 v5, v1 :: v_dual_mov_b32 v4, v0
	s_delay_alu instid0(VALU_DEP_1) | instskip(SKIP_1) | instid1(VALU_DEP_2)
	v_add_co_u32 v0, vcc_lo, v4, 1
	s_wait_alu depctr_va_vcc(0)
	v_add_co_ci_u32_e64 v1, null, 0, v5, vcc_lo
	flat_store_b64 v[2:3], v[0:1]
	flat_load_d16_u8 v4, v[4:5]
	s_wait_loadcnt_dscnt 0x0
	v_cmp_eq_u16_e32 vcc_lo, 0, v4.l
	s_or_b32 s27, vcc_lo, s27
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s27
	s_cbranch_execnz .LBB8_3
; %bb.4:                                ; %while.end11
	s_or_b32 exec_lo, exec_lo, s27
	v_dual_mov_b32 v2, s72 :: v_dual_mov_b32 v3, s73
	v_dual_mov_b32 v4, s58 :: v_dual_mov_b32 v5, s59
	v_dual_mov_b32 v52, s56 :: v_dual_mov_b32 v53, s57
	flat_load_b32 v1, v[2:3]
	v_dual_mov_b32 v31, v51 :: v_dual_mov_b32 v6, 0
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_fprintf_append_string_n@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_fprintf_append_string_n@rel32@hi+24
	s_add_co_i32 s2, s33, 0x70
	s_mov_b64 s[4:5], s[44:45]
	s_mov_b64 s[6:7], s[42:43]
	s_mov_b64 s[8:9], s[40:41]
	s_mov_b64 s[10:11], s[28:29]
	s_mov_b64 s[74:75], src_private_base
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s74, s2
	s_wait_loadcnt_dscnt 0x0
	v_sub_nc_u32_e32 v0, v0, v1
	flat_store_b32 v[4:5], v0
	flat_load_b32 v4, v[4:5]
	flat_load_b64 v[0:1], v[52:53]
	flat_load_b64 v[2:3], v[2:3]
	s_wait_loadcnt_dscnt 0x202
	v_ashrrev_i32_e32 v5, 31, v4
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	v_dual_mov_b32 v2, s62 :: v_dual_mov_b32 v3, s63
	flat_store_b64 v[52:53], v[0:1]
	v_dual_mov_b32 v31, v51 :: v_dual_mov_b32 v4, 0
	v_mov_b32_e32 v5, 0
	flat_load_b32 v3, v[2:3]
	v_mov_b32_e32 v2, 1
	v_dual_mov_b32 v6, 0 :: v_dual_mov_b32 v7, 0
	v_dual_mov_b32 v8, 0 :: v_dual_mov_b32 v9, 0
	v_dual_mov_b32 v10, 0 :: v_dual_mov_b32 v11, 0
	v_dual_mov_b32 v12, 0 :: v_dual_mov_b32 v13, 0
	v_dual_mov_b32 v14, 0 :: v_dual_mov_b32 v15, 0
	v_dual_mov_b32 v16, 0 :: v_dual_mov_b32 v17, 0
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_fprintf_append_args@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_fprintf_append_args@rel32@hi+24
	s_mov_b64 s[4:5], s[44:45]
	s_mov_b64 s[6:7], s[42:43]
	s_mov_b64 s[8:9], s[40:41]
	s_mov_b64 s[10:11], s[28:29]
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	v_dual_mov_b32 v2, s60 :: v_dual_mov_b32 v3, s61
	flat_store_b64 v[52:53], v[0:1]
	v_dual_mov_b32 v4, s74 :: v_dual_mov_b32 v5, s75
	s_mov_b32 s0, 0
	flat_load_b64 v[0:1], v[2:3]
	v_dual_mov_b32 v2, s74 :: v_dual_mov_b32 v3, s75
	s_wait_loadcnt_dscnt 0x0
	flat_store_b64 v[4:5], v[0:1]
.LBB8_5:                                ; %while.cond24
                                        ; =>This Inner Loop Header: Depth=1
	v_dual_mov_b32 v5, v1 :: v_dual_mov_b32 v4, v0
	s_delay_alu instid0(VALU_DEP_1) | instskip(SKIP_1) | instid1(VALU_DEP_2)
	v_add_co_u32 v0, vcc_lo, v4, 1
	s_wait_alu depctr_va_vcc(0)
	v_add_co_ci_u32_e64 v1, null, 0, v5, vcc_lo
	flat_store_b64 v[2:3], v[0:1]
	flat_load_d16_u8 v4, v[4:5]
	s_wait_loadcnt_dscnt 0x0
	v_cmp_eq_u16_e32 vcc_lo, 0, v4.l
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 s0, vcc_lo, s0
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s0
	s_cbranch_execnz .LBB8_5
; %bb.6:                                ; %while.end28
	s_or_b32 exec_lo, exec_lo, s0
	v_dual_mov_b32 v2, s60 :: v_dual_mov_b32 v3, s61
	v_dual_mov_b32 v4, s58 :: v_dual_mov_b32 v5, s59
	v_dual_mov_b32 v52, s56 :: v_dual_mov_b32 v53, s57
	flat_load_b32 v1, v[2:3]
	v_dual_mov_b32 v31, v51 :: v_dual_mov_b32 v6, 0
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_fprintf_append_string_n@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_fprintf_append_string_n@rel32@hi+24
	s_add_co_i32 s2, s33, 0x70
	s_mov_b64 s[4:5], s[44:45]
	s_mov_b64 s[6:7], s[42:43]
	s_mov_b64 s[8:9], s[40:41]
	s_mov_b64 s[10:11], s[28:29]
	s_mov_b64 s[62:63], src_private_base
	s_mov_b32 s27, 0
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s62, s2
	s_wait_loadcnt_dscnt 0x0
	v_sub_nc_u32_e32 v0, v0, v1
	flat_store_b32 v[4:5], v0
	flat_load_b32 v4, v[4:5]
	flat_load_b64 v[0:1], v[52:53]
	flat_load_b64 v[2:3], v[2:3]
	s_wait_loadcnt_dscnt 0x202
	v_ashrrev_i32_e32 v5, 31, v4
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	v_dual_mov_b32 v2, s46 :: v_dual_mov_b32 v3, s47
	flat_store_b64 v[52:53], v[0:1]
	v_dual_mov_b32 v4, s62 :: v_dual_mov_b32 v5, s63
	flat_load_b64 v[0:1], v[2:3]
	v_dual_mov_b32 v2, s62 :: v_dual_mov_b32 v3, s63
	s_wait_loadcnt_dscnt 0x0
	flat_store_b64 v[4:5], v[0:1]
.LBB8_7:                                ; %while.cond39
                                        ; =>This Inner Loop Header: Depth=1
	v_dual_mov_b32 v5, v1 :: v_dual_mov_b32 v4, v0
	s_delay_alu instid0(VALU_DEP_1) | instskip(SKIP_1) | instid1(VALU_DEP_2)
	v_add_co_u32 v0, vcc_lo, v4, 1
	s_wait_alu depctr_va_vcc(0)
	v_add_co_ci_u32_e64 v1, null, 0, v5, vcc_lo
	flat_store_b64 v[2:3], v[0:1]
	flat_load_d16_u8 v4, v[4:5]
	s_wait_loadcnt_dscnt 0x0
	v_cmp_eq_u16_e32 vcc_lo, 0, v4.l
	s_or_b32 s27, vcc_lo, s27
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s27
	s_cbranch_execnz .LBB8_7
; %bb.8:                                ; %while.end43
	s_or_b32 exec_lo, exec_lo, s27
	v_dual_mov_b32 v2, s46 :: v_dual_mov_b32 v3, s47
	v_dual_mov_b32 v4, s58 :: v_dual_mov_b32 v5, s59
	v_dual_mov_b32 v31, v51 :: v_dual_mov_b32 v6, 1
	flat_load_b32 v1, v[2:3]
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_fprintf_append_string_n@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_fprintf_append_string_n@rel32@hi+24
	s_mov_b64 s[4:5], s[44:45]
	s_mov_b64 s[6:7], s[42:43]
	s_mov_b64 s[8:9], s[40:41]
	s_mov_b64 s[10:11], s[28:29]
	s_wait_loadcnt_dscnt 0x0
	v_sub_nc_u32_e32 v0, v0, v1
	flat_store_b32 v[4:5], v0
	flat_load_b32 v4, v[4:5]
	v_dual_mov_b32 v0, s56 :: v_dual_mov_b32 v1, s57
	flat_load_b64 v[0:1], v[0:1]
	flat_load_b64 v[2:3], v[2:3]
	s_wait_loadcnt_dscnt 0x202
	v_ashrrev_i32_e32 v5, 31, v4
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	s_trap 2
	scratch_load_b32 v40, off, s33          ; 4-byte Folded Reload
	v_readlane_b32 s31, v41, 1
	v_readlane_b32 s30, v41, 0
	s_mov_b32 s32, s33
	s_or_saveexec_b32 s0, -1
	scratch_load_b32 v41, off, s33 offset:120 ; 4-byte Folded Reload
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s0
	s_mov_b32 s33, s76
	s_wait_loadcnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	s_setpc_b64 s[30:31]
.Lfunc_end8:
	.size	__assert_fail, .Lfunc_end8-__assert_fail
                                        ; -- End function
	.set __assert_fail.num_vgpr, max(54, .L__ockl_fprintf_stderr_begin.num_vgpr, .L__ockl_fprintf_append_string_n.num_vgpr, .L__ockl_fprintf_append_args.num_vgpr)
	.set __assert_fail.num_agpr, max(0, .L__ockl_fprintf_stderr_begin.num_agpr, .L__ockl_fprintf_append_string_n.num_agpr, .L__ockl_fprintf_append_args.num_agpr)
	.set __assert_fail.numbered_sgpr, max(77, .L__ockl_fprintf_stderr_begin.numbered_sgpr, .L__ockl_fprintf_append_string_n.numbered_sgpr, .L__ockl_fprintf_append_args.numbered_sgpr)
	.set __assert_fail.num_named_barrier, max(0, .L__ockl_fprintf_stderr_begin.num_named_barrier, .L__ockl_fprintf_append_string_n.num_named_barrier, .L__ockl_fprintf_append_args.num_named_barrier)
	.set __assert_fail.private_seg_size, 128+max(.L__ockl_fprintf_stderr_begin.private_seg_size, .L__ockl_fprintf_append_string_n.private_seg_size, .L__ockl_fprintf_append_args.private_seg_size)
	.set __assert_fail.uses_vcc, or(1, .L__ockl_fprintf_stderr_begin.uses_vcc, .L__ockl_fprintf_append_string_n.uses_vcc, .L__ockl_fprintf_append_args.uses_vcc)
	.set __assert_fail.uses_flat_scratch, or(1, .L__ockl_fprintf_stderr_begin.uses_flat_scratch, .L__ockl_fprintf_append_string_n.uses_flat_scratch, .L__ockl_fprintf_append_args.uses_flat_scratch)
	.set __assert_fail.has_dyn_sized_stack, or(0, .L__ockl_fprintf_stderr_begin.has_dyn_sized_stack, .L__ockl_fprintf_append_string_n.has_dyn_sized_stack, .L__ockl_fprintf_append_args.has_dyn_sized_stack)
	.set __assert_fail.has_recursion, or(0, .L__ockl_fprintf_stderr_begin.has_recursion, .L__ockl_fprintf_append_string_n.has_recursion, .L__ockl_fprintf_append_args.has_recursion)
	.set __assert_fail.has_indirect_call, or(0, .L__ockl_fprintf_stderr_begin.has_indirect_call, .L__ockl_fprintf_append_string_n.has_indirect_call, .L__ockl_fprintf_append_args.has_indirect_call)
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 2176
; TotalNumSgprs: 81
; NumVgprs: 54
; ScratchSize: 168
; MemoryBound: 0
	.text
	.hidden	__assertfail                    ; -- Begin function __assertfail
	.weak	__assertfail
	.p2align	7
	.type	__assertfail,@function
__assertfail:                           ; @__assertfail
; %bb.0:                                ; %entry
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_trap 2
	s_setpc_b64 s[30:31]
.Lfunc_end9:
	.size	__assertfail, .Lfunc_end9-__assertfail
                                        ; -- End function
	.set __assertfail.num_vgpr, 0
	.set __assertfail.num_agpr, 0
	.set __assertfail.numbered_sgpr, 32
	.set __assertfail.num_named_barrier, 0
	.set __assertfail.private_seg_size, 0
	.set __assertfail.uses_vcc, 0
	.set __assertfail.uses_flat_scratch, 0
	.set __assertfail.has_dyn_sized_stack, 0
	.set __assertfail.has_recursion, 0
	.set __assertfail.has_indirect_call, 0
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 28
; TotalNumSgprs: 32
; NumVgprs: 0
; ScratchSize: 0
; MemoryBound: 0
	.text
	.p2align	7                               ; -- Begin function __ockl_get_local_id
	.type	__ockl_get_local_id,@function
__ockl_get_local_id:                    ; @__ockl_get_local_id
; %bb.0:
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	v_mov_b32_e32 v1, v0
	s_mov_b32 s0, exec_lo
                                        ; implicit-def: $vgpr0
	s_delay_alu instid0(VALU_DEP_1)
	v_cmpx_lt_i32_e32 0, v1
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s0, exec_lo, s0
	s_cbranch_execz .LBB10_8
; %bb.1:                                ; %NodeBlock
	s_mov_b32 s1, exec_lo
                                        ; implicit-def: $vgpr0
	v_cmpx_lt_i32_e32 1, v1
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s1, exec_lo, s1
	s_cbranch_execz .LBB10_5
; %bb.2:                                ; %LeafBlock1
	v_mov_b32_e32 v0, 0
	s_mov_b32 s2, exec_lo
	v_cmpx_eq_u32_e32 2, v1
; %bb.3:
	v_bfe_u32 v0, v31, 20, 10
; %bb.4:                                ; %Flow
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s2
                                        ; implicit-def: $vgpr31
.LBB10_5:                               ; %Flow5
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_saveexec_b32 s1, s1
; %bb.6:
	v_bfe_u32 v0, v31, 10, 10
; %bb.7:                                ; %Flow6
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s1
                                        ; implicit-def: $vgpr1
                                        ; implicit-def: $vgpr31
.LBB10_8:                               ; %Flow8
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_saveexec_b32 s0, s0
	s_cbranch_execz .LBB10_12
; %bb.9:                                ; %LeafBlock
	v_mov_b32_e32 v0, 0
	s_mov_b32 s1, exec_lo
	v_cmpx_eq_u32_e32 0, v1
; %bb.10:
	v_and_b32_e32 v0, 0x3ff, v31
; %bb.11:                               ; %Flow7
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s1
.LBB10_12:
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s0
	v_mov_b32_e32 v1, 0
	s_setpc_b64 s[30:31]
.Lfunc_end10:
	.size	__ockl_get_local_id, .Lfunc_end10-__ockl_get_local_id
                                        ; -- End function
	.set .L__ockl_get_local_id.num_vgpr, 32
	.set .L__ockl_get_local_id.num_agpr, 0
	.set .L__ockl_get_local_id.numbered_sgpr, 32
	.set .L__ockl_get_local_id.num_named_barrier, 0
	.set .L__ockl_get_local_id.private_seg_size, 0
	.set .L__ockl_get_local_id.uses_vcc, 0
	.set .L__ockl_get_local_id.uses_flat_scratch, 0
	.set .L__ockl_get_local_id.has_dyn_sized_stack, 0
	.set .L__ockl_get_local_id.has_recursion, 0
	.set .L__ockl_get_local_id.has_indirect_call, 0
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 176
; TotalNumSgprs: 32
; NumVgprs: 32
; ScratchSize: 0
; MemoryBound: 0
	.text
	.p2align	7                               ; -- Begin function _ZL20__work_group_barrierj
	.type	_ZL20__work_group_barrierj,@function
_ZL20__work_group_barrierj:             ; @_ZL20__work_group_barrierj
; %bb.0:                                ; %entry
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_mov_b64 s[0:1], src_private_base
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v1, s32 :: v_dual_mov_b32 v2, s1
	s_mov_b32 s0, exec_lo
	flat_store_b32 v[1:2], v0
	v_cmpx_ne_u32_e32 3, v0
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s0, exec_lo, s0
	s_cbranch_execnz .LBB11_3
; %bb.1:                                ; %Flow4
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_saveexec_b32 s0, s0
	s_cbranch_execnz .LBB11_12
.LBB11_2:                               ; %if.end8
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s0
	s_wait_dscnt 0x0
	s_setpc_b64 s[30:31]
.LBB11_3:                               ; %if.else
	v_and_b32_e32 v1, 2, v0
	s_mov_b32 s1, exec_lo
	s_delay_alu instid0(VALU_DEP_1)
	v_cmpx_eq_u32_e32 0, v1
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s1, exec_lo, s1
	s_cbranch_execz .LBB11_9
; %bb.4:                                ; %if.else2
	v_and_b32_e32 v0, 1, v0
	s_mov_b32 s2, exec_lo
	s_delay_alu instid0(VALU_DEP_1)
	v_cmpx_eq_u32_e32 0, v0
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s2, exec_lo, s2
	s_cbranch_execz .LBB11_6
; %bb.5:                                ; %if.else6
	s_barrier_signal -1
	s_barrier_wait -1
.LBB11_6:                               ; %Flow
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_saveexec_b32 s2, s2
	s_cbranch_execz .LBB11_8
; %bb.7:                                ; %if.then5
	s_wait_dscnt 0x0
	s_barrier_signal -1
	s_barrier_wait -1
.LBB11_8:                               ; %Flow1
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s2
.LBB11_9:                               ; %Flow2
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_saveexec_b32 s1, s1
	s_cbranch_execz .LBB11_11
; %bb.10:                               ; %if.then1
	s_wait_storecnt 0x0
	s_barrier_signal -1
	s_barrier_wait -1
	global_inv scope:SCOPE_SE
.LBB11_11:                              ; %Flow3
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s1
	s_and_not1_saveexec_b32 s0, s0
	s_cbranch_execz .LBB11_2
.LBB11_12:                              ; %if.then
	s_wait_storecnt 0x0
	s_wait_loadcnt_dscnt 0x0
	s_barrier_signal -1
	s_barrier_wait -1
	global_inv scope:SCOPE_SE
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s0
	s_setpc_b64 s[30:31]
.Lfunc_end11:
	.size	_ZL20__work_group_barrierj, .Lfunc_end11-_ZL20__work_group_barrierj
                                        ; -- End function
	.set .L_ZL20__work_group_barrierj.num_vgpr, 3
	.set .L_ZL20__work_group_barrierj.num_agpr, 0
	.set .L_ZL20__work_group_barrierj.numbered_sgpr, 33
	.set .L_ZL20__work_group_barrierj.num_named_barrier, 0
	.set .L_ZL20__work_group_barrierj.private_seg_size, 8
	.set .L_ZL20__work_group_barrierj.uses_vcc, 0
	.set .L_ZL20__work_group_barrierj.uses_flat_scratch, 0
	.set .L_ZL20__work_group_barrierj.has_dyn_sized_stack, 0
	.set .L_ZL20__work_group_barrierj.has_recursion, 0
	.set .L_ZL20__work_group_barrierj.has_indirect_call, 0
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 284
; TotalNumSgprs: 33
; NumVgprs: 3
; ScratchSize: 8
; MemoryBound: 0
	.text
	.p2align	7                               ; -- Begin function _ZL9__barrieri
	.type	_ZL9__barrieri,@function
_ZL9__barrieri:                         ; @_ZL9__barrieri
; %bb.0:                                ; %entry
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_mov_b32 s3, s33
	s_mov_b32 s33, s32
	s_xor_saveexec_b32 s0, -1
	scratch_store_b32 off, v3, s33 offset:4 ; 4-byte Folded Spill
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s0
	s_mov_b64 s[0:1], src_private_base
	v_writelane_b32 v3, s30, 0
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v1, s33 :: v_dual_mov_b32 v2, s1
	s_add_co_i32 s32, s32, 16
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, _ZL20__work_group_barrierj@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, _ZL20__work_group_barrierj@rel32@hi+24
	v_writelane_b32 v3, s31, 1
	flat_store_b32 v[1:2], v0
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	v_readlane_b32 s31, v3, 1
	v_readlane_b32 s30, v3, 0
	s_mov_b32 s32, s33
	s_xor_saveexec_b32 s0, -1
	scratch_load_b32 v3, off, s33 offset:4  ; 4-byte Folded Reload
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s0
	s_mov_b32 s33, s3
	s_wait_loadcnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	s_setpc_b64 s[30:31]
.Lfunc_end12:
	.size	_ZL9__barrieri, .Lfunc_end12-_ZL9__barrieri
                                        ; -- End function
	.set .L_ZL9__barrieri.num_vgpr, max(4, .L_ZL20__work_group_barrierj.num_vgpr)
	.set .L_ZL9__barrieri.num_agpr, max(0, .L_ZL20__work_group_barrierj.num_agpr)
	.set .L_ZL9__barrieri.numbered_sgpr, max(34, .L_ZL20__work_group_barrierj.numbered_sgpr)
	.set .L_ZL9__barrieri.num_named_barrier, max(0, .L_ZL20__work_group_barrierj.num_named_barrier)
	.set .L_ZL9__barrieri.private_seg_size, 16+max(.L_ZL20__work_group_barrierj.private_seg_size)
	.set .L_ZL9__barrieri.uses_vcc, or(0, .L_ZL20__work_group_barrierj.uses_vcc)
	.set .L_ZL9__barrieri.uses_flat_scratch, or(0, .L_ZL20__work_group_barrierj.uses_flat_scratch)
	.set .L_ZL9__barrieri.has_dyn_sized_stack, or(0, .L_ZL20__work_group_barrierj.has_dyn_sized_stack)
	.set .L_ZL9__barrieri.has_recursion, or(1, .L_ZL20__work_group_barrierj.has_recursion)
	.set .L_ZL9__barrieri.has_indirect_call, or(0, .L_ZL20__work_group_barrierj.has_indirect_call)
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 200
; TotalNumSgprs: 34
; NumVgprs: 4
; ScratchSize: 24
; MemoryBound: 0
	.section	.text._Z13__syncthreadsv,"axG",@progbits,_Z13__syncthreadsv,comdat
	.hidden	_Z13__syncthreadsv              ; -- Begin function _Z13__syncthreadsv
	.weak	_Z13__syncthreadsv
	.p2align	7
	.type	_Z13__syncthreadsv,@function
_Z13__syncthreadsv:                     ; @_Z13__syncthreadsv
; %bb.0:                                ; %entry
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_mov_b32 s16, s33
	s_mov_b32 s33, s32
	s_xor_saveexec_b32 s0, -1
	scratch_store_b32 off, v4, s33          ; 4-byte Folded Spill
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s0
	v_writelane_b32 v4, s30, 0
	v_mov_b32_e32 v0, 3
	s_add_co_i32 s32, s32, 16
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, _ZL9__barrieri@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, _ZL9__barrieri@rel32@hi+24
	v_writelane_b32 v4, s31, 1
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	s_delay_alu instid0(VALU_DEP_1)
	v_readlane_b32 s31, v4, 1
	v_readlane_b32 s30, v4, 0
	s_mov_b32 s32, s33
	s_xor_saveexec_b32 s0, -1
	scratch_load_b32 v4, off, s33           ; 4-byte Folded Reload
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s0
	s_mov_b32 s33, s16
	s_wait_loadcnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	s_setpc_b64 s[30:31]
.Lfunc_end13:
	.size	_Z13__syncthreadsv, .Lfunc_end13-_Z13__syncthreadsv
                                        ; -- End function
	.set _Z13__syncthreadsv.num_vgpr, max(5, .L_ZL9__barrieri.num_vgpr)
	.set _Z13__syncthreadsv.num_agpr, max(0, .L_ZL9__barrieri.num_agpr)
	.set _Z13__syncthreadsv.numbered_sgpr, max(34, .L_ZL9__barrieri.numbered_sgpr)
	.set _Z13__syncthreadsv.num_named_barrier, max(0, .L_ZL9__barrieri.num_named_barrier)
	.set _Z13__syncthreadsv.private_seg_size, 16+max(.L_ZL9__barrieri.private_seg_size)
	.set _Z13__syncthreadsv.uses_vcc, or(0, .L_ZL9__barrieri.uses_vcc)
	.set _Z13__syncthreadsv.uses_flat_scratch, or(0, .L_ZL9__barrieri.uses_flat_scratch)
	.set _Z13__syncthreadsv.has_dyn_sized_stack, or(0, .L_ZL9__barrieri.has_dyn_sized_stack)
	.set _Z13__syncthreadsv.has_recursion, or(1, .L_ZL9__barrieri.has_recursion)
	.set _Z13__syncthreadsv.has_indirect_call, or(0, .L_ZL9__barrieri.has_indirect_call)
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 180
; TotalNumSgprs: 34
; NumVgprs: 5
; ScratchSize: 40
; MemoryBound: 0
	.text
	.hidden	_Z8crc_initv                    ; -- Begin function _Z8crc_initv
	.globl	_Z8crc_initv
	.p2align	7
	.type	_Z8crc_initv,@function
_Z8crc_initv:                           ; @_Z8crc_initv
; %bb.0:                                ; %entry
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_mov_b32 s0, s33
	s_mov_b32 s33, s32
	s_or_saveexec_b32 s1, -1
	scratch_store_b32 off, v40, s33 offset:16 ; 4-byte Folded Spill
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s1
	v_writelane_b32 v40, s0, 2
	v_mov_b32_e32 v0, 0
	s_add_co_i32 s32, s32, 32
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_get_local_id@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_get_local_id@rel32@hi+24
	v_dual_mov_b32 v2, v31 :: v_dual_mov_b32 v3, 0
	v_writelane_b32 v40, s30, 0
	v_writelane_b32 v40, s31, 1
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	s_mov_b32 s18, exec_lo
	v_cmpx_eq_u32_e32 0, v0
	s_cbranch_execz .LBB14_14
; %bb.1:                                ; %if.then
	s_mov_b64 s[16:17], src_private_base
	s_mov_b32 s16, s33
	s_add_co_i32 s1, s33, 4
	s_add_co_i32 s3, s33, 8
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v5, s16 :: v_dual_mov_b32 v6, s17
	v_dual_mov_b32 v0, s16 :: v_dual_mov_b32 v1, s17
	v_mov_b32_e32 v4, 7
	s_add_co_i32 s19, s33, 12
	s_mov_b32 s0, s1
	s_mov_b32 s1, s17
	s_mov_b32 s2, s3
	s_mov_b32 s3, s17
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s16, s19
	s_mov_b32 s19, 0
	flat_store_b32 v[5:6], v3
                                        ; implicit-def: $sgpr20
	s_branch .LBB14_4
.LBB14_2:                               ; %for.cond.cleanup4
                                        ;   in Loop: Header=BB14_4 Depth=1
	s_or_b32 exec_lo, exec_lo, s22
	v_dual_mov_b32 v6, s1 :: v_dual_mov_b32 v5, s0
	s_mov_b64 s[22:23], src_shared_base
	s_and_not1_b32 s20, s20, exec_lo
	flat_store_b32 v[5:6], v4
	flat_load_b32 v5, v[0:1]
	v_dual_mov_b32 v7, s3 :: v_dual_mov_b32 v6, s2
	flat_load_b32 v7, v[6:7]
	s_wait_loadcnt_dscnt 0x101
	v_ashrrev_i32_e32 v6, 31, v5
	s_delay_alu instid0(VALU_DEP_1) | instskip(NEXT) | instid1(VALU_DEP_1)
	v_lshlrev_b64_e32 v[5:6], 2, v[5:6]
	v_add_co_u32 v5, vcc_lo, 0, v5
	s_wait_alu depctr_sa_sdst(0) depctr_va_vcc(0)
	s_delay_alu instid0(VALU_DEP_2)
	v_add_co_ci_u32_e64 v6, null, s23, v6, vcc_lo
	s_wait_loadcnt_dscnt 0x0
	flat_store_b32 v[5:6], v7
	flat_load_b32 v5, v[0:1]
	s_wait_loadcnt_dscnt 0x0
	v_add_nc_u32_e32 v5, 1, v5
	flat_store_b32 v[0:1], v5
.LBB14_3:                               ; %Flow5
                                        ;   in Loop: Header=BB14_4 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s21
	s_delay_alu instid0(SALU_CYCLE_1)
	s_and_b32 s21, exec_lo, s20
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 s19, s21, s19
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s19
	s_cbranch_execz .LBB14_13
.LBB14_4:                               ; %for.cond
                                        ; =>This Loop Header: Depth=1
                                        ;     Child Loop BB14_8 Depth 2
	flat_load_b32 v5, v[0:1]
	s_or_b32 s20, s20, exec_lo
	s_mov_b32 s21, exec_lo
	s_wait_loadcnt_dscnt 0x0
	v_cmpx_gt_i32_e32 0x100, v5
	s_cbranch_execz .LBB14_3
; %bb.5:                                ; %for.body
                                        ;   in Loop: Header=BB14_4 Depth=1
	flat_load_b32 v9, v[0:1]
	v_dual_mov_b32 v6, s3 :: v_dual_mov_b32 v5, s2
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v7, s16 :: v_dual_mov_b32 v8, s17
	s_mov_b32 s22, 0
                                        ; implicit-def: $sgpr23
	s_wait_loadcnt_dscnt 0x0
	flat_store_b32 v[5:6], v9
	flat_store_b32 v[7:8], v3
	s_branch .LBB14_8
.LBB14_6:                               ; %if.end
                                        ;   in Loop: Header=BB14_8 Depth=2
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s25
	v_dual_mov_b32 v5, s16 :: v_dual_mov_b32 v6, s17
	s_and_not1_b32 s23, s23, exec_lo
	flat_load_b32 v7, v[5:6]
	s_wait_loadcnt_dscnt 0x0
	v_add_nc_u32_e32 v7, 1, v7
	flat_store_b32 v[5:6], v7
.LBB14_7:                               ; %Flow4
                                        ;   in Loop: Header=BB14_8 Depth=2
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s24
	s_delay_alu instid0(SALU_CYCLE_1)
	s_and_b32 s24, exec_lo, s23
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 s22, s24, s22
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s22
	s_cbranch_execz .LBB14_2
.LBB14_8:                               ; %for.cond2
                                        ;   Parent Loop BB14_4 Depth=1
                                        ; =>  This Inner Loop Header: Depth=2
	v_dual_mov_b32 v5, s16 :: v_dual_mov_b32 v6, s17
	s_or_b32 s23, s23, exec_lo
	s_mov_b32 s24, exec_lo
	flat_load_b32 v5, v[5:6]
	s_wait_loadcnt_dscnt 0x0
	v_cmpx_gt_i32_e32 8, v5
	s_cbranch_execz .LBB14_7
; %bb.9:                                ; %for.body5
                                        ;   in Loop: Header=BB14_8 Depth=2
	v_dual_mov_b32 v6, s3 :: v_dual_mov_b32 v5, s2
	s_mov_b32 s25, exec_lo
	flat_load_b32 v5, v[5:6]
	s_wait_loadcnt_dscnt 0x0
	v_and_b32_e32 v6, 1, v5
	v_lshrrev_b32_e32 v5, 1, v5
	s_delay_alu instid0(VALU_DEP_2)
	v_cmpx_eq_u32_e32 0, v6
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s25, exec_lo, s25
	s_cbranch_execz .LBB14_11
; %bb.10:                               ; %if.else
                                        ;   in Loop: Header=BB14_8 Depth=2
	v_dual_mov_b32 v7, s3 :: v_dual_mov_b32 v6, s2
	flat_store_b32 v[6:7], v5
                                        ; implicit-def: $vgpr5
.LBB14_11:                              ; %Flow
                                        ;   in Loop: Header=BB14_8 Depth=2
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_saveexec_b32 s25, s25
	s_cbranch_execz .LBB14_6
; %bb.12:                               ; %if.then6
                                        ;   in Loop: Header=BB14_8 Depth=2
	v_xor_b32_e32 v7, 0x8408, v5
	v_dual_mov_b32 v6, s3 :: v_dual_mov_b32 v5, s2
	flat_store_b32 v[5:6], v7
	s_branch .LBB14_6
.LBB14_13:                              ; %for.cond.cleanup
	s_or_b32 exec_lo, exec_lo, s19
	v_dual_mov_b32 v3, 4 :: v_dual_mov_b32 v0, s0
	v_mov_b32_e32 v1, s1
	flat_store_b32 v[0:1], v3
.LBB14_14:                              ; %Flow6
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s18
	v_mov_b32_e32 v31, v2
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, _Z13__syncthreadsv@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, _Z13__syncthreadsv@rel32@hi+24
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	v_readlane_b32 s31, v40, 1
	v_readlane_b32 s30, v40, 0
	s_mov_b32 s32, s33
	v_readlane_b32 s0, v40, 2
	s_or_saveexec_b32 s1, -1
	scratch_load_b32 v40, off, s33 offset:16 ; 4-byte Folded Reload
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s1
	s_mov_b32 s33, s0
	s_wait_loadcnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	s_setpc_b64 s[30:31]
.Lfunc_end14:
	.size	_Z8crc_initv, .Lfunc_end14-_Z8crc_initv
                                        ; -- End function
	.set _Z8crc_initv.num_vgpr, max(41, .L__ockl_get_local_id.num_vgpr, _Z13__syncthreadsv.num_vgpr)
	.set _Z8crc_initv.num_agpr, max(0, .L__ockl_get_local_id.num_agpr, _Z13__syncthreadsv.num_agpr)
	.set _Z8crc_initv.numbered_sgpr, max(34, .L__ockl_get_local_id.numbered_sgpr, _Z13__syncthreadsv.numbered_sgpr)
	.set _Z8crc_initv.num_named_barrier, max(0, .L__ockl_get_local_id.num_named_barrier, _Z13__syncthreadsv.num_named_barrier)
	.set _Z8crc_initv.private_seg_size, 32+max(.L__ockl_get_local_id.private_seg_size, _Z13__syncthreadsv.private_seg_size)
	.set _Z8crc_initv.uses_vcc, or(1, .L__ockl_get_local_id.uses_vcc, _Z13__syncthreadsv.uses_vcc)
	.set _Z8crc_initv.uses_flat_scratch, or(0, .L__ockl_get_local_id.uses_flat_scratch, _Z13__syncthreadsv.uses_flat_scratch)
	.set _Z8crc_initv.has_dyn_sized_stack, or(0, .L__ockl_get_local_id.has_dyn_sized_stack, _Z13__syncthreadsv.has_dyn_sized_stack)
	.set _Z8crc_initv.has_recursion, or(1, .L__ockl_get_local_id.has_recursion, _Z13__syncthreadsv.has_recursion)
	.set _Z8crc_initv.has_indirect_call, or(0, .L__ockl_get_local_id.has_indirect_call, _Z13__syncthreadsv.has_indirect_call)
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 920
; TotalNumSgprs: 36
; NumVgprs: 41
; ScratchSize: 72
; MemoryBound: 0
	.text
	.hidden	_Z9crc_tablejj                  ; -- Begin function _Z9crc_tablejj
	.globl	_Z9crc_tablejj
	.p2align	7
	.type	_Z9crc_tablejj,@function
_Z9crc_tablejj:                         ; @_Z9crc_tablejj
; %bb.0:                                ; %entry
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_mov_b32 s0, s33
	s_mov_b32 s33, s32
	s_or_saveexec_b32 s1, -1
	scratch_store_b32 off, v41, s33 offset:20 ; 4-byte Folded Spill
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s1
	v_writelane_b32 v41, s0, 8
	s_add_co_i32 s32, s32, 32
	s_add_co_i32 s2, s33, 4
	s_mov_b64 s[0:1], src_private_base
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s0, s2
	v_writelane_b32 v41, s30, 0
	s_add_co_i32 s2, s33, 8
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v3, s1 :: v_dual_mov_b32 v2, s0
	s_add_co_i32 s0, s33, 12
	v_writelane_b32 v41, s31, 1
	scratch_store_b32 off, v40, s33         ; 4-byte Folded Spill
	v_writelane_b32 v41, s34, 2
	s_mov_b32 s34, s2
	v_writelane_b32 v41, s35, 3
	s_mov_b32 s35, s1
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v4, s34 :: v_dual_mov_b32 v5, s35
	flat_store_b32 v[2:3], v0
	flat_store_b32 v[4:5], v1
	flat_load_b32 v2, v[2:3]
	v_writelane_b32 v41, s36, 4
	s_mov_b32 s36, s0
	s_add_co_i32 s0, s33, 16
	s_getpc_b64 s[2:3]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s3, s3
	s_add_co_u32 s2, s2, _Z8crc_initv@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s3, s3, _Z8crc_initv@rel32@hi+24
	v_writelane_b32 v41, s37, 5
	s_mov_b32 s37, s1
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v0, s36 :: v_dual_mov_b32 v1, s37
	v_writelane_b32 v41, s38, 6
	s_mov_b32 s38, s0
	v_writelane_b32 v41, s39, 7
	s_mov_b32 s39, s1
	s_wait_loadcnt_dscnt 0x0
	flat_store_b32 v[0:1], v2
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[2:3]
	v_mov_b32_e32 v2, s38
	v_mov_b32_e32 v0, s38
	v_dual_mov_b32 v4, 0 :: v_dual_mov_b32 v3, s39
	v_mov_b32_e32 v1, s39
	s_mov_b32 s0, 0
	s_mov_b64 s[4:5], src_shared_base
                                        ; implicit-def: $sgpr1
	flat_store_b32 v[2:3], v4
	s_branch .LBB15_2
.LBB15_1:                               ; %Flow
                                        ;   in Loop: Header=BB15_2 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s2
	s_delay_alu instid0(SALU_CYCLE_1)
	s_and_b32 s2, exec_lo, s1
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 s0, s2, s0
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s0
	s_cbranch_execz .LBB15_4
.LBB15_2:                               ; %for.cond
                                        ; =>This Inner Loop Header: Depth=1
	flat_load_b32 v2, v[0:1]
	s_or_b32 s1, s1, exec_lo
	s_mov_b32 s2, exec_lo
	s_wait_loadcnt_dscnt 0x0
	v_cmpx_gt_i32_e32 4, v2
	s_cbranch_execz .LBB15_1
; %bb.3:                                ; %for.body
                                        ;   in Loop: Header=BB15_2 Depth=1
	v_dual_mov_b32 v2, s36 :: v_dual_mov_b32 v3, s37
	v_dual_mov_b32 v4, s34 :: v_dual_mov_b32 v5, s35
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 s1, s1, exec_lo
	flat_load_b32 v8, v[2:3]
	flat_load_b32 v6, v[4:5]
	v_mov_b32_e32 v7, s5
	s_wait_loadcnt_dscnt 0x0
	v_xor_b32_e32 v6, v8, v6
	s_delay_alu instid0(VALU_DEP_1) | instskip(NEXT) | instid1(VALU_DEP_1)
	v_and_b32_e32 v6, 0xff, v6
	v_lshlrev_b32_e32 v6, 2, v6
	flat_load_b32 v6, v[6:7]
	v_lshrrev_b32_e32 v7, 8, v8
	s_wait_loadcnt_dscnt 0x0
	s_delay_alu instid0(VALU_DEP_1)
	v_xor_b32_e32 v6, v7, v6
	flat_store_b32 v[2:3], v6
	flat_load_b32 v2, v[4:5]
	s_wait_loadcnt_dscnt 0x0
	v_lshrrev_b32_e32 v2, 8, v2
	flat_store_b32 v[4:5], v2
	flat_load_b32 v2, v[0:1]
	s_wait_loadcnt_dscnt 0x0
	v_add_nc_u32_e32 v2, 1, v2
	flat_store_b32 v[0:1], v2
	s_branch .LBB15_1
.LBB15_4:                               ; %for.cond.cleanup
	s_or_b32 exec_lo, exec_lo, s0
	v_dual_mov_b32 v0, s36 :: v_dual_mov_b32 v1, s37
	scratch_load_b32 v40, off, s33          ; 4-byte Folded Reload
	v_readlane_b32 s39, v41, 7
	v_readlane_b32 s38, v41, 6
	v_readlane_b32 s37, v41, 5
	flat_load_b32 v0, v[0:1]
	v_readlane_b32 s36, v41, 4
	v_readlane_b32 s35, v41, 3
	v_readlane_b32 s34, v41, 2
	v_readlane_b32 s31, v41, 1
	v_readlane_b32 s30, v41, 0
	s_mov_b32 s32, s33
	v_readlane_b32 s0, v41, 8
	s_or_saveexec_b32 s1, -1
	scratch_load_b32 v41, off, s33 offset:20 ; 4-byte Folded Reload
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s1
	s_mov_b32 s33, s0
	s_wait_loadcnt_dscnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	s_setpc_b64 s[30:31]
.Lfunc_end15:
	.size	_Z9crc_tablejj, .Lfunc_end15-_Z9crc_tablejj
                                        ; -- End function
	.set _Z9crc_tablejj.num_vgpr, max(42, _Z8crc_initv.num_vgpr)
	.set _Z9crc_tablejj.num_agpr, max(0, _Z8crc_initv.num_agpr)
	.set _Z9crc_tablejj.numbered_sgpr, max(40, _Z8crc_initv.numbered_sgpr)
	.set _Z9crc_tablejj.num_named_barrier, max(0, _Z8crc_initv.num_named_barrier)
	.set _Z9crc_tablejj.private_seg_size, 32+max(_Z8crc_initv.private_seg_size)
	.set _Z9crc_tablejj.uses_vcc, or(1, _Z8crc_initv.uses_vcc)
	.set _Z9crc_tablejj.uses_flat_scratch, or(0, _Z8crc_initv.uses_flat_scratch)
	.set _Z9crc_tablejj.has_dyn_sized_stack, or(0, _Z8crc_initv.has_dyn_sized_stack)
	.set _Z9crc_tablejj.has_recursion, or(1, _Z8crc_initv.has_recursion)
	.set _Z9crc_tablejj.has_indirect_call, or(0, _Z8crc_initv.has_indirect_call)
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 768
; TotalNumSgprs: 42
; NumVgprs: 42
; ScratchSize: 104
; MemoryBound: 0
	.text
	.hidden	_Z8crc_loopjj                   ; -- Begin function _Z8crc_loopjj
	.globl	_Z8crc_loopjj
	.p2align	7
	.type	_Z8crc_loopjj,@function
_Z8crc_loopjj:                          ; @_Z8crc_loopjj
; %bb.0:                                ; %entry
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_mov_b32 s0, s33
	s_mov_b32 s33, s32
	s_or_saveexec_b32 s1, -1
	scratch_store_b32 off, v44, s33 offset:32 ; 4-byte Folded Spill
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s1
	v_writelane_b32 v44, s0, 21
	s_add_co_i32 s32, s32, 48
	s_add_co_i32 s0, s33, 16
	s_clause 0x3                            ; 16-byte Folded Spill
	scratch_store_b32 off, v40, s33 offset:12
	scratch_store_b32 off, v41, s33 offset:8
	scratch_store_b32 off, v42, s33 offset:4
	scratch_store_b32 off, v43, s33
	v_mov_b32_e32 v43, 0
	v_writelane_b32 v44, s30, 0
	v_writelane_b32 v44, s31, 1
	v_writelane_b32 v44, s34, 2
	v_writelane_b32 v44, s35, 3
	s_mov_b64 s[34:35], s[10:11]
	v_writelane_b32 v44, s36, 4
	v_writelane_b32 v44, s37, 5
	s_mov_b64 s[36:37], s[8:9]
	v_writelane_b32 v44, s38, 6
	v_writelane_b32 v44, s39, 7
	s_mov_b64 s[38:39], s[6:7]
	v_writelane_b32 v44, s48, 8
	v_writelane_b32 v44, s49, 9
	s_mov_b64 s[48:49], s[4:5]
	v_writelane_b32 v44, s50, 10
	s_mov_b32 s50, s15
	v_writelane_b32 v44, s51, 11
	s_mov_b32 s51, s14
	v_writelane_b32 v44, s52, 12
	s_mov_b32 s52, s13
	v_writelane_b32 v44, s53, 13
	s_mov_b32 s53, s12
	v_writelane_b32 v44, s54, 14
	v_writelane_b32 v44, s55, 15
	s_mov_b64 s[54:55], src_private_base
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s54, s0
	s_add_co_i32 s0, s33, 20
	v_mov_b32_e32 v40, v31
	v_writelane_b32 v44, s64, 16
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s64, s0
	v_mov_b32_e32 v6, s54
	s_add_co_i32 s0, s33, 24
	s_add_co_i32 s1, s33, 28
	v_writelane_b32 v44, s65, 17
	s_mov_b32 s65, s55
	v_dual_mov_b32 v2, s54 :: v_dual_mov_b32 v3, s55
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v4, s64 :: v_dual_mov_b32 v7, s55
	v_mov_b32_e32 v5, s65
	flat_store_b32 v[2:3], v0
	flat_store_b32 v[4:5], v1
	flat_load_b32 v4, v[6:7]
	v_writelane_b32 v44, s66, 18
	s_mov_b32 s66, s0
	s_mov_b32 s0, s1
	s_mov_b32 s1, s55
	s_mov_b32 s54, 0
	v_writelane_b32 v44, s67, 19
	s_mov_b32 s67, s55
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v0, s66 :: v_dual_mov_b32 v1, s67
	v_dual_mov_b32 v42, s1 :: v_dual_mov_b32 v41, s0
	v_dual_mov_b32 v3, s1 :: v_dual_mov_b32 v2, s0
	v_writelane_b32 v44, s68, 20
                                        ; implicit-def: $sgpr68
	s_wait_loadcnt_dscnt 0x0
	flat_store_b32 v[0:1], v4
	flat_store_b32 v[2:3], v43
	s_branch .LBB16_3
.LBB16_1:                               ; %if.end
                                        ;   in Loop: Header=BB16_3 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s1
	v_dual_mov_b32 v0, s64 :: v_dual_mov_b32 v1, s65
	s_and_not1_b32 s68, s68, exec_lo
	flat_load_b32 v2, v[0:1]
	s_wait_loadcnt_dscnt 0x0
	v_lshrrev_b32_e32 v2, 1, v2
	flat_store_b32 v[0:1], v2
	flat_load_b32 v0, v[41:42]
	s_wait_loadcnt_dscnt 0x0
	v_add_nc_u32_e32 v0, 1, v0
	flat_store_b32 v[41:42], v0
.LBB16_2:                               ; %Flow1
                                        ;   in Loop: Header=BB16_3 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s0
	s_delay_alu instid0(SALU_CYCLE_1)
	s_and_b32 s0, exec_lo, s68
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 s54, s0, s54
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_b32 exec_lo, exec_lo, s54
	s_cbranch_execz .LBB16_8
.LBB16_3:                               ; %for.cond
                                        ; =>This Inner Loop Header: Depth=1
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, G@gotpcrel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, G@gotpcrel32@hi+24
	v_dual_mov_b32 v31, v40 :: v_dual_mov_b32 v6, s55
	s_load_b64 s[0:1], s[0:1], 0x0
	v_mov_b32_e32 v1, 0
	v_mov_b32_e32 v3, 0
	s_mov_b64 s[4:5], s[48:49]
	s_mov_b64 s[6:7], s[38:39]
	s_mov_b64 s[8:9], s[36:37]
	s_mov_b64 s[10:11], s[34:35]
	s_mov_b32 s12, s53
	s_mov_b32 s13, s52
	s_mov_b32 s14, s51
	s_mov_b32 s15, s50
	s_wait_kmcnt 0x0
	global_load_b32 v4, v43, s[0:1]
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __assert_fail@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __assert_fail@rel32@hi+24
	s_add_co_i32 s2, s33, 16
	s_wait_alu depctr_sa_sdst(0)
	v_mov_b32_e32 v5, s2
	s_swappc_b64 s[30:31], s[0:1]
	flat_load_b32 v0, v[41:42]
	s_or_b32 s68, s68, exec_lo
	s_mov_b32 s0, exec_lo
	s_wait_loadcnt_dscnt 0x0
	v_cmpx_gt_i32_e32 4, v0
	s_cbranch_execz .LBB16_2
; %bb.4:                                ; %for.body
                                        ;   in Loop: Header=BB16_3 Depth=1
	v_dual_mov_b32 v0, s66 :: v_dual_mov_b32 v1, s67
	v_dual_mov_b32 v2, s64 :: v_dual_mov_b32 v3, s65
	s_mov_b32 s1, exec_lo
	flat_load_b32 v0, v[0:1]
	flat_load_b32 v1, v[2:3]
	s_wait_loadcnt_dscnt 0x0
	v_xor_b32_e32 v1, v0, v1
	v_lshrrev_b32_e32 v0, 1, v0
	s_delay_alu instid0(VALU_DEP_2) | instskip(NEXT) | instid1(VALU_DEP_1)
	v_and_b32_e32 v1, 1, v1
	v_cmpx_eq_u32_e32 0, v1
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s1, exec_lo, s1
	s_cbranch_execz .LBB16_6
; %bb.5:                                ; %if.else
                                        ;   in Loop: Header=BB16_3 Depth=1
	v_dual_mov_b32 v1, s66 :: v_dual_mov_b32 v2, s67
	flat_store_b32 v[1:2], v0
                                        ; implicit-def: $vgpr0
.LBB16_6:                               ; %Flow
                                        ;   in Loop: Header=BB16_3 Depth=1
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_saveexec_b32 s1, s1
	s_cbranch_execz .LBB16_1
; %bb.7:                                ; %if.then
                                        ;   in Loop: Header=BB16_3 Depth=1
	v_xor_b32_e32 v2, 0x8408, v0
	v_dual_mov_b32 v0, s66 :: v_dual_mov_b32 v1, s67
	flat_store_b32 v[0:1], v2
	s_branch .LBB16_1
.LBB16_8:                               ; %for.cond.cleanup
	s_or_b32 exec_lo, exec_lo, s54
	v_dual_mov_b32 v0, s66 :: v_dual_mov_b32 v1, s67
	s_clause 0x3                            ; 16-byte Folded Reload
	scratch_load_b32 v43, off, s33
	scratch_load_b32 v42, off, s33 offset:4
	scratch_load_b32 v41, off, s33 offset:8
	scratch_load_b32 v40, off, s33 offset:12
	v_readlane_b32 s68, v44, 20
	v_readlane_b32 s67, v44, 19
	v_readlane_b32 s66, v44, 18
	flat_load_b32 v0, v[0:1]
	v_readlane_b32 s65, v44, 17
	v_readlane_b32 s64, v44, 16
	v_readlane_b32 s55, v44, 15
	v_readlane_b32 s54, v44, 14
	v_readlane_b32 s53, v44, 13
	v_readlane_b32 s52, v44, 12
	v_readlane_b32 s51, v44, 11
	v_readlane_b32 s50, v44, 10
	v_readlane_b32 s49, v44, 9
	v_readlane_b32 s48, v44, 8
	v_readlane_b32 s39, v44, 7
	v_readlane_b32 s38, v44, 6
	v_readlane_b32 s37, v44, 5
	v_readlane_b32 s36, v44, 4
	v_readlane_b32 s35, v44, 3
	v_readlane_b32 s34, v44, 2
	v_readlane_b32 s31, v44, 1
	v_readlane_b32 s30, v44, 0
	s_mov_b32 s32, s33
	v_readlane_b32 s0, v44, 21
	s_or_saveexec_b32 s1, -1
	scratch_load_b32 v44, off, s33 offset:32 ; 4-byte Folded Reload
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s1
	s_mov_b32 s33, s0
	s_wait_loadcnt_dscnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	s_setpc_b64 s[30:31]
.Lfunc_end16:
	.size	_Z8crc_loopjj, .Lfunc_end16-_Z8crc_loopjj
                                        ; -- End function
	.set _Z8crc_loopjj.num_vgpr, max(45, __assert_fail.num_vgpr)
	.set _Z8crc_loopjj.num_agpr, max(0, __assert_fail.num_agpr)
	.set _Z8crc_loopjj.numbered_sgpr, max(69, __assert_fail.numbered_sgpr)
	.set _Z8crc_loopjj.num_named_barrier, max(0, __assert_fail.num_named_barrier)
	.set _Z8crc_loopjj.private_seg_size, 48+max(__assert_fail.private_seg_size)
	.set _Z8crc_loopjj.uses_vcc, or(1, __assert_fail.uses_vcc)
	.set _Z8crc_loopjj.uses_flat_scratch, or(1, __assert_fail.uses_flat_scratch)
	.set _Z8crc_loopjj.has_dyn_sized_stack, or(0, __assert_fail.has_dyn_sized_stack)
	.set _Z8crc_loopjj.has_recursion, or(1, __assert_fail.has_recursion)
	.set _Z8crc_loopjj.has_indirect_call, or(0, __assert_fail.has_indirect_call)
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 1252
; TotalNumSgprs: 81
; NumVgprs: 54
; ScratchSize: 216
; MemoryBound: 0
	.text
	.hidden	_Z13VERIFY_RESULTjjPi           ; -- Begin function _Z13VERIFY_RESULTjjPi
	.globl	_Z13VERIFY_RESULTjjPi
	.p2align	7
	.type	_Z13VERIFY_RESULTjjPi,@function
_Z13VERIFY_RESULTjjPi:                  ; @_Z13VERIFY_RESULTjjPi
; %bb.0:                                ; %entry
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_mov_b32 s0, s33
	s_mov_b32 s33, s32
	s_or_saveexec_b32 s1, -1
	scratch_store_b32 off, v58, s33 offset:64 ; 4-byte Folded Spill
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s1
	v_writelane_b32 v58, s0, 24
	s_addk_co_i32 s32, 0x50
	s_add_co_i32 s2, s33, 40
	s_mov_b64 s[0:1], src_private_base
	s_add_co_i32 s3, s33, 44
	v_writelane_b32 v58, s30, 0
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s0, s2
	s_clause 0x9                            ; 40-byte Folded Spill
	scratch_store_b32 off, v40, s33 offset:36
	scratch_store_b32 off, v41, s33 offset:32
	scratch_store_b32 off, v42, s33 offset:28
	scratch_store_b32 off, v43, s33 offset:24
	scratch_store_b32 off, v44, s33 offset:20
	scratch_store_b32 off, v45, s33 offset:16
	scratch_store_b32 off, v46, s33 offset:12
	scratch_store_b32 off, v47, s33 offset:8
	scratch_store_b32 off, v56, s33 offset:4
	scratch_store_b32 off, v57, s33
	v_dual_mov_b32 v40, v31 :: v_dual_mov_b32 v43, s1
	v_writelane_b32 v58, s31, 1
	s_mov_b32 s2, s3
	s_mov_b32 s3, s1
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v42, s0 :: v_dual_mov_b32 v45, s3
	v_writelane_b32 v58, s34, 2
	s_add_co_i32 s0, s33, 48
	v_mov_b32_e32 v47, s1
	v_writelane_b32 v58, s35, 3
	v_writelane_b32 v58, s36, 4
	v_writelane_b32 v58, s37, 5
	v_writelane_b32 v58, s38, 6
	v_writelane_b32 v58, s39, 7
	v_writelane_b32 v58, s48, 8
	v_writelane_b32 v58, s49, 9
	s_mov_b64 s[48:49], s[10:11]
	v_writelane_b32 v58, s50, 10
	v_writelane_b32 v58, s51, 11
	s_mov_b64 s[50:51], s[8:9]
	v_writelane_b32 v58, s52, 12
	v_writelane_b32 v58, s53, 13
	s_mov_b64 s[52:53], s[6:7]
	v_writelane_b32 v58, s54, 14
	v_writelane_b32 v58, s55, 15
	s_mov_b64 s[54:55], s[4:5]
	v_writelane_b32 v58, s64, 16
	s_mov_b32 s64, s15
	v_writelane_b32 v58, s65, 17
	s_mov_b32 s65, s14
	v_writelane_b32 v58, s66, 18
	s_mov_b32 s66, s13
	v_writelane_b32 v58, s67, 19
	s_mov_b32 s67, s12
	v_writelane_b32 v58, s68, 20
	v_writelane_b32 v58, s69, 21
	s_mov_b32 s69, s1
	v_writelane_b32 v58, s70, 22
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s70, s0
	s_add_co_i32 s0, s33, 56
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 s68, s0
	v_writelane_b32 v58, s71, 23
	s_mov_b32 s71, s1
	v_mov_b32_e32 v44, s2
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v4, s70 :: v_dual_mov_b32 v5, s71
	flat_store_b32 v[42:43], v0
	flat_store_b32 v[44:45], v1
	flat_load_b32 v0, v[42:43]
	flat_load_b32 v1, v[44:45]
	s_add_co_i32 s0, s33, 60
	s_getpc_b64 s[2:3]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s3, s3
	s_add_co_u32 s2, s2, _Z9crc_tablejj@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s3, s3, _Z9crc_tablejj@rel32@hi+24
	v_mov_b32_e32 v46, s0
	flat_store_b64 v[4:5], v[2:3]
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[2:3]
	v_dual_mov_b32 v56, s68 :: v_dual_mov_b32 v57, s69
	v_mov_b32_e32 v31, v40
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, _Z8crc_loopjj@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, _Z8crc_loopjj@rel32@hi+24
	s_mov_b64 s[4:5], s[54:55]
	s_mov_b64 s[6:7], s[52:53]
	flat_store_b32 v[56:57], v0
	flat_load_b32 v0, v[42:43]
	flat_load_b32 v1, v[44:45]
	s_mov_b64 s[8:9], s[50:51]
	s_mov_b64 s[10:11], s[48:49]
	s_mov_b32 s12, s67
	s_mov_b32 s13, s66
	s_mov_b32 s14, s65
	s_mov_b32 s15, s64
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	flat_store_b32 v[46:47], v0
	flat_load_b32 v1, v[56:57]
	s_mov_b32 s0, exec_lo
	s_wait_loadcnt_dscnt 0x0
	v_cmpx_ne_u32_e64 v1, v0
	s_cbranch_execz .LBB17_2
; %bb.1:                                ; %if.then
	v_dual_mov_b32 v0, s70 :: v_dual_mov_b32 v1, s71
	v_mov_b32_e32 v2, 1
	flat_load_b64 v[0:1], v[0:1]
	s_wait_loadcnt_dscnt 0x0
	flat_store_b32 v[0:1], v2
.LBB17_2:                               ; %if.end
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s0
	s_clause 0x9                            ; 40-byte Folded Reload
	scratch_load_b32 v57, off, s33
	scratch_load_b32 v56, off, s33 offset:4
	scratch_load_b32 v47, off, s33 offset:8
	scratch_load_b32 v46, off, s33 offset:12
	scratch_load_b32 v45, off, s33 offset:16
	scratch_load_b32 v44, off, s33 offset:20
	scratch_load_b32 v43, off, s33 offset:24
	scratch_load_b32 v42, off, s33 offset:28
	scratch_load_b32 v41, off, s33 offset:32
	scratch_load_b32 v40, off, s33 offset:36
	v_readlane_b32 s71, v58, 23
	v_readlane_b32 s70, v58, 22
	v_readlane_b32 s69, v58, 21
	v_readlane_b32 s68, v58, 20
	v_readlane_b32 s67, v58, 19
	v_readlane_b32 s66, v58, 18
	v_readlane_b32 s65, v58, 17
	v_readlane_b32 s64, v58, 16
	v_readlane_b32 s55, v58, 15
	v_readlane_b32 s54, v58, 14
	v_readlane_b32 s53, v58, 13
	v_readlane_b32 s52, v58, 12
	v_readlane_b32 s51, v58, 11
	v_readlane_b32 s50, v58, 10
	v_readlane_b32 s49, v58, 9
	v_readlane_b32 s48, v58, 8
	v_readlane_b32 s39, v58, 7
	v_readlane_b32 s38, v58, 6
	v_readlane_b32 s37, v58, 5
	v_readlane_b32 s36, v58, 4
	v_readlane_b32 s35, v58, 3
	v_readlane_b32 s34, v58, 2
	v_readlane_b32 s31, v58, 1
	v_readlane_b32 s30, v58, 0
	s_mov_b32 s32, s33
	v_readlane_b32 s0, v58, 24
	s_or_saveexec_b32 s1, -1
	scratch_load_b32 v58, off, s33 offset:64 ; 4-byte Folded Reload
	s_wait_alu depctr_sa_sdst(0)
	s_mov_b32 exec_lo, s1
	s_mov_b32 s33, s0
	s_wait_loadcnt_dscnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	s_setpc_b64 s[30:31]
.Lfunc_end17:
	.size	_Z13VERIFY_RESULTjjPi, .Lfunc_end17-_Z13VERIFY_RESULTjjPi
                                        ; -- End function
	.set _Z13VERIFY_RESULTjjPi.num_vgpr, max(59, _Z9crc_tablejj.num_vgpr, _Z8crc_loopjj.num_vgpr)
	.set _Z13VERIFY_RESULTjjPi.num_agpr, max(0, _Z9crc_tablejj.num_agpr, _Z8crc_loopjj.num_agpr)
	.set _Z13VERIFY_RESULTjjPi.numbered_sgpr, max(72, _Z9crc_tablejj.numbered_sgpr, _Z8crc_loopjj.numbered_sgpr)
	.set _Z13VERIFY_RESULTjjPi.num_named_barrier, max(0, _Z9crc_tablejj.num_named_barrier, _Z8crc_loopjj.num_named_barrier)
	.set _Z13VERIFY_RESULTjjPi.private_seg_size, 80+max(_Z9crc_tablejj.private_seg_size, _Z8crc_loopjj.private_seg_size)
	.set _Z13VERIFY_RESULTjjPi.uses_vcc, or(1, _Z9crc_tablejj.uses_vcc, _Z8crc_loopjj.uses_vcc)
	.set _Z13VERIFY_RESULTjjPi.uses_flat_scratch, or(1, _Z9crc_tablejj.uses_flat_scratch, _Z8crc_loopjj.uses_flat_scratch)
	.set _Z13VERIFY_RESULTjjPi.has_dyn_sized_stack, or(0, _Z9crc_tablejj.has_dyn_sized_stack, _Z8crc_loopjj.has_dyn_sized_stack)
	.set _Z13VERIFY_RESULTjjPi.has_recursion, or(1, _Z9crc_tablejj.has_recursion, _Z8crc_loopjj.has_recursion)
	.set _Z13VERIFY_RESULTjjPi.has_indirect_call, or(0, _Z9crc_tablejj.has_indirect_call, _Z8crc_loopjj.has_indirect_call)
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 1200
; TotalNumSgprs: 81
; NumVgprs: 59
; ScratchSize: 296
; MemoryBound: 0
	.text
	.p2align	7                               ; -- Begin function __ockl_get_group_id
	.type	__ockl_get_group_id,@function
__ockl_get_group_id:                    ; @__ockl_get_group_id
; %bb.0:
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	v_mov_b32_e32 v1, v0
	s_mov_b32 s0, exec_lo
                                        ; implicit-def: $vgpr0
	s_delay_alu instid0(VALU_DEP_1)
	v_cmpx_lt_i32_e32 0, v1
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s0, exec_lo, s0
	s_cbranch_execz .LBB18_8
; %bb.1:                                ; %NodeBlock
	s_mov_b32 s1, exec_lo
                                        ; implicit-def: $vgpr0
	v_cmpx_lt_i32_e32 1, v1
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s1, exec_lo, s1
	s_cbranch_execz .LBB18_5
; %bb.2:                                ; %LeafBlock1
	v_mov_b32_e32 v0, 0
	s_mov_b32 s2, exec_lo
	v_cmpx_eq_u32_e32 2, v1
; %bb.3:
	s_lshr_b32 s3, ttmp7, 16
	s_wait_alu depctr_sa_sdst(0)
	v_mov_b32_e32 v0, s3
; %bb.4:                                ; %Flow
	s_or_b32 exec_lo, exec_lo, s2
.LBB18_5:                               ; %Flow5
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_saveexec_b32 s1, s1
; %bb.6:
	s_and_b32 s2, ttmp7, 0xffff
	s_wait_alu depctr_sa_sdst(0)
	v_mov_b32_e32 v0, s2
; %bb.7:                                ; %Flow6
	s_or_b32 exec_lo, exec_lo, s1
                                        ; implicit-def: $vgpr1
.LBB18_8:                               ; %Flow8
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_saveexec_b32 s0, s0
	s_cbranch_execz .LBB18_12
; %bb.9:                                ; %LeafBlock
	v_mov_b32_e32 v0, 0
	s_mov_b32 s1, exec_lo
	v_cmpx_eq_u32_e32 0, v1
; %bb.10:
	s_wait_alu depctr_sa_sdst(0)
	v_mov_b32_e32 v0, ttmp9
; %bb.11:                               ; %Flow7
	s_or_b32 exec_lo, exec_lo, s1
.LBB18_12:
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s0
	v_mov_b32_e32 v1, 0
	s_setpc_b64 s[30:31]
.Lfunc_end18:
	.size	__ockl_get_group_id, .Lfunc_end18-__ockl_get_group_id
                                        ; -- End function
	.set .L__ockl_get_group_id.num_vgpr, 2
	.set .L__ockl_get_group_id.num_agpr, 0
	.set .L__ockl_get_group_id.numbered_sgpr, 32
	.set .L__ockl_get_group_id.num_named_barrier, 0
	.set .L__ockl_get_group_id.private_seg_size, 0
	.set .L__ockl_get_group_id.uses_vcc, 0
	.set .L__ockl_get_group_id.uses_flat_scratch, 0
	.set .L__ockl_get_group_id.has_dyn_sized_stack, 0
	.set .L__ockl_get_group_id.has_recursion, 0
	.set .L__ockl_get_group_id.has_indirect_call, 0
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 176
; TotalNumSgprs: 32
; NumVgprs: 2
; ScratchSize: 0
; MemoryBound: 0
	.text
	.p2align	7                               ; -- Begin function __ockl_get_local_size
	.type	__ockl_get_local_size,@function
__ockl_get_local_size:                  ; @__ockl_get_local_size
; %bb.0:
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	v_mov_b32_e32 v2, v0
	s_mov_b32 s0, exec_lo
                                        ; implicit-def: $vgpr0_vgpr1
	s_delay_alu instid0(VALU_DEP_1)
	v_cmpx_lt_i32_e32 0, v2
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s0, exec_lo, s0
	s_cbranch_execnz .LBB19_3
; %bb.1:                                ; %Flow8
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_saveexec_b32 s2, s0
	s_cbranch_execnz .LBB19_10
.LBB19_2:
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s2
	s_setpc_b64 s[30:31]
.LBB19_3:                               ; %NodeBlock
	s_mov_b32 s1, exec_lo
                                        ; implicit-def: $vgpr0_vgpr1
	v_cmpx_lt_i32_e32 1, v2
	s_wait_alu depctr_sa_sdst(0)
	s_xor_b32 s1, exec_lo, s1
	s_cbranch_execz .LBB19_7
; %bb.4:                                ; %LeafBlock1
	v_mov_b32_e32 v0, 1
	v_mov_b32_e32 v1, 0
	s_mov_b32 s2, exec_lo
	v_cmpx_eq_u32_e32 2, v2
	s_cbranch_execz .LBB19_6
; %bb.5:
	s_load_b32 s3, s[8:9], 0x8
	s_lshr_b32 s4, ttmp7, 16
	v_mov_b32_e32 v1, 0
	s_mov_b32 s5, 0
	s_wait_kmcnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	s_cmp_lt_u32 s4, s3
	s_cselect_b32 s4, 16, 22
	s_wait_alu depctr_sa_sdst(0)
	s_add_nc_u64 s[4:5], s[8:9], s[4:5]
	global_load_d16_b16 v0, v1, s[4:5]
	s_wait_loadcnt 0x0
	v_and_b32_e32 v0, 0xffff, v0
.LBB19_6:                               ; %Flow
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s2
.LBB19_7:                               ; %Flow5
	s_wait_alu depctr_sa_sdst(0)
	s_and_not1_saveexec_b32 s1, s1
	s_cbranch_execz .LBB19_9
; %bb.8:
	s_load_b32 s2, s[8:9], 0x4
	s_and_b32 s3, ttmp7, 0xffff
	v_mov_b32_e32 v1, 0
	s_wait_kmcnt 0x0
	s_wait_alu depctr_sa_sdst(0)
	s_cmp_lt_u32 s3, s2
	s_mov_b32 s3, 0
	s_cselect_b32 s2, 14, 20
	s_wait_alu depctr_sa_sdst(0)
	s_add_nc_u64 s[2:3], s[8:9], s[2:3]
	global_load_d16_b16 v0, v1, s[2:3]
	s_wait_loadcnt 0x0
	v_and_b32_e32 v0, 0xffff, v0
.LBB19_9:                               ; %Flow6
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s1
                                        ; implicit-def: $vgpr2
	s_and_not1_saveexec_b32 s2, s0
	s_cbranch_execz .LBB19_2
.LBB19_10:                              ; %LeafBlock
	v_mov_b32_e32 v0, 1
	v_mov_b32_e32 v1, 0
	s_mov_b32 s1, 0
	s_mov_b32 s3, exec_lo
	v_cmpx_eq_u32_e32 0, v2
	s_cbranch_execz .LBB19_12
; %bb.11:
	s_load_b32 s0, s[8:9], 0x0
	v_mov_b32_e32 v1, 0
	s_wait_kmcnt 0x0
	s_cmp_lt_u32 ttmp9, s0
	s_cselect_b32 s0, 12, 18
	s_wait_alu depctr_sa_sdst(0)
	s_add_nc_u64 s[0:1], s[8:9], s[0:1]
	global_load_d16_b16 v0, v1, s[0:1]
	s_wait_loadcnt 0x0
	v_and_b32_e32 v0, 0xffff, v0
.LBB19_12:                              ; %Flow7
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s3
	s_delay_alu instid0(SALU_CYCLE_1)
	s_or_b32 exec_lo, exec_lo, s2
	s_setpc_b64 s[30:31]
.Lfunc_end19:
	.size	__ockl_get_local_size, .Lfunc_end19-__ockl_get_local_size
                                        ; -- End function
	.set .L__ockl_get_local_size.num_vgpr, 3
	.set .L__ockl_get_local_size.num_agpr, 0
	.set .L__ockl_get_local_size.numbered_sgpr, 32
	.set .L__ockl_get_local_size.num_named_barrier, 0
	.set .L__ockl_get_local_size.private_seg_size, 0
	.set .L__ockl_get_local_size.uses_vcc, 0
	.set .L__ockl_get_local_size.uses_flat_scratch, 0
	.set .L__ockl_get_local_size.has_dyn_sized_stack, 0
	.set .L__ockl_get_local_size.has_recursion, 0
	.set .L__ockl_get_local_size.has_indirect_call, 0
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 388
; TotalNumSgprs: 32
; NumVgprs: 3
; ScratchSize: 0
; MemoryBound: 0
	.section	.text._Z9atomicAddPii,"axG",@progbits,_Z9atomicAddPii,comdat
	.hidden	_Z9atomicAddPii                 ; -- Begin function _Z9atomicAddPii
	.weak	_Z9atomicAddPii
	.p2align	7
	.type	_Z9atomicAddPii,@function
_Z9atomicAddPii:                        ; @_Z9atomicAddPii
; %bb.0:                                ; %entry
	s_wait_loadcnt_dscnt 0x0
	s_wait_expcnt 0x0
	s_wait_samplecnt 0x0
	s_wait_bvhcnt 0x0
	s_wait_kmcnt 0x0
	s_mov_b64 s[0:1], src_private_base
	s_add_co_i32 s0, s32, 8
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v4, s1 :: v_dual_mov_b32 v3, s32
	v_dual_mov_b32 v5, s0 :: v_dual_mov_b32 v6, s1
	s_add_co_i32 s0, s32, 12
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v8, s1 :: v_dual_mov_b32 v7, s0
	flat_store_b64 v[3:4], v[0:1]
	flat_store_b32 v[5:6], v2
	flat_store_b32 v[7:8], v2
	flat_atomic_add_u32 v0, v[0:1], v2 th:TH_ATOMIC_RETURN scope:SCOPE_DEV
	s_add_co_i32 s0, s32, 16
	s_wait_alu depctr_sa_sdst(0)
	v_mov_b32_e32 v3, s0
	s_wait_loadcnt_dscnt 0x0
	flat_store_b32 v[3:4], v0
	s_wait_dscnt 0x0
	s_setpc_b64 s[30:31]
.Lfunc_end20:
	.size	_Z9atomicAddPii, .Lfunc_end20-_Z9atomicAddPii
                                        ; -- End function
	.set _Z9atomicAddPii.num_vgpr, 9
	.set _Z9atomicAddPii.num_agpr, 0
	.set _Z9atomicAddPii.numbered_sgpr, 33
	.set _Z9atomicAddPii.num_named_barrier, 0
	.set _Z9atomicAddPii.private_seg_size, 24
	.set _Z9atomicAddPii.uses_vcc, 0
	.set _Z9atomicAddPii.uses_flat_scratch, 0
	.set _Z9atomicAddPii.has_dyn_sized_stack, 0
	.set _Z9atomicAddPii.has_recursion, 0
	.set _Z9atomicAddPii.has_indirect_call, 0
	.section	.AMDGPU.csdata,"",@progbits
; Function info:
; codeLenInByte = 148
; TotalNumSgprs: 33
; NumVgprs: 9
; ScratchSize: 24
; MemoryBound: 0
	.text
	.protected	test_crc_kernel         ; -- Begin function test_crc_kernel
	.globl	test_crc_kernel
	.p2align	8
	.type	test_crc_kernel,@function
test_crc_kernel:                        ; @test_crc_kernel
; %bb.0:                                ; %entry
	s_mov_b64 s[84:85], s[0:1]
	s_load_b64 s[0:1], s[4:5], 0x0
	v_dual_mov_b32 v41, v0 :: v_dual_mov_b32 v0, 0
	s_mov_b64 s[96:97], src_private_base
	s_mov_b32 s96, 8
	v_mov_b32_e32 v1, s97
	s_delay_alu instid0(VALU_DEP_2)
	v_mov_b32_e32 v31, v41
	s_mov_b64 s[80:81], s[6:7]
	s_mov_b64 s[82:83], s[2:3]
	s_add_nc_u64 s[86:87], s[4:5], 8
	s_getpc_b64 s[2:3]
	s_sext_i32_i16 s3, s3
	s_add_co_u32 s2, s2, _Z8crc_initv@rel32@lo+8
	s_add_co_ci_u32 s3, s3, _Z8crc_initv@rel32@hi+16
	s_mov_b64 s[4:5], s[84:85]
	s_mov_b64 s[6:7], s[82:83]
	s_mov_b64 s[8:9], s[86:87]
	s_mov_b64 s[10:11], s[80:81]
	s_mov_b32 s32, 32
	s_mov_b32 s34, 16
	s_mov_b32 s36, 20
	s_mov_b32 s35, s97
	s_wait_kmcnt 0x0
	v_dual_mov_b32 v4, s96 :: v_dual_mov_b32 v3, s1
	v_dual_mov_b32 v2, s0 :: v_dual_mov_b32 v5, s97
	s_mov_b32 s37, s97
	flat_store_b64 v[0:1], v[2:3]
	flat_store_b64 v[4:5], v[2:3]
	s_swappc_b64 s[30:31], s[2:3]
	v_dual_mov_b32 v40, 0 :: v_dual_mov_b32 v31, v41
	v_mov_b32_e32 v0, 0
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_get_local_id@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_get_local_id@rel32@hi+24
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	v_dual_mov_b32 v3, v0 :: v_dual_mov_b32 v0, 0
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_get_group_id@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_get_group_id@rel32@hi+24
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	v_mov_b32_e32 v4, v0
	v_mov_b32_e32 v0, 0
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_get_local_size@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_get_local_size@rel32@hi+24
	s_mov_b64 s[4:5], s[84:85]
	s_mov_b64 s[8:9], s[86:87]
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	v_mad_co_u64_u32 v[0:1], null, v4, v0, v[3:4]
	v_mul_lo_u32 v6, 0x1010101, v3
	v_dual_mov_b32 v1, s34 :: v_dual_mov_b32 v2, s35
	v_dual_mov_b32 v4, s36 :: v_dual_mov_b32 v5, s37
	s_mov_b32 s0, exec_lo
	s_delay_alu instid0(VALU_DEP_4) | instskip(NEXT) | instid1(VALU_DEP_4)
	v_not_b32_e32 v0, v0
	v_xor_b32_e32 v6, 0xa5a5a5a5, v6
	flat_store_b32 v[1:2], v0
	flat_store_b32 v[4:5], v6
	v_cmpx_eq_u32_e32 0, v3
	s_cbranch_execz .LBB21_2
; %bb.1:                                ; %if.then
	s_mov_b64 s[2:3], src_shared_base
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v0, 0x400 :: v_dual_mov_b32 v1, s3
	flat_store_b32 v[0:1], v40
.LBB21_2:                               ; %if.end
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s0
	v_mov_b32_e32 v31, v41
	s_getpc_b64 s[98:99]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s99, s99
	s_add_co_u32 s98, s98, _Z13__syncthreadsv@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s99, s99, _Z13__syncthreadsv@rel32@hi+24
	s_mov_b64 s[4:5], s[84:85]
	s_mov_b64 s[6:7], s[82:83]
	s_mov_b64 s[8:9], s[86:87]
	s_mov_b64 s[10:11], s[80:81]
	s_mov_b64 s[38:39], src_private_base
	s_mov_b32 s38, 24
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[98:99]
	v_dual_mov_b32 v47, s39 :: v_dual_mov_b32 v46, s38
	v_dual_mov_b32 v0, s34 :: v_dual_mov_b32 v1, s35
	v_dual_mov_b32 v2, s36 :: v_dual_mov_b32 v3, s37
	flat_store_b32 v[46:47], v40
	flat_load_b32 v0, v[0:1]
	flat_load_b32 v1, v[2:3]
	v_dual_mov_b32 v31, v41 :: v_dual_mov_b32 v2, 24
	v_mov_b32_e32 v3, s39
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, _Z13VERIFY_RESULTjjPi@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, _Z13VERIFY_RESULTjjPi@rel32@hi+24
	s_mov_b64 s[4:5], s[84:85]
	s_mov_b64 s[6:7], s[82:83]
	s_mov_b64 s[8:9], s[86:87]
	s_mov_b64 s[10:11], s[80:81]
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	flat_load_b32 v0, v[46:47]
	s_mov_b32 s33, exec_lo
	s_wait_loadcnt_dscnt 0x0
	v_cmpx_ne_u32_e32 0, v0
	s_cbranch_execz .LBB21_4
; %bb.3:                                ; %if.then9
	s_mov_b64 s[0:1], src_shared_base
	v_dual_mov_b32 v31, v41 :: v_dual_mov_b32 v0, 0x400
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v1, s1 :: v_dual_mov_b32 v2, 1
	s_getpc_b64 s[2:3]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s3, s3
	s_add_co_u32 s2, s2, _Z9atomicAddPii@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s3, s3, _Z9atomicAddPii@rel32@hi+24
	s_mov_b64 s[4:5], s[84:85]
	s_mov_b64 s[6:7], s[82:83]
	s_mov_b64 s[8:9], s[86:87]
	s_mov_b64 s[10:11], s[80:81]
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[2:3]
.LBB21_4:                               ; %if.end11
	s_wait_alu depctr_sa_sdst(0)
	s_or_b32 exec_lo, exec_lo, s33
	v_mov_b32_e32 v31, v41
	s_mov_b64 s[4:5], s[84:85]
	s_mov_b64 s[6:7], s[82:83]
	s_mov_b64 s[8:9], s[86:87]
	s_mov_b64 s[10:11], s[80:81]
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[98:99]
	v_dual_mov_b32 v31, v41 :: v_dual_mov_b32 v0, 0
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, __ockl_get_local_id@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, __ockl_get_local_id@rel32@hi+24
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
	s_mov_b32 s0, exec_lo
	v_cmpx_eq_u32_e32 0, v0
	s_cbranch_execz .LBB21_6
; %bb.5:                                ; %if.then14
	s_mov_b64 s[0:1], src_shared_base
	v_dual_mov_b32 v0, s96 :: v_dual_mov_b32 v1, s97
	s_wait_alu depctr_sa_sdst(0)
	v_dual_mov_b32 v2, 0x400 :: v_dual_mov_b32 v3, s1
	v_mov_b32_e32 v31, v41
	flat_load_b64 v[0:1], v[0:1]
	flat_load_b32 v2, v[2:3]
	s_getpc_b64 s[0:1]
	s_wait_alu depctr_sa_sdst(0)
	s_sext_i32_i16 s1, s1
	s_add_co_u32 s0, s0, _Z9atomicAddPii@rel32@lo+12
	s_wait_alu depctr_sa_sdst(0)
	s_add_co_ci_u32 s1, s1, _Z9atomicAddPii@rel32@hi+24
	s_mov_b64 s[4:5], s[84:85]
	s_mov_b64 s[6:7], s[82:83]
	s_mov_b64 s[8:9], s[86:87]
	s_mov_b64 s[10:11], s[80:81]
	s_wait_alu depctr_sa_sdst(0)
	s_swappc_b64 s[30:31], s[0:1]
.LBB21_6:                               ; %if.end16
	s_endpgm
	.section	.rodata,"a",@progbits
	.p2align	6, 0x0
	.amdhsa_kernel test_crc_kernel
		.amdhsa_group_segment_fixed_size 1028
		.amdhsa_private_segment_fixed_size 328
		.amdhsa_kernarg_size 264
		.amdhsa_user_sgpr_count 8
		.amdhsa_user_sgpr_dispatch_ptr 1
		.amdhsa_user_sgpr_queue_ptr 1
		.amdhsa_user_sgpr_kernarg_segment_ptr 1
		.amdhsa_user_sgpr_dispatch_id 1
		.amdhsa_user_sgpr_private_segment_size 0
		.amdhsa_wavefront_size32 1
		.amdhsa_uses_dynamic_stack 1
		.amdhsa_enable_private_segment 1
		.amdhsa_system_sgpr_workgroup_id_x 1
		.amdhsa_system_sgpr_workgroup_id_y 1
		.amdhsa_system_sgpr_workgroup_id_z 1
		.amdhsa_system_sgpr_workgroup_info 0
		.amdhsa_system_vgpr_workitem_id 2
		.amdhsa_next_free_vgpr 59
		.amdhsa_next_free_sgpr 100
		.amdhsa_reserve_vcc 1
		.amdhsa_float_round_mode_32 0
		.amdhsa_float_round_mode_16_64 0
		.amdhsa_float_denorm_mode_32 3
		.amdhsa_float_denorm_mode_16_64 3
		.amdhsa_fp16_overflow 0
		.amdhsa_workgroup_processor_mode 1
		.amdhsa_memory_ordered 0
		.amdhsa_forward_progress 0
		.amdhsa_inst_pref_size 8
		.amdhsa_round_robin_scheduling 0
		.amdhsa_exception_fp_ieee_invalid_op 0
		.amdhsa_exception_fp_denorm_src 0
		.amdhsa_exception_fp_ieee_div_zero 0
		.amdhsa_exception_fp_ieee_overflow 0
		.amdhsa_exception_fp_ieee_underflow 0
		.amdhsa_exception_fp_ieee_inexact 0
		.amdhsa_exception_int_div_zero 0
	.end_amdhsa_kernel
	.text
.Lfunc_end21:
	.size	test_crc_kernel, .Lfunc_end21-test_crc_kernel
                                        ; -- End function
	.set test_crc_kernel.num_vgpr, max(48, _Z8crc_initv.num_vgpr, .L__ockl_get_local_id.num_vgpr, .L__ockl_get_group_id.num_vgpr, .L__ockl_get_local_size.num_vgpr, _Z13__syncthreadsv.num_vgpr, _Z13VERIFY_RESULTjjPi.num_vgpr, _Z9atomicAddPii.num_vgpr)
	.set test_crc_kernel.num_agpr, max(0, _Z8crc_initv.num_agpr, .L__ockl_get_local_id.num_agpr, .L__ockl_get_group_id.num_agpr, .L__ockl_get_local_size.num_agpr, _Z13__syncthreadsv.num_agpr, _Z13VERIFY_RESULTjjPi.num_agpr, _Z9atomicAddPii.num_agpr)
	.set test_crc_kernel.numbered_sgpr, max(100, _Z8crc_initv.numbered_sgpr, .L__ockl_get_local_id.numbered_sgpr, .L__ockl_get_group_id.numbered_sgpr, .L__ockl_get_local_size.numbered_sgpr, _Z13__syncthreadsv.numbered_sgpr, _Z13VERIFY_RESULTjjPi.numbered_sgpr, _Z9atomicAddPii.numbered_sgpr)
	.set test_crc_kernel.num_named_barrier, max(0, _Z8crc_initv.num_named_barrier, .L__ockl_get_local_id.num_named_barrier, .L__ockl_get_group_id.num_named_barrier, .L__ockl_get_local_size.num_named_barrier, _Z13__syncthreadsv.num_named_barrier, _Z13VERIFY_RESULTjjPi.num_named_barrier, _Z9atomicAddPii.num_named_barrier)
	.set test_crc_kernel.private_seg_size, 32+max(_Z8crc_initv.private_seg_size, .L__ockl_get_local_id.private_seg_size, .L__ockl_get_group_id.private_seg_size, .L__ockl_get_local_size.private_seg_size, _Z13__syncthreadsv.private_seg_size, _Z13VERIFY_RESULTjjPi.private_seg_size, _Z9atomicAddPii.private_seg_size)
	.set test_crc_kernel.uses_vcc, or(1, _Z8crc_initv.uses_vcc, .L__ockl_get_local_id.uses_vcc, .L__ockl_get_group_id.uses_vcc, .L__ockl_get_local_size.uses_vcc, _Z13__syncthreadsv.uses_vcc, _Z13VERIFY_RESULTjjPi.uses_vcc, _Z9atomicAddPii.uses_vcc)
	.set test_crc_kernel.uses_flat_scratch, or(0, _Z8crc_initv.uses_flat_scratch, .L__ockl_get_local_id.uses_flat_scratch, .L__ockl_get_group_id.uses_flat_scratch, .L__ockl_get_local_size.uses_flat_scratch, _Z13__syncthreadsv.uses_flat_scratch, _Z13VERIFY_RESULTjjPi.uses_flat_scratch, _Z9atomicAddPii.uses_flat_scratch)
	.set test_crc_kernel.has_dyn_sized_stack, or(0, _Z8crc_initv.has_dyn_sized_stack, .L__ockl_get_local_id.has_dyn_sized_stack, .L__ockl_get_group_id.has_dyn_sized_stack, .L__ockl_get_local_size.has_dyn_sized_stack, _Z13__syncthreadsv.has_dyn_sized_stack, _Z13VERIFY_RESULTjjPi.has_dyn_sized_stack, _Z9atomicAddPii.has_dyn_sized_stack)
	.set test_crc_kernel.has_recursion, or(1, _Z8crc_initv.has_recursion, .L__ockl_get_local_id.has_recursion, .L__ockl_get_group_id.has_recursion, .L__ockl_get_local_size.has_recursion, _Z13__syncthreadsv.has_recursion, _Z13VERIFY_RESULTjjPi.has_recursion, _Z9atomicAddPii.has_recursion)
	.set test_crc_kernel.has_indirect_call, or(0, _Z8crc_initv.has_indirect_call, .L__ockl_get_local_id.has_indirect_call, .L__ockl_get_group_id.has_indirect_call, .L__ockl_get_local_size.has_indirect_call, _Z13__syncthreadsv.has_indirect_call, _Z13VERIFY_RESULTjjPi.has_indirect_call, _Z9atomicAddPii.has_indirect_call)
	.section	.AMDGPU.csdata,"",@progbits
; Kernel info:
; codeLenInByte = 964
; TotalNumSgprs: 104
; NumVgprs: 59
; ScratchSize: 328
; MemoryBound: 0
; FloatMode: 240
; IeeeMode: 1
; LDSByteSize: 1028 bytes/workgroup (compile time only)
; SGPRBlocks: 0
; VGPRBlocks: 7
; NumSGPRsForWavesPerEU: 104
; NumVGPRsForWavesPerEU: 59
; Occupancy: 16
; WaveLimiterHint : 1
; COMPUTE_PGM_RSRC2:SCRATCH_EN: 1
; COMPUTE_PGM_RSRC2:USER_SGPR: 8
; COMPUTE_PGM_RSRC2:TRAP_HANDLER: 0
; COMPUTE_PGM_RSRC2:TGID_X_EN: 1
; COMPUTE_PGM_RSRC2:TGID_Y_EN: 1
; COMPUTE_PGM_RSRC2:TGID_Z_EN: 1
; COMPUTE_PGM_RSRC2:TIDIG_COMP_CNT: 2
	.section	.AMDGPU.gpr_maximums,"",@progbits
	.set amdgpu.max_num_vgpr, 59
	.set amdgpu.max_num_agpr, 0
	.set amdgpu.max_num_sgpr, 77
	.set amdgpu.max_num_named_barrier, 0
	.section	.AMDGPU.csdata,"",@progbits
	.type	.L__const.__assert_fail.fmt,@object ; @__const.__assert_fail.fmt
	.section	.rodata.str1.16,"aMS",@progbits,1
	.p2align	4, 0x0
.L__const.__assert_fail.fmt:
	.asciz	"%s:%u: %s: Device-side assertion `%s' failed.\n"
	.size	.L__const.__assert_fail.fmt, 47

	.protected	threadIdx
	.protected	blockIdx
	.protected	blockDim
	.type	.L.str,@object                  ; @.str
	.section	.rodata.str1.1,"aMS",@progbits,1
.L.str:
	.asciz	"workgroup"
	.size	.L.str, 10

	.type	.L.str.1,@object                ; @.str.1
.L.str.1:
	.asciz	"global"
	.size	.L.str.1, 7

	.type	.L.str.2,@object                ; @.str.2
.L.str.2:
	.asciz	"local"
	.size	.L.str.2, 6

	.type	__hip_cuid_b312a08b1316ee1f,@object ; @__hip_cuid_b312a08b1316ee1f
	.section	.bss,"aw",@nobits
	.globl	__hip_cuid_b312a08b1316ee1f
__hip_cuid_b312a08b1316ee1f:
	.byte	0                               ; 0x0
	.size	__hip_cuid_b312a08b1316ee1f, 1

	.type	__oclc_ISA_version,@object      ; @__oclc_ISA_version
	.section	.rodata,"a",@progbits
	.p2align	2, 0x0
__oclc_ISA_version:
	.long	12001                           ; 0x2ee1
	.size	__oclc_ISA_version, 4

	.type	__oclc_ABI_version,@object      ; @__oclc_ABI_version
	.p2align	2, 0x0
__oclc_ABI_version:
	.long	600                             ; 0x258
	.size	__oclc_ABI_version, 4

	.type	G,@object                       ; @G
	.data
	.globl	G
	.p2align	2, 0x0
G:
	.long	2147483648                      ; 0x80000000
	.size	G, 4

	.weak	threadIdx
	.weak	blockIdx
	.weak	blockDim
	.ident	"clang version 22.0.0git (https://github.com/llvm/llvm-project 86b9f90b9574b3a7d15d28a91f6316459dcfa046+PATCHED)"
	.ident	"AMD clang version 20.0.0git (https://github.com/RadeonOpenCompute/llvm-project roc-7.1.1 25444 27682a16360e33e37c4f3cc6adf9a620733f8fe1)"
	.section	".note.GNU-stack","",@progbits
	.amdgpu_metadata
---
amdhsa.kernels:
  - .args:
      - .address_space:  global
        .name:           result.coerce
        .offset:         0
        .size:           8
        .value_kind:     global_buffer
      - .offset:         8
        .size:           4
        .value_kind:     hidden_block_count_x
      - .offset:         12
        .size:           4
        .value_kind:     hidden_block_count_y
      - .offset:         16
        .size:           4
        .value_kind:     hidden_block_count_z
      - .offset:         20
        .size:           2
        .value_kind:     hidden_group_size_x
      - .offset:         22
        .size:           2
        .value_kind:     hidden_group_size_y
      - .offset:         24
        .size:           2
        .value_kind:     hidden_group_size_z
      - .offset:         26
        .size:           2
        .value_kind:     hidden_remainder_x
      - .offset:         28
        .size:           2
        .value_kind:     hidden_remainder_y
      - .offset:         30
        .size:           2
        .value_kind:     hidden_remainder_z
      - .offset:         48
        .size:           8
        .value_kind:     hidden_global_offset_x
      - .offset:         56
        .size:           8
        .value_kind:     hidden_global_offset_y
      - .offset:         64
        .size:           8
        .value_kind:     hidden_global_offset_z
      - .offset:         72
        .size:           2
        .value_kind:     hidden_grid_dims
      - .offset:         88
        .size:           8
        .value_kind:     hidden_hostcall_buffer
      - .offset:         96
        .size:           8
        .value_kind:     hidden_multigrid_sync_arg
      - .offset:         104
        .size:           8
        .value_kind:     hidden_heap_v1
      - .offset:         112
        .size:           8
        .value_kind:     hidden_default_queue
      - .offset:         120
        .size:           8
        .value_kind:     hidden_completion_action
      - .offset:         208
        .size:           8
        .value_kind:     hidden_queue_ptr
    .group_segment_fixed_size: 1028
    .kernarg_segment_align: 8
    .kernarg_segment_size: 264
    .language:       OpenCL C
    .language_version:
      - 2
      - 0
    .max_flat_workgroup_size: 1024
    .name:           test_crc_kernel
    .private_segment_fixed_size: 328
    .sgpr_count:     104
    .sgpr_spill_count: 0
    .symbol:         test_crc_kernel.kd
    .uniform_work_group_size: 1
    .uses_dynamic_stack: true
    .vgpr_count:     59
    .vgpr_spill_count: 0
    .wavefront_size: 32
    .workgroup_processor_mode: 1
amdhsa.target:   amdgcn-amd-amdhsa--gfx700
amdhsa.version:
  - 1
  - 2
...

	.end_amdgpu_metadata
