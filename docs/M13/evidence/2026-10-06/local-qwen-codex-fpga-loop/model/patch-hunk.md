finish_reason: stop
model: qwen3.8-local

--- a/rtl/local_model_axi_lite.v
+++ b/rtl/local_model_axi_lite.v
@@ -1,3 +1,4 @@
 REG_RESULT: begin
-  s_axi_rdata <= ~input_reg;
+  s_axi_rdata <= (control_reg[1]) ? (input_reg + offset_reg) : (~input_reg);
   s_axi_rresp <= AXI_OKAY;
 end
