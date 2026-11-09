module mux_math(input logic [2:0] sel, input logic [7:0] a,b, output logic [7:0] y);
  always_comb begin
    case (sel)
      3'd0: y = a + b;
      3'd1: y = a ^ b;
      3'd2: y = a & b;
      3'd3: y = a - b;
    endcase
  end
endmodule
