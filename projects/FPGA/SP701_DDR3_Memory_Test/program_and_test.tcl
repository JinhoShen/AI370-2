# Authorized physical test. Programs only after exact JTAG identity assertion.
set script_dir [file dirname [file normalize [info script]]]
set evidence_dir [file normalize [file join $script_dir .. .. .. docs M11 evidence ddr3-hardware-test-2026-10-02]]
set bit_file [file join $script_dir artifacts SP701_DDR3_Memory_Test.bit]
set probe_file [file join $script_dir SP701_DDR3_Memory_Test.runs impl_1 SP701_DDR3_Memory_Test.ltx]
set expected_target "127.0.0.1:3121/xilinx_tcf/Xilinx/46602010028A"
set expected_idcode "00000011011111000111000010010011"

if {![file exists $bit_file] || ![file exists $probe_file]} {
  error "Required bitstream or debug probes file is missing"
}
open_hw_manager
connect_hw_server -url TCP:127.0.0.1:3121
refresh_hw_server
set targets [get_hw_targets]
puts "DDR_PREPROGRAM_TARGET_COUNT=[llength $targets]"
puts "DDR_PREPROGRAM_TARGETS=$targets"
if {[lsearch -exact $targets $expected_target] < 0} { error "Expected SP701 JTAG target is absent; programming refused" }
open_hw_target $expected_target
set devices [get_hw_devices]
puts "DDR_PREPROGRAM_DEVICE_COUNT=[llength $devices]"
if {[llength $devices] != 1} { error "Expected exactly one FPGA on the SP701 target" }
set device [lindex $devices 0]
current_hw_device $device
refresh_hw_device $device
set part [get_property PART $device]
set idcode [get_property IDCODE $device]
puts "DDR_PREPROGRAM_DEVICE=$device"
puts "DDR_PREPROGRAM_PART=$part"
puts "DDR_PREPROGRAM_IDCODE=$idcode"
puts "DDR_PREPROGRAM_IDCODE_HEX=0x037c7093"
if {$part ne "xc7s100" || $idcode ne $expected_idcode} { error "Live FPGA identity mismatch; programming refused" }

set_property PROGRAM.FILE $bit_file $device
set_property PROBES.FILE $probe_file $device
puts "DDR_PROGRAM_START_EPOCH=[clock seconds]"
program_hw_devices $device
puts "DDR_PROGRAM_RESULT=PASS"
puts "DDR_PROGRAM_END_EPOCH=[clock seconds]"
refresh_hw_device -update_hw_probes true $device

set ilas [get_hw_ilas -of_objects $device]
puts "DDR_HW_ILA_COUNT=[llength $ilas]"
if {[llength $ilas] != 1} { error "Expected one MIG telemetry ILA after programming" }
set ila [lindex $ilas 0]
puts "DDR_HW_ILA=$ila"
puts "DDR_HW_ILA_PROBES=[get_hw_probes -of_objects $ila]"

# The official MIG generator begins traffic after calibration. Allow a bounded
# 30-second calibration/test dwell, then take an on-device ILA snapshot.
set dwell_start [clock seconds]
puts "DDR_TEST_DWELL_START_EPOCH=$dwell_start"
after 30000
set dwell_end [clock seconds]
puts "DDR_TEST_DWELL_END_EPOCH=$dwell_end"
puts "DDR_TEST_DWELL_SECONDS=[expr {$dwell_end - $dwell_start}]"
run_hw_ila -trigger_now $ila
wait_on_hw_ila $ila
set data [upload_hw_ila_data $ila]
set csv_file [file join $evidence_dir ddr-ila-data.csv]
set ila_file [file join $evidence_dir ddr-ila-data.ila]
write_hw_ila_data -force -csv_file $csv_file $data
write_hw_ila_data -force $ila_file $data
puts "DDR_ILA_CSV=$csv_file"
puts "DDR_ILA_BINARY=$ila_file"

# Post-test JTAG/device check before disconnecting.
refresh_hw_server
set post_targets [get_hw_targets]
puts "DDR_POSTTEST_TARGET_COUNT=[llength $post_targets]"
puts "DDR_POSTTEST_TARGETS=$post_targets"
if {[lsearch -exact $post_targets $expected_target] < 0} { error "SP701 target disappeared after the DDR test" }
refresh_hw_device -update_hw_probes true $device
set post_devices [get_hw_devices]
puts "DDR_POSTTEST_DEVICES=$post_devices"
if {[llength $post_devices] != 1 || [get_property IDCODE [lindex $post_devices 0]] ne $expected_idcode} {
  error "FPGA/JTAG identity did not remain accessible after DDR test"
}
puts "DDR_POSTTEST_JTAG=PASS"
close_hw_target
close_hw_manager
exit
