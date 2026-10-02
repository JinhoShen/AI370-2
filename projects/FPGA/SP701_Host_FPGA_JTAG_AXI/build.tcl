set here [file normalize [file dirname [info script]]]
set proj_dir [file join $here vivado]
create_project SP701_Host_FPGA_JTAG_AXI $proj_dir -part xc7s100fgga676-2 -force
set_property board_part xilinx.com:sp701:part0:1.0 [current_project]
create_ip -name jtag_axi -vendor xilinx.com -library ip -version 1.2 -module_name jtag_axi_0
set_property -dict [list CONFIG.M_AXI_ADDR_WIDTH {32} CONFIG.M_AXI_DATA_WIDTH {32} CONFIG.PROTOCOL {2}] [get_ips jtag_axi_0]
generate_target all [get_ips jtag_axi_0]
add_files -norecurse [file join $here src sp701_host_fpga_top.v]
add_files -fileset constrs_1 -norecurse [file join $here constraints sp701_sysclk.xdc]
set_property top sp701_host_fpga_top [current_fileset]
update_compile_order -fileset sources_1
update_compile_order -fileset sim_1
set_property strategy {Vivado Implementation Defaults} [get_runs impl_1]
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
set run_status [get_property STATUS [get_runs impl_1]]
puts "M12_IMPL_STATUS=$run_status"
if {![string match "*Complete!*" $run_status]} {error "Implementation/bitstream did not complete: $run_status"}
open_run impl_1
report_drc -file [file join $here build-drc.rpt]
report_timing_summary -file [file join $here build-timing.rpt]
report_utilization -file [file join $here build-utilization.rpt]
puts "M12_BITSTREAM=[file join $proj_dir SP701_Host_FPGA_JTAG_AXI.runs impl_1 SP701_Host_FPGA_JTAG_AXI.bit]"
close_project
