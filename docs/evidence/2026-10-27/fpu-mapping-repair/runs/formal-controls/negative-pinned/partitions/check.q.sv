module miter (
  input  [  0:0] \__pi_a ,
  input  [  0:0] \__pi_b ,
  input  [  0:0] \__pi_clk ,
  input  [  0:0] \__pi_rst ,
`ifdef DIRECT_CROSS_POINTS
`else
`endif
  output [  0:0] \__po_q__gold ,
  output [  0:0] \__po_q__gate
);
  \gold.check.q gold (
    .\__pi_a (\__pi_a ),
    .\__pi_b (\__pi_b ),
    .\__pi_clk (\__pi_clk ),
    .\__pi_rst (\__pi_rst ),
`ifdef DIRECT_CROSS_POINTS
`else
`endif
    .\__po_q (\__po_q__gold )
  );
  \gate.check.q gate (
    .\__pi_a (\__pi_a ),
    .\__pi_b (\__pi_b ),
    .\__pi_clk (\__pi_clk ),
    .\__pi_rst (\__pi_rst ),
`ifdef DIRECT_CROSS_POINTS
`else
`endif
    .\__po_q (\__po_q__gate )
  );
`ifdef ASSUME_DEFINED_INPUTS
  miter_def_prop #(1, "assume") \__pi_a__assume (\__pi_a );
  miter_def_prop #(1, "assume") \__pi_b__assume (\__pi_b );
  miter_def_prop #(1, "assume") \__pi_clk__assume (\__pi_clk );
  miter_def_prop #(1, "assume") \__pi_rst__assume (\__pi_rst );
`endif
`ifndef DIRECT_CROSS_POINTS
`endif
`ifdef CHECK_MATCH_POINTS
`endif
`ifdef CHECK_OUTPUTS
  miter_cmp_prop #(1, "assert") \__po_q__assert (\__po_q__gold , \__po_q__gate );
`endif
`ifdef COVER_DEF_CROSS_POINTS
  `ifdef DIRECT_CROSS_POINTS
  `else
  `endif
`endif
`ifdef COVER_DEF_GOLD_MATCH_POINTS
`endif
`ifdef COVER_DEF_GATE_MATCH_POINTS
`endif
`ifdef COVER_DEF_GOLD_OUTPUTS
  miter_def_prop #(1, "cover") \__po_q__gold_cover (\__po_q__gold );
`endif
`ifdef COVER_DEF_GATE_OUTPUTS
  miter_def_prop #(1, "cover") \__po_q__gate_cover (\__po_q__gate );
`endif
endmodule
module miter_cmp_prop #(parameter WIDTH=1, parameter TYPE="assert") (input [WIDTH-1:0] in_gold, in_gate);
  reg okay;
  integer i;
  always @* begin
    okay = 1;
    for (i = 0; i < WIDTH; i = i+1)
      okay = okay && (in_gold[i] === 1'bx || in_gold[i] === in_gate[i]);
  end
  generate
    if (TYPE == "assert") always @* assert(okay);
    if (TYPE == "assume") always @* assume(okay);
    if (TYPE == "cover")  always @* cover(okay);
  endgenerate
endmodule
module miter_def_prop #(parameter WIDTH=1, parameter TYPE="assert") (input [WIDTH-1:0] in);
  wire okay = ^in !== 1'bx;
  generate
    if (TYPE == "assert") always @* assert(okay);
    if (TYPE == "assume") always @* assume(okay);
    if (TYPE == "cover")  always @* cover(okay);
  endgenerate
endmodule
module \gold.check.q (
  input  [  0:0] \__pi_a ,
  input  [  0:0] \__pi_b ,
  input  [  0:0] \__pi_clk ,
  input  [  0:0] \__pi_rst ,
  output [  0:0] \__po_q
);
endmodule
module \gate.check.q (
  input  [  0:0] \__pi_a ,
  input  [  0:0] \__pi_b ,
  input  [  0:0] \__pi_clk ,
  input  [  0:0] \__pi_rst ,
  output [  0:0] \__po_q
);
endmodule
