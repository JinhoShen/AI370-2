# Local Qwen3.8 alternate candidate: FPGA RTL change request

Read the project README and full RTL source included below. Propose one minimal source modification only; do not provide shell commands, claim validation, or invoke tools. Return a short plan and one unified diff against `projects/FPGA/Local_AI_FPGA_Engineering_Test/src/local_model_axi_lite.v`.

## Requested behavior

The AXI4-Lite register block has REG0 input at 0x00, REG1 control at 0x04, REG2 read-only result at 0x08 and REG3 configurable offset at 0x0c. Current result is bitwise NOT of input. Add mode selected by control bit 1: if bit 1 is one, return input + offset using 32-bit modulo arithmetic; if zero, preserve bitwise NOT. Preserve protocol, addresses, byte strobes, reset and errors; change no unrelated files and introduce no vendor IP.

## Prior model/tool feedback

The preferred local Qwen3.8 Q4_K_M candidate produced semantically correct conditional RTL but its hunk counts did not match its context. `git apply --check` rejected the generated patch; source remained unchanged. The exact source hunk below starts at line 107 and includes 9 old-side lines and 12 new-side lines. A valid unified diff must use those counts. This is the model's independent first attempt; emit a syntactically valid patch yourself.

## Project README

# Local Model FPGA engineering test

This is an isolated, synthesis-only sandbox for testing whether the local Qwen3.8 model can modify an existing FPGA design from a written change request and respond to Vivado tool feedback.

- No M11/M12 source, project, reports, bitstream or Golden evidence is edited.
- FPGA target for synthesis: `xc7s100fgga676-2`; no board I/O, implementation, bitstream, JTAG or programming is used.
- Baseline is a deterministic AXI4-Lite register block with input, control, result and offset registers. Original operation returns bitwise NOT of input.
- Local Model's requested change is in `docs/M13/evidence/local-model-fpga-engineering-2026-10-05/task_spec.md`.
- `src/local_model_axi_lite.v` is the original baseline until the model-produced patch is reviewed and applied.
- `sim/tb_local_model_axi_lite.sv` provides an independent functional oracle. The baseline test checks the existing mode; `TEST_NEW_MODE` enables addition/offset assertions after the Local Model patch.
- Vivado build products and generated project files belong under ignored `output/M13/Local_AI_FPGA_Engineering_Test/`.

Only Codex may run Vivado, XSim, or shell commands. The Local Model receives the spec and source as prompt text and may return analysis/unified diff; it has no tool or shell access. Maximum model correction retries: three.

## Complete original RTL source

```verilog
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

```

## Exact target context (lines 107 onward)

```verilog
          REG_CONTROL: begin
            s_axi_rdata <= control_reg;
            s_axi_rresp <= AXI_OKAY;
          end
          REG_RESULT: begin
            s_axi_rdata <= ~input_reg;
            s_axi_rresp <= AXI_OKAY;
          end
          REG_OFFSET: begin
```

Return only a short plan followed by one complete unified diff.
