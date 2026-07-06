	.amdgcn_target "amdgcn-amd-amdhsa--gfx700"
	.amdhsa_code_object_version 6
	.text
	.globl	empty                           ; -- Begin function empty
	.p2align	8
	.type	empty,@function
empty:                                  ; @empty
; %bb.0:                                ; %entry
	s_endpgm
	.section	.rodata,"a",@progbits
	.p2align	6, 0x0
	.amdhsa_kernel empty
		.amdhsa_group_segment_fixed_size 0
		.amdhsa_private_segment_fixed_size 0
		.amdhsa_kernarg_size 256
		.amdhsa_user_sgpr_count 14
		.amdhsa_user_sgpr_private_segment_buffer 1
		.amdhsa_user_sgpr_dispatch_ptr 1
		.amdhsa_user_sgpr_queue_ptr 1
		.amdhsa_user_sgpr_kernarg_segment_ptr 1
		.amdhsa_user_sgpr_dispatch_id 1
		.amdhsa_user_sgpr_flat_scratch_init 1
		.amdhsa_user_sgpr_private_segment_size 0
		.amdhsa_uses_dynamic_stack 0
		.amdhsa_system_sgpr_private_segment_wavefront_offset 0
		.amdhsa_system_sgpr_workgroup_id_x 1
		.amdhsa_system_sgpr_workgroup_id_y 1
		.amdhsa_system_sgpr_workgroup_id_z 1
		.amdhsa_system_sgpr_workgroup_info 0
		.amdhsa_system_vgpr_workitem_id 2
		.amdhsa_next_free_vgpr 1
		.amdhsa_next_free_sgpr 1
		.amdhsa_reserve_vcc 0
		.amdhsa_reserve_flat_scratch 0
		.amdhsa_float_round_mode_32 0
		.amdhsa_float_round_mode_16_64 0
		.amdhsa_float_denorm_mode_32 3
		.amdhsa_float_denorm_mode_16_64 3
		.amdhsa_exception_fp_ieee_invalid_op 0
		.amdhsa_exception_fp_denorm_src 0
		.amdhsa_exception_fp_ieee_div_zero 0
		.amdhsa_exception_fp_ieee_overflow 0
		.amdhsa_exception_fp_ieee_underflow 0
		.amdhsa_exception_fp_ieee_inexact 0
		.amdhsa_exception_int_div_zero 0
	.end_amdhsa_kernel
	.text
.Lfunc_end0:
	.size	empty, .Lfunc_end0-empty
                                        ; -- End function
	.set empty.num_vgpr, 0
	.set empty.num_agpr, 0
	.set empty.numbered_sgpr, 0
	.set empty.num_named_barrier, 0
	.set empty.private_seg_size, 0
	.set empty.uses_vcc, 0
	.set empty.uses_flat_scratch, 0
	.set empty.has_dyn_sized_stack, 0
	.set empty.has_recursion, 0
	.set empty.has_indirect_call, 0
	.section	.AMDGPU.csdata,"",@progbits
; Kernel info:
; codeLenInByte = 4
; TotalNumSgprs: 0
; NumVgprs: 0
; ScratchSize: 0
; MemoryBound: 0
; FloatMode: 240
; IeeeMode: 1
; LDSByteSize: 0 bytes/workgroup (compile time only)
; SGPRBlocks: 0
; VGPRBlocks: 0
; NumSGPRsForWavesPerEU: 1
; NumVGPRsForWavesPerEU: 1
; Occupancy: 10
; WaveLimiterHint : 0
; COMPUTE_PGM_RSRC2:SCRATCH_EN: 0
; COMPUTE_PGM_RSRC2:USER_SGPR: 14
; COMPUTE_PGM_RSRC2:TRAP_HANDLER: 0
; COMPUTE_PGM_RSRC2:TGID_X_EN: 1
; COMPUTE_PGM_RSRC2:TGID_Y_EN: 1
; COMPUTE_PGM_RSRC2:TGID_Z_EN: 1
; COMPUTE_PGM_RSRC2:TIDIG_COMP_CNT: 2
	.section	.AMDGPU.gpr_maximums,"",@progbits
	.set amdgpu.max_num_vgpr, 0
	.set amdgpu.max_num_agpr, 0
	.set amdgpu.max_num_sgpr, 0
	.set amdgpu.max_num_named_barrier, 0
	.section	.AMDGPU.csdata,"",@progbits
	.section	".note.GNU-stack","",@progbits
	.amdgpu_metadata
---
amdhsa.kernels:
  - .args:
      - .offset:         0
        .size:           4
        .value_kind:     hidden_block_count_x
      - .offset:         4
        .size:           4
        .value_kind:     hidden_block_count_y
      - .offset:         8
        .size:           4
        .value_kind:     hidden_block_count_z
      - .offset:         12
        .size:           2
        .value_kind:     hidden_group_size_x
      - .offset:         14
        .size:           2
        .value_kind:     hidden_group_size_y
      - .offset:         16
        .size:           2
        .value_kind:     hidden_group_size_z
      - .offset:         18
        .size:           2
        .value_kind:     hidden_remainder_x
      - .offset:         20
        .size:           2
        .value_kind:     hidden_remainder_y
      - .offset:         22
        .size:           2
        .value_kind:     hidden_remainder_z
      - .offset:         40
        .size:           8
        .value_kind:     hidden_global_offset_x
      - .offset:         48
        .size:           8
        .value_kind:     hidden_global_offset_y
      - .offset:         56
        .size:           8
        .value_kind:     hidden_global_offset_z
      - .offset:         64
        .size:           2
        .value_kind:     hidden_grid_dims
      - .offset:         80
        .size:           8
        .value_kind:     hidden_hostcall_buffer
      - .offset:         88
        .size:           8
        .value_kind:     hidden_multigrid_sync_arg
      - .offset:         96
        .size:           8
        .value_kind:     hidden_heap_v1
      - .offset:         104
        .size:           8
        .value_kind:     hidden_default_queue
      - .offset:         112
        .size:           8
        .value_kind:     hidden_completion_action
      - .offset:         192
        .size:           4
        .value_kind:     hidden_private_base
      - .offset:         196
        .size:           4
        .value_kind:     hidden_shared_base
      - .offset:         200
        .size:           8
        .value_kind:     hidden_queue_ptr
    .group_segment_fixed_size: 0
    .kernarg_segment_align: 8
    .kernarg_segment_size: 256
    .max_flat_workgroup_size: 1024
    .name:           empty
    .private_segment_fixed_size: 0
    .sgpr_count:     0
    .sgpr_spill_count: 0
    .symbol:         empty.kd
    .uniform_work_group_size: 1
    .uses_dynamic_stack: false
    .vgpr_count:     0
    .vgpr_spill_count: 0
    .wavefront_size: 64
amdhsa.target:   amdgcn-amd-amdhsa--gfx700
amdhsa.version:
  - 1
  - 2
...

	.end_amdgpu_metadata
