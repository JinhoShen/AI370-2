set part_name xc7s100fgga676-2
set source_dir [file normalize [file join [file dirname [file normalize [info script]]] .. .. M9 native-toolchain-smoke]]
set out_dir [file normalize [file join [pwd] output M12 pre-hardware]]
file mkdir $out_dir
set project_dir [file join $out_dir vivado]

create_project -force m12_sp701 $project_dir -part $part_name
add_files [file join $source_dir adder.v]
set_property top m9_adder [current_fileset]
update_compile_order -fileset sources_1
synth_design -top m9_adder -part $part_name
write_checkpoint -force [file join $out_dir post_synth.dcp]
report_utilization -file [file join $out_dir utilization.rpt]

opt_design
place_design
phys_opt_design
route_design
report_timing_summary -file [file join $out_dir timing_summary.rpt] -warn_on_violation
report_utilization -file [file join $out_dir utilization_implemented.rpt]
write_checkpoint -force [file join $out_dir post_route.dcp]
write_bitstream -force [file join $out_dir m12_sp701.bit]
puts "M12_SP701_IMPLEMENTATION=PASS"
puts "M12_SP701_BITSTREAM=[file join $out_dir m12_sp701.bit]"
close_project
exit
