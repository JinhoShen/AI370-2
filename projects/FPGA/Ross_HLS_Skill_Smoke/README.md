# Ross HLS Skill smoke component

Small isolated C-synthesis target used to verify the installed Ross HLS run-flow and synth-report Skill procedures against Vitis HLS 2026.1. The function matches the deterministic transform used by the M12 FPGA register design; this is a separate C-synthesis check, not board execution or a replacement for M10 evidence.

Run from the repository root after sourcing Vitis 2026.1:

```bash
vitis-run --mode hls --csim --config projects/FPGA/Ross_HLS_Skill_Smoke/hls_config.cfg \
  --work_dir output/M13/ross-hls-skill-smoke
v++ -c --mode hls --part xc7s100fgga676-2 \
  --config projects/FPGA/Ross_HLS_Skill_Smoke/hls_config.cfg \
  --work_dir output/M13/ross-hls-skill-smoke
```

The generated HLS work directory is under ignored `output/` and must not be committed wholesale.
