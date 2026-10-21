# FP32 均衡工作負載與資格檢查

更新：2026-10-20。已核准以下 4+4 項與兩個子群各 50% 的評分權重。
現有八份 fixture／尺寸／容差／ELF 已納入 [AP5B v1 契約](../baselines/ap5b-post-lsu-v1/manifest.json)，
[正式量測](evidence/2026-10-18/post-lsu-baseline/README.md)8/8、3,629 筆通過。
FP32 主集合 ≥1.20 倍已核准；未另加子群門檻。以下資格紀錄及較大資料提案保留原範圍。

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
其餘七項的後續裸機數值檢查已完成，見下節；FIR 舊 pilot 與新共同 harness
的計時入口不同，不將兩者的診斷週期差解讀為 CPU 改善。

KissFFT object 仍有軟體 double、`cos/sin/floor/sqrt`、配置器及錯誤輸出依賴。
原始碼中的 twiddle／分解初始化需要數學函式庫。建議固定 2 的冪次 FFT、
不同的輸入輸出緩衝區，將配置及初始化放在 ROI 外；完整 ELF 和呼叫追蹤
已在下述 256 點資格案例完成精確 ELF 的呼叫稽核及配置器 guard；
其他尺寸仍須重新確認。

## 八項裸機數值資格結果

從乾淨 commit `df97854c719014df862d6d6df450d02fe0cee756` 執行
`make qualify-fp-balanced-dut JOBS=4`：主機、Spike、DUT 各 **8/8 通過**，
目標 ELF 的 ISA／single-float ABI 均符合預期。完整
[封存證據](evidence/2026-10-17/fp32-balanced-qualification/README.md)包含每項資料、
輸入與參考值雜湊、編譯命令、逐筆原始輸出、工具身分與診斷週期。

獨立 Python double 參考先對序列化 binary32 輸入計算；DUT 與主機各輸出
3,629 筆結果，主機逐筆以 `abs(error) <= atol + rtol * abs(reference)` 重算檢查。
兩者八項輸出 checksum 全部一致；Spike 執行 ELF 內的 binary32 參考檢查，
其 MMIO 輸出不由 Spike 轉送。這不是完整指令／FP flag 差分測試。

| 核心 | 檢查數量 | 暫定 atol / rtol | DUT 最大絕對誤差 | 診斷 ROI 週期 |
| --- | ---: | --- | ---: | ---: |
| FIR | 574 | 1e-5 / 1e-5 | 0 | 75,326 |
| IIR | 528 | 1e-6 / 2e-5 | 7.603e-9 | 17,653 |
| FFT | 512 | 2e-5 / 2e-5 | 3.666e-6 | 41,929 |
| PID | 515 | 1e-5 / 1e-5 | 0 | 8,782 |
| GEMM | 500 | 1e-5 / 1e-5 | 2.456e-6 | 155,749 |
| BiCG | 80 | 1e-5 / 1e-5 | 1.971e-6 | 24,053 |
| Cholesky | 820 | 1e-4 / 2e-4 | 4.828e-7 | 225,987 |
| SVM | 100 | 分類標籤完全相同 | 0 | 45,492 |

FIR／IIR 包含整批、4×64 串流輸出及各自末端狀態，兩種分段結果逐位元一致；
PID 核對完整軌跡與末端狀態。FIR／PID 的這組二進位分數資料恰好運算精確，
誤差為零不代表已涵蓋一般捨入情境。

Cholesky 核對全部下三角及正對角，double 重建相對 infinity-norm 殘差為
`5.0252092818979085e-08`，低於暫定 `2e-5`；序列化輸入的 double 參考條件數
估計為 `1671.5124509163`。SVM 使用上游 test-1 固定模型：100 筆、10 維、
4 個 support vectors；全部標籤也與獨立 double 權重折疊參考一致。
最小決策絕對值為 `0.6061864351498374`，這組資料未涵蓋接近邊界的分類。

FFT 採上游 `NDEBUG` 關閉選用的 stderr logging；數值檢查仍啟用。
精確 ELF 的靜態呼叫稽核顯示計時函式閉包沒有軟體 double／libm 呼叫；
配置器 guard 確認本次沒有 malloc／free 嘗試。twiddle 配置與數學初始化在 ROI 外。
移植時的標頭／stderr 連結失敗已修正，原始開發失敗另存於封存，不當成 DUT 結果。

