module bad(input a, input s, output reg y);
always @* if(s) y=a;
endmodule
