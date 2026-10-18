# FMA 融合政策與同條件對照

更新：2026-10-18。這輪比較編譯器是否融合乘加；兩組使用同一份修正後 RTL，
沒有切換 CPU 的 FMA 硬體。正式 FMA 政策尚未凍結。

## 開與關的意思

對 FP32 的 `a*b+c`，`round` 表示依浮點捨入模式取 binary32 結果：

- **off**：`round(round(a*b)+c)`，乘法、加法各捨入一次。
- **fast**：允許形成 `round(a*b+c)`，乘積保留精度，最後只捨入一次。

實際比較 `-O3 -fno-fast-math -ffp-contract=off` 與
`-O3 -fno-fast-math -ffp-contract=fast`。`fast` 是這個選項允許融合的值，
沒有啟用 `-ffast-math` 的廣泛重排或其他假設；編譯器也不保證每個乘加都融合。
`off` 不會禁止程式明確要求的 FMA intrinsic／組合語言；本輪八個 ROI 的
退休 FMA 計數實際為零，fast 則八項均有 FMA。

例：`a=1+2^-23`、`b=1-2^-23`、`c=-1`，分開運算得到 0，融合得到
`-2^-46`。兩者語意不同，不能要求 checksum 一律相同。單次 FMA 更接近該
實數乘加表達式，但整個演算法的最大誤差不保證下降；應按既定數值契約核對。
浮點旗標也可能不同：此例分開運算有 NX，融合結果可精確表示而沒有 NX。

## 比較條件與結果

完整可執行來源：`581ee86f1bd55bc6eff7cc123c660ab94446eb6f`，執行起迄工作樹乾淨。
[封存](evidence/2026-10-18/fma-contraction/README.md)保留原始日誌、命令、來源／映像／ELF
雜湊與數值報告；[機器可讀比較](evidence/2026-10-18/fma-contraction/comparison.json)
核對兩組來源、工具鏈、資料、容差及模擬器一致。

共同條件：xPack GCC 15.2.0、RV32IMF+Zicsr／ilp32f、scalar 上游核心，
1 MiB RAM、資料服務延遲 1 cycle、無隨機額外延遲。
沿用已通過日常資格的八項資料、參考答案與容差；每項計一次初始化後的核心呼叫，
設定及輸出檢查在 ROI 外，未新增暖機。計時器成本仍含於原本量測方式，尚未校正。

| 核心 | off ROI cycles | fast ROI cycles | off／fast 加速比 | fast ROI 退休 FMA |
| --- | ---: | ---: | ---: | ---: |
| FIR | 75,326 | 74,311 | 1.014× | 8,192 |
| IIR | 17,653 | 13,523 | 1.305× | 4,096 |
| FFT | 41,929 | 40,867 | 1.026× | 1,536 |
| PID | 8,782 | 7,248 | 1.212× | 1,024 |
| GEMM | 155,749 | 133,275 | 1.169× | 15,000 |
| BiCG | 24,053 | 23,927 | 1.005× | 3,192 |
| Cholesky | 225,987 | 194,161 | 1.164× | 10,660 |
| SVM | 45,492 | 43,392 | 1.048× | 4,400 |

控制／DSP 幾何平均 **1.133×**；矩陣／ML **1.094×**；兩群各 50% 得 **1.113×**。
這是目前資料的編譯政策診斷比值，不是正式上游 benchmark 分數，
也不是 CPU 架構變更的 ≥1.20× 成績。沒有量測 MHz、面積或實體時序。

統計器在第一、第二個 `rdcycle` 之間觀察 commit，排除兩個計數器讀取，
只統計退休的單精度四種 FMA 指令。每項確認恰有兩個標記；合成事件測試通過。
同一 FIR ELF／模型各以統計開與關重跑，off、fast 的 ROI 週期及 checksum
均不變；[原始檢查](evidence/2026-10-18/fma-contraction/profile-invariance.json)已封存。

## 數值與正確性

兩組各自 **8/8 主機、Spike、DUT 通過**；每組主機與 DUT 各逐筆檢查
3,629 個輸出。所有資料與原容差保持一致，沒有為 fast 放寬門檻。

