# 可信進度與 AP5B 基線審查草案

更新：2026-10-18。本文件供共同討論進度關卡、基線與量測契約；
尚未凍結 CPU 優化方向或效能驗收契約。專案沒有硬性時程。

## 目前能證明的進度

| 關卡（對照 [計畫](../PLAN.md)） | 證據 | 狀態 |
| --- | --- | --- |
| 1. 現行文件與歷史資料整理 | 規格與報告已校正／封存，連結及流程檢查完成 | 完成 |
| 2. 固定工作負載資格 | Embench 19/19 與 FP32 暫定日常資料 8/8 主機、Spike、DUT 通過；FP32 每次逐筆核對 3,629 筆結果，正式資料與契約未凍結 | 日常數值資格完成；量測資格進行中 |
| 3. 驗證基礎 | FP store 與 FMA 精度修正後，18/18 定向及 commit 比對、Embench 19/19、3,400 個有限 FMA 結果／旗標案例通過；ACT4／完整 FP 覆蓋仍缺 | 進行中 |
| 4. AP5B 雙類效能與實體基線 | 正式尺寸、FMA／計時／記憶體契約及新鮮實體量測未齊 | 尚未成立 |
| 5. 目標與第一項 CPU 方案 | 兩類各 ≥1.20 倍、面積 ≤1.10 倍已核准為規劃目標；第一項 CPU 方案尚未選定 | 部分完成 |
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

為確保 ELF 雜湊可重現，FP 資格腳本在連結後以 `strip --strip-unneeded`
移除 GCC 隨機命名的暫存 object 本機符號，同時保留 Spike 需要的
`tohost`、`fromhost`。連續兩次 `minver` 建置所得 ELF SHA-256 均為
`18aacebbf740134d2a42b5550224155b171250ebf3456c087030258ac1e66aff`，
兩次主機、Spike、DUT 自我檢查均通過；完整 19 項參考檢查也在這個
輸出規則下重跑並 19/19 通過。先前未去除本機符號的 ELF 雜湊仍對應其原始
追蹤，但不能與新 ELF 雜湊視為同一份檔案。

已選 FP32 集合的上游來源可由 `make fetch-fp-sources` 取得、
`make check-fp-sources` 核對：CMSIS-DSP 與 KissFFT 固定 Git commit，
PolyBench/C 固定封存檔 SHA-256 及所需檔案內容。本機三項來源檢查均通過；
它不代表裸機數值驗收。[來源檢查腳本](../scripts/prepare_fp_sources.py)
與[集合紀錄](FP32_BALANCED_PROPOSAL.md)保留準確版本及範圍。
另有 [FIR pilot](../software/fp_bench/fir_pilot.c) 已在主機、Spike 和 DUT
通過逐筆 double 卷積及末端狀態檢查；主機與 DUT 全部輸出的 checksum
均為 `30ef51c5`，DUT ROI 為 75,334 週期。這項輸入及 `1e-5` 容差
尚未核准為正式 FP32 量測契約，不能代替八項集合分數。

完成一次完整 19 項 DUT 診斷，主機、RV32 建置、Spike 和 DUT
自我檢查均 **19/19 通過**，全部 19 項都有 ROI 週期、總週期及退休指令。
原始命令、每項退出狀態、ELF 雜湊與 DUT 日誌已存入
[可審查證據](evidence/2026-10-17/README.md)。診斷報告的模擬器
SHA-256 為 `44d59f5b29fe427e20988799d2780e127b15f833f21e10a3af7348361e54c1c7`，
腳本 SHA-256 為 `677e52f1c508a6d79c93a9632c47f6014c23d02dcff68751e8d6dac5280f340a`。
ROI 週期範圍從 `wikisort` 的 2,173,042 到 `cubic` 的 14,490,894；
這些是單一 DUT 的診斷週期，尚無新舊架構加速比。
執行時工作樹已含下述 FP-store 修正但尚未 commit，JSON 中的 Git HEAD
只記到修正前的提交。正式基線須在乾淨提交、量測契約凍結後重跑。

新設定已抽查的 DUT 程式；表中 `minver` 是修正前的紀錄：

