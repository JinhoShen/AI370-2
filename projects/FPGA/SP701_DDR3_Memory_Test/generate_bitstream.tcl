set script_dir [file dirname [file normalize [info script]]]
set project_file [file join $script_dir SP701_DDR3_Memory_Test.xpr]
set evidence_dir [file normalize [file join $script_dir .. .. .. docs M11 evidence ddr3-hardware-test-2026-10-02]]
set bit_dir [file join $script_dir artifacts]
file mkdir $bit_dir
open_project $project_file
set_property part xc7s100fgga676-2 [current_project]
set_property board_part xilinx.com:sp701:part0:1.0 [current_project]
open_run impl_1
set setup_path [get_timing_paths -setup -max_paths 1]
set hold_path [get_timing_paths -hold -max_paths 1]
set wns [get_property SLACK $setup_path]
set whs [get_property SLACK $hold_path]
puts "DDR_PRE_BITSTREAM_WNS_NS=$wns"
puts "DDR_PRE_BITSTREAM_WHS_NS=$whs"
if {$wns < 0 || $whs < 0} { error "Timing safety gate failed; refusing bitstream generation" }
close_design

launch_runs impl_1 -to_step write_bitstream -jobs 6
wait_on_run impl_1
set status [get_property STATUS [get_runs impl_1]]
puts "DDR_BITSTREAM_RUN_STATUS=$status"
if {![string match "*Complete*" $status]} { error "Bitstream run failed: $status" }
set source_bit [file join $script_dir SP701_DDR3_Memory_Test.runs impl_1 SP701_DDR3_Memory_Test.bit]
set saved_bit [file join $bit_dir SP701_DDR3_Memory_Test.bit]
if {![file exists $source_bit]} { error "Expected bitstream is missing: $source_bit" }
file copy -force $source_bit $saved_bit
puts "DDR_BITSTREAM_PATH=$saved_bit"
puts "DDR_BITSTREAM_SIZE=[file size $saved_bit]"
puts "DDR_BITSTREAM_SHA256=[exec sha256sum $saved_bit]"
report_drc -file [file join $evidence_dir drc_bitstream.rpt]
close_project
exit
