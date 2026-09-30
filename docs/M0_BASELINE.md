# AI370 2 — M0 Baseline

盤點時間：2026-09-30 15:55:58–15:55:59，Asia/Taipei（UTC+08:00）。
專案目錄：`/home/shen/AI370-2`。

**結果：M0 唯讀盤點與文件保存完成；未進入安裝。**
原始證據位於 [M0](M0/)，結構化快照為 [inventory.json](M0/inventory.json)，
各命令、回傳碼、stderr、工具版本與裝置屬性均保留。
本輪只寫入專案文件與證據，未安裝或更新套件、修改設定或 Git，
也未執行 GPU/NPU 工作負載、推論、壓力測試、磁碟修復或韌體操作。

## 1. 硬體與 BIOS

| 項目 | 實機結果 |
|---|---|
| 專案名稱 | AI370 2 開發工作站 |
| DMI 製造商／產品 | Micro Computer (HK) Tech Limited／AI Series，版本 1.0 |
| 主機板 | Meigao Innovation Technology (Shen Zhen) Co., Ltd，F8BAC，版本 1.0 |
| BIOS | American Megatrends International, LLC.，版本 1.06 |
| BIOS 日期欄位 | `01/05/2026`，保留 DMI 原始格式 |
| Secure Boot | disabled |
| CPU | AMD Ryzen AI 9 HX 370 w/ Radeon 890M，x86_64 |
| 核心／執行緒 | 1 socket，12 核心／24 執行緒，NUMA 1 node |
| 回報頻率範圍 | 約 605–5158 MHz，boost enabled；不是效能測試結果 |
| CPU 能力 | AMD-V、AVX2、AVX-512、BF16 等旗標，完整清單見原始 lscpu |
| RAM：Linux MemTotal | 48,928,816 KiB，約 46.66 GiB |
| RAM：MemAvailable | 45,542,536 KiB，約 43.43 GiB（盤點時） |
| Swap | 約 8 GiB；盤點時使用 344 KiB |

證據：[bios.txt](M0/bios.txt)、[cpu.txt](M0/cpu.txt)、[ram.txt](M0/ram.txt)。
資源下載後有大量可回收檔案快取，因此 free 較低而 available 仍約 43 GiB。
`lshw` 在一般使用者權限下回報 47 GiB system memory 並提示資訊可能不完整；
本輪未讀取受 root 權限保護的 SMBIOS memory table，**實體 DIMM 容量、
數量、速度與型號未確認**。不能將 Linux MemTotal 當成整機實體 RAM 容量。

## 2. Ubuntu 與 Kernel

| 項目 | 結果 |
|---|---|
| Ubuntu | 24.04.4 LTS，Noble Numbat |
| Kernel | `6.17.0-14-generic` |
| Kernel 套件版本 | `6.17.0-14.14~24.04.1` |
| Kernel 配套 | 已安裝對應 headers 與 `generic-hwe-24.04` image/headers meta package |
| Linux firmware | `20240318.git3b128b60-0ubuntu2.23` |
| AMD microcode 套件 | `3.20250311.1ubuntu0.24.04.1` |
| 桌面 | Wayland，`DISPLAY=:0`、`WAYLAND_DISPLAY=wayland-0` |
| 系統時區／同步 | Asia/Taipei，NTPSynchronized=yes |
| 開機狀態 | 盤點時 uptime 約 1 小時 46 分鐘 |

證據：[system.txt](M0/system.txt)、[graphics_packages.txt](M0/graphics_packages.txt)、
[optional_install_locations.txt](M0/optional_install_locations.txt)。

## 3. 磁碟與檔案系統

| 裝置 | 型號與容量 | 用途 |
|---|---|---|
| `/dev/nvme0n1` | Crucial CT1000P310SSD8，1,000,204,886,016 bytes（931.51 GiB） | 本機 NVMe |
| `/dev/nvme0n1p1` | 1,127,219,200 bytes，vfat | `/boot/efi` |
| `/dev/nvme0n1p2` | 999,074,824,192 bytes，ext4 | `/` |
| `/dev/sda` | PSSD T7，1,000,204,886,016 bytes，USB | 外接資源碟 |
| `/dev/sda1` | exFAT | `/media/shen/T7`，盤點時仍掛載 |