| 程式 | Spike 自我檢查 | DUT 自我檢查 | DUT 計時區間週期 | 結論 |
| --- | --- | --- | ---: | --- |
| `crc32` | PASS | PASS | 5,402,220 | 一般嵌入式個例 |
| `nbody` | PASS | PASS | 5,893,151 | 軟體 double 個例 |
| `minver`（修正前） | PASS | FAIL，退出碼 1 | 878,777 | FP store 資料錯誤，見下方修正紀錄 |

`minver` 的完整執行追蹤進一步找到第一筆可見差異：第 262,506 筆 commit
事件（從 0 起算），PC `0x80001220`、指令 `0x00d62027`，即
`fsw fa3, 0(a2)`。儲存位址均為 `0x80043980`，但 DUT 寫入
`0x00000000`，Spike 寫入 `0x41100000`（9.0）；之前 `fa3` 的載入
均為 9.0，後續 DUT 載入也讀到 0。後續檢查確定：整數與 FP physical register
編號屬不同 domain，但 [core 的 operand1 旁路](../rtl/core/rv32_ooo_core.sv)
先依編號接受整數 completion，才考慮 `FSW` 的 FP 資料。同號碰撞時可能把
整數結果寫進 FP store。[修正](../rtl/core/rv32_ooo_core.sv)依來源 domain
先選 FP 資料路徑，再處理整數旁路。

在原始 ELF（下方 SHA-256）上重建 DUT 後，`minver` 自我檢查從退出碼 1
變為 PASS；量測區間仍為 878,777 週期。修正後追蹤與原 Spike 追蹤在前
263,004 筆已解析 commit 事件相符，涵蓋原錯誤點第 262,506 筆。
下一個差異為 `rdcycle` 值寫入 `start_cycles_64` 的 store；兩個模型的計數值
本來不同，因此這項追蹤比較不宣稱整個程式的完整架構等價。
可重跑的 `make check-minver-fp` 同時檢查主機、Spike 與 DUT 自我檢查，
目前均通過；每次重建的 ELF 雜湊須與當次報告一起保存。

追蹤檔位於 `build/qualification/toolchain/minver-fp-{dut,spike}.trace`，
第一筆差異紀錄為同目錄的 `minver-first-divergence.txt`。
比較沿用專案 parser 的欄位及動態計數器正規化；未比較完整 trap／FP flag 狀態。
本次 `minver` ELF SHA-256：
`2060b84c6bd7133c60292c59d923a8b78647b3064646265131d715ebb72ecf09`；
DUT 模擬器 SHA-256：
`d84eb0db5f49be49bc6006c11c1c8ed4ad5cd82d675fa565bff8c3a6d45e64a9`。

修正前這三項的週期只供除錯；上面的完整 19 項功能診斷也不是正式加速比。
先前在較舊工具鏈下的
`cubic` DUT 試跑達 180 秒上限，未取得完成結果，不能算為新工具鏈的 DUT 結果。
目前診斷腳本[在此](../scripts/qualify_embench_candidates.py)；完整命令、ELF
SHA-256、原始輸出與失敗紀錄在忽略版本控制的 `build/qualification/`。

從 repo 根目錄重建：

```bash
make docker-build-sim                 # 首次建立 G1 基礎映像時
make docker-build-fp
make check-fp-env
make fetch-fp-sources               # 取得／核對已選 FP32 的固定上游來源
make qualify-embench-fp-reference    # 19 項主機、建置及 Spike 檢查
make check-minver-fp                  # 單項主機、Spike、DUT 正確性回歸
make qualify-fp-fir-pilot             # 暫定 FIR 逐筆數值與狀態檢查
```

用 `make qualify-embench-fp-dut` 會額外嘗試 19 項 DUT；本次功能診斷全通過，
正式量測契約仍待確認。單項可用
`python3 scripts/qualify_embench_candidates.py --toolchain fp --suite full --bench minver --run-spike --run-dut`
在 FP 映像內重現。完整執行後，`make summarize-embench-fp-dut` 檢查固定
19 項的主機／Spike／DUT 結果，另產出每項 ROI 週期及模擬器雜湊的診斷報告；
任一項失敗仍保留於報告，且不產生集合分數。新的 19 項設定不與舊
GCC／14 項成績相除。

## 已核准 Embench 19 項的乾淨版本重跑

