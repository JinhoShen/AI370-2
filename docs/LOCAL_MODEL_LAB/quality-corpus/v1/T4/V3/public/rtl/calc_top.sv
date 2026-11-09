module calc_top(input logic [7:0] a,b, input logic [1:0] op,
  output logic [7:0] y, output logic valid);
  logic [7:0] result;
  alu u_alu(.a(a), .b(b), .op(op), .y(result), .valid_o(valid));
  assign y = result;
endmodule
