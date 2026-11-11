module mux_math(input logic [2:0] sel, input logic [7:0] a,b, output logic [7:0] y);
  always_comb begin
    case (sel)
      0:y=a+b; 1:y=a^b; 2:y=a&b; 3:y=a-b; default:y=8'h00;
    endcase
  end
endmodule
