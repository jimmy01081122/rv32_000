# 完整 ORFS global-route 步驟：API 資格確認

2026-10-18。小型 fixture 的完整 ORFS step qualification，**不是 CPU 基線**。
輸入為前輪四個 cell 的已放置資料庫，放在 ORFS 的 `4_cts.odb` 介面位置；
它不是全核心的 CTS。完整核心 CTS 快取另有真實成功 stage log／資料庫核對。

固定 ORFS／OpenROAD／ASAP7，採 TT 建置、普通 setup／hold／electrical repair，
`OPT_POST_GRT_WNS=0 REPORT_CLOCK_SKEW=0`。`make.log` 與逐 stage log 記錄
`do-5_1_grt` 真實退出 0，經 pin access、global routing、寄生估算、修復、
增量繞線、報告及最終 OpenDB／SDC 寫出。這驗證避開不支援的 `reroute` move
之後，後續 ORFS API 仍可完整執行。

原四個 cell 加入四個 hold buffers 後，共 8 cells、2 registers、0 macros，
幾何面積 1.21014 µm²。重新在獨立 process 以 production `report.tcl` 載入
最後資料庫／global-route 寄生，5,500 ps 下的結果如下：

| Corner | Setup slack ps | Hold slack ps |
| --- | ---: | ---: |
| TT | 3170.014 | 16.831 |
| SS | 3130.124 | 36.592 |
| FF | 3192.203 | 3.716 |

三個 corner 的約束與電氣違例報告均為空，四類路徑都有報告，時序審查器接受
此正例。它與前輪刻意保留的負例共同檢查 gate 不會永遠通過或永遠拒絕。
這些數字只適用這個小電路，不能換算 CPU 頻率、面積或改善幅度。

`cache-negative-controls/` 保留兩次真實 CLI 反例：從 14,000 ps CTS 快取改成
15,000 ps，或把 ABC 政策改為 platform mapping，均在啟動 worker 前被拒絕。
主機上的完整 CTS SDC 也已通過 period、最大／最小 I/O、uncertainty、slew、
load 與 timing-exception 核對。

ASAP7 fixture 的 antenna log 回報零違例，並列出無 `CORE ANTENNACELL` 的警告；
這不建立製造層級的 antenna／DRC／LVS 保證。全核心仍須另做 global-route
完成紀錄、獨立三 corner 閉合與正式 27 項量測。

在此目錄執行 `sha256sum -c SHA256SUMS` 核對封存。
