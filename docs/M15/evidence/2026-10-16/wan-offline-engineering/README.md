# Actual WAN-offline engineering acceptance — 2026-10-16

**WAN_OFFLINE_ENGINEERING_PASS.** Actual execution 09:14:38–09:19:38 +08:00; agent elapsed 295.053 seconds. Qwen3.8-27B-UD-Q4_K_XL used existing ENGINEERING Vulkan16K/24-thread service, genuine Ross Skill/local KB calls, one model-authored RTL patch and two fixed XSim runs (seeded failure, then PASS). No Codex runtime or cloud model was used; unchanged testbench is retained.

Temporary NetworkManager active-device never-default properties removed IPv4/IPv6 default routes. External IPv4/IPv6 TCP probes both returned ENETUNREACH (101). Routes were checked periodically while the job ran. NIC/link stayed up for host-locked licensing; internal Docker/loopback access remained. This is WAN isolation, **not physical air-gap certification or complete traffic capture**.

An independent systemd restore timer was armed before changing routes. Restoration PASS; saved profile remained unchanged and runtime-after.json verifies original formal profile. No protected packages, license, model or FPGA configuration changed. Private restore-plan (profile UUID), caches and binaries remain excluded from Git.

First attempt safely failed the route gate before model execution: NetworkManager reapply had not yet removed the route. Network restoration passed. The second controller waits up to five seconds for actual kernel routes to settle; no safety check was bypassed. See initial-route-gate-failure.json.

Logs in workspace/runs are curated only to remove trailing whitespace; raw SHA256 and curated SHA256 are recorded. Raw originals remain in output/M15/wan-offline/20261016T091438+0800. Trace and JSON copied verbatim. This is one bounded acceptance, not a new A/B benchmark or arbitrary-project autonomy PASS.
