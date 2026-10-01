# Local recovery checkpoint

使用者指定：不備份到 T7；本機 checkpoint 位於 Git 忽略的 `output/recovery/`。

最新 checkpoint：`output/recovery/CP0-20261001T024200Z/`。root/EFI archive SHA 驗證與關鍵檔案隔離抽取已通過，詳見 [`CP0-20261001T024200Z-VERIFICATION.txt`](CP0-20261001T024200Z-VERIFICATION.txt)。Root archive 約 50 GiB；SHA-256 `2c6f3aea44a904fd4a8c9d49e024e0e80d4519169c7a1da5a25c3e99eaa475f3`。EFI archive SHA-256 `30e0565058015941328cbabf3d22b628a57e1be5e9ca3994e3e1990a1256dd94`。目錄為 root-owned mode 0700。

此為同一 NVMe 上的 live file-level 備份，非 atomic snapshot／disk image，不能抵禦磁碟故障；未做完整開機還原，不代表 M0.1/full recovery PASS。保留 root 檔案 ownership/ACL/xattrs、EFI archive、package/kernel/磁碟配置、partition table 與 SHA。備份期間 `/var/log/syslog` 會持續寫入，故排除該單一檔案並另存當前 boot 的 journald/kernel journal；tar stderr 中的 snap xattr 不支援與執行中 socket 跳過已記錄，root tar exit code 為 0。

排除 resources、整個 project `output/`（包含 checkpoint 本身）、runtime 掛載點與 swap。resources 保留既有 manifest，但沒有納入此 checkpoint；project 輸出目錄的生成物也未納入。archive 可能包含帳號秘密，目錄限制 root 存取，不上 Git 或公開分享。

建立 checkpoint 的命令：

```bash
sudo bash /home/shen/AI370-2/scripts/create_local_checkpoint.sh
```

重新驗證指定 checkpoint（不帶參數時預設選最新 CP0）：

```bash
sudo bash /home/shen/AI370-2/scripts/verify_local_checkpoint.sh \
  /home/shen/AI370-2/output/recovery/CP0-20261001T024200Z
```

驗證會檢查 SHA，並在 checkpoint 私有目錄建立暫存區抽取 `/etc/passwd`、`/etc/fstab`、dpkg database、目前 kernel/initramfs 與 EFI。後續仍需安排獨立 scratch disk/VM 的完整恢復演練及離機 recovery 介質。restore 至原 root 屬破壞性操作，須獨立 approval；Git不能代替備份。
