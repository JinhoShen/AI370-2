# Rebuild scripts

後续腳本固定版本、預設check/plan、明確install模式、失敗停止。
不使用無條件upgrade、不整庫安裝DEB、不自動跨越approval gate。

`apt_change_guard.py` 只執行 `apt-get -s`，不安裝套件。它拒絕包含 Kernel、Mesa/RADV、libdrm、ROCm/HIP/HSA、XRT、amdxdna 或 AMD GPU/NPU firmware 變更的 transaction；輸出完整模擬日誌與 JSON verdict 到 ignored `output/M14/apt-simulations/`。輸入是明確套件名稱，不接受 apt flags。Parser regression 使用 `python3 scripts/test_apt_change_guard.py`；新增套件安裝前仍須閱讀實際 simulation log。
