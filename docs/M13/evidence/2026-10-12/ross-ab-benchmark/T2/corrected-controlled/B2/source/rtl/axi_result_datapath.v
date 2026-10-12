module axi_result_datapath (
  input wire [31:0] value, input wire [31:0] control,
  input wire [31:0] offset, input wire [31:0] operand_b,
  output reg [31:0] result
);
  always @* begin
    if (control[1]) result = value ^ offset;
    else result = ~value;
  end
endmodule
