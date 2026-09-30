# M0.1 Recovery checkpoint — BLOCKED / NOT CREATED

日期：2026-09-30。Golden M0 Git與checksum驗證完成；系統checkpoint尚未建立，不宣稱M0.1整階段PASS。

## PRECHECK

現有磁碟為單一NVMe ext4 root + vfat EFI，無既有LVM/Btrfs snapshot。
本輪確認外接T7未掛載且lsblk未列出該裝置。`sudo -n true`失敗：需要密碼。
本機資源已存在，無須重新下載；Git只能恢復專案文件。

## ACTION（待人工前置條件，尚未執行）

1. 提供離機備份目的地；確認實際可用容量，可容納系統使用區塊與必要資料。原T7資源備份不是root/EFI映像，歷史剩餘容量不可假設足夠。
2. 提供合法可用的系統管理權限；不要把密碼傳入聊天或寫入腳本。
3. 選擇可信live recovery環境，先確認介質、checksum/簽章及映像工具。若需新工具/介質，先做精確材料準備，不重下載已驗證資源。
4. 優先在root離線狀態建立disk/partition image：保存GPT/partition配置、EFI、root、bootloader/UEFI相關metadata。保留當前6.17.0-14 kernel/modules/headers、firmware、APT來源/key/package版本、udev和system設定。
5. exFAT目的地使用能保留POSIX metadata的image/archive，勿把root直接以普通檔案拷貝當成可開機snapshot。
6. 不格式化、不覆寫來源NVMe；恢復演練只在獨立scratch disk/VM進行。寫入physicaldisk、製作bootUSB與人工重開機另依使用者gate確認。

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

目前缺少系統管理授權方式及離機備份目的地，屬使用者允許停止的人工操作gate。
在checkpoint PASS前，不安裝Mesa/Vulkan工具、ROCm、XRT或任何系統套件。
