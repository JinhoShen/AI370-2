set_param general.maxThreads 24
read_verilog -sv {/home/shen/AI370-2/output/local-ui/20261016T115526-418a2f/workspace/rtl/local_model_axi_lite.v}
synth_design -top local_model_axi_lite -part xc7s100fgga676-2
create_clock -name aclk -period 10.000 [get_ports aclk]
report_utilization -file {/home/shen/AI370-2/output/local-ui/20261016T115526-418a2f/workspace/vivado-synthesis/utilization.rpt}
report_timing_summary -file {/home/shen/AI370-2/output/local-ui/20261016T115526-418a2f/workspace/vivado-synthesis/timing.rpt}
puts LOCAL_UI_VIVADO_SYNTHESIS_PASS
exit
