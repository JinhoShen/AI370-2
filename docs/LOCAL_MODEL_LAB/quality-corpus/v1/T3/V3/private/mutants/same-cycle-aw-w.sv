module axi_regs (
  input  logic        aclk,
  input  logic        aresetn,
  input  logic [7:0]  s_axi_awaddr,
  input  logic        s_axi_awvalid,
  output logic        s_axi_awready,
  input  logic [31:0] s_axi_wdata,
  input  logic [3:0]  s_axi_wstrb,
  input  logic        s_axi_wvalid,
  output logic        s_axi_wready,
  output logic [1:0]  s_axi_bresp,
  output logic        s_axi_bvalid,
  input  logic        s_axi_bready,
  input  logic [7:0]  s_axi_araddr,
  input  logic        s_axi_arvalid,
  output logic        s_axi_arready,
  output logic [31:0] s_axi_rdata,
  output logic [1:0]  s_axi_rresp,
  output logic        s_axi_rvalid,
  input  logic        s_axi_rready
);
  logic [31:0] regs [0:3];
  logic aw_pending, w_pending;
  logic [7:0] aw_hold;
  logic [31:0] wd_hold;
  logic [3:0] ws_hold;
  logic aw_hs, w_hs;
  logic [7:0] selected_aw;
  logic [31:0] selected_wd;
  logic [3:0] selected_ws;
  logic selected_aw_valid, selected_w_valid;
  logic [1:0] write_resp;
  integer b;
  assign s_axi_awready = aresetn && !aw_pending && !s_axi_bvalid && s_axi_wvalid;
  assign s_axi_wready = aresetn && !w_pending && !s_axi_bvalid;
  assign s_axi_arready = aresetn && !s_axi_rvalid;
  always_comb begin
    selected_aw = aw_pending ? aw_hold : s_axi_awaddr;
    selected_wd = w_pending ? wd_hold : s_axi_wdata;
    selected_ws = w_pending ? ws_hold : s_axi_wstrb;
    selected_aw_valid = aw_pending || (s_axi_awvalid && s_axi_awready);
    selected_w_valid = w_pending || (s_axi_wvalid && s_axi_wready);
    aw_hs = s_axi_awvalid && s_axi_awready;
    w_hs = s_axi_wvalid && s_axi_wready;
    write_resp = (selected_aw[1:0] == 0 && selected_aw[7:4] == 0) ? 2'b00 : 2'b10;
  end
  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      regs[0] <= 32'h89ABCDEF;
      regs[1] <= 32'h76543210;
      regs[2] <= 32'hDEADBEEF;
      regs[3] <= 32'h01020304;
      aw_pending <= 0; w_pending <= 0; aw_hold <= 0; wd_hold <= 0; ws_hold <= 0;
      s_axi_bvalid <= 0; s_axi_bresp <= 0; s_axi_rvalid <= 0; s_axi_rresp <= 0; s_axi_rdata <= 0;
    end else begin
      if (s_axi_bvalid && s_axi_bready) s_axi_bvalid <= 0;
      if (aw_hs) begin aw_hold <= s_axi_awaddr; aw_pending <= 1; end
      if (w_hs) begin wd_hold <= s_axi_wdata; ws_hold <= s_axi_wstrb; w_pending <= 1; end
      if (selected_aw_valid && selected_w_valid && !s_axi_bvalid) begin
        aw_pending <= 0; w_pending <= 0; s_axi_bvalid <= 1; s_axi_bresp <= write_resp;
        if (write_resp == 0) begin
          case (selected_aw[3:2])
            0: for (b=0;b<4;b=b+1) if (selected_ws[b]) regs[0][8*b +: 8] <= selected_wd[8*b +: 8];
            1: for (b=0;b<4;b=b+1) if (selected_ws[b]) regs[1][8*b +: 8] <= selected_wd[8*b +: 8];
            2: for (b=0;b<4;b=b+1) if (selected_ws[b]) regs[2][8*b +: 8] <= selected_wd[8*b +: 8];
            3: for (b=0;b<4;b=b+1) if (selected_ws[b]) regs[3][8*b +: 8] <= selected_wd[8*b +: 8];
          endcase
        end
      end
      if (s_axi_rvalid && s_axi_rready) s_axi_rvalid <= 0;
      if (s_axi_arvalid && s_axi_arready) begin
        s_axi_rvalid <= 1; s_axi_rresp <= 2'b00; s_axi_rdata <= 0;
        if (s_axi_araddr[1:0] != 0 || s_axi_araddr[7:4] != 0) s_axi_rresp <= 2'b10;
        else case (s_axi_araddr[3:2])
          0: s_axi_rdata <= regs[0]; 1: s_axi_rdata <= regs[1];
          2: s_axi_rdata <= regs[2]; 3: s_axi_rdata <= regs[3];
        endcase
      end
    end
  end
endmodule
