# 固定工作負載與量測契約

更新：2026-10-18。修正後 AP5B v1 已凍結；
[manifest](../baselines/ap5b-post-lsu-v1/manifest.json)是來源、ELF、fixture／尺寸／容差、
記憶體與實體條件的機器可讀契約，[正式證據](evidence/2026-10-18/post-lsu-baseline/README.md)
保存全部 27 項原始結果。兩個主集合各自驗收，不混成單一總分。

## 主集合與輔助測試

| 集合 | 角色 | v1 狀態 |
| --- | --- | --- |
| Embench-IoT 1.0 完整 19 項 | 一般嵌入式主目標 | 原始資料、精度、暖機與迭代不變；固定 ELF，正式 19/19 通過 |
| scalar FP32 DSP 四項＋矩陣／ML 四項 | 浮點主目標 | 兩群各 50%；原 fixture／容差與 ELF 固定，正式 8/8、3,629 筆數值通過 |
| CoreMark 1.0 | 歷史對照、快速檢查與獨立附表 | 不併入主分數；正式報告須另符合上游執行規則 |
| 專案微型／六案例 LSU 測試 | 歸因、危險情境與優化假設 | 不代替完整集合，不將等待計數直接換算可省週期 |

Embench 版本為 `embench-1.0`，SHA
`0466a18e4f6b47e19598d7c6ba72916d54b68f65`；
[上游](https://github.com/embench/embench-iot)、[固定來源](../software/embench/embench-iot)。
完整集合為 `aha-mont64`、`crc32`、`cubic`、`edn`、`huffbench`、`matmult-int`、
`minver`、`nbody`、`nettle-aes`、`nettle-sha256`、`nsichneu`、`picojpeg`、
`qrduino`、`sglib-combined`、`slre`、`st`、`statemate`、`ud`、`wikisort`。
保留上游數值語意與其中的軟體 double／函式庫成本，不把單一程式改寫成 FP32。
舊 14 項 runner 與舊工具鏈分數不作本次加速比的分母。

FP32 來源為固定 CMSIS-DSP、KissFFT、PolyBench/C。集合為 FIR、IIR biquad、
複數 FFT、PID，以及 GEMM、BiCG、Cholesky、線性 SVM；
[來源與獨立參考方法](FP32_BALANCED_PROPOSAL.md)保留資格沿革。
FIR／IIR 分段狀態、PID 軌跡、FFT 複數輸出、矩陣輸出／重建及 SVM 標籤
都納入核對。這是專案選定的 scalar FP32 集合，不宣稱完整上游 benchmark 分數。
現有日常 fixture 已成為 v1 契約；擴大資料、改容差或新增集合須先共同討論，
並替基線與候選重建同一份新契約，不能單方面更換。

## 編譯、計時與記憶體

- 裸機工具鏈固定 xPack GCC 15.2.0／newlib 4.5.0，ISA／ABI
  `rv32imf_zicsr / ilp32f`；完整命令在
  [build-contract.json](../baselines/ap5b-post-lsu-v1/build-contract.json)。主比較直接
  使用凍結 ELF bytes，避免重編譯差異冒充 CPU 改善。
- FP32 主設定為 `-ffp-contract=fast -fno-fast-math`；off 僅作獨立敏感度。
  [先前 off／fast 1.113×](FMA_CONTRACTION_REVIEW.md)是編譯器診斷收益，
  不計入未來 CPU 架構加速。
- 沿用原 ELF 的 RDCYCLE ROI，包含既有計時入口開銷，不事後扣除。
  deterministic 模擬以 DUT cycles 計效能；主機模擬 wall time 只反映流程成本。
- 1 MiB RAM、I／D 獨立通道。基線 core period **10,000 ps**，I response、
  I initiation interval、D response 各固定 **10,000 ps**；候選提頻時 ps 不變。
  取樣在到期後第一個 core edge，量化誤差另記錄。這是研究模型，未量得真實 SRAM。
- 主場景無 random extra delay 或 fault injection。延遲附表只把 D response
  改為基準的 2／4 倍，I timing 不變，不併入主分數。
- 原始結果、ELF hash、數值／checksum、記憶體交易與延遲 audit、ROI profile、
  退休 SP stack headroom 均保留。退休 SP 是診斷，不是瞬間 stack 峰值的形式證明。

## 實體與加速比

ASAP7 RVT、TT-only 建置、TT／SS／FF 獨立分析；global-route estimated
parasitics，共用平台 nominal wire RC。I/O delay、slew、load、uncertainty
固定為 manifest 的絕對值，不隨試驗 period 放寬。全核心面積含 PRF／SQ、
commit trace 與 clock／repair cells，外部 RAM 不含在內。

基線 **10 ns（100 MHz）、22,081.1184 µm²**；9.9 ns 在 SS setup 失敗，
10 ns 三 corner 全通過。候選須使用同一工具／模型、mapping／backend 政策、
修復餘裕、路由階段、時序網格與面積邊界。不得沿用不同 RTL 的 synthesis cache。
Detailed-route DRC／LVS、OCV、多 corner RC 抽取及活動量功耗仍是後續工作。

每項 `time = ROI cycles × qualified core period`；週期效率另報
`cycles_baseline / cycles_candidate`，正式系統時間加速為
`time_baseline / time_candidate`。Embench19 等權取幾何平均；FP32 的 DSP 與
矩陣／ML 各自取幾何平均，再以兩群各 50% 合併，子群結果各自可見。

已核准規劃目標：**兩個主集合各 ≥1.20×、標準元件面積 ≤1.10×**；
面積對應上限為 **24,289.23024 µm²**。功能失敗、缺項、超時、hash 不符或
時序未閉合使完整集合結果無效，不能縮小分母或以一般嵌入式改善掩蓋 FP32 未達標。
沒有另加未核准的子群最低改善或個別退步門檻。尚無候選架構的達標宣稱。

## 擴充與覆蓋邊界

既有 [Embench 資格](evidence/2026-10-17/embench-approved-rerun/README.md)、
[FP32 資格](evidence/2026-10-17/fp32-balanced-qualification/README.md)及
[LSU 介面修復](LSU_INTERFACE_FIX.md)的功能證據各保留其來源與分母。
本輪正式 DUT 量測不代表重新執行全部 Spike，或完整 RV32F rounding／flags、
NaN／Inf、trap 架構覆蓋。未解驗證項目見 [STATUS.md](STATUS.md)。

CoreMark-PRO、較大 FP32 資料與 stencil 可在未來另立契約；本階段未增加。
CoreMark 正式報告須符合[上游規則](https://github.com/eembc/coremark/blob/main/README.md)，
固定 26 次迭代不保證在任意 ASIC 頻率達到要求的執行時間。
