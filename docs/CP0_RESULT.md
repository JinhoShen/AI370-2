# CP0 local recovery result

日期：2026-10-01。狀態：**PASS — LOCAL FILE-LEVEL ARCHIVE AND SELECTED-FILE RESTORE**；完整 M0.1/full recovery 仍未完成。

最新備份位於 root-only `output/recovery/CP0-20261001T024200Z/`；root/EFI SHA 驗證及 `/etc/passwd`、`/etc/fstab`、dpkg database、目前 Kernel/initramfs、EFI 隔離抽取通過，詳見 [CP0-20261001T024200Z-VERIFICATION.txt](CP0-20261001T024200Z-VERIFICATION.txt)。Root archive SHA-256 `2c6f3aea44a904fd4a8c9d49e024e0e80d4519169c7a1da5a25c3e99eaa475f3`，EFI archive SHA-256 `30e0565058015941328cbabf3d22b628a57e1be5e9ca3994e3e1990a1256dd94`。

此份為同 NVMe live file-level checkpoint，不是 disk image，不能抵禦磁碟故障，也不保證跨應用 transaction 一致性。resources 與 project `output/` 依既有策略排除；`/var/log/syslog` 因持續寫入而排除，journal 另存。snap mount xattr 不支援與 runtime socket 跳過屬已記錄的 tar warnings，tar exit code 為 0。

2026-09-30 的舊 checkpoint 與驗證報告仍保留。2026-10-01 第一次新備份因 syslog 在讀取時改變而正確回報失敗；保留失敗碼/stderr、刪除 50 GiB incomplete archive 後，以排除活動 syslog 並另存 journald 的流程成功重建。該次 false start 未覆寫舊或新成功 checkpoint。

此狀態不等同 offline recovery 或 M14 完整 recovery PASS。重大 kernel/driver/DKMS 操作仍需單獨確認可恢復性，不能只靠同碟 CP0。