根檔案系統 df 容量 982,240,026,624 bytes，已用 200,285,499,392 bytes，
可用 731,984,011,264 bytes（約 **681.71 GiB**），使用率 22%。
資源已保存在本機 `resources/`；其資料檔不屬於已安裝工具。
證據：[disks.txt](M0/disks.txt)。

## 4. Radeon GPU 與圖形驅動

| 項目 | 結果 |
|---|---|
| GPU | Radeon 890M 整合 GPU（CPU 型號及 PCI/Kernel 資料交叉辨識） |
| PCI 位址／ID | `0000:c5:00.0`／`1002:150e`，revision c1 |
| 綁定／已載入驅動 | `amdgpu`，Kernel 內建模組 |
| 模組位置 | `/lib/modules/6.17.0-14-generic/kernel/drivers/gpu/drm/amd/amdgpu/amdgpu.ko.zst` |
| Kernel 日誌 | amdgpu 初始化完成；KFD 已加入裝置；active CU 16 |
| VRAM／UMA 回報 | 17,179,869,184 bytes（16 GiB） |
| GTT 回報 | 25,051,553,792 bytes（約 23.33 GiB） |
| DRM 裝置 | `/dev/dri/card1`、`/dev/dri/renderD128` |
| 計算裝置 | `/dev/kfd` 存在 |
| 裝置電源狀態 | active（盤點時） |
| Mesa | 25.2.8，包含 OpenGL 與 Vulkan 驅動套件 |
| libdrm-amdgpu | `2.4.125-1ubuntu0.1~24.04.1` |
| Vulkan loader | `1.3.275.0-1build1` |
| Xorg amdgpu driver | `23.0.0-1ubuntu0.24.04.1` |

這些是驅動的配置／回報值，不是獨立 VRAM 容量，也不能與 RAM/GTT
直接相加當作可用模型容量。ROCm/HIP 安裝資源已下載，但本機尚未安裝
ROCm/HIP runtime 或編譯工具，未驗證 OpenGL/Vulkan/ROCm 實際工作負載。

## 5. XDNA2 NPU

| 項目 | 結果 |
|---|---|
| NPU | HX 370 的 XDNA2 NPU，PCI signal processing controller |
| PCI 位址／ID | `0000:c6:00.1`／`1022:17f0`，revision 10 |
| 綁定／已載入驅動 | `amdxdna`，Kernel 內建模組 |
| 模組位置 | `/lib/modules/6.17.0-14-generic/kernel/drivers/accel/amdxdna/amdxdna.ko.zst` |
| 裝置節點 | `/dev/accel/accel0` |
| Kernel 日誌 | `amdxdna_accel_driver` 初始化完成 |
| 韌體 | 已有 `17f0_10/npu.sbin.1.0.0.63.zst`、`17f0_11/npu.sbin.1.0.0.166.zst` 等；完整路徑見證據 |
| 裝置電源狀態 | suspended（盤點時） |
| 使用者空間環境 | 未安裝 XRT／Ryzen AI Python runtime；已下載的資源不等於已安裝 |

電源狀態 suspended 單獨不能判定 NPU 故障。本輪只確認硬體枚舉、
Kernel 綁定、模組與裝置節點，未呼叫 NPU runtime 或執行推論。

## 6. PCI、周邊驅動與權限

完整 PCI 清單共 **42 個裝置**，保存在 [pci.txt](M0/pci.txt)。

| 主要裝置 | PCI ID | 綁定驅動 |
|---|---|---|
| NVMe SSD controller | `c0a9:5427` | nvme |
| MediaTek 7925 無線網卡 | `14c3:7925` | mt7925e |
| Realtek RTL8125 2.5GbE ×2 | `10ec:8125` | r8169 |
| Radeon GPU | `1002:150e` | amdgpu |
| XDNA2 NPU | `1022:17f0` | amdxdna |
| AMD 音效 | `1002:1640`、`1022:15e3` | snd_hda_intel |
| AMD encryption controller | `1022:17e0` | ccp |
| AMD sensor controller | `1022:164a` | pcie_mp2_amd（amd_sfh） |
| USB／USB4 相關控制器 | 完整 ID 見 PCI 清單 | xhci_hcd、thunderbolt |

USB 清單另見 [usb.txt](M0/usb.txt)，全部載入模組及模組位置、
vermagic/signing metadata 見 [modules.txt](M0/modules.txt)、
[driver_metadata.txt](M0/driver_metadata.txt)。

