# 固定工作負載與量測契約草案

更新：2026-10-17。已確認：一般嵌入式與 FP32 效能同等重要，兩者都需要改善。
FP32 內部也確認採控制／訊號處理與矩陣／ML 均衡方向。
已確認：FP32 的 4+4 項及兩子群各 50% 權重。
待確認：來源/資料集/編譯選項、記憶體條件、基線與數字門檻。
目前 runner 尚未實作完整集合。

初步證據見[2026-10-16 資格檢查](WORKLOAD_QUALIFICATION_2026-10-16.md)：
缺少的五項 Embench 通過主機自我檢查，但目標連結受工具鏈函式庫阻礙；
四項 PolyBench 的 MINI／SMALL 已完成主機執行及 RISC-V object 編譯，
尚未完成裸機執行與數值驗收。
新建的獨立 FP 工具鏈已讓[全部 19 項通過建置與 Spike 自我檢查](PROGRESS_REVIEW.md)；
`minver` 的 FP store 旁路錯誤已修正，完整 19 項也通過 DUT 自我檢查。
量測契約與實體結果仍待確認，集合效能基線未成立。

## 候選集合

| 集合 | 角色 | 目前狀態 |
| --- | --- | --- |
| Embench-IoT 1.0 全部 19 項 | 一般嵌入式主目標 | FP 資格腳本已建置並在主機／Spike／DUT 驗證 19 項；現有效能 runner 仍只跑 14 項 |
| 控制／DSP、矩陣／ML 均衡 FP32 子集 | 浮點主目標 | 已選 4+4 項、子群各 50%；部分來源已初檢，裸機與數值資格待完成 |
| CoreMark 1.0 | 歷史對照、快速檢查與獨立附表 | 已有 port 與 runner；短跑屬開發量測 |
| 專案微型測試 | 瓶頸歸因、危險情境與優化假設 | 部分已存在；不併入應用總分 |

兩個主集合各自計算加速比及幾何平均，不把所有程式混成單一總分。
CoreMark 不作為 FP32 效能代理；正確性測試與效能驗收各自保留。

## Embench 候選清單

