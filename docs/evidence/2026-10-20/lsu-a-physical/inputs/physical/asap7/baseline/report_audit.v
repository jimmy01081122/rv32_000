// Small sequential fixture for report qualification, never a CPU score.
module report_audit(input clk, input A, input B, input CI,
                    output FCON, output HCON, output HSN, output Q);
wire sum, stage;
FAx1_ASAP7_75t_R fa(.A(A),.B(B),.CI(CI),.CON(FCON),.SN(sum));
HAxp5_ASAP7_75t_R ha(.A(stage),.B(B),.CON(HCON),.SN(HSN));
DFFHQNx1_ASAP7_75t_R ff0(.CLK(clk),.D(sum),.QN(stage));
DFFHQNx1_ASAP7_75t_R ff1(.CLK(clk),.D(stage),.QN(Q));
endmodule
