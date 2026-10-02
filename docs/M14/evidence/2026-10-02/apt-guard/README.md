# M14 APT dependency/change guard evidence

`apt_change_guard.py` runs an APT simulation only. A simulation for the previously absent `cowsay` userspace package returned `SAFE_SIMULATION`, one planned new package, zero protected package changes; no install command was executed. The full APT transaction transcript and machine result are retained in this directory.

Six parser cases passed: a safe userspace package; protected Mesa/libdrm changes; protected kernel/XRT/firmware removals; protected ROCm library/AMDGPU driver changes; mixed safe/protected transaction; and fail-closed handling for an unknown simulation output shape. Exact test output is retained.

The guard rejects changes to Linux Kernel/firmware, Mesa, libdrm, ROCm/HIP/HSA, AMD XRT, amdxdna and AMD GPU/NPU firmware. It also rejects malformed requests rather than forwarding user-supplied APT options. This does not claim that any package was installed or that a clean rebuild was performed.