版本：`embench-1.0`，SHA `0466a18e4f6b47e19598d7c6ba72916d54b68f65`。
[上游專案](https://github.com/embench/embench-iot)；
[固定版本來源](../software/embench/embench-iot)。

現有 14 項：`aha-mont64`、`crc32`、`edn`、`huffbench`、`matmult-int`、
`nettle-aes`、`nettle-sha256`、`nsichneu`、`picojpeg`、`qrduino`、
`sglib-combined`、`slre`、`statemate`、`ud`。

待補的五項及依賴：

| 項目 | 資格確認重點 |
| --- | --- |
| `minver` | 主要為單精度矩陣反解；確認 FP 指令、結果與數值容差 |
| `wikisort` | 排序與資料搬移，含 `sqrt` 函式庫依賴 |
| `cubic` | 含 double/long double 及數學函式庫依賴 |
| `nbody` | double 數值模擬及 `sqrt` |
| `st` | double 統計計算及數學函式庫依賴 |

RV32F 不提供 double 硬體運算。完整 Embench 成績包含軟體浮點/函式庫成本，
因此應稱為一般嵌入式集合，而非純整數或純 FPU 集合。保留上游數值語意，
不把 double 改成 float 後沿用原集合名稱。

目前 [runner](../scripts/run_embench.py) 使用 `rv32im_zicsr`、`ilp32`，
預設 `-O3`。是否改採允許 F 的設定，必須在建置所有候選程式及檢查反組譯後
共同凍結；一旦更換，AP5B 與候選 RTL 都用同一套新設定重新量測。
新[資格腳本](../scripts/qualify_embench_candidates.py)已以
`rv32imf_zicsr / ilp32f` 建置及在 Spike 執行 19 項，但未改動舊效能 runner
或驗收門檻；新設定尚須完成 DUT 正確性和工作負載契約討論。
歷史 14 項分數與新的 19 項分數不可直接相除當作架構加速比。

## FP32 候選清單

使用者已確認控制／訊號處理與矩陣／ML 兩者均衡。
已選以下 4+4 項，兩個子群各占 50%；資料大小與數值契約尚未凍結。

| 子群 | 候選 | 預期觀察行為 |
| --- | --- | --- |
| 控制／DSP | FIR、IIR biquad、複數 FFT、PID | 乘加、濾波／控制狀態、蝶形與短相依鏈 |
| 矩陣／ML | GEMM、BiCG、Cholesky、線性 SVM | 矩陣重用、除法／平方根及分類推論 |

來源為 CMSIS-DSP、KissFFT 及 PolyBench/C；可用 `make fetch-fp-sources`
下載並核對[固定來源](FP32_BALANCED_PROPOSAL.md)。固定版本、初始尺寸、
參考方法與評分公式見[均衡集合](FP32_BALANCED_PROPOSAL.md)。
新增來源的 9 個 translation units 均通過主機及 RV32 object 編譯；
FIR 已有[暫定裸機 pilot](FP32_BALANCED_PROPOSAL.md) 通過主機、Spike、DUT
逐筆數值與狀態檢查，其餘七項尚無連結／執行／數值驗收結果。
原有 `jacobi-2d` 初檢仍有效，保留作 stencil／記憶體診斷候選。

資格確認須固定支援 FP32 的版本與設定，檢查 ELF 實際指令與函式庫呼叫，
避免量到非預期的軟體 double。完整輸出須與參考結果比較；浮點容差、
乘加融合規則、捨入/例外需求應在看到優化結果前訂好。
候選方案為小資料集供日常回歸、另一固定資料集供里程碑驗收，兩者分開報告。
報告名稱明列「專案選定的 scalar FP32 集合」，不宣稱完整上游套件分數。

## 必須凍結的條件

1. Benchmark SHA、來源修改、輸入資料/種子、資料大小、暖機及迭代次數。
2. GCC、libc/libm/libgcc 版本、ISA、ABI、全部編譯/連結選項與 ELF 雜湊。
3. 計時區間、計時器、結果/CRC/浮點容差檢查，以及超時與失敗的處理方式。
4. 記憶體容量、服務延遲、頻寬、背壓與隨機種子；先驗證模型參數的握手意義。
5. RTL SHA、核心配置、實體工具/PDK、角落、I/O 預算及通過時序的頻率。

現有模擬 RAM 為 1 MiB，資料延遲參數預設為 1、隨機額外延遲預設為 0。
這是模擬環境，不能當作已實作 SRAM。核心提頻時，固定 cycle 延遲等於讓
記憶體服務速度同步改變；須明列此假設，或使用固定時間/獨立時脈的系統模型。
延遲敏感度場景分別報告，主成績採哪個場景待共同確認。

## 指標與數字草案

每個工作負載保留結果正確性、計時週期、退休指令、IPC、程式大小及原始記錄。
FP32 分別計算控制／DSP 及矩陣／ML 的幾何平均，再以兩群各 50%
合併；兩群結果各自可見，子群最低改善門檻待共同審查。
每週期效率用 `cycles_baseline / cycles_candidate` 比較。
估算吞吐使用 `time = cycles / closed_frequency`，再對各程式的
`time_baseline / time_candidate` 取等權幾何平均；只有記憶體與實體條件符合
已凍結的比較契約時，才能合併週期與頻率。主機模擬時間另列為流程成本。

草案為：兩個主集合各自 ≥1.20 倍、標準元件面積 ≤1.10 倍、個別程式退步
超過 5% 進入共同審查。這些數字尚未核定；絕對頻率與能耗目標待基線後討論。
不允許用通過的子集自動縮小分母，或以整數進步掩蓋浮點未達標。

## 資格確認及擴充

先驗證所有候選程式的建置、執行成本與結果，再審查代表性、凍結契約。
任何未完成項目須明列，未通過正確性檢查的量測不納入有效效能成績。
CoreMark 正式報告須符合其[執行與報告規則](https://github.com/eembc/coremark/blob/main/README.md)，
包括宣告時脈下的執行時間與記憶體條件；固定 26 次迭代不是普遍適用的門檻。

CoreMark-PRO 可列後續候選，需要評估裸機 port、記憶體需求與執行成本。
本階段不要求安裝新硬體或商用工具，也尚未增加這個集合。