| 核心 | off 最大絕對誤差 | fast 最大絕對誤差 | 兩組不同的輸出 word 數 |
| --- | ---: | ---: | ---: |
| FIR | 0 | 0 | 0 |
| IIR | 7.60254e-9 | 6.76218e-9 | 266 |
| FFT | 3.66617e-6 | 3.66617e-6 | 312 |
| PID | 0 | 0 | 0 |
| GEMM | 2.45571e-6 | 2.47739e-6 | 126 |
| BiCG | 1.97106e-6 | 1.75952e-6 | 24 |
| Cholesky | 4.82793e-7 | 5.42397e-7 | 518 |
| SVM | 標籤 100/100 相符 | 標籤 100/100 相符 | 0 |

FIR／PID 的 dyadic 資料容易精確表示，SVM 資料也不靠近分類邊界；
零誤差或相同標籤不代表一般輸入皆相同。串流狀態、Cholesky 重建等既有檢查亦通過。
正式尺寸、代表性與容差仍須依[集合紀錄](FP32_BALANCED_PROPOSAL.md)共同審查。

對照前的 cancellation 探針找出真實 RTL 錯誤：四種融合操作將應為
`±2^-46` 的結果算成 `±2^-26`，Spike 通過而舊 DUT 失敗。
[修正前紀錄](evidence/2026-10-18/fma-contraction/before/context.json)與失敗輸出獨立封存。
修正 `25c1dd1` 保留乘加的低位精度直到完整相消／正規化之後，
並修正共用 packing 對 subnormal 的編碼及 tininess-after-rounding 處理。
比較的 off 與 fast 都使用此修正，沒有拿錯誤舊模型當效能基線。

新增整數精確參考器，以固定 seed 產生 170 組有限輸入，涵蓋四種 FMA 指令、
五種 RISC-V 捨入模式，共 **3,400 案例**。Spike、DUT 的結果 bit pattern 及
全部五個 fflags 位元均相符；涵蓋相消、次正規輸入／輸出、溢位、下溢及 signed zero。
[向量與報告](evidence/2026-10-18/fma-contraction/finite/summary.json)可核查。
此有限集合不建立完整 IEEE-754／RV32F 正確性；NaN／Inf 輸入、非法模式／trap，
以及其他 FP 操作仍需更廣覆蓋。

修正後同一乾淨提交的回歸：lint／模擬建置通過、定向程式 **18/18**、
Spike commit 比對 **18/18**、完整 Embench **19/19 主機／Spike／DUT** 通過；
量測版本的兩類 Python 驗證器共 **12** 項控制測試通過；
量測後另補子程序失敗時使舊成績失效的防護，新增負向測試後 **13/13** 通過。
這些不是完整 ISA 或實體 signoff。
共用 FP 資料路徑已變更，正式基線必須重新取得 synthesis／PPA 結果。

## 建議共同決定的方向

建議將 **`-ffp-contract=fast -fno-fast-math` 列為正式主設定候選**，
保留 off 做數值及效能敏感度附表。目前 qualifier 預設仍為 off，
未代替使用者凍結正式政策。若採 fast，之後的 AP5B 基線與所有 CPU 候選
都須使用相同 fast ELF／資料／契約；不能把這次編譯收益算成架構改善。
Embench 的編譯政策也須獨立明列並在基線前固定，本輪未改其既有設定。

CPU 下一步建議先補 ROI 的停頓／相依與執行單元統計，再共同選第一項結構優化。
FIR 退休指令減少 11.82%，週期卻只減少 1.35%；BiCG 分別減少 16.20%、0.52%。
這值得追查第三運算元就緒、排程／功能單元接受能力及記憶體等待，但現有計數
還不能歸因。應同時檢查 Embench，維持兩類效能同等重要，並受 ≤1.10× 面積目標約束。

重跑：

```bash
make fetch-fp-sources
python3 -m unittest discover -s scripts -p 'test_fp*.py'
make compare-fp-contraction JOBS=4  # 先建置、執行有限 FMA 正確性檢查，再跑 off/fast
make test diff-test JOBS=4
make qualify-embench-fp-dut JOBS=4
make summarize-embench-fp-dut
```
