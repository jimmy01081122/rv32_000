# 可信進度與 AP5B 基線審查草案

更新：2026-10-17。本文件供共同討論進度關卡、基線與數字；
尚未凍結 CPU 優化方向或效能驗收契約。專案沒有硬性時程。

## 目前能證明的進度

| 關卡（對照 [計畫](../PLAN.md)） | 證據 | 狀態 |
| --- | --- | --- |
| 1. 現行文件與歷史資料整理 | 規格與報告已校正／封存，連結及流程檢查完成 | 完成 |
| 2. 固定工作負載資格 | Embench 19/19 主機、RV32 建置及 Spike 自我檢查通過；FP32 原有四項完成主機／object 初檢，新增 DSP／SVM／FFT 來源完成 18/18 主機及 RV32 object 編譯 | 進行中 |
| 3. 驗證基礎 | 既有 18 項定向程式及 Spike 差異檢查曾通過；`minver` 在新設定的 DUT 自我檢查失敗，ACT4／FP 覆蓋仍缺 | 進行中、有阻礙 |
| 4. AP5B 雙類效能與實體基線 | DUT 全集合正確性、FP32 裸機輸出、記憶體契約及新鮮實體量測未齊 | 尚未成立 |
| 5. 目標與第一項 CPU 方案 | 兩類各 1.20 倍、面積 ≤1.10 倍仍是待共同審查的規劃值 | 待討論 |
| 6. 優化驗收 | 須對同條件 AP5B 基線驗證正確性、兩類效能及面積 | 未開始 |

進度以關卡、分母和原始證據呈現。程序超時、驗證失敗、缺少環境分別列出；
不將可建置、Spike 通過或某一項 DUT 通過換算成整個專案的完成百分比。

## 新工具鏈的證據邊界

舊 `rv32ooo-sim:g1` 映像中的 GCC 16.1 預建套件只有 D ABI 的函式庫。
新 [FP 映像](../containers/rv32ooo-fp/Dockerfile)沿用該映像的 Verilator／Spike，
額外固定 xPack GCC 15.2.0、新版 newlib 4.5.0，以及 `rv32imf_zicsr / ilp32f`
multilib。下載檔 SHA-256 固定於 [toolchain.lock](../toolchain.lock)。
目前本機映像 `rv32ooo-fp:p1` ID：
`sha256:2140263677b3a378d5cab75a3d0d4fd285ddb38a1a5a1f81f5cf97db024a02d5`。
完整 19 項參考探測已在工具鏈提交
`0cbc3411a8250eab87841b71ec0a48d85c7ffdfa` 上重跑。

使用相同的 `-std=gnu11 -O3 -march=rv32imf_zicsr -mabi=ilp32f`，
原始 Embench 1.0 的 19 項均通過：主機上游自我檢查、裸機 ELF 建置、
Spike 整個程式自我檢查。19 個 ELF attributes 均為
`rv32i2p1_m2p0_f2p2_zicsr2p0_zmmul1p0`、single-float ABI，未混入 A/C/D。
新 libm 需要的裸機 syscall 有[明確失敗處理](../software/embench/fail_syscalls.c)；
若被呼叫，程式會報錯，避免默默接受無效 I/O。這些結果證明移植及參考執行可行，
沒有證明 DUT 的全部指令、數值或效能正確。

新設定已抽查的 DUT 程式：

| 程式 | Spike 自我檢查 | DUT 自我檢查 | DUT 計時區間週期 | 結論 |
| --- | --- | --- | ---: | --- |
| `crc32` | PASS | PASS | 5,402,220 | 一般嵌入式個例 |
| `nbody` | PASS | PASS | 5,893,151 | 軟體 double 個例 |
| `minver` | PASS | FAIL，退出碼 1 | 878,777 | FP store 資料出錯，根因待定位 |

`minver` 的完整執行追蹤進一步找到第一筆可見差異：第 262,506 筆 commit
事件（從 0 起算），PC `0x80001220`、指令 `0x00d62027`，即
`fsw fa3, 0(a2)`。儲存位址均為 `0x80043980`，但 DUT 寫入
`0x00000000`，Spike 寫入 `0x41100000`（9.0）；之前 `fa3` 的載入
均為 9.0，後續 DUT 載入也讀到 0。這將問題縮小到儲存資料取得／傳遞，
還不能認定是哪個 RTL 模組的根因。此診斷未修改 CPU RTL。

