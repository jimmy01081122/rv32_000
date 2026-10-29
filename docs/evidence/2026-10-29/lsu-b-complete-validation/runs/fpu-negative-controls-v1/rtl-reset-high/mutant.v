module rv32_ooo_fp_execute (
	clk,
	rst,
	flush_valid,
	core_state,
	issue_valid,
	issue_req,
	issue_ready,
	cmp_valid,
	cmp_data,
	cmp_ready
);
	reg _sv2v_0;
	input wire clk;
	input wire rst;
	input wire flush_valid;
	input wire [2:0] core_state;
	input wire issue_valid;
	localparam integer rv32_ooo_params_FETCH_EPOCH_W = 4;
	localparam integer rv32_ooo_params_LQ_IDX_W = 4;
	localparam integer rv32_ooo_params_LSQ_GEN_W = 4;
	localparam integer rv32_ooo_params_ARCH_REG_W = 5;
	localparam integer rv32_ooo_params_PHYS_W = 6;
	localparam integer rv32_ooo_params_ROB_IDX_W = 4;
	localparam integer rv32_ooo_params_ROB_SEQ_WIDTH = 12;
	localparam integer rv32_ooo_params_SQ_IDX_W = 4;
	input wire [(((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? (((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 40 : 1 - ((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39)) + 95:0] issue_req;
	output wire issue_ready;
	output wire cmp_valid;
	output wire [(((((((1 + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 3) + rv32_ooo_params_PHYS_W) + 112) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) - 1:0] cmp_data;
	input wire cmp_ready;
	wire [31:0] op0 = issue_req[95-:32];
	wire [31:0] op1 = issue_req[63-:32];
	wire [31:0] op2 = issue_req[31-:32];
	wire [2:0] rm = issue_req[(((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? ((((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? (((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 40 : 1 - ((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39)) + 95) - (((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) - ((7 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))) - 2)) : (96 + (2 - (7 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))) + 2)-:3];
	localparam [31:0] CANONICAL_NAN = 32'h7fc00000;
	function automatic is_nan;
		input reg [31:0] f;
		is_nan = (f[30:23] == 8'hff) && (f[22:0] != 23'd0);
	endfunction
	function automatic is_snan;
		input reg [31:0] f;
		is_snan = ((f[30:23] == 8'hff) && (f[22] == 1'b0)) && (f[21:0] != 22'd0);
	endfunction
	function automatic is_qnan;
		input reg [31:0] f;
		is_qnan = (f[30:23] == 8'hff) && (f[22] == 1'b1);
	endfunction
	function automatic is_inf;
		input reg [31:0] f;
		is_inf = (f[30:23] == 8'hff) && (f[22:0] == 23'd0);
	endfunction
	function automatic is_zero;
		input reg [31:0] f;
		is_zero = f[30:0] == 31'd0;
	endfunction
	function automatic is_subnormal;
		input reg [31:0] f;
		is_subnormal = (f[30:23] == 8'd0) && (f[22:0] != 23'd0);
	endfunction
	function automatic signed [31:0] msb_index_32;
		input reg [31:0] val;
		reg signed [31:0] res;
		begin
			res = 0;
			begin : sv2v_autoblock_1
				reg signed [31:0] i;
				for (i = 0; i < 32; i = i + 1)
					if (val[i])
						res = i;
			end
			msb_index_32 = res;
		end
	endfunction
	function automatic signed [31:0] sv2v_cast_32_signed;
		input reg signed [31:0] inp;
		sv2v_cast_32_signed = inp;
	endfunction
	task automatic unpack_f32;
		input reg [31:0] f;
		output reg s;
		output reg signed [31:0] e;
		output reg [23:0] m;
		begin
			s = f[31];
			if (f[30:23] == 8'd0) begin
				e = -126;
				m = {1'b0, f[22:0]};
			end
			else begin
				e = sv2v_cast_32_signed(f[30:23]) - 127;
				m = {1'b1, f[22:0]};
			end
		end
	endtask
	function automatic signed [7:0] sv2v_cast_8_signed;
		input reg signed [7:0] inp;
		sv2v_cast_8_signed = inp;
	endfunction
	task automatic round_and_pack;
		input reg sign;
		input reg signed [31:0] exp;
		input reg [47:0] mantissa;
		input reg [2:0] rmode;
		output reg [31:0] out_f;
		output reg [4:0] flags;
		reg signed [31:0] norm_exp;
		reg [47:0] norm_mant;
		reg guard;
		reg round_bit;
		reg sticky;
		reg round_up;
		reg [24:0] significand;
		reg signed [31:0] final_exp;
		reg [5:0] msb_pos;
		reg signed [31:0] shift_amt;
		reg signed [31:0] max_lshift;
		reg [47:0] sticky_mask;
		begin
			flags = 1'sb0;
			norm_exp = exp;
			norm_mant = mantissa;
			sticky = 1'b0;
			guard = 1'b0;
			round_bit = 1'b0;
			round_up = 1'b0;
			significand = 1'sb0;
			final_exp = 0;
			out_f = 1'sb0;
			msb_pos = 1'sb0;
			shift_amt = 0;
			max_lshift = 0;
			sticky_mask = 1'sb0;
			if (norm_mant == 48'd0)
				out_f = {sign, 31'd0};
			else begin
				if (norm_mant[47])
					msb_pos = 6'd47;
				else if (norm_mant[46])
					msb_pos = 6'd46;
				else if (norm_mant[45])
					msb_pos = 6'd45;
				else if (norm_mant[44])
					msb_pos = 6'd44;
				else if (norm_mant[43])
					msb_pos = 6'd43;
				else if (norm_mant[42])
					msb_pos = 6'd42;
				else if (norm_mant[41])
					msb_pos = 6'd41;
				else if (norm_mant[40])
					msb_pos = 6'd40;
				else if (norm_mant[39])
					msb_pos = 6'd39;
				else if (norm_mant[38])
					msb_pos = 6'd38;
				else if (norm_mant[37])
					msb_pos = 6'd37;
				else if (norm_mant[36])
					msb_pos = 6'd36;
				else if (norm_mant[35])
					msb_pos = 6'd35;
				else if (norm_mant[34])
					msb_pos = 6'd34;
				else if (norm_mant[33])
					msb_pos = 6'd33;
				else if (norm_mant[32])
					msb_pos = 6'd32;
				else if (norm_mant[31])
					msb_pos = 6'd31;
				else if (norm_mant[30])
					msb_pos = 6'd30;
				else if (norm_mant[29])
					msb_pos = 6'd29;
				else if (norm_mant[28])
					msb_pos = 6'd28;
				else if (norm_mant[27])
					msb_pos = 6'd27;
				else if (norm_mant[26])
					msb_pos = 6'd26;
				else if (norm_mant[25])
					msb_pos = 6'd25;
				else if (norm_mant[24])
					msb_pos = 6'd24;
				else if (norm_mant[23])
					msb_pos = 6'd23;
				else if (norm_mant[22])
					msb_pos = 6'd22;
				else if (norm_mant[21])
					msb_pos = 6'd21;
				else if (norm_mant[20])
					msb_pos = 6'd20;
				else if (norm_mant[19])
					msb_pos = 6'd19;
				else if (norm_mant[18])
					msb_pos = 6'd18;
				else if (norm_mant[17])
					msb_pos = 6'd17;
				else if (norm_mant[16])
					msb_pos = 6'd16;
				else if (norm_mant[15])
					msb_pos = 6'd15;
				else if (norm_mant[14])
					msb_pos = 6'd14;
				else if (norm_mant[13])
					msb_pos = 6'd13;
				else if (norm_mant[12])
					msb_pos = 6'd12;
				else if (norm_mant[11])
					msb_pos = 6'd11;
				else if (norm_mant[10])
					msb_pos = 6'd10;
				else if (norm_mant[9])
					msb_pos = 6'd9;
				else if (norm_mant[8])
					msb_pos = 6'd8;
				else if (norm_mant[7])
					msb_pos = 6'd7;
				else if (norm_mant[6])
					msb_pos = 6'd6;
				else if (norm_mant[5])
					msb_pos = 6'd5;
				else if (norm_mant[4])
					msb_pos = 6'd4;
				else if (norm_mant[3])
					msb_pos = 6'd3;
				else if (norm_mant[2])
					msb_pos = 6'd2;
				else if (norm_mant[1])
					msb_pos = 6'd1;
				else
					msb_pos = 6'd0;
				shift_amt = sv2v_cast_32_signed(msb_pos) - 26;
				if (shift_amt > 0) begin
					sticky_mask = (shift_amt >= 48 ? {48 {1'sb1}} : (48'd1 << shift_amt) - 48'd1);
					sticky = |(norm_mant & sticky_mask);
					norm_mant = (shift_amt >= 48 ? {48 {1'sb0}} : norm_mant >> shift_amt);
					norm_exp = norm_exp + shift_amt;
				end
				if (shift_amt < 0) begin
					max_lshift = norm_exp + 126;
					if (max_lshift <= 0) begin : sv2v_autoblock_2
						reg signed [31:0] sub_rshift;
						sub_rshift = -(norm_exp + 126);
						sticky_mask = (sub_rshift >= 48 ? {48 {1'sb1}} : (48'd1 << sub_rshift) - 48'd1);
						sticky = |(norm_mant & sticky_mask);
						norm_mant = (sub_rshift >= 48 ? {48 {1'sb0}} : norm_mant >> sub_rshift);
						norm_exp = -126;
					end
					else begin : sv2v_autoblock_3
						reg signed [31:0] lshift;
						lshift = (-shift_amt < max_lshift ? -shift_amt : max_lshift);
						norm_mant = norm_mant << lshift;
						norm_exp = norm_exp - lshift;
					end
				end
				guard = norm_mant[2];
				round_bit = norm_mant[1];
				sticky = sticky | norm_mant[0];
				round_up = 1'b0;
				case (rmode)
					3'b000: round_up = guard && ((round_bit || sticky) || norm_mant[3]);
					3'b001: round_up = 1'b0;
					3'b010: round_up = sign && ((guard || round_bit) || sticky);
					3'b011: round_up = !sign && ((guard || round_bit) || sticky);
					3'b100: round_up = guard;
					default: round_up = guard && ((round_bit || sticky) || norm_mant[3]);
				endcase
				if ((guard || round_bit) || sticky)
					flags[0] = 1'b1;
				significand = {1'b0, norm_mant[26:3]} + (round_up ? 25'd1 : 25'd0);
				final_exp = norm_exp;
				if (significand[24]) begin
					significand = {1'b0, significand[24:1]};
					final_exp = final_exp + 1;
				end
				if (final_exp >= 128) begin
					flags[2] = 1'b1;
					flags[0] = 1'b1;
					case (rmode)
						3'b000, 3'b100: out_f = {sign, 31'h7f800000};
						3'b001: out_f = {sign, 31'h7f7fffff};
						3'b010: out_f = (sign ? 32'hff800000 : 32'h7f7fffff);
						3'b011: out_f = (sign ? 32'hff7fffff : 32'h7f800000);
						default: out_f = {sign, 31'h7f800000};
					endcase
				end
				else if (final_exp < -126) begin
					flags[1] = 1'b1;
					flags[0] = 1'b1;
					out_f = {sign, 31'd0};
				end
				else if ((final_exp == -126) && !significand[23]) begin
					out_f = {sign, 8'd0, significand[22:0]};
					flags[1] = flags[0];
				end
				else
					out_f = {sign, sv2v_cast_8_signed(final_exp + 127), significand[22:0]};
			end
		end
	endtask
	reg [31:0] res_data;
	reg [1:0] res_domain;
	reg [4:0] res_flags;
	function automatic [47:0] sv2v_cast_48;
		input reg [47:0] inp;
		sv2v_cast_48 = inp;
	endfunction
	function automatic [71:0] sv2v_cast_72;
		input reg [71:0] inp;
		sv2v_cast_72 = inp;
	endfunction
	always @(*) begin
		if (_sv2v_0)
			;
		res_data = 32'd0;
		res_domain = 2'b10;
		res_flags = 1'sb0;
		case (issue_req[(((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? ((((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? (((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 40 : 1 - ((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39)) + 95) - (((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) : ((96 - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) >= (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) ? ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) - (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40)))))))))) + 1 : ((4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + 1)) - 1)-:((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) >= (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) ? ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) - (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40)))))))))) + 1 : ((4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + 1)])
			8'd73: begin : blk_fcvt_w
				reg s0;
				reg signed [31:0] e0;
				reg [23:0] m0;
				reg signed [31:0] int_val;
				reg round_up;
				s0 = 1'b0;
				e0 = 0;
				m0 = 1'sb0;
				int_val = 0;
				round_up = 1'b0;
				res_domain = 2'b01;
				if (is_nan(op0)) begin
					res_flags[4] = 1'b1;
					res_data = 32'h7fffffff;
				end
				else if (is_inf(op0)) begin
					res_flags[4] = 1'b1;
					res_data = (op0[31] ? 32'h80000000 : 32'h7fffffff);
				end
				else begin
					unpack_f32(op0, s0, e0, m0);
					if (e0 < -1) begin
						res_flags[0] = |op0[30:0];
						res_data = (((rm == 3'b010) && s0) && |op0[30:0] ? -32'd1 : (((rm == 3'b011) && !s0) && |op0[30:0] ? 32'd1 : 32'd0));
					end
					else if (e0 > 30) begin
						if (((e0 == 31) && s0) && (m0[22:0] == 23'd0))
							res_data = 32'h80000000;
						else begin
							res_flags[4] = 1'b1;
							res_data = (s0 ? 32'h80000000 : 32'h7fffffff);
						end
					end
					else begin
						if (e0 >= 23)
							int_val = sv2v_cast_32_signed(m0[23:0]) << (e0 - 23);
						else begin : sv2v_autoblock_4
							reg signed [31:0] shift;
							reg [23:0] mask;
							reg [23:0] shifted_m0;
							reg guard;
							reg sticky;
							shift = 23 - e0;
							mask = (shift > 1 ? (24'd1 << (shift - 1)) - 24'd1 : 24'd0);
							shifted_m0 = m0 >> (shift - 1);
							guard = shifted_m0[0];
							sticky = |(m0 & mask);
							int_val = sv2v_cast_32_signed(m0[23:0]) >> shift;
							round_up = 1'b0;
							case (rm)
								3'b000: round_up = guard && (sticky || int_val[0]);
								3'b001: round_up = 1'b0;
								3'b010: round_up = s0 && (guard || sticky);
								3'b011: round_up = !s0 && (guard || sticky);
								3'b100: round_up = guard;
								default: round_up = guard && (sticky || int_val[0]);
							endcase
							if (guard || sticky)
								res_flags[0] = 1'b1;
							if (round_up)
								int_val = int_val + 1;
						end
						res_data = (s0 ? -int_val : int_val);
					end
				end
			end
			8'd74: begin : blk_fcvt_wu
				reg s0;
				reg signed [31:0] e0;
				reg [23:0] m0;
				reg signed [31:0] uint_val;
				reg round_up;
				s0 = 1'b0;
				e0 = 0;
				m0 = 1'sb0;
				uint_val = 0;
				round_up = 1'b0;
				res_domain = 2'b01;
				if (is_nan(op0) || (op0[31] && !is_zero(op0))) begin
					res_flags[4] = 1'b1;
					res_data = (is_nan(op0) ? 32'hffffffff : 32'd0);
				end
				else if (is_inf(op0)) begin
					res_flags[4] = 1'b1;
					res_data = 32'hffffffff;
				end
				else begin
					unpack_f32(op0, s0, e0, m0);
					if (e0 < 0) begin
						res_flags[0] = |op0[30:0];
						res_data = (((rm == 3'b011) && !s0) && |op0[30:0] ? 32'd1 : 32'd0);
					end
					else if (e0 >= 32) begin
						res_flags[4] = 1'b1;
						res_data = 32'hffffffff;
					end
					else begin
						if (e0 >= 23)
							uint_val = sv2v_cast_32_signed(m0[23:0]) << (e0 - 23);
						else begin : sv2v_autoblock_5
							reg signed [31:0] shift;
							reg [23:0] mask;
							reg [23:0] shifted_m0;
							reg guard;
							reg sticky;
							shift = 23 - e0;
							mask = (shift > 1 ? (24'd1 << (shift - 1)) - 24'd1 : 24'd0);
							shifted_m0 = m0 >> (shift - 1);
							guard = shifted_m0[0];
							sticky = |(m0 & mask);
							uint_val = sv2v_cast_32_signed(m0[23:0]) >> shift;
							round_up = 1'b0;
							case (rm)
								3'b000: round_up = guard && (sticky || uint_val[0]);
								3'b001: round_up = 1'b0;
								3'b010: round_up = 1'b0;
								3'b011: round_up = guard || sticky;
								3'b100: round_up = guard;
								default: round_up = guard && (sticky || uint_val[0]);
							endcase
							if (guard || sticky)
								res_flags[0] = 1'b1;
							if (round_up)
								uint_val = uint_val + 1;
						end
						res_data = uint_val;
					end
				end
			end
			8'd80: begin : blk_fcvt_sw
				reg sign;
				reg [31:0] uval;
				reg signed [31:0] lz;
				reg [47:0] mant;
				sign = 1'b0;
				uval = 1'sb0;
				lz = 0;
				mant = 1'sb0;
				res_domain = 2'b10;
				if (op0 == 32'd0)
					res_data = 32'd0;
				else begin
					sign = op0[31];
					uval = (sign ? -sv2v_cast_32_signed(op0) : op0);
					lz = msb_index_32(uval);
					if (lz >= 26) begin : sv2v_autoblock_6
						reg signed [31:0] rshift;
						reg [31:0] rmask;
						rshift = lz - 26;
						rmask = (rshift > 0 ? (32'd1 << rshift) - 32'd1 : 32'd0);
						mant = {16'd0, uval >> rshift} | {47'd0, |(uval & rmask)};
					end
					else
						mant = {16'd0, uval} << (26 - lz);
					round_and_pack(sign, lz, mant, rm, res_data, res_flags);
				end
			end
			8'd81: begin : blk_fcvt_swu
				reg signed [31:0] lz;
				reg [47:0] mant;
				lz = 0;
				mant = 1'sb0;
				res_domain = 2'b10;
				if (op0 == 32'd0)
					res_data = 32'd0;
				else begin
					lz = msb_index_32(op0);
					if (lz >= 26) begin : sv2v_autoblock_7
						reg signed [31:0] rshift;
						reg [31:0] rmask;
						rshift = lz - 26;
						rmask = (rshift > 0 ? (32'd1 << rshift) - 32'd1 : 32'd0);
						mant = {16'd0, op0 >> rshift} | {47'd0, |(op0 & rmask)};
					end
					else
						mant = {16'd0, op0} << (26 - lz);
					round_and_pack(1'b0, lz, mant, rm, res_data, res_flags);
				end
			end
			8'd63, 8'd64: begin : blk_fadd
				reg [31:0] effective_op1;
				reg s0;
				reg s1;
				reg signed [31:0] e0;
				reg signed [31:0] e1;
				reg [23:0] m0;
				reg [23:0] m1;
				reg signed [31:0] exp_diff;
				reg [47:0] mant0;
				reg [47:0] mant1;
				reg signed [31:0] base_exp;
				reg [47:0] sum_mant;
				reg res_sign;
				effective_op1 = 1'sb0;
				s0 = 1'sb0;
				s1 = 1'sb0;
				e0 = 0;
				e1 = 0;
				m0 = 1'sb0;
				m1 = 1'sb0;
				exp_diff = 0;
				mant0 = 1'sb0;
				mant1 = 1'sb0;
				base_exp = 0;
				sum_mant = 1'sb0;
				res_sign = 1'b0;
				res_domain = 2'b10;
				effective_op1 = (issue_req[(((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? ((((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? (((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 40 : 1 - ((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39)) + 95) - (((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) : ((96 - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) >= (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) ? ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) - (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40)))))))))) + 1 : ((4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + 1)) - 1)-:((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) >= (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) ? ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) - (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40)))))))))) + 1 : ((4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + 1)] == 8'd64 ? {~op1[31], op1[30:0]} : op1);
				if (is_snan(op0) || is_snan(effective_op1)) begin
					res_flags[4] = 1'b1;
					res_data = CANONICAL_NAN;
				end
				else if (is_nan(op0) || is_nan(effective_op1))
					res_data = CANONICAL_NAN;
				else if (is_inf(op0) && is_inf(effective_op1)) begin
					if (op0[31] != effective_op1[31]) begin
						res_flags[4] = 1'b1;
						res_data = CANONICAL_NAN;
					end
					else
						res_data = op0;
				end
				else if (is_inf(op0))
					res_data = op0;
				else if (is_inf(effective_op1))
					res_data = effective_op1;
				else if (is_zero(op0) && is_zero(effective_op1)) begin
					res_sign = (op0[31] == effective_op1[31] ? op0[31] : rm == 3'b010);
					res_data = {res_sign, 31'd0};
				end
				else begin
					unpack_f32(op0, s0, e0, m0);
					unpack_f32(effective_op1, s1, e1, m1);
					exp_diff = e0 - e1;
					mant0 = {21'd0, m0[23:0], 3'd0};
					mant1 = {21'd0, m1[23:0], 3'd0};
					if (exp_diff >= 0) begin
						base_exp = e0;
						if (exp_diff > 47)
							mant1 = {47'd0, |mant1};
						else if (exp_diff > 0) begin : sv2v_autoblock_8
							reg [47:0] mask1;
							mask1 = (48'd1 << exp_diff) - 48'd1;
							mant1 = (mant1 >> exp_diff) | {47'd0, |(mant1 & mask1)};
						end
					end
					else begin : sv2v_autoblock_9
						reg signed [31:0] neg_diff;
						neg_diff = -exp_diff;
						base_exp = e1;
						if (neg_diff > 47)
							mant0 = {47'd0, |mant0};
						else if (neg_diff > 0) begin : sv2v_autoblock_10
							reg [47:0] mask0;
							mask0 = (48'd1 << neg_diff) - 48'd1;
							mant0 = (mant0 >> neg_diff) | {47'd0, |(mant0 & mask0)};
						end
					end
					if (s0 == s1) begin
						res_sign = s0;
						sum_mant = mant0 + mant1;
					end
					else if (mant0 >= mant1) begin
						res_sign = s0;
						sum_mant = mant0 - mant1;
					end
					else begin
						res_sign = s1;
						sum_mant = mant1 - mant0;
					end
					if (sum_mant == 48'd0)
						res_data = {rm == 3'b010, 31'd0};
					else
						round_and_pack(res_sign, base_exp, sum_mant, rm, res_data, res_flags);
				end
			end
			8'd65: begin : blk_fmul
				reg sign_mul;
				reg s0;
				reg s1;
				reg signed [31:0] e0;
				reg signed [31:0] e1;
				reg [23:0] m0;
				reg [23:0] m1;
				reg [47:0] prod;
				reg [47:0] prod_mant;
				reg signed [31:0] prod_exp;
				sign_mul = 1'b0;
				s0 = 1'sb0;
				s1 = 1'sb0;
				e0 = 0;
				e1 = 0;
				m0 = 1'sb0;
				m1 = 1'sb0;
				prod = 1'sb0;
				prod_mant = 1'sb0;
				prod_exp = 0;
				res_domain = 2'b10;
				sign_mul = op0[31] ^ op1[31];
				if (is_snan(op0) || is_snan(op1)) begin
					res_flags[4] = 1'b1;
					res_data = CANONICAL_NAN;
				end
				else if (is_nan(op0) || is_nan(op1))
					res_data = CANONICAL_NAN;
				else if ((is_inf(op0) && is_zero(op1)) || (is_zero(op0) && is_inf(op1))) begin
					res_flags[4] = 1'b1;
					res_data = CANONICAL_NAN;
				end
				else if (is_inf(op0) || is_inf(op1))
					res_data = {sign_mul, 31'h7f800000};
				else if (is_zero(op0) || is_zero(op1))
					res_data = {sign_mul, 31'd0};
				else begin
					unpack_f32(op0, s0, e0, m0);
					unpack_f32(op1, s1, e1, m1);
					prod = sv2v_cast_48(m0[23:0]) * sv2v_cast_48(m1[23:0]);
					prod_mant = {20'd0, prod[47:20]} | {47'd0, |prod[19:0]};
					prod_exp = e0 + e1;
					round_and_pack(sign_mul, prod_exp, prod_mant, rm, res_data, res_flags);
				end
			end
			8'd59, 8'd60, 8'd61, 8'd62: begin : blk_fma
				reg negate_prod;
				reg negate_c;
				reg [31:0] c_val;
				reg sign_prod;
				reg s0;
				reg s1;
				reg sc;
				reg signed [31:0] e0;
				reg signed [31:0] e1;
				reg signed [31:0] ec;
				reg [23:0] m0;
				reg [23:0] m1;
				reg [23:0] mc;
				reg [47:0] prod;
				reg signed [31:0] ep;
				reg signed [31:0] exp_diff;
				reg [71:0] fma_prod;
				reg [71:0] fma_c;
				reg [71:0] sum;
				reg [47:0] fma_mant;
				reg [71:0] fma_sticky_mask;
				reg signed [31:0] fma_msb;
				reg signed [31:0] fma_shift;
				reg signed [31:0] base_exp;
				reg sign_final;
				negate_prod = 1'b0;
				negate_c = 1'b0;
				c_val = 1'sb0;
				sign_prod = 1'b0;
				s0 = 1'sb0;
				s1 = 1'sb0;
				sc = 1'sb0;
				e0 = 0;
				e1 = 0;
				ec = 0;
				m0 = 1'sb0;
				m1 = 1'sb0;
				mc = 1'sb0;
				prod = 1'sb0;
				ep = 0;
				exp_diff = 0;
				fma_prod = 1'sb0;
				fma_c = 1'sb0;
				sum = 1'sb0;
				fma_mant = 1'sb0;
				base_exp = 0;
				sign_final = 1'b0;
				fma_sticky_mask = 1'sb0;
				fma_msb = 0;
				fma_shift = 0;
				res_domain = 2'b10;
				negate_prod = (issue_req[(((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? ((((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? (((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 40 : 1 - ((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39)) + 95) - (((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) : ((96 - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) >= (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) ? ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) - (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40)))))))))) + 1 : ((4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + 1)) - 1)-:((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) >= (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) ? ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) - (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40)))))))))) + 1 : ((4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + 1)] == 8'd61) || (issue_req[(((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? ((((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? (((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 40 : 1 - ((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39)) + 95) - (((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) : ((96 - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) >= (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) ? ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) - (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40)))))))))) + 1 : ((4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + 1)) - 1)-:((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) >= (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) ? ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) - (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40)))))))))) + 1 : ((4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + 1)] == 8'd62);
				negate_c = (issue_req[(((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? ((((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? (((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 40 : 1 - ((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39)) + 95) - (((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) : ((96 - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) >= (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) ? ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) - (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40)))))))))) + 1 : ((4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + 1)) - 1)-:((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) >= (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) ? ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) - (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40)))))))))) + 1 : ((4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + 1)] == 8'd60) || (issue_req[(((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? ((((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? (((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 40 : 1 - ((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39)) + 95) - (((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) : ((96 - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) >= (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) ? ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) - (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40)))))))))) + 1 : ((4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + 1)) - 1)-:((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) >= (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) ? ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))) - (4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40)))))))))) + 1 : ((4 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) + 1)] == 8'd62);
				c_val = op2;
				if (negate_c)
					c_val[31] = ~c_val[31];
				sign_prod = (op0[31] ^ op1[31]) ^ negate_prod;
				if ((is_snan(op0) || is_snan(op1)) || is_snan(c_val)) begin
					res_flags[4] = 1'b1;
					res_data = CANONICAL_NAN;
				end
				else if ((is_nan(op0) || is_nan(op1)) || is_nan(c_val))
					res_data = CANONICAL_NAN;
				else if ((is_inf(op0) && is_zero(op1)) || (is_zero(op0) && is_inf(op1))) begin
					res_flags[4] = 1'b1;
					res_data = CANONICAL_NAN;
				end
				else if (is_inf(op0) || is_inf(op1)) begin
					if (is_inf(c_val) && (sign_prod != c_val[31])) begin
						res_flags[4] = 1'b1;
						res_data = CANONICAL_NAN;
					end
					else
						res_data = {sign_prod, 31'h7f800000};
				end
				else if (is_inf(c_val))
					res_data = c_val;
				else begin
					unpack_f32(op0, s0, e0, m0);
					unpack_f32(op1, s1, e1, m1);
					unpack_f32(c_val, sc, ec, mc);
					prod = sv2v_cast_48(m0[23:0]) * sv2v_cast_48(m1[23:0]);
					ep = e0 + e1;
					exp_diff = ep - ec;
					fma_prod = {1'b0, prod, 23'd0};
					fma_c = {2'd0, mc[23:0], 46'd0};
					if (exp_diff >= 0) begin
						base_exp = ep;
						if (exp_diff >= 72)
							fma_c = {71'd0, |fma_c};
						else if (exp_diff != 0) begin
							fma_sticky_mask = (72'd1 << exp_diff) - 1;
							fma_c = (fma_c >> exp_diff) | {71'd0, |(fma_c & fma_sticky_mask)};
						end
					end
					else begin
						base_exp = ec;
						if (-exp_diff >= 72)
							fma_prod = {71'd0, |fma_prod};
						else begin
							fma_sticky_mask = (72'd1 << -exp_diff) - 1;
							fma_prod = (fma_prod >> -exp_diff) | {71'd0, |(fma_prod & fma_sticky_mask)};
						end
					end
					if (sign_prod == sc) begin
						sign_final = sign_prod;
						sum = fma_prod + fma_c;
					end
					else if (fma_prod >= fma_c) begin
						sign_final = sign_prod;
						sum = fma_prod - fma_c;
					end
					else begin
						sign_final = sc;
						sum = fma_c - fma_prod;
					end
					if (sum == 72'd0)
						res_data = {(((prod == 0) && (mc == 0)) && (sign_prod == sc) ? sign_prod : rm == 3'b010), 31'd0};
					else begin
						begin : sv2v_autoblock_11
							reg signed [31:0] bit_index;
							for (bit_index = 0; bit_index < 72; bit_index = bit_index + 1)
								if (sum[bit_index])
									fma_msb = bit_index;
						end
						base_exp = (base_exp + fma_msb) - 69;
						if (fma_msb > 26) begin
							fma_shift = fma_msb - 26;
							fma_sticky_mask = (72'd1 << fma_shift) - 1;
							fma_mant = sv2v_cast_48(sum >> fma_shift) | {47'd0, |(sum & fma_sticky_mask)};
						end
						else
							fma_mant = sv2v_cast_48(sum << (26 - fma_msb));
						if (base_exp < -126) begin
							fma_shift = -(126 + base_exp);
							if (fma_shift >= 48)
								fma_mant = {47'd0, |fma_mant};
							else begin
								fma_sticky_mask = (72'd1 << fma_shift) - 1;
								fma_mant = (fma_mant >> fma_shift) | {47'd0, |(sv2v_cast_72(fma_mant) & fma_sticky_mask)};
							end
							base_exp = -126;
						end
						round_and_pack(sign_final, base_exp, fma_mant, rm, res_data, res_flags);
					end
				end
			end
			default: begin
				res_data = 32'd0;
				res_domain = 2'b10;
			end
		endcase
	end
	reg [(((((((1 + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 3) + rv32_ooo_params_PHYS_W) + 112) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) - 1:0] comb_cmp;
	always @(*) begin
		if (_sv2v_0)
			;
		comb_cmp = 1'sb0;
		if (issue_valid) begin
			comb_cmp[1 + ((rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W) + (3 + (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))))))] = 1'b1;
			comb_cmp[(rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W) + (3 + (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))))-:(((rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W) + (3 + (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))))) >= (3 + (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))))) ? (((rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W) + (3 + (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))))) - (3 + (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))))))) + 1 : ((3 + (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))))) - ((rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W) + (3 + (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))))))) + 1)] = issue_req[(((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? ((((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? (((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 40 : 1 - ((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39)) + 95) - (((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) - ((rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W) + (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))))) : ((96 - ((rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W) + (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))))) + (((rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W) + (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) >= (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) ? (((rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W) + (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40)))))))))) + 1 : ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) - ((rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W) + (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))))) + 1)) - 1)-:(((rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W) + (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) >= (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) ? (((rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W) + (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))))) - (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40)))))))))) + 1 : ((12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 40))))))))) - ((rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W) + (12 + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0)) + ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))))))) + 1)];
			comb_cmp[3 + (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))))] = issue_req[(((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? ((((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? (((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 40 : 1 - ((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39)) + 95) - (((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) - (((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))) - (((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) - 1) - (3 + (rv32_ooo_params_ARCH_REG_W + (rv32_ooo_params_PHYS_W + (rv32_ooo_params_PHYS_W - 1))))))) : 96 + ((((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) - 1) - (3 + (rv32_ooo_params_ARCH_REG_W + (rv32_ooo_params_PHYS_W + (rv32_ooo_params_PHYS_W - 1))))) - ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39)))))))];
			comb_cmp[2 + (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))))-:((2 + (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))))) >= (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))))) ? ((2 + (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))))) - (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))))) + 1 : ((rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))))) - (2 + (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))))) + 1)] = res_domain;
			comb_cmp[rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))-:((rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))) >= (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))) ? ((rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))) - (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))))) + 1 : ((112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))) - (rv32_ooo_params_PHYS_W + (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))))) + 1)] = issue_req[(((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? ((((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? (((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 40 : 1 - ((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39)) + 95) - (((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) - (((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))) - (((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) - 1) - (rv32_ooo_params_PHYS_W + (rv32_ooo_params_PHYS_W - 1))))) : ((96 + ((((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) - 1) - (rv32_ooo_params_PHYS_W + (rv32_ooo_params_PHYS_W - 1))) - ((((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W) + (69 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 39))))))) + ((rv32_ooo_params_PHYS_W + (rv32_ooo_params_PHYS_W - 1)) >= (rv32_ooo_params_PHYS_W + 0) ? ((rv32_ooo_params_PHYS_W + (rv32_ooo_params_PHYS_W - 1)) - (rv32_ooo_params_PHYS_W + 0)) + 1 : ((rv32_ooo_params_PHYS_W + 0) - (rv32_ooo_params_PHYS_W + (rv32_ooo_params_PHYS_W - 1))) + 1)) - 1)-:((rv32_ooo_params_PHYS_W + (rv32_ooo_params_PHYS_W - 1)) >= (rv32_ooo_params_PHYS_W + 0) ? ((rv32_ooo_params_PHYS_W + (rv32_ooo_params_PHYS_W - 1)) - (rv32_ooo_params_PHYS_W + 0)) + 1 : ((rv32_ooo_params_PHYS_W + 0) - (rv32_ooo_params_PHYS_W + (rv32_ooo_params_PHYS_W - 1))) + 1)];
			comb_cmp[112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))-:((112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))) >= (80 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))) ? ((112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))) - (80 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))))) + 1 : ((80 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))) - (112 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))) + 1)] = res_data;
			comb_cmp[42 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))] = 1'b1;
			comb_cmp[41 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))-:((41 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))) >= (36 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))) ? ((41 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))) - (36 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))))) + 1 : ((36 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))) - (41 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))) + 1)] = res_flags;
			comb_cmp[80 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))-:((80 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))) >= (42 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))) ? ((80 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))) - (42 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0))))) + 1 : ((42 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + (1 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))) - (80 + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W) + ((rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W) + 0)))) + 1)] = issue_req[(((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? ((((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39) >= 0 ? (((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 40 : 1 - ((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 39)) + 95) - ((((((((((((64 + ((rv32_ooo_params_FETCH_EPOCH_W + 32) >= 0 ? rv32_ooo_params_FETCH_EPOCH_W + 33 : 1 - (rv32_ooo_params_FETCH_EPOCH_W + 32))) + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 12) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_PHYS_W) + 0) >= 0 ? (3 + rv32_ooo_params_PHYS_W) + 1 : 1 - ((3 + rv32_ooo_params_PHYS_W) + 0))) + (((3 + rv32_ooo_params_ARCH_REG_W) + rv32_ooo_params_PHYS_W) + rv32_ooo_params_PHYS_W)) + 69) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) + 2) : 96)-:38];
		end
	end
	reg holding_valid;
	reg [(((((((1 + (rv32_ooo_params_ROB_SEQ_WIDTH + rv32_ooo_params_ROB_IDX_W)) + 3) + rv32_ooo_params_PHYS_W) + 112) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_LQ_IDX_W)) + 1) + (rv32_ooo_params_LSQ_GEN_W + rv32_ooo_params_SQ_IDX_W)) - 1:0] holding_data;
	wire can_accept = !holding_valid || cmp_ready;
	assign issue_ready = can_accept;
	always @(posedge clk)
		if (rst || flush_valid) begin
			holding_valid <= 1'b1;
			holding_data <= 1'sb0;
		end
		else if (can_accept) begin
			holding_valid <= issue_valid;
			if (issue_valid)
				holding_data <= comb_cmp;
			else
				holding_data <= 1'sb0;
		end
	assign cmp_valid = holding_valid;
	assign cmp_data = holding_data;
	initial _sv2v_0 = 0;
endmodule
