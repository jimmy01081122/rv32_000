# FP32 均衡工作負載與資格檢查

更新：2026-10-17。已核准以下 4+4 項與兩個子群各 50% 的評分權重。
資料大小、數值容差、編譯與量測契約及子群改善門檻仍需資格檢查與共同審查；
FP32 主集合 ≥1.20 倍已核准為規劃目標。

## 已選集合

| 子群 | 核心 | 建議來源 | 觀察重點 |
| --- | --- | --- | --- |
| 控制／DSP | FIR | CMSIS-DSP `arm_fir_f32` | 乘加、延遲線與連續資料搬移 |
| 控制／DSP | IIR biquad | CMSIS-DSP `arm_biquad_cascade_df2T_f32` | 遞迴狀態與短資料相依鏈 |
| 控制／DSP | 複數 FFT | KissFFT `kiss_fft`，float、out-of-place | 複數乘加、蝶形運算與非連續存取 |
| 控制／DSP | PID | CMSIS-DSP `arm_pid_f32` | 逐筆控制計算與跨取樣狀態相依 |
| 矩陣／ML | GEMM | PolyBench/C `gemm`，FP32 | 矩陣乘加、重用與吞吐 |
| 矩陣／ML | BiCG | PolyBench/C `bicg`，FP32 | 矩陣向量存取及兩組累加 |
| 矩陣／ML | Cholesky | PolyBench/C `cholesky`，FP32 | 相依計算、除法與平方根 |
| 矩陣／ML | 線性 SVM | CMSIS-DSP `arm_svm_linear_predict_f32` | 固定模型的分類推論、點積與判斷 |

SVM 加入實際分類介面；此子群仍是核心運算集合，尚不代表完整神經網路應用。
原先已初檢的 `jacobi-2d` 保留作 stencil／記憶體診斷候選，不列入這份 4+4 集合。
原有四項 PolyBench 的[初檢紀錄](WORKLOAD_QUALIFICATION_2026-10-16.md)保留原範圍。
這是專案選定的 scalar FP32 集合，報告不沿用上游完整 benchmark 的官方分數名稱。

## 版本與初步可移植性