追蹤檔位於 `build/qualification/toolchain/minver-fp-{dut,spike}.trace`，
第一筆差異紀錄為同目錄的 `minver-first-divergence.txt`。
比較沿用專案 parser 的欄位及動態計數器正規化；未比較完整 trap／FP flag 狀態。
本次 `minver` ELF SHA-256：
`2060b84c6bd7133c60292c59d923a8b78647b3064646265131d715ebb72ecf09`；
DUT 模擬器 SHA-256：
`d84eb0db5f49be49bc6006c11c1c8ed4ad5cd82d675fa565bff8c3a6d45e64a9`。

這三項的週期只供除錯；它們不是有效的 19 項分數。先前在較舊工具鏈下的
`cubic` DUT 試跑達 180 秒上限，未取得完成結果，不能算為新工具鏈的 DUT 結果。
目前診斷腳本[在此](../scripts/qualify_embench_candidates.py)；完整命令、ELF
SHA-256、原始輸出與失敗紀錄在忽略版本控制的 `build/qualification/`。

從 repo 根目錄重建：

```bash
make docker-build-sim                 # 首次建立 G1 基礎映像時
make docker-build-fp
make check-fp-env
make qualify-embench-fp-reference    # 19 項主機、建置及 Spike 檢查
```

用 `make qualify-embench-fp-dut` 會額外嘗試 19 項 DUT；現階段有已知失敗，
非「預期全通過」的流程。單項可用
`python3 scripts/qualify_embench_candidates.py --toolchain fp --suite full --bench minver --run-spike --run-dut`
在 FP 映像內重現。新的 19 項設定不與舊 GCC／14 項成績相除。

## 何時才可稱為可信 AP5B 基線

1. **程式與功能**：Embench 全 19 項及選定 FP32 子集有固定來源、編譯命令、
   ELF 雜湊及完整參考輸出；DUT 結果與獨立參考一致。修正 `minver` 等失敗，
   建立 FP rounding／flags、例外、記憶體回應及 redirect 覆蓋。
2. **量測契約**：固定 ROI、資料大小、迭代、1 MiB RAM 條件與資料記憶體服務模型；
   每項保留正確性、週期、退休指令、IPC、原始輸出和超時資訊。現有固定
   cycle 延遲模型會隨核心提頻而加速外部記憶體，系統時間比較須先處理此假設。
3. **實體結果**：對同一 AP5B SHA，在固定 ORFS／ASAP7、約束及角落取得
   可重現的時序、面積；用工作負載活動量測能耗。舊 AP5A 或 generic Yosys
   結果不能填補此欄。
4. **可比性**：基線與候選 RTL 用同一工具鏈、ELF、記憶體與實體流程。
   兩個主集合各自保留每項結果及幾何平均；任一失敗或超時均使該集合總分無效。

## 建議共同決定

- 是否採完整 Embench 19 項作一般嵌入式主集合，接受其中的軟體 double
  成本；CoreMark 保留獨立附表。建議採用，但須先讓 DUT 全部通過。
- 已確認 FP32 控制／訊號處理與矩陣／ML 兩者均衡。
  [新提案](FP32_BALANCED_PROPOSAL.md)為兩群各 4 項、各 50% 權重；
  項目、資料、容差及權重仍須資格確認，原先四項 PolyBench 不再是唯一候選。
- 暫定一般嵌入式和 FP32 **各 ≥1.20 倍**、標準元件面積 **≤1.10 倍**；
  個別退步超過 5% 共同審查。兩類都達標才算優化成功。
  這些數字待基線完成後審核，絕對頻率和能耗數字當時再定。
- 系統吞吐的主記憶體模型與服務時間尚須選定；固定 cycle 模型可先報
  週期效率，另列延遲敏感度。這項選擇會直接影響提頻收益，需在看優化結果前固定。

下一個可審查的工作單位是 `minver` 差異歸因及其回歸測試，再擴展 DUT
工作負載檢查。CPU 結構優化須在正確性與基線成立後共同排序。
