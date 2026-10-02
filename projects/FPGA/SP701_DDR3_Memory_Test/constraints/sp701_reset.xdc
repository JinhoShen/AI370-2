# Only non-DDR top-level reset connection. Values copied from the installed
# Vivado 2026.1 SP701 board definition: part0_pins.xml pin 29, RESET, AE15,
# LVCMOS18; board.xml reset interface specifies active-high polarity.
# Configuration bank 0 is VCCO_3V3 per AMD SP701 UG1319, Table 7.
set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property IOSTANDARD LVCMOS18 [get_ports RESET]
set_property PACKAGE_PIN AE15 [get_ports RESET]
