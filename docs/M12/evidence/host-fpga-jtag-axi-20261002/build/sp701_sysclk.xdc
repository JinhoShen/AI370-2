# Copied verbatim from Vivado 2026.1 MIG-generated SP701 XDC in the M11
# official-preset build (see docs/M11/SP701_DDR3_Memory_Test_Report.md).
set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
create_clock -period 5.000 [get_ports sys_clk_p]
set_property IOSTANDARD LVDS_25 [get_ports sys_clk_p]
set_property PACKAGE_PIN AE8 [get_ports sys_clk_p]
set_property IOSTANDARD LVDS_25 [get_ports sys_clk_n]
set_property PACKAGE_PIN AE7 [get_ports sys_clk_n]
set_property CLOCK_DEDICATED_ROUTE BACKBONE [get_nets sys_clk_p]
