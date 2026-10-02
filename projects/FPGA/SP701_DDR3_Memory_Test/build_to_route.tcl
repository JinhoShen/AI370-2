# Run through route only. Review saved DRC/timing reports before bitstream.
set script_dir [file dirname [file normalize [info script]]]
set project_file [file join $script_dir SP701_DDR3_Memory_Test.xpr]
set evidence_dir [file normalize [file join $script_dir .. .. .. docs M11 evidence ddr3-hardware-test-2026-10-02]]
file mkdir $evidence_dir
open_project $project_file
set_property part xc7s100fgga676-2 [current_project]
set_property board_part xilinx.com:sp701:part0:1.0 [current_project]
update_compile_order -fileset sources_1
reset_run synth_1
launch_runs synth_1 -jobs 6
wait_on_run synth_1
set synth_status [get_property STATUS [get_runs synth_1]]
puts "DDR_SYNTH_STATUS=$synth_status"
if {![string match "*Complete*" $synth_status]} { error "Synthesis did not complete successfully: $synth_status" }
open_run synth_1
report_utilization -file [file join $evidence_dir utilization_synth.rpt]
report_drc -file [file join $evidence_dir drc_synth.rpt]
write_checkpoint -force [file join $evidence_dir post_synth.dcp]
close_design

reset_run impl_1
launch_runs impl_1 -to_step route_design -jobs 6
wait_on_run impl_1
set impl_status [get_property STATUS [get_runs impl_1]]
puts "DDR_IMPL_ROUTE_STATUS=$impl_status"
if {![string match "*Complete*" $impl_status]} { error "Implementation through route did not complete: $impl_status" }
open_run impl_1
report_utilization -file [file join $evidence_dir utilization_route.rpt]
report_drc -file [file join $evidence_dir drc_route.rpt]
report_timing_summary -delay_type min_max -report_unconstrained -file [file join $evidence_dir timing_route.rpt]
write_checkpoint -force [file join $evidence_dir post_route.dcp]
close_design
puts "DDR_ROUTE_REPORTS_WRITTEN=1"
close_project
exit