| 來源 | 固定候選版本 | 授權 |
| --- | --- | --- |
| [CMSIS-DSP](https://github.com/ARM-software/CMSIS-DSP/tree/4b6f26593e9d3b24a9bc93b3646a3a859238eae2) | v1.18.0；`4b6f26593e9d3b24a9bc93b3646a3a859238eae2` | Apache-2.0 |
| [KissFFT](https://github.com/mborgerding/kissfft/tree/7bce4153c6bc8aba2db0e889e576f9d00505cbe1) | 131.2.0；`7bce4153c6bc8aba2db0e889e576f9d00505cbe1` | BSD-3-Clause |
| [PolyBench/C](https://sourceforge.net/projects/polybench/files/polybench-c-4.2.1-beta.tar.gz/download) | 4.2.1-beta；封存檔 SHA-256 見初檢紀錄 | 上游 Ohio State 發行授權 |

本次未改動上游來源，使用既有 `rv32ooo-fp:p1`：GCC 15.2、
`-std=gnu11 -O3 -ffp-contract=off -march=rv32imf_zicsr -mabi=ilp32f`。
CMSIS-DSP 以其 `__GNUC_PYTHON__` 選項停用 CMSIS-Core 相依，走純 C scalar 分支；
未啟用 ARM DSP、Neon 或 MVE。

下列 **9 個 translation units × 2 種目標，18/18 object 編譯通過**：

- FIR 與 init、biquad DF2T 與 init、PID init 與 inline 函式包裝：6 個。
- 線性 SVM predict 與 init：2 個。
- KissFFT `kiss_fft.c`：1 個。

兩種目標為 Ubuntu GCC 11.4 主機及 RV32IMF GCC 15.2。
RV32 objects 的 attributes 均為 `rv32i2p1_m2p0_f2p2_zicsr2p0_zmmul1p0`。
反組譯可見單精度運算；這些 object 的初檢本身不構成數值或 DUT 驗收。
此次沒有執行 CMSIS-DSP 的完整上游測試套件。

已建立一項[可重跑 FIR 裸機 pilot](../scripts/qualify_fp_fir_pilot.py)：
`make qualify-fp-fir-pilot` 會先核對來源，建置主機與 RV32 程式，
再在 Spike 和 DUT 執行。固定暫定 32 taps × 256 samples、模數公式輸入；
每筆輸出與獨立 double 直接卷積作絕對誤差 `1e-5` 檢查，
並核對末端 FIR 狀態。初始化在計時區間外。主機與 DUT 輸出 checksum
均為 `30ef51c5`；Spike 的整個程式自我檢查通過。DUT 計時區間為
75,334 週期；ELF SHA-256 為
`91a6a903790aa3a17626e17c2d260e269637d74a507aa2e147b92411bf6a7506`。
完整原始結果與編譯命令見忽略版本控制的
`build/qualification/fp-balanced/fir-pilot/summary.json`。
這項尺寸及容差只供資格實驗，尚未核定為最終 4+4 量測契約；
其餘七項尚未完成裸機數值檢查。

KissFFT object 仍有軟體 double、`cos/sin/floor/sqrt`、配置器及錯誤輸出依賴。
原始碼中的 twiddle／分解初始化需要數學函式庫。建議固定 2 的冪次 FFT、
不同的輸入輸出緩衝區，將配置及初始化放在 ROI 外；完整 ELF 和呼叫追蹤
仍須確認計時區間內沒有非預期的軟體 double 或 heap 操作。

原始命令、object、反組譯與錯誤紀錄存於忽略版本控制的
`build/qualification/fp-balanced/`；這些來源不複製進 repo。
從 repo 根目錄執行 `make fetch-fp-sources` 取得缺少的來源，
`make check-fp-sources` 會核對兩個 Git commit、checkout 是否有追蹤檔修改、
PolyBench 封存檔 SHA-256 及本集合所需的來源檔內容。
來源驗證輸出在 `build/qualification/fp-balanced/source-summary.json`；
這是來源身分檢查，還不是數值資格驗收。
例如在 FP 映像內，可重現 FIR object 探測：

```bash
src=build/qualification/fp-balanced/CMSIS-DSP
riscv-none-elf-gcc -std=gnu11 -O3 -ffp-contract=off \
  -march=rv32imf_zicsr -mabi=ilp32f -D__GNUC_PYTHON__ \
  -I"$src/Include" -I"$src/PrivateInclude" \
  -c "$src/Source/FilteringFunctions/arm_fir_f32.c" \
  -o build/qualification/fp-balanced/fir-probe.o
```

## 資料與正確性資格方案

| 核心 | 日常資料候選 | 里程碑資料候選 | 獨立參考方法 |
| --- | --- | --- | --- |
| FIR | 32 taps × 256 samples | 64 taps × 1024 samples | 主機 double 直接卷積，檢查全部輸出及末端狀態 |
| IIR | 4 sections × 256 samples | 8 sections × 1024 samples | 穩定係數的 double 差分方程，檢查輸出及狀態 |
| FFT | 256 complex points | 1024 complex points | 主機 double DFT；檢查所有複數輸出與正規化規則 |
| PID | 單一狀態鏈、512 samples | 單一狀態鏈、4096 samples | 固定輸入軌跡及 double 遞推，檢查完整輸出序列與狀態 |
| GEMM | PolyBench MINI：20/25/30 | SMALL：60/70/80 | double 矩陣計算與完整輸出 |
| BiCG | MINI：M/N=38/42 | SMALL：116/124 | double 矩陣向量參考，核對兩組輸出 |
| Cholesky | MINI：N=40 | SMALL：N=120 | double 分解及重建殘差，記錄矩陣條件 |
| SVM | 固定上游 F32 model／samples／labels | 從上游 benchmark patterns 選第二個固定規模 | 所有分類標籤、獨立 double 決策值及邊界診斷 |

SVM 的生成程式使用 NumPy／scikit-learn 且未在該檔固定亂數種子；
先採 pinned commit 內的生成結果作資格檢查，不能無條件重跑生成器後沿用資料身份。
正式模型、輸入、規模及雜湊仍待核定；模型訓練放在主機端，不計入推論 ROI。

其他條件：

1. 係數、種子、輸入與模型固定；帶狀態的核心在暖機及量測前有明確重置規則。
   PID 採預錄輸入軌跡，ROI 不加入模擬被控物的計算。
2. 配置、初始化、計時器之外的 I/O 及結果檢查放在 ROI 外；輸出必須被驗證，
   防止整段計算被編譯器消除。計時批量須讓讀計數器成本低於 ROI 的 1%。
3. 本次 `-ffp-contract=off` 是來源資格探測條件。正式 FMA 融合政策與容差在
   看優化成績前核定；不從 object 編譯成功推導任何 FP 正確性結論。
4. 每項須核對 RAM／stack 尖峰、完整輸出、數值容差及執行成本。
   上表大小尚未在 DUT 執行；PolyBench SMALL 陣列尖峰至多 115,200 bytes，
   其餘程式連結後仍須逐項確認符合現有 1 MiB RAM。

## 已核准的均衡評分權重

控制／DSP 和矩陣／ML 各占 FP32 主成績的 **50%**，子群內每項等權。
令每項加速比為相同量測契約下的 `baseline_time / candidate_time`：

- `G_DSP = geomean(FIR, IIR, FFT, PID)`。
- `G_MAT_ML = geomean(GEMM, BiCG, Cholesky, SVM)`。
- `G_FP32 = sqrt(G_DSP × G_MAT_ML)`。

兩個子群都個別列出結果及改善幅度。建議總分達標時兩個子群都必須改善，
子群最低門檻仍需共同審核，不以總分掩蓋其中一群退步。
Embench 一般嵌入式集合仍獨立驗收；「一般與 FP32 各 ≥1.20 倍」
及「面積 ≤1.10 倍」已核准為規劃目標，正式量測契約與基線尚未建立。
任一預定項目未通過或超時，整個 FP32 主分數無效，不自動縮小分母。
