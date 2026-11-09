module mux_math(input logic [2:0] sel, input logic [7:0] a,b, output logic [7:0] y);
  always_comb begin
    casez (sel)
      3'b0??: y = a + b;
      3'b100: y = a ^ b;
      3'b101: y = a & b;
      3'b110: y = a - b;
    endcase
  end
endmodule
