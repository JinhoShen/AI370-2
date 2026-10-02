// Thin board wrapper around AMD's MIG 7-series example_top.
// DDR controller, traffic generator, patterns and MIG timing/pin settings are
// retained from the official generated example. This wrapper only provides
// the SP701 active-high reset polarity and captures test telemetry.
module SP701_DDR3_Memory_Test (
    inout  [15:0] ddr3_dq,
    inout  [1:0]  ddr3_dqs_n,
    inout  [1:0]  ddr3_dqs_p,
    output [14:0] ddr3_addr,
    output [2:0]  ddr3_ba,
    output        ddr3_ras_n,
    output        ddr3_cas_n,
    output        ddr3_we_n,
    output        ddr3_reset_n,
    output        ddr3_ck_p,
    output        ddr3_ck_n,
    output        ddr3_cke,
    output [1:0]  ddr3_dm,
    output        ddr3_odt,
    input         sys_clk_p,
    input         sys_clk_n,
    input         RESET
);
  wire calib_done;
  wire compare_error;
  wire ui_clk;
  wire test_complete;
  wire write_complete;
  wire read_complete;
  wire write_status_valid;
  wire read_status_valid;
  reg [31:0] write_status_count = 32'd0;
  reg [31:0] read_status_count = 32'd0;

  // SP701 board definition: RESET is active high. MIG config is active low.
  example_top #(
      .BEGIN_ADDRESS(32'h00000000),
      .END_ADDRESS(32'h00ffffff)
  ) u_example_top (
      .ddr3_dq(ddr3_dq),
      .ddr3_dqs_n(ddr3_dqs_n),
      .ddr3_dqs_p(ddr3_dqs_p),
      .ddr3_addr(ddr3_addr),
      .ddr3_ba(ddr3_ba),
      .ddr3_ras_n(ddr3_ras_n),
      .ddr3_cas_n(ddr3_cas_n),
      .ddr3_we_n(ddr3_we_n),
      .ddr3_reset_n(ddr3_reset_n),
      .ddr3_ck_p(ddr3_ck_p),
      .ddr3_ck_n(ddr3_ck_n),
      .ddr3_cke(ddr3_cke),
      .ddr3_dm(ddr3_dm),
      .ddr3_odt(ddr3_odt),
      .sys_clk_p(sys_clk_p),
      .sys_clk_n(sys_clk_n),
      .sys_rst(~RESET),
      .tg_compare_error(compare_error),
      .init_calib_complete(calib_done),
      .debug_clk(ui_clk),
      .test_cmptd(test_complete),
      .write_cmptd(write_complete),
      .read_cmptd(read_complete),
      .dbg_wr_sts_vld(write_status_valid),
      .dbg_rd_sts_vld(read_status_valid)
  );

  // Count completed AXI status records in MIG's UI clock domain. This is a
  // telemetry counter only; the official sticky compare/error signal remains
  // the authority for data integrity. No MIG/XDC parameters are changed.
  always @(posedge ui_clk) begin
    if (RESET) begin
      write_status_count <= 32'd0;
      read_status_count <= 32'd0;
    end else begin
      if (write_status_valid && write_status_count != 32'hffffffff)
        write_status_count <= write_status_count + 1'b1;
      if (read_status_valid && read_status_count != 32'hffffffff)
        read_status_count <= read_status_count + 1'b1;
    end
  end

  ila_0 u_ila (
      .clk(ui_clk),
      .probe0(calib_done),
      .probe1(compare_error),
      .probe2(write_status_count),
      .probe3(read_status_count),
      .probe4(test_complete),
      .probe5(write_complete),
      .probe6(read_complete)
  );
endmodule
