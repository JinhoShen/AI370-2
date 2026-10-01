set part_name xc7s100fgga676-2
set source_dir [file dirname [file normalize [info script]]]
set work_dir [file normalize [file join $source_dir work vivado]]
set board_repo [file normalize [file join $::env(XILINX_VIVADO) data boards board_files]]

puts "M9_VIVADO_VERSION=[version -short]"
set_param board.repoPaths [list $board_repo]
set boards [get_board_parts -quiet *sp701*]
if {[llength $boards] == 0} {
    error "AMD/Xilinx SP701 board definition was not found in $board_repo"
}
puts "M9_BOARD_FOUND=[get_property NAME [lindex $boards 0]]"
set parts [get_parts -quiet $part_name]
if {[llength $parts] == 0} {
    error "Required smoke-test part is unavailable: $part_name"
}
puts "M9_PART_FOUND=[get_property NAME [lindex $parts 0]]"

create_project -force m9_smoke $work_dir -part $part_name
add_files [file join $source_dir adder.v]
set_property top m9_adder [current_fileset]
update_compile_order -fileset sources_1
synth_design -top m9_adder -part $part_name
report_utilization -file [file join $work_dir utilization.rpt]
puts "M9_SP701_SYNTHESIS=PASS"
close_project
exit
