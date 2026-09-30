# Local recovery checkpoint

使用者指定：不備份到T7；改存本機 `output/recovery/`（Git忽略）。

此為施工前live file-level備份，非atomic snapshot／disk image。與來源同一NVMe，不能抵禦磁碟故障；未完成restore驗證前不標CP0/M0.1 PASS。
保留root檔案ownership/ACL/xattrs、EFI archive、package/kernel/磁碟配置與SHA。若sfdisk已存在則保存partition table；缺少時需另補metadata。
排除已另存備份的resources、checkpoint本身、runtime掛載點、swap。排除的資源必須保留既有manifest；swap可重建。archive可能包含帳號秘密，目錄限制root存取，不上Git或公開分享。

本機終端執行（關閉重負載程式；sudo密碼僅在終端輸入）：

```bash
sudo bash /home/shen/AI370-2/scripts/create_local_checkpoint.sh
```

任何tar非零exit都停止並由agent檢查，不直接當PASS；live檔案變動不宜忽略。此腳本未執行且不安裝工具、不修改kernel/driver。

後續需檢查stderr、關鍵檔案可抽取、SHA與EFI內容，安排scratch restore/recovery介質。restore至原root屬破壞性操作，須獨立approval；Git不能代替備份。
