set source_dir [file dirname [file normalize [info script]]]
set work_dir [file normalize [file join $source_dir work hls]]
set part_name xc7s100fgga676-2

open_project -reset $work_dir
file copy -force [file join $source_dir hls_adder.cpp] [file join $work_dir hls_adder.cpp]
cd [file dirname $work_dir]
puts "M9_HLS_CWD=[pwd]"
puts "M9_HLS_SOURCE_EXISTS=[file exists [file join $work_dir hls_adder.cpp]]"
set_top m9_adder
add_files [file join $work_dir hls_adder.cpp]
open_solution -reset solution1 -flow_target vivado
set_part $part_name
create_clock -period 10
csynth_design
close_project
exit
