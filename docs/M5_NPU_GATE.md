# M5 NPU — PRECHECK PASS / XRT DECISION REQUIRED

2026-09-30。Kernel6.17.0-14內建amdxdna保留；module位於kernel/drivers/accel/amdxdna/，未安裝DKMS。
shen render群組的新session可讀寫/dev/accel/accel0（sg render驗證），未設0666。只驗證access，未驗證NPU inference。

目前沒有XRT provider。下載材料有SDK1.7.1配套XRT2.21，及Lemonade庫中的2.25。依使用者要求，版本取捨必須approval，不能混裝。

建議決策：先鎖定Ryzen AI1.7.1配套XRT2.21；維持inbox amdxdna，先檢查受支持的userspace/plugin與driver組合，不安裝會替換driver的SDK plugin，不引入2.25。
此決策不是DKMS授權。現有plugin postinst會dkms install、rmmod/modprobe並寫0666，已列MASTER_PLAN_REVIEW；若inbox路線不可行，另提driver變更gate，不以改腳本或略過plugin宣稱官方支持。
若選2.25，需要另審RyzenAI1.7.1 ABI配套及Lemonade NPU backend；現階段沒有足夠本機workload證據支持直接取代2.21。

STOP：M3已PASS/commit後停在此版本決策，未執行M5 runtime安裝或後續phase。

決策更新：使用者核准2.21 userspace、不DKMS、不替換driver、不混2.25；施工結果FAIL/compatibility blocked，見M5/RESULT.md。
