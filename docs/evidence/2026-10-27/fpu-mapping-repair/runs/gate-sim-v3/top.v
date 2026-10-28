module top(input clk,rst,flush,valid,ready,fault,input [2:0] state,input [400:0] req,output gr,mr,gv,mv,output [154:0] gd,md);
wire [154:0] rawmd;
gold g(.clk(clk),.rst(rst),.flush_valid(flush),.core_state(state),.issue_valid(valid),.issue_req(req),.issue_ready(gr),.cmp_valid(gv),.cmp_data(gd),.cmp_ready(ready));
gate m(.clk(clk),.rst(rst),.flush_valid(flush),.core_state(state),.issue_valid(valid),.issue_req(req),.issue_ready(mr),.cmp_valid(mv),.cmp_data(rawmd),.cmp_ready(ready));
assign md = rawmd ^ (fault ? (155'd1 << 115) : 155'd0);
endmodule