使用者核准完整 Embench-IoT 1.0 的 19 項作一般嵌入式主集合後，
從乾淨 commit `7ba020297da6e6cdc4e5857fdde6ff57fec627d6` 重建 DUT 並執行
`make qualify-embench-fp-dut JOBS=4`。主機建置／自我檢查、RV32 建置、
Spike 及 DUT 自我檢查皆為 **19/19 通過**，沒有失敗或超時。
完整性報告及 ELF ISA／single-float ABI 檢查也各為 19/19 通過。

本輪採原始精度、GCC 15.2.0、`-O3`、`rv32imf_zicsr / ilp32f`、
`WARMUP_HEAT=1`、`CPU_MHZ=1` 縮放，以及目前 1 MiB RAM、資料延遲
1 cycle、無隨機額外延遲的模擬預設。19 項 ELF SHA-256、ROI／總週期與
退休指令數均與先前診斷一致；模擬器 SHA-256 也相同。

[本輪封存](evidence/2026-10-17/embench-approved-rerun/README.md)包含來源與映像
身分、完整命令、每項診斷週期、DUT 原始輸出、其他階段原始記錄及雜湊清單。
這補齊乾淨來源版本的 Embench 功能證據；上游自我檢查不等於完整指令追蹤或
FP flag 比較，量測契約與實體基線仍未成立，也尚未驗證 1.20 倍／1.10 倍目標。

## FMA 融合開／關的同條件對照

[比較紀錄](FMA_CONTRACTION_REVIEW.md)使用乾淨來源 `581ee86`、同一修正後 RTL、
資料及容差。off／fast 各 8/8 主機、Spike、DUT 通過；ROI 退休 FMA 在 off
皆為零，fast 八項皆有。診斷幾何平均：DSP 1.133×、矩陣／ML 1.094×、
兩群等權 1.113×。部分輸出因捨入改變，全部仍通過既有獨立數值檢查。

相消探針發現舊 FMA 的低位精度錯誤，已修正並封存修正前失敗；
3,400 個有限輸入／四種指令／五種模式的值與旗標檢查全部通過。
同一乾淨提交的 Embench 19/19 與定向／commit 比對 18/18 回歸通過。
這不是完整 FP ISA 證明，亦沒有量測新面積或 MHz。

建議 fast 作主設定候選、off 保留附表，尚未凍結政策或更改 qualifier 預設。
先補 FIR／BiCG 的相依、停頓與功能單元統計，再共同排序 CPU 結構方案；
此編譯器收益不能當成 ≥1.20× 架構目標的進度。正式 AP5B 基線須含修正後的新 PPA。

## 何時才可稱為可信 AP5B 基線

FP32 日常數值資格已補齊：[乾淨來源版本封存](evidence/2026-10-17/fp32-balanced-qualification/README.md)
對應 `df97854c719014df862d6d6df450d02fe0cee756`，主機／Spike／DUT 各 8/8。
`make qualify-fp-balanced-dut JOBS=4` 可重跑；六項驗證器正反向測試通過。
FIR／IIR 串流狀態、PID 軌跡、FFT 全複數輸出、矩陣輸出／重建與 SVM 標籤均核對；
其資料代表性與正式契約的限制見 [FP32 資格紀錄](FP32_BALANCED_PROPOSAL.md)。

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

## 已定目標與待共同決定事項

- 已核准完整 Embench 19 項作一般嵌入式主集合，保留原始精度及其中的軟體
  double 成本；CoreMark 保留獨立附表。編譯與量測契約仍須固定。
- 已核准 [FP32 集合](FP32_BALANCED_PROPOSAL.md)：控制／DSP 與矩陣／ML
  各 4 項、各 50% 權重。資料、容差與完整量測契約仍須資格確認。
- 已核准一般嵌入式和 FP32 **各 ≥1.20 倍**、標準元件面積 **≤1.10 倍**
  作為規劃目標；兩類都須達標。個別退步超過 5% 共同審查仍是提案。
  基線完成後須審查量測契約與目標可行性；任何目標調整都須再與使用者討論。
  絕對頻率和能耗數字屆時再定。
- 系統吞吐的主記憶體模型與服務時間尚須選定；固定 cycle 模型可先報
  週期效率，另列延遲敏感度。這項選擇會直接影響提頻收益，需在看優化結果前固定。

接下來須共同審查正式資料規模、容差與 FMA 政策，補齊計時／stack 餘裕與
記憶體及實體量測契約。CPU 結構優化須在正確性與基線成立後共同排序。
