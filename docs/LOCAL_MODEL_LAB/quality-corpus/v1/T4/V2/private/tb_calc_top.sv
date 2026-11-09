`timescale 1ns/1ps
module tb_calc_top;
  logic [7:0] a,b,y; logic [1:0] op; logic valid;
  calc_top dut(.a(a),.b(b),.op(op),.y(y),.valid(valid));
  task automatic check(input logic [7:0] aa,bb,input logic [1:0] oo,input logic [7:0] expected);
    begin a=aa;b=bb;op=oo;#1;if(!valid || y!==expected) $fatal(1,"mismatch op=%0d got=%h expected=%h",oo,y,expected); end
  endtask
  initial begin
    check(8'h15,8'h22,0,8'h37); check(8'hf0,8'h0f,1,8'hff);
    check(8'hcc,8'h0f,2,8'h0c); check(8'h03,8'h05,3,8'hfe);
    check(8'hff,8'h01,0,8'h00);
    $display("QUALITY_T4_PASS checks=5"); $finish;
  end
  initial begin #1000;$fatal(1,"T4 watchdog");end
endmodule
