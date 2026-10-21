module adder_audit(input clk, input A, input B, input CI,
                   output FCON, output FSN, output HCON, output HSN);
FAx1_ASAP7_75t_R fa(.A(A),.B(B),.CI(CI),.CON(FCON),.SN(FSN));
HAxp5_ASAP7_75t_R ha(.A(A),.B(B),.CON(HCON),.SN(HSN));
endmodule
