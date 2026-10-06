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
          s_axi_rdata <= (control_reg[1]) ? (input_reg + offset_reg) : (~input_reg);
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
