# LSU B v1 審查

2026-10-21。B 已完成獨立實驗：功能與完整同頻 cycle 診斷通過，
固定實體流程未通過時序。**目前不建議將這版 B 納入主線。**
凍結基線維持 `58a4159`，後續方向由使用者共同選擇。

| 項目 | A | B v1 |
| --- | ---: | ---: |
| 完整 Embench19，同頻 cycle 比 | 1.045830× | 1.029459× |
| 完整均衡 FP32 八項，同頻 cycle 比 | 1.078255× | 1.009599× |
| 標準元件面積 | 22,162.24152 µm² | 21,983.62194 µm² |
| 面積／凍結基線 | 1.003674× | 0.995585× |
| 100 MHz 三 corner 實體資格 | 通過 | 未通過 |
| 最短已測完整合格 period | 9,900 ps | 無 |

兩者 CPU 同頻診斷皆用 10,000 ps，I response／I initiation interval／D response
各固定 10,000 ps。A 的 100 MHz 資料已有實體資格，B 欄僅為 cycle 診斷，
不能將兩欄都當成已合格的系統時間成績。兩類各 ≥1.20×、面積 ≤1.10× 目標不變。

## 實作與驗證

B 來源為乾淨 `95ac0dd6451a1799f9f3fe948c7b74c02f5fccd2`，直接從凍結基線分支；
共用 A 已審查工具，但 33 個 RTL／simulation／physical 輸入中僅 LSU 不同。
完整 ROB tag 匹配、地址／資料有效、無例外／flush 且 RUN 的頭端 store，
可在 SQ marking 同拍提出請求。保留原 response-buffer 排除、一筆外部 outstanding、
16-slot SQ、成功 response 後才退休與精確 fault；未混入 A 的交接重疊。

原基線／B 各 62 項實際 LSU pin-driven cases、原 RTL 負向節拍控制、
directed 18、Spike 18、介面 48、fixed-time 58、finite FMA 3,400 全通過。
完整 27/27、原 3,629 筆 FP32 輸出、原 ELF／容差／尺寸、memory／stack、
退休分類與逐 PC／instruction／kind 工作量均核對。31 項契約／review controls
及跨候選、mapping、baseline 模式的實際拒收控制通過。這些是定向與工作負載資格，
完整 ISA／特殊 FP 等既有覆蓋缺口仍在。

理想 16-store 串流從 48 降為 32 cycles，機制假設成立；完整 CPU 收益則小得多。
BiCG 的 store 等待減少 4,784 cycles，但後續 FP load 頭端等待增加 4,577，
總 ROI 只減少 207。PID 由 7,248 增為 8,261 cycles，執行時間增加 13.9763%；
GEMM 也略退步。這是等待位置的非重疊週期對帳，尚未證明全部排程根因。

## 實體結果與判定

沿用原 pinned ORFS／ASAP7 RVT、TT-only、ABC 5,500 ps mapping、14,000 ps
backend、TT 45% slew／50 ps hold ECO 與完整 global route。三階段均實際 exit 0，
輸入雜湊不變；B 使用自己的網表、CTS、GRT，未重用 A 或基線 cache。
最終 overflow、兩次 ECO placement failures、antenna net／pin violations 均為零。
面積含所有 clock／repair cells 與 debug／commit trace，不含外部 RAM。

| 實測 period | SS setup ps | FF hold ps | 完整三 corner 結果 |
| ---: | ---: | ---: | --- |
| 10,000 ps | −2,282.992 | −0.333 | 未通過 |
| 12,200 ps | −82.991 | −0.333 | 未通過 |
| 12,300 ps | +17.009 | −0.333 | 未通過 |
| 14,000 ps | +1,717.009 | −0.333 | 未通過 |

12.3 ns 只是相鄰 100 ps 網格的 setup-only 通過點，仍有 FF hold 失敗，
沒有最快完整合格操作點，因此沒有第二組正式效能量測。
完整 `review_cpu_experiment.py` 已正確拒收這份實體資料；功能／同頻原始資料
另由獨立 reviewer 完整通過，兩種資格沒有混在一起。

最差 SS setup 位於 FP 輸入到 completion 暫存器，FF hold 位於
`dmem_req_ready` 到 LSU in-flight tracking 暫存器。FPU RTL 沒改；這是一次固定
映射／布局的結果，不能據此證明頭端 store 邏輯必然造成全部時序退步。
本次維持原門檻與 flow，沒有放寬失敗值或自動改成 A+B。

後續[時序診斷](LSU_B_TIMING_DIAGNOSIS.md)已完成：9 組原 routed corner
重現通過，另 3 組 synthesis zero-wire 診斷確認未改 FPU 的時序差距在布局前
就已出現；FF 則有兩個 LSU tracking hold 端點失敗。
建議先共同選擇可比實體流程的改善，再決定下一項架構實驗；原門檻與基線仍不變。
A／B 個別收益不能直接相加。B v1 的功能機制保留為證據，目前實作不取代基線。

[完整原始證據與重播條件](evidence/2026-10-21/lsu-b/README.md)包含所有 27 項、
失敗 corner、最終 ODB／網表、binary gzip、來源譜系與 copy inventory。
[事前契約](../experiments/lsu-b-v1/manifest.json)與
[B 實驗入口](../experiments/lsu-b-v1/README.md)保留獨立範圍。
