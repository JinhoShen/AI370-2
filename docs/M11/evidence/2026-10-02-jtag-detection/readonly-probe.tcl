open_hw_manager
connect_hw_server -url TCP:127.0.0.1:3121
refresh_hw_server
set targets {}
if {[catch {set targets [get_hw_targets]} err]} {
  puts "M11_TARGET_SCAN_ERROR=$err"
} else {
  puts "M11_HW_TARGET_COUNT=[llength $targets]"
}
foreach target $targets {
  puts "M11_HW_TARGET=$target"
  if {[catch {open_hw_target $target} err]} {
    puts "M11_OPEN_TARGET_ERROR=$err"
    continue
  }
  set devices [get_hw_devices]
  puts "M11_HW_DEVICE_COUNT=[llength $devices]"
  foreach device $devices {
    puts "M11_DEVICE_NAME=$device"
    foreach prop {PART IDCODE DNA IR_LENGTH} {
      if {[catch {set value [get_property $prop $device]} err]} {
        puts "M11_DEVICE_${prop}=UNAVAILABLE ($err)"
      } else {
        puts "M11_DEVICE_${prop}=$value"
      }
    }
  }
  close_hw_target
}
disconnect_hw_server
close_hw_manager
exit
