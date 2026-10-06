finish_reason: length
model: qwen3.8-local

```diff
--- a/local_model_axi_lite.v
+++ b/local_model_axi_lite.v
@@ -1,5 +1,6 @@
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
+
