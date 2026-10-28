module check(input clk, rst, a, b, output reg q); always @(posedge clk) q <= (a & b) & ~rst; endmodule