驗證器的六項正反向測試通過：包含錯誤數值、NaN／infinity、漏樣／重複樣本、
錯誤分類與超標的 Cholesky 重建殘差。這些容差在 DUT 執行前設定，沒有因失敗放寬。
日常尺寸的裸機數值資格已成立，現有 fixture 已凍結為 v1，FMA 主設定為 fast。
正式 ROI 含計時器成本、退休 SP 餘裕及固定 10 ns 記憶體／實體契約均已記錄；
stack 瞬間峰值未經形式證明；後續候選 CPU 結果另見 [A 雙操作點研究](evidence/2026-10-20/lsu-a-physical/README.md)。

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
v1 模型、輸入、規模及雜湊以 manifest／fixtures 為準；較大資料提案尚未核定。
模型訓練放在主機端，不計入推論 ROI。

較大資料提案的其他條件（未加入 v1 驗收規則）：

1. 係數、種子、輸入與模型固定；帶狀態的核心在暖機及量測前有明確重置規則。
   PID 採預錄輸入軌跡，ROI 不加入模擬被控物的計算。
2. 配置、初始化、計時器之外的 I/O 及結果檢查放在 ROI 外；輸出必須被驗證，
   防止整段計算被編譯器消除。計時批量須讓讀計數器成本低於 ROI 的 1%。
3. 2026-10-17 的 `-ffp-contract=off` 是當時來源資格探測條件。完成開／關對照後，
   使用者已核准 `fast -fno-fast-math` 作主設定，off 保留對照；v1 沿用原數值容差並鎖定 hash。
   不從 object 編譯成功推導任何 FP 正確性結論。
4. 每項須核對 RAM／stack 尖峰、完整輸出、數值容差及執行成本。
   日常欄的暫定大小已在 DUT 通過；里程碑欄尚未執行。
   已保留靜態 text/data/bss 與編譯器 stack frame 記錄，仍須量測實際 stack 峰值；
   PolyBench SMALL 陣列尖峰至多 115,200 bytes，須另做 RAM 餘裕確認。

## 已核准的均衡評分權重

控制／DSP 和矩陣／ML 各占 FP32 主成績的 **50%**，子群內每項等權。
令每項加速比為相同量測契約下的 `baseline_time / candidate_time`：

- `G_DSP = geomean(FIR, IIR, FFT, PID)`。
- `G_MAT_ML = geomean(GEMM, BiCG, Cholesky, SVM)`。
- `G_FP32 = sqrt(G_DSP × G_MAT_ML)`。

兩個子群都個別列出結果及改善幅度；目前沒有額外子群門檻，
任何新增門檻都須先共同審核。
Embench 一般嵌入式集合仍獨立驗收；「一般與 FP32 各 ≥1.20 倍」
及「面積 ≤1.10 倍」已核准為規劃目標，正式 v1 量測契約與 global-route 基線已建立。
[A 候選研究](evidence/2026-10-20/lsu-a-physical/README.md)在 100 MHz 的 FP32 GM 為 1.078255×，
101.01 MHz 為 0.700275×，兩者皆保留原八項與 3,629 筆數值；目標仍未達。
任一預定項目未通過或超時，整個 FP32 主分數無效，不自動縮小分母。

## FMA 融合政策的後續實驗（2026-10-18）

[同條件對照](FMA_CONTRACTION_REVIEW.md)在乾淨來源 `581ee86` 上完成 off／fast
各 8/8 主機、Spike、DUT 檢查。資料、參考及容差與上面日常資格完全相同；
兩組使用同一修正後 RTL。控制／DSP、矩陣／ML 與等權綜合診斷週期比
分別為 1.133×、1.094×、1.113×；並保存 ROI 實際退休 FMA 計數。
部分輸出不同，仍通過所有原數值門檻；GEMM／Cholesky 的最大誤差略增。

比較前發現 FMA 相消精度與次正規 packing 問題並修正，3,400 個有限輸入的
精確值／旗標案例及完整 Embench 回歸通過。舊資料保留為其來源版本的歷史證據。
後續使用者已核准 fast 作主設定，qualifier 預設改為 fast；off 保留敏感度附表。
這些不是 CPU 架構改善分數，這份歷史對照不替代後來已成立的 v1 global-route 基線。
後續的[退休指令／等待分析](FMA_BOTTLENECK_REVIEW.md)在相同 RTL 上確認
FIR／BiCG 減少量全部來自乘加融合；load response 與 store ack 等待暴露，
解釋週期改善有限。預設 fast 的獨立入口 8/8 通過且 ELF 與明確指定 fast 相同。
