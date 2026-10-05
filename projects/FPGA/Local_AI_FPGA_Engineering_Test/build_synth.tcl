set root [file normalize [file dirname [info script]]]
set out_root [file normalize [file join $root .. .. .. output M13 Local_AI_FPGA_Engineering_Test]]
file mkdir $out_root
set proj_dir [file join $out_root vivado]
create_project Local_AI_FPGA_Engineering_Test $proj_dir -part xc7s100fgga676-2 -force
add_files -norecurse [file join $root src local_model_axi_lite.v]
set_property top local_model_axi_lite [current_fileset]
read_xdc [file join $root constraints synth_clock.xdc]
update_compile_order -fileset sources_1
synth_design -top local_model_axi_lite -part xc7s100fgga676-2
report_utilization -file [file join $out_root utilization.rpt]
report_timing_summary -file [file join $out_root timing-summary.rpt]
puts "LOCAL_MODEL_FPGA_SYNTHESIS=PASS"
puts "LOCAL_MODEL_FPGA_PROJECT=$proj_dir/Local_AI_FPGA_Engineering_Test.xpr"
close_project
