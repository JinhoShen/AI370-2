set expected_target "127.0.0.1:3121/xilinx_tcf/Xilinx/46602010028A"
set expected_idcode "00000011011111000111000010010011"
set bit_file [file normalize [file join [file dirname [info script]] vivado SP701_Host_FPGA_JTAG_AXI.runs impl_1 sp701_host_fpga_top.bit]]
set probes_file [file normalize [file join [file dirname [info script]] vivado SP701_Host_FPGA_JTAG_AXI.runs impl_1 sp701_host_fpga_top.ltx]]
if {![file exists $bit_file] || ![file exists $probes_file]} {error "Bitstream/probes file absent"}
puts "M12_BITSTREAM=$bit_file"
puts "M12_PROBES=$probes_file"
open_hw_manager
connect_hw_server -url TCP:127.0.0.1:3121
refresh_hw_server
set targets [get_hw_targets]
puts "M12_TARGETS=$targets"
if {[lsearch -exact $targets $expected_target] < 0} {error "Expected SP701 target missing; refuse programming"}
open_hw_target $expected_target
set devices [get_hw_devices]
if {[llength $devices] != 1} {error "Expected exactly one FPGA"}
set device [lindex $devices 0]
current_hw_device $device
refresh_hw_device $device
set part [get_property PART $device]
set idcode [get_property IDCODE $device]
puts "M12_PREPROGRAM_PART=$part"
puts "M12_PREPROGRAM_IDCODE=$idcode"
if {$part ne "xc7s100" || $idcode ne $expected_idcode} {error "Unexpected FPGA identity; refuse programming"}
set_property PROGRAM.FILE $bit_file $device
set_property PROBES.FILE $probes_file $device
puts "M12_PROGRAM_START=[clock seconds]"
program_hw_devices $device
refresh_hw_device -update_hw_probes true $device
puts "M12_PROGRAM_RESULT=PASS"
set axi_cores [get_hw_axis -of_objects $device]
puts "M12_JTAG_AXI_CORES=$axi_cores"
if {[llength $axi_cores] != 1} {error "Expected one detected JTAG-to-AXI core"}
set axi [lindex $axi_cores 0]
set inputs {0x12345678 0x00000000 0xffffffff 0xa5a5f00d}
set expecteds {0xedcba987 0xffffffff 0x00000000 0x5a5a0ff2}
set index 0
foreach input $inputs expected $expecteds {
  set wr_name m12_write_$index
  set rd_name m12_read_$index
  create_hw_axi_txn $wr_name $axi -type write -address 0x00000000 -data $input -force
  run_hw_axi [get_hw_axi_txns $wr_name]
  puts "M12_WRITE_$index=[report_hw_axi_txn $wr_name -w 32]"
  create_hw_axi_txn $rd_name $axi -type read -address 0x00000004 -force
  run_hw_axi [get_hw_axi_txns $rd_name]
  set report [report_hw_axi_txn $rd_name -w 32]
  puts "M12_READ_$index=$report"
  if {![regexp -nocase [string range $expected 2 end] $report]} {error "Readback mismatch at vector $index, expected $expected"}
  incr index
}
refresh_hw_server
if {[lsearch -exact [get_hw_targets] $expected_target] < 0} {error "SP701 JTAG target vanished after transactions"}
refresh_hw_device -update_hw_probes true $device
puts "M12_POSTTEST_DEVICE=[get_hw_devices]"
puts "M12_POSTTEST_IDCODE=[get_property IDCODE $device]"
puts "M12_AXI_LOOPBACK_TRANSFORM=PASS"
puts "M12_POSTTEST_JTAG=PASS"
close_hw_target
close_hw_manager
exit