目前帳號 `shen`（uid 1000）不在 render/video 群組。

| 裝置 | 帳號讀写權限 |
|---|---|
| `/dev/dri/renderD128` | 可讀寫，ACL 有 `user:shen:rw-` |
| `/dev/kfd` | 受限，root:render，無帳號 ACL |
| `/dev/accel/accel0` | 受限，root:render，無帳號 ACL |

ACL 與群組原始資料見 [device_permissions.txt](M0/device_permissions.txt)。
本輪未調整群組或權限。`lspci` 對一個 PCI label 的讀取出現
Operation not permitted，主要 ID 與 driver 枚舉結果已保存。

## 7. 已安裝開發工具

| 工具 | 實際版本／位置 |
|---|---|
| GCC／G++ | 13.3.0，`/usr/bin/gcc`、`/usr/bin/g++` |
| GNU Make | 4.3，`/usr/bin/make` |
| Git | 2.43.0，`/usr/bin/git` |
| Python | 3.12.3，`/usr/bin/python3` |
| Node.js | 18.19.1，`/usr/bin/node` |
| npm | 9.2.0，`/usr/bin/npm` |
| Codex | PATH 中存在 `/usr/local/bin/codex`；本輪未呼叫其 runtime |

`build-essential` 已安裝；完整 Debian 套件名、版本與安裝狀態見
[packages.txt](M0/packages.txt)。版本命令的輸出保存在 inventory.json。

PATH 未找到 CMake、Ninja、Clang、uv、pip、Conda、Rust/Cargo、Go、
Docker/Podman、VS Code、Git LFS、ROCm/HIP、XRT、Lemonade、Vivado/Vitis，
亦未找到 glxinfo/vulkaninfo/clinfo；`/opt` 為空。
目前 Python metadata 未找到 NumPy、PyTorch、TensorFlow、ONNX、
Transformers、OpenVINO 等目標 AI 套件。Python 有 venv 模組但無 pip；
未建立或測試虛擬環境。詳見 [python_packages.txt](M0/python_packages.txt)。

`resources/Downloads` 中的 CMake、VS Code、ROCm 等安裝包只是已準備的
檔案，**不得列為已安裝／已驗證工具**。

## 8. Git repository 狀態

`/home/shen/AI370-2` 及其父目錄不是 Git working tree。
`git rev-parse`、`git status`、`git log`、`git remote` 均回報
`fatal: not a git repository`；目前沒有可確認的 branch、HEAD、
remote 或 tracked/untracked 狀態。

本輪保存這個狀態，未 git init、clone、fetch、import bundle、stage 或 commit。
證據：[git_state.txt](M0/git_state.txt)。

歷史 SER9 bundle 位於 resources；它是備份檔，不是 AI370 2 的 repository。
bundle main/HEAD 為 `dc94da9322b7ba7d9601767f0b46ff6f449d9b4c`，
與較新故障紀錄引用的 `95effc6…` 不一致；不作新機已驗證歷史。
已唯讀保存 refs 清單：[historical_bundle.txt](M0/historical_bundle.txt)。

## 9. 目前日誌觀察與驗證界線

證據：[kernel_gpu_npu.txt](M0/kernel_gpu_npu.txt)、
[kernel_warnings.txt](M0/kernel_warnings.txt)。

- GPU/NPU 均有初始化完成紀錄；GPU 日誌仍含選用 ISP/安全韌體
  不可用、MES 版本提示，以及 HDMI vendor infoframe 設定失敗 `-22`。
- 開機警告含 RDSEED32 停用、部分 ACPI/輸入裝置、Bluetooth、NVMe 提示。
- 14:41:49 有 T7 exFAT volume 未正常卸載的警告。這不是已確認的
  檔案毀損結論；先前已複製資源的 checksum 驗證紀錄仍保留。
  本輪沒有 fsck、修復、卸載或修改外接碟。

M0 確認的是当前硬體與系統基線。未驗證 GPU/NPU 推論、FPGA 編譯、
裝置效能、長時間穩定性或工具安裝相容性；未进入後續安裝階段。

## 原始證據完整性

原始資料與本文件的 SHA256 列於 [SHA256SUMS](M0/SHA256SUMS)。
收集腳本：[collect_m0.py](collect_m0.py)。
重跑會刷新 M0 快照；保留本輪基線時應先另存新一輪證據目錄。
