# 修正後 AP5B v1：global-route 基線

2026-10-18。實體研究基線已通過，正式 27 項量測待完成。
CPU 的 18 份 RTL 與 `71c24f5` 相同，尚未實作 A／B／C。

- 實測週期 **10,000 ps（100 MHz）**：TT／SS／FF 在同一資料庫各自獨立
  通過 setup、hold、電氣及約束涵蓋檢查。相鄰 9,900 ps 在 SS setup 失敗；
  這是最小已測通過的 100 ps 網格點，不是由 WNS 推算的連續 Fmax。
- 標準元件面積 **22,081.118400 µm²**，180,612 CORE instances、18,157
  registers、0 macros。包含 PRF／SQ、commit trace、clock／repair cells；
  外部 RAM 不含在內。
- I response、I initiation interval、D response 固定為 **10,000 ps**。
  候選 CPU 提頻時這些 ps 值不變，於到期後第一個 core edge 取樣。
- ORFS `8359fde81991e6118b15b8a93fcde606b577794d`、ASAP7 RVT，TT-only
  建置；synthesis mapping 原約束 5,500 ps、backend 建置 14,000 ps，最終
  以實際 9,900／10,000 ps STA 定週期，三者分開記錄。普通 ABC mapping。
- 既有 ORFS 相容性 overrides 保留於 `physical/run.json`：使用 pinned
  placement default、停用不支援的額外 `reroute` move，保留一般修復。
  最後從原始 v4 route checkpoint 單次執行 TT 45% slew margin／50 ps hold
  repair 及全設計 global routing，不沿用 v5／v6 混合開發 ECO 結果。
- 175,272 routed nets、wirelength 1,438,123 µm、總 routing demand 29.60%，
  各層 overflow 0；兩次 placement legalization failures 均為 0。

`physical/initial-14000ps/` 保留初次通過的 14 ns 三 corner 報告；
`physical/boundary-9900-10000ps/` 保留實際邊界報告和 closure review。
每個 corner 的報告檔案 inventory 及工具／平台 204-file 前後核對均保留。
`physical/routing-review.json` 記錄完整路由 stdout 與 native placement／antenna
檢查；資料庫、SDC、guide 以 gzip 保存，解壓後 bytes 與原分析輸入一致。
未通過的早期結果在相鄰的 `global-route-initial-review/` 與
`global-route-slew-diagnosis/`，不作正式比較分母。

本結果限於 **global-route 寄生估算的研究基線**，三個 library corners 共用
平台 nominal wire RC。尚無 detailed-route DRC／LVS、多 corner 寄生抽取、
OCV 或 workload activity 功耗量測。Antenna 的模型檢查不能替代製造驗證。
完整 ACT4／FP 架構覆蓋也仍有獨立缺口，詳見 `docs/STATUS.md`。

`input-manifest.json` 固定正式量測要消耗的輸入契約。先以乾淨提交執行全
Embench19 與 FP32 fast 八項，核對 3,629 筆數值、原 ELF／ROI cycles、
記憶體 audit 與 profile；完成前整體 manifest 維持 `preparing`。
