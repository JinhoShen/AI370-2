`timescale 1ns/1ps
module tb_axi_regs;
  localparam logic [31:0] R0 = 32'h10203040;
  localparam logic [31:0] R1 = 32'hA5A55A5A;
  localparam logic [31:0] R2 = 32'h0BADF00D;
  localparam logic [31:0] R3 = 32'h55AA33CC;
  logic aclk=0, aresetn=0;
  logic [7:0] awaddr=0, araddr=0;
  logic awvalid=0, wvalid=0, bready=0, arvalid=0, rready=0;
  logic [31:0] wdata=0;
  logic [3:0] wstrb=0;
  wire awready, wready, bvalid, arready, rvalid;
  wire [1:0] bresp, rresp;
  wire [31:0] rdata;
  integer checks=0;
  always #5 aclk=~aclk;
  axi_regs dut(.aclk, .aresetn, .s_axi_awaddr(awaddr), .s_axi_awvalid(awvalid),
    .s_axi_awready(awready), .s_axi_wdata(wdata), .s_axi_wstrb(wstrb),
    .s_axi_wvalid(wvalid), .s_axi_wready(wready), .s_axi_bresp(bresp),
    .s_axi_bvalid(bvalid), .s_axi_bready(bready), .s_axi_araddr(araddr),
    .s_axi_arvalid(arvalid), .s_axi_arready(arready), .s_axi_rdata(rdata),
    .s_axi_rresp(rresp), .s_axi_rvalid(rvalid), .s_axi_rready(rready));

  task automatic check_read(input logic [7:0] addr, input logic [31:0] exp_data,
                            input logic [1:0] exp_resp);
    begin
      @(negedge aclk); araddr=addr; arvalid=1; rready=0;
      do @(posedge aclk); while (!arready);
      @(negedge aclk); arvalid=0;
      wait(rvalid===1'b1);
      repeat (2) begin
        @(posedge aclk);
        if (!rvalid || rdata!==exp_data || rresp!==exp_resp)
          $fatal(1,"R response changed or mismatch addr=%h data=%h resp=%b",addr,rdata,rresp);
        checks=checks+1;
      end
      @(negedge aclk); rready=1;
      @(posedge aclk);
      @(negedge aclk); rready=0;
    end
  endtask

  task automatic finish_write(input logic [1:0] exp_resp);
    begin
      wait(bvalid===1'b1);
      repeat (2) begin
        @(posedge aclk);
        if (!bvalid || bresp!==exp_resp)
          $fatal(1,"B response changed or mismatch resp=%b",bresp);
        checks=checks+1;
      end
      @(negedge aclk); bready=1;
      @(posedge aclk);
      @(negedge aclk); bready=0;
    end
  endtask

  task automatic write_aw_first(input logic [7:0] addr, input logic [31:0] data,
                                 input logic [3:0] strb, input logic [1:0] resp);
    begin
      @(negedge aclk); awaddr=addr; awvalid=1;
      do @(posedge aclk); while (!awready);
      @(negedge aclk); awvalid=0;
      repeat (2) @(posedge aclk);
      @(negedge aclk); wdata=data; wstrb=strb; wvalid=1;
      do @(posedge aclk); while (!wready);
      @(negedge aclk); wvalid=0;
      finish_write(resp);
    end
  endtask

  task automatic write_w_first(input logic [7:0] addr, input logic [31:0] data,
                                input logic [3:0] strb, input logic [1:0] resp);
    begin
      @(negedge aclk); wdata=data; wstrb=strb; wvalid=1;
      do @(posedge aclk); while (!wready);
      @(negedge aclk); wvalid=0;
      repeat (2) @(posedge aclk);
      @(negedge aclk); awaddr=addr; awvalid=1;
      do @(posedge aclk); while (!awready);
      @(negedge aclk); awvalid=0;
      finish_write(resp);
    end
  endtask

  task automatic write_together(input logic [7:0] addr, input logic [31:0] data,
                                 input logic [3:0] strb, input logic [1:0] resp);
    begin
      @(negedge aclk); awaddr=addr; awvalid=1; wdata=data; wstrb=strb; wvalid=1;
      do @(posedge aclk); while (!(awready && wready));
      @(negedge aclk); awvalid=0; wvalid=0;
      finish_write(resp);
    end
  endtask

  initial begin
    repeat (3) @(posedge aclk);
    @(negedge aclk); aresetn=1;
    check_read(8'h00,R0,2'b00); check_read(8'h04,R1,2'b00);
    check_read(8'h08,R2,2'b00); check_read(8'h0c,R3,2'b00);
    write_aw_first(8'h00,32'h12345678,4'hf,2'b00);
    check_read(8'h00,32'h12345678,2'b00);
    write_w_first(8'h04,32'hA1B2C3D4,4'hf,2'b00);
    check_read(8'h04,32'hA1B2C3D4,2'b00);
    write_together(8'h08,32'hFFEEDDCC,4'hf,2'b00);
    check_read(8'h08,32'hFFEEDDCC,2'b00);
    write_together(8'h00,32'hAA00CC00,4'b0101,2'b00);
    check_read(8'h00,32'h12005600,2'b00);
    write_aw_first(8'h10,32'h12345678,4'hf,2'b10);
    write_w_first(8'h03,32'h12345678,4'hf,2'b10);
    check_read(8'h10,32'h00000000,2'b10);
    check_read(8'h03,32'h00000000,2'b10);
    if (checks < 32) $fatal(1,"scenario coverage incomplete checks=%0d",checks);
    $display("QUALITY_T3_SCENARIO_reset_PASS");
    $display("QUALITY_T3_SCENARIO_aw_before_w_PASS");
    $display("QUALITY_T3_SCENARIO_w_before_aw_PASS");
    $display("QUALITY_T3_SCENARIO_simultaneous_PASS");
    $display("QUALITY_T3_SCENARIO_wstrb_PASS");
    $display("QUALITY_T3_SCENARIO_unmapped_PASS");
    $display("QUALITY_T3_SCENARIO_b_backpressure_PASS");
    $display("QUALITY_T3_SCENARIO_r_backpressure_PASS");
    $display("QUALITY_T3_SCENARIO_consecutive_PASS");
    $display("QUALITY_T3_PASS checks=%0d",checks);
    $finish;
  end
  initial begin #200000; $fatal(1,"T3 simulation watchdog"); end
endmodule
