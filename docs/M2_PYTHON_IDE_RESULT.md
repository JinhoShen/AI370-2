# M2 Python / IDE foundation

2026-09-30。CLI/Python foundation PASS；IDE CLI/extensions驗證PASS，GUI debugger未人工操作。

PRECHECK：uv、code DEB與五個穩定VSIX重新比對既有SHA，全部一致；code模擬僅1新增、0upgrade、0remove。未使用Prerelease-Archive。
ACTION：uv0.12.21/uvx安裝至~/.local/bin；uv使用現有/usr/bin/python3.12.3離線建立output/M2/python-env。VSCode1.139.1以本機DEB安裝；debconf code/add-microsoft-repo=false，不新增Microsoft APT來源。五個VSIX分別安裝。
VERIFY：Python sys.prefix!=sys.base_prefix，版本3.12.3；C++compile/run通過；code --version及--list-extensions --show-versions正常；dpkg --audit無輸出。
PASS CRITERIA：CLI、venv與IDE命令列基礎均滿足；不宣稱尚未操作的GUIdebug或AI Python依賴已驗證。
ROLLBACK：移除新uv/uvx、測試venv；VSCode移除先模擬，extensions按M2_EXTENSIONS.txt撤回，保留個人設定備份。
DOCUMENT/COMMIT：M2_EXTENSIONS.txt、M2_CODE_INSTALL.txt及本文件。

注意：VSCode安裝VSIX時自動補入ms-python.vscode-python-envs1.38.0與ms-vscode.cpp-devtools0.6.18，已列入實際清單；這兩項不在原始離線VSIX集合，完整offline IDE重建仍需補其來源/下載artifact。CLI emit的Node url.parse deprecation不影響此次安裝成功。
uv提供venv/package management；尚未裝system pip，不為此升級Python。ROCm與NPU Python環境未建立，將各自獨立。
