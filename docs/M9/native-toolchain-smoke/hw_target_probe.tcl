open_hw_manager
connect_hw_server
set targets [get_hw_targets]
puts "M9_HW_TARGET_COUNT=[llength $targets]"
puts "M9_HW_TARGETS=$targets"
disconnect_hw_server
close_hw_manager
exit
