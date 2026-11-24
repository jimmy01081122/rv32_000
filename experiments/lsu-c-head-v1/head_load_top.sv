// Drive the production ROB exclusively through its port interface.
module head_load_top
  import rv32_ooo_types::*;
(
  input logic clk, rst, alloc, load_op, fp_dest, dst_valid, store_op,
  input logic completion, preview, fault, store_ack,
  input logic [15:0] tag,
  input logic [31:0] data,
  output logic [15:0] next_tag,
  output logic ready, retiring, trapping, trace_retire, trace_trap,
  output logic trace_int, trace_fp,
  output logic [31:0] trace_data, trace_tval, trace_cause,
  output logic [63:0] event_order
);
  renamed_uop_t uop;
  completion_t load_completion;
  dmem_pending_t pending;
  commit_trace_t trace_event;
  always_comb begin
    uop = '0;
    uop.op = load_op ? (fp_dest ? UOP_FLW : UOP_LW) : (store_op ? UOP_SW : UOP_ADDI);
    uop.lq_valid = load_op;
    uop.sq_valid = store_op;
    uop.dst.valid = dst_valid;
    uop.dst.domain = fp_dest ? REG_FP : REG_INT;
    uop.dst.arch = dst_valid ? 5'd3 : '0;
    load_completion = '0;
    load_completion.valid = completion;
    load_completion.rob_tag = rob_tag_t'(tag);
    load_completion.result_data = data;
    load_completion.exception.valid = fault;
    load_completion.exception.cause = EXC_LOAD_ACCESS_FAULT;
    load_completion.exception.tval = 32'h4000_1234;
    pending = '0;
`ifndef ROOM_PARENT
    pending.buffered_load_valid = preview;
    pending.buffered_load_tag = rob_tag_t'(tag);
    pending.buffered_load_data = data;
`endif
  end
  rv32_ooo_rob rob (
    .clk(clk), .rst(rst), .core_state(), .lsu_load_bypass_room(),
    .dmem_pending(pending), .alloc_valid(alloc), .alloc_uop(uop), .alloc_ready(ready),
    .alloc_rob_tag(next_tag), .int_cmp('0), .ld_cmp(load_completion), .fp_cmp('0),
    .sq_retire_valid(), .sq_retire_rob_tag(), .sq_retire_ack(store_ack),
    .retire_store_addr('0), .retire_store_mask('0), .retire_store_data('0),
    .retire_valid(retiring), .retire_entry(), .commit_trace(trace_event),
    .retire_fp_valid(), .retire_fflags_delta(), .rollback_valid(), .rollback_rob_tag(),
    .trap_valid(trapping), .mret_valid(), .trap_pc(), .trap_cause(), .trap_tval()
  );
  assign trace_retire = trace_event.retire_valid;
  assign trace_trap = trace_event.trap_valid;
  assign trace_int = trace_event.int_dst_valid;
  assign trace_fp = trace_event.fp_dst_valid;
  assign trace_data = trace_fp ? trace_event.fp_dst_data : trace_event.int_dst_data;
  assign trace_tval = trace_event.trap_tval;
  assign trace_cause = trace_event.trap_cause;
  assign event_order = trace_event.event_order;
endmodule
