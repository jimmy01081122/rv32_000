module check(input clk, rst, a, b, output reg q); always @(posedge clk) if (rst) q <= 0; else q <= a ^ b; endmodule
