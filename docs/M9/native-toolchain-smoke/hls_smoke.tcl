set source_dir [file dirname [file normalize [info script]]]
set work_dir [file normalize [file join $source_dir work hls]]
set part_name xc7a35ticsg324-1L

open_project -reset $work_dir
set_top m9_adder
add_files [file join $source_dir hls_adder.cpp]
open_solution -reset solution1 -flow_target vivado
set_part $part_name
create_clock -period 10
csynth_design
close_project
exit
