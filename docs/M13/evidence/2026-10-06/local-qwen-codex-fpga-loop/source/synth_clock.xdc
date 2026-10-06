# Synthetic 100 MHz AXI clock for synthesis timing estimation only.
# This sandbox has no physical board pin constraints and is never programmed.
create_clock -name axi_clk -period 10.000 [get_ports aclk]
