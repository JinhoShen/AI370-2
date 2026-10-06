set root [file normalize [file join [file dirname [info script]] ..]]
set out_dir [file normalize [file join $root build $::env(RUN_TAG)]]
read_verilog [file join $root rtl local_model_axi_lite.v]
read_xdc [file join $root constraints synth_clock.xdc]
synth_design -top local_model_axi_lite -part xc7s100fgga676-2
report_utilization -file [file join $out_dir utilization.rpt]
report_timing_summary -file [file join $out_dir timing-summary.rpt]
puts "CODEX_QWEN_VIVADO_SYNTHESIS=PASS"
close_design
