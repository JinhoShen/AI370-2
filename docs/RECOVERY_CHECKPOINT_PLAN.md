# M0.1 Recovery checkpoint — PARTIAL / LOCAL FILE CHECKPOINT VERIFIED

日期：2026-10-01。Golden M0 Git與checksum驗證完成；本機 live file-level checkpoint 已建立與抽取驗證，但不宣稱M0.1/full recovery整階段PASS。詳見 [LOCAL_RECOVERY.md](LOCAL_RECOVERY.md) 及 [CP0-20261001T024200Z-VERIFICATION.txt](CP0-20261001T024200Z-VERIFICATION.txt)。

## PRECHECK

現有磁碟為單一NVMe ext4 root + vfat EFI，無既有LVM/Btrfs snapshot。
外接T7未掛載且lsblk未列出該裝置。2026-10-01本機checkpoint使用已可用的非互動sudo建立；沒有連接外部目的地。
本機資源已存在，無須重新下載；Git只能恢復專案文件。

## REMAINING RECOVERY WORK（本機file-level部分已執行）

1. 現在只有同 NVMe 備份，尚無外接/off-device 目的地；連接後再檢查實際容量與 filesystem metadata 能力。舊 T7 資源備份不是 root/EFI 映像，歷史剩餘容量不可假設足夠。
2. 尚未建立離線 system image 或在 scratch disk/VM 做完整 boot restore。任何新增 recovery media/image 需固定工具版本、核對 checksum/簽章並保存 GPT、EFI、root、bootloader metadata。
3. resources 與 project output 仍由此 root checkpoint 排除；若需同碟副本或獨立目的地副本，應另計容量和驗證步驟。
4. 不格式化、不覆寫來源 NVMe；完整恢復演練只在獨立 scratch disk/VM 進行。寫入 physical disk、製作 boot USB 與原盤 restore 屬破壞性步驟，須依使用者 gate 確認。

## VERIFY / PASS CRITERIA

備份工具完成、manifest/SHA一致；映像可讀、可抽取關鍵檔案；在scratch目標完成恢復/boot或記錄明確驗證界線。
目的地與來源識別清楚，恢復程序含EFI/root/bootloader；沒有可恢復證據不可標checkpoint PASS。

## ROLLBACK

後續變更失敗時停服務、保存診斷，從recovery介質對獨立確認的目標恢復；原盤restore是破壞性操作，須獨立approval。
單獨APT downgrade或切回舊kernel不能保證恢復driver/firmware/userspace組合。

## DOCUMENT / COMMIT

建立後保存工具版本、目的地識別、容量、排除項、SHA、恢復測試及限制；映像不進Git。
每次kernel/driver/DKMS/firmware前另建checkpoint；GPU、NPU、FPGA測試通過後保存各自版本與回復程序。

## STOP

外接目的地或破壞性 restore 另行等待使用者決定；目前 local file-level checkpoint 的範圍與限制已明確。此 checkpoint 不取代 kernel/driver/DKMS/firmware 變更前的專用回復方案。
