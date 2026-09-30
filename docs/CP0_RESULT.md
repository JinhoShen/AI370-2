# CP0 local recovery result

日期：2026-09-30。狀態：**PASS — LOCAL FILE-LEVEL CHECKPOINT**。

使用者選擇本機備份，不使用T7。SHA重新驗證與關鍵檔案/Kernel/initramfs/EFI隔離抽取成功，見CP0_VERIFICATION.txt。
使用者提供完整root-tar.stderr：僅Snap唯讀掛載點的Cannot flistxattr（Operation not supported）與ibus/Codex runtime socket ignored；tar exit0，未見一般檔案讀取失敗。socket為執行中IPC，不需作靜態恢復。

限制：live非atomic；不保證跨應用transaction一致性；同NVMe不能抵禦磁碟故障；未測整機boot restore。
此PASS僅指檔案層級施工checkpoint，不是disk-image/boot-recovery或M14完整recovery PASS。允許繼續小型可逆userspace transaction；重大kernel/driver/DKMS仍需獨立checkpoint與approval，不能只靠本次CP0。
