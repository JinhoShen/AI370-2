module sp701_host_fpga_top(
    input wire sys_clk_p,
    input wire sys_clk_n
);
  wire clk_ibuf;
  wire axi_clk;
  IBUFDS u_sysclk_ibuf(.I(sys_clk_p), .IB(sys_clk_n), .O(clk_ibuf));
  BUFG u_sysclk_bufg(.I(clk_ibuf), .O(axi_clk));

  wire [31:0] awaddr, wdata, araddr, rdata;
  wire [3:0] wstrb;
  wire awvalid, awready, wvalid, wready, bvalid, bready;
  wire [1:0] bresp, rresp;
  wire arvalid, arready, rvalid, rready;

  jtag_axi_0 u_jtag_axi (
    .aclk(axi_clk), .aresetn(1'b1),
    .m_axi_awaddr(awaddr), .m_axi_awvalid(awvalid), .m_axi_awready(awready),
    .m_axi_wdata(wdata), .m_axi_wstrb(wstrb), .m_axi_wvalid(wvalid), .m_axi_wready(wready),
    .m_axi_bresp(bresp), .m_axi_bvalid(bvalid), .m_axi_bready(bready),
    .m_axi_araddr(araddr), .m_axi_arvalid(arvalid), .m_axi_arready(arready),
    .m_axi_rdata(rdata), .m_axi_rresp(rresp), .m_axi_rvalid(rvalid), .m_axi_rready(rready)
  );

  sp701_axi_lite_transform u_registers (
    .clk(axi_clk), .resetn(1'b1),
    .s_awaddr(awaddr), .s_awvalid(awvalid), .s_awready(awready),
    .s_wdata(wdata), .s_wstrb(wstrb), .s_wvalid(wvalid), .s_wready(wready),
    .s_bresp(bresp), .s_bvalid(bvalid), .s_bready(bready),
    .s_araddr(araddr), .s_arvalid(arvalid), .s_arready(arready),
    .s_rdata(rdata), .s_rresp(rresp), .s_rvalid(rvalid), .s_rready(rready)
  );
endmodule

module sp701_axi_lite_transform(
    input wire clk, resetn,
    input wire [31:0] s_awaddr, input wire s_awvalid, output wire s_awready,
    input wire [31:0] s_wdata, input wire [3:0] s_wstrb, input wire s_wvalid, output wire s_wready,
    output reg [1:0] s_bresp, output reg s_bvalid, input wire s_bready,
    input wire [31:0] s_araddr, input wire s_arvalid, output wire s_arready,
    output reg [31:0] s_rdata, output reg [1:0] s_rresp, output reg s_rvalid, input wire s_rready
);
  reg [31:0] input_reg;
  reg [31:0] result_reg;
  reg aw_seen, w_seen;
  reg [31:0] awaddr_hold, wdata_hold;
  reg [3:0] wstrb_hold;

  assign s_awready = !aw_seen && !s_bvalid;
  assign s_wready = !w_seen && !s_bvalid;
  assign s_arready = !s_rvalid;

  always @(posedge clk) begin
    if (!resetn) begin
      input_reg <= 0; result_reg <= 0;
      aw_seen <= 0; w_seen <= 0;
      s_bvalid <= 0; s_bresp <= 0;
      s_rvalid <= 0; s_rresp <= 0; s_rdata <= 0;
      awaddr_hold <= 0; wdata_hold <= 0; wstrb_hold <= 0;
    end else begin
      if (s_awvalid && s_awready) begin aw_seen <= 1; awaddr_hold <= s_awaddr; end
      if (s_wvalid && s_wready) begin w_seen <= 1; wdata_hold <= s_wdata; wstrb_hold <= s_wstrb; end
      if (aw_seen && w_seen && !s_bvalid) begin
        if (awaddr_hold[7:0] == 8'h00) begin
          input_reg <= wdata_hold;
          result_reg <= ~wdata_hold;
          s_bresp <= 2'b00;
        end else begin
          s_bresp <= 2'b10;
        end
        aw_seen <= 0; w_seen <= 0; s_bvalid <= 1;
      end
      if (s_bvalid && s_bready) s_bvalid <= 0;
      if (s_arvalid && s_arready) begin
        if (s_araddr[7:0] == 8'h04) begin s_rdata <= result_reg; s_rresp <= 2'b00; end
        else if (s_araddr[7:0] == 8'h00) begin s_rdata <= input_reg; s_rresp <= 2'b00; end
        else begin s_rdata <= 32'hBAAD_F00D; s_rresp <= 2'b10; end
        s_rvalid <= 1;
      end
      if (s_rvalid && s_rready) s_rvalid <= 0;
    end
  end
endmodule
