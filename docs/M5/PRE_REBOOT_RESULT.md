# M5 driver switch — pre-reboot result

2026-09-30；**實際 CNN workload PASS，M5 整階段 PENDING REBOOT**。

## PRECHECK / ACTION

依使用者明確批准切換。Gate/recovery紀錄 commit e18fee9；CP5 SHA再次PASS。精確APT simulation為2 new / 0 upgrades / 0 removals（dkms + xrt_plugin-amdxdna）。Ubuntu HTTPS取得唯一缺少的dkms 3.0.11-1ubuntu13，SHA符合既有APTmetadata。APT --no-download遇非標準local檔名取檔問題，沒有變更套件；以dpkg -i兩個精確local DEB完成，未apt update/upgrade，未安裝base-dev或XRT2.25。

DKMS完成編譯/安裝至 /lib/modules/6.17.0-14-generic/updates/dkms/amdxdna.ko.zst；套件postinst已live reload。實際 /sys/module version與XRT均確認2.21.260102.53.release_20260309及driver commit6f881ad；XRT回報實際firmware **1.1.2.64**。原inboxmodule仍保留，Kernel未換，GPUdriver/Mesa未換。

package原udev MODE0666已收斂為render/0660，實際 /dev/accel/accel0 root:render0660。已update-initramfs同一Kernel；initramfs包含udevrule，driver/firmware由rootfs供PCI probe載入，不宣稱initramfs裡已嵌入它們。這部分須重開機實證。

## VERIFY / PASS CRITERIA

CNN模型SHA7a78c7e85bac3a0681e3d2f77e69093a761e1c8f62f7fc65ff5ce3e1b82c5ba3。實際ORT1.23.3.dev20260320。10次 inference；strict test hardware npu time從0增加14,712,721ns；所有執行node profile為VitisAI；explicit session.disable_cpu_ep_fallback=1、runtime disable_fallback、禁止emulation。CPU僅作獨立reference；最大輸出差 **0.0**，測試門檻rtol0.001/atol0.0001。見research/live-cnn-result.json、live-ort-profile.json及完整log。

切換後HIP/Vulkan各1024結果正確，dpkg --audit無輸出。但未重開機，因此不能標M5 PASS或進M6。

## REBOOT / ROLLBACK

已建立/enable ai370-m5-verify.service，只在output/M5/reboot.pending存在時於下次boot跑。記錄目前boot ID，腳本拒絕同一次boot充當重開機驗證；尚未start這個service。下一boot驗證Kernel/module/firmware、嚴格CNN、usage/no-fallback、HIP/Vulkan與kernel error；通過才寫docs/M5/reboot/STATUS、RESULT.md、BUILD_PROGRESS及Git commit。

失敗trap保存kernel/log，呼叫scripts/rollback_npu_cp5.sh：移除精確plugin/DKMS、新增firmware；恢復CP5 inbox module、firmware、initramfs與原SHIM，depmod/reload並核對SHA，回歸GPU。若回復不完整會記錄RECOVERY_INCOMPLETE，不能假稱恢復成功。完整boot restore未測；服務與rollback腳本已syntax/unit驗證，但真正reboot/失敗回復演練尚未發生。

## DOCUMENT / COMMIT

scripts/install_npu21_driver.sh記錄可重建安裝；rollback與post-reboot verify script、systemd unit留專案。所有安裝/版本/模型/回歸log提交Git；SDK、DEB、module、checkpoint仍不入Git。
