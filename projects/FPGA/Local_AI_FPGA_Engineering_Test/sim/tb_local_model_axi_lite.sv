`timescale 1ns/1ps

module tb_local_model_axi_lite;
  reg aclk = 1'b0;
  reg aresetn = 1'b0;
  always #5 aclk = ~aclk;

  reg [7:0] awaddr = 0;
  reg awvalid = 0;
  wire awready;
  reg [31:0] wdata = 0;
  reg [3:0] wstrb = 4'hf;
  reg wvalid = 0;
  wire wready;
  wire [1:0] bresp;
  wire bvalid;
  reg bready = 0;
  reg [7:0] araddr = 0;
  reg arvalid = 0;
  wire arready;
  wire [31:0] rdata;
  wire [1:0] rresp;
  wire rvalid;
  reg rready = 0;

  local_model_axi_lite dut (
    .aclk(aclk), .aresetn(aresetn),
    .s_axi_awaddr(awaddr), .s_axi_awvalid(awvalid), .s_axi_awready(awready),
    .s_axi_wdata(wdata), .s_axi_wstrb(wstrb), .s_axi_wvalid(wvalid), .s_axi_wready(wready),
    .s_axi_bresp(bresp), .s_axi_bvalid(bvalid), .s_axi_bready(bready),
    .s_axi_araddr(araddr), .s_axi_arvalid(arvalid), .s_axi_arready(arready),
    .s_axi_rdata(rdata), .s_axi_rresp(rresp), .s_axi_rvalid(rvalid), .s_axi_rready(rready)
  );

  task automatic axi_write(input [7:0] address, input [31:0] value);
    begin
      @(negedge aclk);
      awaddr = address; awvalid = 1'b1;
      wdata = value; wstrb = 4'hf; wvalid = 1'b1; bready = 1'b1;
      while (!(awready && wready)) @(posedge aclk);
      @(negedge aclk);
      awvalid = 1'b0; wvalid = 1'b0;
      wait (bvalid);
      @(posedge aclk); #1;
      if (bresp !== 2'b00) $fatal(1, "write response error address=%h resp=%b", address, bresp);
      @(negedge aclk); bready = 1'b0;
    end
  endtask

  task automatic axi_read(input [7:0] address, output reg [31:0] value);
    begin
      @(negedge aclk);
      araddr = address; arvalid = 1'b1; rready = 1'b1;
      while (!arready) @(posedge aclk);
      @(negedge aclk); arvalid = 1'b0;
      wait (rvalid); #1;
      value = rdata;
      if (rresp !== 2'b00) $fatal(1, "read response error address=%h resp=%b", address, rresp);
      @(negedge aclk); rready = 1'b0;
    end
  endtask

  reg [31:0] value;
  initial begin
    repeat (3) @(posedge aclk);
    @(negedge aclk); aresetn = 1'b1;
    axi_write(8'h00, 32'h12345678);
    axi_read(8'h00, value);
    if (value !== 32'h12345678) $fatal(1, "REG0 mismatch: %h", value);
    axi_read(8'h08, value);
    if (value !== 32'hedcba987) $fatal(1, "baseline REG2 mismatch: %h", value);

    if ($test$plusargs("TEST_NEW_MODE")) begin
      axi_write(8'h0c, 32'h01020304);
      axi_write(8'h04, 32'h00000002);
      axi_read(8'h08, value);
      if (value !== 32'h1336597c) $fatal(1, "add mode mismatch: %h", value);

      axi_write(8'h04, 32'h00000000);
      axi_read(8'h08, value);
      if (value !== 32'hedcba987) $fatal(1, "legacy mode changed: %h", value);

      axi_write(8'h00, 32'hffffffff);
      axi_write(8'h0c, 32'h00000001);
      axi_write(8'h04, 32'h00000002);
      axi_read(8'h08, value);
      if (value !== 32'h00000000) $fatal(1, "32-bit wraparound mismatch: %h", value);
    end

    $display("TEST_PASS baseline_and_selected_mode=%0d", $test$plusargs("TEST_NEW_MODE"));
    $finish;
  end
endmodule
