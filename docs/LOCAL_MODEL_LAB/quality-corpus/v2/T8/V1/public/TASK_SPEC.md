# T8 Autonomous Agent: complete RTL delivery cycle

Implement the four-register AXI4-Lite slave in `rtl/axi_regs.sv` from the interface and behavioral requirements in this file. The register reset values in order are 0x10203040, 0xA5A55A5A, 0x0BADF00D, 0x55AA33CC. Support independent AW/W handshakes, one pending write, WSTRB byte updates, aligned addresses 0x00–0x0c, SLVERR for unsupported addresses, read response stability under backpressure, and reset. Only the DUT file is editable.

## Interface

Use exactly this module name and port list, including directions and widths; the fixed validator connects to the ports by name. `aclk` is the clock. `aresetn` is a synchronous, active-low reset.

```systemverilog
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
```

Work autonomously: inspect the starter RTL, run the unchanged baseline once, diagnose the fixed tool output, patch the design, rerun the fixed validator, and then give a concise delivery summary. The summary must contain separate lines in this exact form: `STATUS=PASS`, `XSim=PASS marker=<exact marker>`, `SYNTHESIS=PASS report=<exact utilization report path>`, and `RTL_SHA256=<final source SHA-256>`. Report only facts shown by the fixed validator output. The evaluator verifies all four statements against its actual trace, hashes, simulation log, and synthesis report.
