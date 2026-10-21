// Scalar pin adapter for the real LSU. No forced internal state or timing model.
module lsu_overlap_top
  import rv32_ooo_params::*;
  import rv32_ooo_types::*;
(
  input logic clk, rst, run,
  input logic agu_valid, agu_store, agu_fp,
  input logic [11:0] agu_seq,
  input logic [5:0] agu_dst,
  input logic [31:0] agu_addr, agu_data,
  input logic [1:0] agu_size,
  input logic agu_unsigned,
  input logic retire_valid,
  input logic [11:0] retire_seq,
  input logic flush_valid,
  input logic [11:0] flush_seq,
  input logic req_ready, rsp_valid, rsp_error,
  input logic [31:0] rsp_data,
  output logic req_valid, req_write, rsp_ready, ready, retire_ack,
  output logic [31:0] req_addr, req_data,
  output logic [3:0] req_mask,
  output logic cmp_valid, cmp_result, cmp_fp, cmp_error,
  output logic [4:0] cmp_cause,
  output logic [11:0] cmp_seq,
  output logic [5:0] cmp_dst,
  output logic [31:0] cmp_data, cmp_tval,
  output logic pending_valid, pending_store,
  output logic [11:0] pending_seq,
  output logic buffer_valid, buffer_ack, external_inflight
);
  exec_req_t request;
  completion_t completion;
  dmem_pending_t pending;
  rob_tag_t retire_tag, flush_tag;
  always_comb begin
    request = '0;
    request.uop.mem.is_load = !agu_store;
    request.uop.mem.is_store = agu_store;
    request.uop.mem.is_fp = agu_fp;
    request.uop.mem.size = mem_size_e'(agu_size);
    request.uop.mem.load_ext = agu_unsigned ? LOAD_UNSIGNED : LOAD_SIGNED;
    request.uop.rob_tag = '{seq: agu_seq, idx: agu_seq[ROB_IDX_W-1:0]};
    request.uop.dst.valid = !agu_store;
    request.uop.dst.domain = agu_fp ? REG_FP : REG_INT;
    request.uop.dst.new_phys = agu_dst;
    request.operand1 = agu_data;
    retire_tag = '{seq: retire_seq, idx: retire_seq[ROB_IDX_W-1:0]};
    flush_tag = '{seq: flush_seq, idx: flush_seq[ROB_IDX_W-1:0]};
  end
  rv32_ooo_lsu dut (
    .clk(clk), .rst(rst), .core_state(run ? CORE_RUN : BRANCH_ROLLBACK),
    .dmem_pending(pending), .disp_valid(1'b0), .disp_uop('0),
    .agu_valid(agu_valid), .agu_req(request), .agu_addr(agu_addr),
    .int_cmp('0), .fp_cmp('0), .ld_cmp(completion), .lsu_ready(ready),
    .sq_retire_valid(retire_valid), .sq_retire_rob_tag(retire_tag),
    .sq_retire_ack(retire_ack), .retire_store_addr(),
    .retire_store_mask(), .retire_store_data(),
    .dmem_req_valid(req_valid), .dmem_req_addr(req_addr),
    .dmem_req_wdata(req_data), .dmem_req_byte_en(req_mask),
    .dmem_req_wen(req_write), .dmem_req_ready(req_ready),
    .dmem_rsp_valid(rsp_valid), .dmem_rsp_rdata(rsp_data),
    .dmem_rsp_error(rsp_error), .dmem_rsp_ready(rsp_ready),
    .flush_valid(flush_valid), .flush_rob_tag(flush_tag)
  );
  assign cmp_valid = completion.valid;
  assign cmp_result = completion.result_valid;
  assign cmp_fp = completion.result_domain == REG_FP;
  assign cmp_seq = completion.rob_tag.seq;
  assign cmp_dst = completion.result_phys;
  assign cmp_data = completion.result_data;
  assign cmp_error = completion.exception.valid;
  assign cmp_cause = completion.exception.cause;
  assign cmp_tval = completion.exception.tval;
  assign pending_valid = pending.valid;
  assign pending_store = pending.sq_valid;
  assign pending_seq = pending.rob_tag.seq;
  assign buffer_valid = dut.rsp_buf_valid;
  assign buffer_ack = dut.rsp_buf_ack;
  assign external_inflight = dut.in_flight_valid;
endmodule
