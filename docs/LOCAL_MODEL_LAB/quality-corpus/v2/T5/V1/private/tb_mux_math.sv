`timescale 1ns/1ps
module tb_mux_math;
  logic [2:0] sel; logic [7:0] a,b,y; integer i; logic [7:0] expected;
  mux_math dut(.sel(sel),.a(a),.b(b),.y(y));
  initial begin
    a=8'hd3;b=8'h37;
    for(i=0;i<8;i=i+1) begin sel=i; #1; case(i)
      0:expected=8'h0a; 1:expected=8'he4; 2:expected=8'h13; 3:expected=8'h9c;
      default:expected=0;
    endcase if(y!==expected) $fatal(1,"selector %0d got %h expected %h",i,y,expected); end
    $display("QUALITY_T5_PASS checks=8");$finish;
  end
endmodule
