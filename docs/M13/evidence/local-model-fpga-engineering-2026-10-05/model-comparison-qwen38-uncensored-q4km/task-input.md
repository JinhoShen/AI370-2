You are editing a small existing FPGA RTL project. Read the complete project contract and RTL below. Return a short plan (at most 4 bullets) followed by exactly one unified diff patch. Do not include shell commands. Do not alter AXI protocol, register addresses, reset behavior, write strobes, response behavior, or unrelated logic. Do not use markdown fences.

Change request: Add an operation mode controlled by REG1 bit[1]. When bit[1] is 1, REG2 must read REG0 + REG3 using 32-bit unsigned wraparound. When bit[1] is 0, preserve the existing REG2 result exactly. REG0 is input at address 0x00, REG1 control at 0x04, REG2 result at 0x08, REG3 configurable offset at 0x0c. Existing design returns bitwise complement of REG0 through REG2. The new mode must be combinationally selected from the stored control and offset registers and remain AXI4-Lite compliant.

The project testbench will check: REG0 write/read; legacy result with mode disabled; input 0x12345678 + offset 0x01020304 = 0x1336597c in mode 1; mode 0 restores legacy result 0xedcba987; and 0xffffffff + 1 wraps to zero. The patch must apply to the exact source below. Use a valid unified diff with correct hunk counts and filename `local_model_axi_lite.v`.

COMPLETE SOURCE:
module local_model_axi_lite (
    input  wire        aclk,
    input  wire        aresetn,
    input  wire [7:0]  s_axi_awaddr,
    input  wire        s_axi_awvalid,
    output wire        s_axi_awready,
    input  wire [31:0] s_axi_wdata,
    input  wire [3:0]  s_axi_wstrb,
    input  wire        s_axi_wvalid,
    output wire        s_axi_wready,
    output reg  [1:0]  s_axi_bresp,
    output reg         s_axi_bvalid,
    input  wire        s_axi_bready,
    input  wire [7:0]  s_axi_araddr,
    input  wire        s_axi_arvalid,
    output wire        s_axi_arready,
    output reg  [31:0] s_axi_rdata,
    output reg  [1:0]  s_axi_rresp,
    output reg         s_axi_rvalid,
    input  wire        s_axi_rready
);
  localparam [1:0] AXI_OKAY   = 2'b00;
  localparam [1:0] AXI_SLVERR = 2'b10;

  localparam [7:0] REG_INPUT   = 8'h00;
  localparam [7:0] REG_CONTROL = 8'h04;
  localparam [7:0] REG_RESULT  = 8'h08;
  localparam [7:0] REG_OFFSET  = 8'h0c;

  reg [31:0] input_reg;
  reg [31:0] control_reg;
  reg [31:0] offset_reg;

  reg aw_pending;
  reg w_pending;
  reg [7:0]  awaddr_hold;
  reg [31:0] wdata_hold;
  reg [3:0]  wstrb_hold;
  integer byte_index;

  assign s_axi_awready = !aw_pending && !s_axi_bvalid;
  assign s_axi_wready  = !w_pending && !s_axi_bvalid;
  assign s_axi_arready = !s_axi_rvalid;

  always @(posedge aclk) begin
    if (!aresetn) begin
      input_reg    <= 32'h00000000;
      control_reg  <= 32'h00000000;
      offset_reg   <= 32'h00000000;
      aw_pending   <= 1'b0;
      w_pending    <= 1'b0;
      awaddr_hold  <= 8'h00;
      wdata_hold   <= 32'h00000000;
      wstrb_hold   <= 4'h0;
      s_axi_bresp  <= AXI_OKAY;
      s_axi_bvalid <= 1'b0;
      s_axi_rdata  <= 32'h00000000;
      s_axi_rresp  <= AXI_OKAY;
      s_axi_rvalid <= 1'b0;
    end else begin
      if (s_axi_awvalid && s_axi_awready) begin
        aw_pending  <= 1'b1;
        awaddr_hold <= s_axi_awaddr;
      end
      if (s_axi_wvalid && s_axi_wready) begin
        w_pending  <= 1'b1;
        wdata_hold <= s_axi_wdata;
        wstrb_hold <= s_axi_wstrb;
      end

      if (aw_pending && w_pending && !s_axi_bvalid) begin
        case (awaddr_hold)
          REG_INPUT: begin
            for (byte_index = 0; byte_index < 4; byte_index = byte_index + 1)
              if (wstrb_hold[byte_index])
                input_reg[byte_index*8 +: 8] <= wdata_hold[byte_index*8 +: 8];
            s_axi_bresp <= AXI_OKAY;
          end
          REG_CONTROL: begin
            for (byte_index = 0; byte_index < 4; byte_index = byte_index + 1)
              if (wstrb_hold[byte_index])
                control_reg[byte_index*8 +: 8] <= wdata_hold[byte_index*8 +: 8];
            s_axi_bresp <= AXI_OKAY;
          end
          REG_OFFSET: begin
            for (byte_index = 0; byte_index < 4; byte_index = byte_index + 1)
              if (wstrb_hold[byte_index])
                offset_reg[byte_index*8 +: 8] <= wdata_hold[byte_index*8 +: 8];
            s_axi_bresp <= AXI_OKAY;
          end
          default: s_axi_bresp <= AXI_SLVERR;
        endcase
        aw_pending   <= 1'b0;
        w_pending    <= 1'b0;
        s_axi_bvalid <= 1'b1;
      end

      if (s_axi_bvalid && s_axi_bready)
        s_axi_bvalid <= 1'b0;

      if (s_axi_arvalid && s_axi_arready) begin
        case (s_axi_araddr)
          REG_INPUT: begin
            s_axi_rdata <= input_reg;
            s_axi_rresp <= AXI_OKAY;
          end
          REG_CONTROL: begin
            s_axi_rdata <= control_reg;
            s_axi_rresp <= AXI_OKAY;
          end
          REG_RESULT: begin
            s_axi_rdata <= ~input_reg;
            s_axi_rresp <= AXI_OKAY;
          end
          REG_OFFSET: begin
            s_axi_rdata <= offset_reg;
            s_axi_rresp <= AXI_OKAY;
          end
          default: begin
            s_axi_rdata <= 32'hbaad_f00d;
            s_axi_rresp <= AXI_SLVERR;
          end
        endcase
        s_axi_rvalid <= 1'b1;
      end

      if (s_axi_rvalid && s_axi_rready)
        s_axi_rvalid <= 1'b0;
    end
  end
endmodule
