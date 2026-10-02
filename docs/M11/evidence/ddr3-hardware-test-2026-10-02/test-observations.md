# Physical DDR observation summary

- Board target: `127.0.0.1:3121/xilinx_tcf/Xilinx/46602010028A`
- FPGA: `xc7s100_0`, IDCODE `0x037C7093`
- Program result: PASS; Vivado reported startup status HIGH.
- ILA dwell: 30 seconds, 2026-10-02 12:35:30–12:36:00 Asia/Taipei.
- Captured ILA depth: 1,024 samples; probes: `calib_done`, `compare_error`, write/read completion, test completion, and write/read status counters.
- `calib_done`: 1 in all samples.
- `compare_error`: 0 in all samples.
- Final write status counter: `0x00d8d445` = 14,210,117.
- Final read status counter: `0x0064133a` = 6,558,522.
- Wrapper counters saturate and count MIG debug status-valid events. They are not bytes or an independently validated transaction count.
- The final capture did not observe the brief test/write/read completion signals. The official generator is continuously active; completion pulses were not captured, and per-pattern completion is not claimed.
- Actual design traffic window: `0x00000000`–`0x00ffffff` (16 MiB). This does not demonstrate full 512 MiB MIG or 1 GiB physical module coverage.
- Sticky official MIG `tg_compare_error` aggregates command, compare, write and read errors. It remained low; the example has no total error counter, so numeric error count is unavailable.
- Post-test target/device/IDCODE query passed.
