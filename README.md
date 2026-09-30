# AI370 2 Engineering Workstation

Clean rebuild validation for AMD Ryzen AI 9 HX 370 / Radeon 890M / XDNA2 / FPGA.

施工依據：[MASTER_PLAN_REVIEW](docs/MASTER_PLAN_REVIEW.md)。
硬體與系統基線：[M0_BASELINE](docs/M0_BASELINE.md)。

每階段：precheck → action → verify → document → commit；PASS 後前進。
Kernel更換、DKMS/amdxdna替換、XRT版本取捨、graphics regression風險、FPGA unsupported OS、破壞性操作及人工帳號/硬體要求需停止確認。

GPU、NPU、FPGA使用獨立環境；XRT 2.21/2.25禁止混裝。
resources/output/虛擬環境與大型artifact不入Git；來源、版本與SHA manifest留在docs。
Git不能代替系統備份。舊SER9 PASS不繼承。

目前 Git commit identity 為本機自動化識別 `AI370 2 Build Agent <ai370-2-build@localhost>`，不代表使用者GitHub身分；無remote。
