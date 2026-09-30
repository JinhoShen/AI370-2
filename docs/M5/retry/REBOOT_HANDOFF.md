# Retry reboot handoff

Original post-reboot compute passed; the signature-warning policy false negative triggered CP5 recovery. CP5 archive/module/firmware hashes, initramfs byte comparison, absent added DKMS module/registry/firmware and current inbox/XRT firmware state were checked before reapplying the exact approved stack. No compatibility research was repeated.

Reapplied DKMS 2.21.260102.53.release and firmware 1.1.2.64. Secure Boot disabled. Pre-reboot CNN passed 10 VitisAI-only iterations, positive NPU hardware time 14,828,180 ns, maximum reference error 0, CPU fallback disabled. HIP and Vulkan each passed 1024 results; dpkg audit clean.

Reboot is authorized and scheduled. ai370-m5-verify.service will run full verification on a new boot ID. Expected signature warning is WARNING only; functional failure retains CP5 rollback. Only successful full verification writes M5 PASS and creates the NPU Golden State commit/tag. This handoff is not M5 PASS.
