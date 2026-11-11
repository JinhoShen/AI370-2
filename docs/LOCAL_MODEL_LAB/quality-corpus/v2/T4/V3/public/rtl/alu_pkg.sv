package alu_pkg;
  localparam integer DATA_W = 8;
  typedef enum logic [1:0] {ADD=2'b00, XOR_OP=2'b01, AND_OP=2'b10, SUB=2'b11} opcode_t;
endpackage
