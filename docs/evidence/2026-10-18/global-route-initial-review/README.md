# 全核心 global-route 初次三 corner 審查：未閉合

2026-10-18。修正後 AP5B 相同 18 份 RTL，普通 ABC mapping，TT-only 建置。
`run.json` 記錄 global-route 作業退出 **0**、輸入前後雜湊一致；最後 OpenDB／
SDC 成功寫出。這只完成實體建置階段，**基線尚未凍結**。

此作業重用已完成的 TT CTS checkpoint，停用 pinned binary 不支援的額外
`reroute` WNS pass，保留普通 electrical/setup/hold repair。繞線 stdout 回報
169,694 nets、第一輪 wirelength 1,429,819 µm、total overflow 0。原始 log 與
後續增量修復紀錄均保留。Antenna 回報 0 net／pin violations，並有
`CORE ANTENNACELL` 不存在的模型警告；這不是製造 DRC／LVS 保證。

`initial-14000ps/` 在三個全新 process 各自讀原始 TT／SS／FF libraries，從
同一 OpenDB 還原 global-route 寄生。完整 204-file 工具／平台雜湊在前後均
通過核對，原始約束、units、四類路徑與電氣報告均保留。

| Corner | 14 ns setup slack ps | Hold slack ps | 電氣 slew 違例 |
| --- | ---: | ---: | ---: |
| TT | 6897.356 | 20.634 | 0 |
| SS | 3921.620 | 47.756 | 541 |
| FF | 8552.704 | 1.047 | 30 |

最差 SS slew 428.17 ps、FF 328.35 ps，對應的 library 上限是 320 ps。約束
涵蓋檢查為空、setup/hold 均為正，但 `closure-review.json` 正確回報
`passed=false`、`qualified_periods_ps=[]`。這些 slew 限制須透過 cell／buffer
與配線修復，不能把當前 14 ns 當作已合格的工作週期。

幾何 cell 面積 21,474.09468 µm²、175,035 個 CORE 類型 instances、18,157
registers、0 macros，在三個 corner 一致。這是**未閉合的初次實作數字**；
manifest 的正式面積／週期仍為 null，不作 CPU 目標比較的分母。

資料庫、SDC 與 guide 以 gzip 保存；解壓後的資料庫 SHA 在分析 `run.json`，
其餘原始輸出及每個 corner 的 output inventories 不改寫。後續 TT ECO 將採
30% slew optimizer margin、50 ps hold repair margin，重新合法化／增量繞線；
獨立驗收仍用原本的 I/O、uncertainty、slew／capacitance limits。

ORFS 原始功耗摘要使用預設活動率（vectorless）；尚無 workload activity 資料。
本封存沒有 CPU 加速或 workload 功耗比較。在此目錄執行
`sha256sum -c SHA256SUMS` 核對封存。
