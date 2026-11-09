module alu(input logic [7:0] a,b, input logic [1:0] op,
  output logic [7:0] y, output logic valid);
  import alu_pkg::*;
  always_comb begin
    valid = 1'b1;
    case (opcode_t'(op))
      ADD: y = a + b; XOR_OP: y = a ^ b; AND_OP: y = a & b; SUB: y = a - b;
      default: begin y = '0; valid = 1'b0; end
    endcase
  end
endmodule
