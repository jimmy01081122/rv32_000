# LSU A v1：已暫存回應消耗與下一請求重疊

2026-10-19。使用者核准 A 先實驗、B 另作獨立對照。來源基線為
`58a4159da0372b3286758be1e6c1b50f9f28cc27`，凍結契約維持不變。
本實驗已完成[功能與完整同頻量測](../../docs/evidence/2026-10-19/lsu-a-functional/README.md)：
乾淨 `39bc12d` 的 27/27 通過，FP32 3,629 筆數值符合原容差。
100 MHz、記憶體固定 10 ns 下，Embench GM 為 1.045830×、FP32 為 1.078255×；
實體 synthesis 正在執行，面積／合格頻率尚待量測，尚未完成 CPU 改善驗收。

唯一功能 RTL 變更是 LSU 的請求排除條件：舊 response buffer 本拍確實
交付、無 error、沒有 external in-flight、沒有 flush，才可接受下一個已就緒
請求。保留一筆 external outstanding、原 response register、16-slot SQ、
store response 後退休與 B 的原 SQ marking 節拍。Flush／fault 採保守排除。

事前驗證與量測條件：

1. 獨立 LSU harness 比較原基線與 A：證明成功 load 的連續請求間隔從 3 拍
   到 2 拍，原 completion 延遲不變；檢查 load→load、load→已授權 store、
   request backpressure、INT／FP destination、tag wrap、flush、load／store
   error、forwarding／misalign arbitration。另檢查 B 的 marking 節拍未改。
2. 改寫原互斥 assertions，加入交接後 in-flight／pending tag 及地址追蹤。
   以 `--assert` 建置執行；保留原基線不能通過 A 節拍要求的負向對照。
3. 完整 48 項 ready／fault 介面、18 directed／Spike、有限 FMA、固定時間
   controls 及全 Embench19／FP32 八項，FP32 原 3,629 筆輸出及容差不變。
4. 使用原 ELF bytes，CPU period 與記憶體服務 ps 分開。I response、I
   initiation interval、D response 永遠固定 10,000 ps；同頻率診斷先採
   10,000 ps CPU，不提前宣稱實體執行時間加速。主比較須用實測閉合 period。
5. 相同 pinned ORFS／ASAP7 RVT、TT-only、普通 ABC 5,500 ps mapping、
   14,000 ps backend、TT 45% slew／50 ps hold ECO 及最終全設計 global route。
   TT／SS／FF 各用新 process 審查；100 ps 網格與固定 I/O／RC／面積邊界不變。
   不可重用不同 RTL 的 synthesis／CTS／GRT cache。
6. 機制、正確性、完整兩集合執行時間與標準元件面積分開報告。目標仍是
   一般嵌入式與 FP32 各 ≥1.20×、面積 ≤1.10×；單獨 A 未達目標也保留原數據，
   再討論保留、調整或撤回，不預先把 A／B 效益相加。
