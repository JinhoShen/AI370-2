module mux_math(input logic [2:0] sel, input logic [7:0] a,b, output logic [7:0] y);
  always_comb begin
    if (sel == 0) y = a + b;
    else if (sel == 1) y = a ^ b;
    else if (sel == 2) y = a & b;
    else if (sel == 3) y = a - b;
  end
endmodule
