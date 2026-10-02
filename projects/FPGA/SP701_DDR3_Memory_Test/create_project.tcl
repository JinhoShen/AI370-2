# Reproducible SP701 MIG official example project generation.
# Run with Vivado 2026.1 batch mode from any working directory.
set script_dir [file dirname [file normalize [info script]]]
set project_root $script_dir
set staging_root [file join $project_root _staging]
set board_part_name xilinx.com:sp701:part0:1.0
set fpga_part_name xc7s100fgga676-2
set mig_input [file normalize [file join $project_root config sp701_mig.prj]]
set config_dir [file join $staging_root mig_config]
set example_dir [file join $staging_root mig_example]

if {![file exists $mig_input]} {
  error "Missing preserved SP701 MIG project: $mig_input"
}
if {![file exists [file join $project_root SP701_DDR3_Memory_Test.xpr]] ||
    ![file exists [file join $project_root src official_mig_example example_top.v]]} {
  # This exact subdirectory is reserved for disposable Vivado generator state.
  # The durable final project is saved in project_root, never removed here.
  if {[file exists $staging_root]} {
    file delete -force $staging_root
  }
  file mkdir $staging_root
  create_project -force sp701_mig_config $config_dir -part $fpga_part_name
  set_property board_part $board_part_name [current_project]
  create_ip -vendor xilinx.com -library ip -name mig_7series -version 4.2 -module_name mig_7series_0
  set mig [get_ips mig_7series_0]
  set_property CONFIG.XML_INPUT_FILE $mig_input $mig
  generate_target all $mig
  create_ip_run $mig
  launch_runs mig_7series_0_synth_1 -jobs 4
  wait_on_run mig_7series_0_synth_1
  open_example_project -force -dir $example_dir -in_process $mig
  save_project_as -force -dir $project_root SP701_DDR3_Memory_Test
} else {
  open_project [file join $project_root SP701_DDR3_Memory_Test.xpr]
}

set_property part $fpga_part_name [current_project]
set_property board_part $board_part_name [current_project]
puts "SP701_DDR_PROJECT=[current_project]"
puts "SP701_DDR_PROJECT_FILE=[get_property DIRECTORY [current_project]]/[get_property NAME [current_project]].xpr"
puts "SP701_DDR_BOARD_PART=[get_property BOARD_PART [current_project]]"
puts "SP701_DDR_FPGA_PART=[get_property PART [current_project]]"
