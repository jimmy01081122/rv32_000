module good(input clk, input a, input b, input s, output reg y, output reg q);
always @* if(s) y=a; else y=b;
always @(posedge clk) q<=y;
endmodule
