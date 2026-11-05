# 第 1、3、5 項：同流程 A 比較與 FP 證據研究

更新：2026-11-05（UTC）；第一輪觀測資料日期為 2026-10-30。使用者已選擇架構圖的 1、3、5，本輪已完成獨立 A 的同流程實體資格、兩個時脈點的完整重測、FP 阻塞觀測與 FPU 時序分析；下一個 RTL 候選仍共同選擇。CPU RTL、凍結工作負載、10 ns 記憶體政策及兩類各 ≥1.20×／面積 ≤1.10× 目標維持原狀。

| 項目 | 本輪狀態 | 尚未完成 |
| --- | --- | --- |
| 1：LSU A 同流程比較 | 新 native 建置、TT／SS／FF、實際相鄰失敗點及兩次完整 27 項重測通過 | 共同選擇後續架構候選 |
| 3：FP EX0／單元 ready／completion | baseline、A、B 的唯讀觀測與獨立對照通過 | 選定並實作發射策略候選，再跑完整工作負載 |
| 5：FPU 路徑／延遲／吞吐 | 既有 native 路徑、實際單元延遲和連續發射證據已核對 | 新組合邏輯或 pipeline 候選的等價、實體與系統時間實驗 |

## A 同流程比較完成

A 在乾淨來源 `8a1c582` 使用與 baseline／B 相同的共同 FPU、TT 建置、45% slew／40 ps hold 修復及單一 `dmem_req_ready` BUFx2 guard。獨立 TT／SS／FF 審查通過 **9.4 ns 與 10 ns**；9.3 ns 的 SS setup 實測失敗 **−52.245 ps**，9.4 ns 為 **+47.755 ps**，FF hold 為 **+16.906 ps**。這是實際測試的 100 ps 邊界，不是由 WNS 外推頻率。

| 同流程實體結果 | baseline | A | B |
| --- | ---: | ---: | ---: |
| 標準元件面積（µm²） | 21,545.492940 | **21,602.442420** | 21,309.821820 |
| 相對同流程 baseline 面積 | 1.000000× | **1.002643×** | 0.989062× |
| 最短已測合格 period | 9.5 ns | **9.4 ns** | 9.6 ns |

A 相對原凍結基線面積為 **0.978322×**，符合 ≤1.10× 預算；此比例包含共同流程修復。guard 恰增加一個 BUFx2、0.0729 µm²，原有 cells／pins／ports 的連接核對通過，沒有新增暫存器。

A 在獨立乾淨工作目錄 `bf6702c`，用已資格確認的 A executable 完成兩次全 27 項重測。每次皆通過 3,629 個 FP32 數值、固定 10 ns 記憶體稽核及與凍結 baseline 相同的 per-PC 退休工作量；100 MHz 的全部 profile／memory JSON 更逐 byte 符合原 A。來源、ELF、模型、原資格確認日誌與 shared-FPU 等價／映射連結均重新核對。沿用的 directed／Spike／interface／fixed-time／FMA 資格確認沒有冒稱本輪重新執行。

| 完整工作負載，對原凍結 100 MHz baseline | Embench19 GM | FP32 八項平衡 GM |
| --- | ---: | ---: |
| **A：100 MHz，10 ns** | **1.045830×** | **1.078255×** |
| A：106.38 MHz，9.4 ns | 0.765250× | 0.737524× |
| B：100 MHz，10 ns | 1.029459× | 1.009599× |
| B：104.17 MHz，9.6 ns | 0.748705× | 0.719680× |

9.4 ns 下，固定 10 ns 記憶體服務需兩拍才可取樣；原始 audit 的實際回應為 **18.8 ns**，因此提頻後系統時間更差。A 的兩類 ≥1.20× 目標仍未達成。若從 A 的 100 MHz 結果繼續，Embench／FP32 分別還需要約 **14.74%／11.29%** 額外相對加速。

共同 100 MHz 下，A／B 的集合加速比為 **1.015902×／1.068003×**；27 項中 A 快 18 項、B 快 9 項。FP32 的 IIR、FFT 仍是 B 較快，不能由集合平均推論每項都改善。建議以 **A 的 100 MHz 結果作下一輪選項比較的參考**，保留原凍結 baseline 和目前 B 分支，先共同決定下一個候選。

## 觀測結果

先核對三版本各 27 項，合計 **81 份既有 profile** 的雜湊、ELF、cycle partition、退休解碼及原始日誌。正式 baseline 使用 `measurement-formal-10000ps`；早期 5.5 ns 準備資料不納入比較。

再對每版本的 FP32 八項及 Embench `minver` 執行 observer off/on，合計 **27 組、54 次執行**。其餘 18 項 Embench 在既有三版本 ROI 均沒有硬體 FP 指令；它們接受既有記錄核對，沒有宣稱重新跑完整 27 項。

每次新的 profile、memory audit 均逐 byte 符合原記錄；數值輸出、總 cycle、ROI cycle、退休類別與 per-PC 計數一致。原日誌唯一容許的差異是已驗證 ELF 的絕對路徑列，off/on 日誌本身完全一致。這些是保留原生成模型及 runtime objects、只重連主機 harness 的診斷測試；新 harness 來源以 SHA 固定，不冒稱新的 clean-commit RTL／Spike 全面資格確認。

| `minver`，CPU／記憶體皆 10 ns | baseline | A | B |
| --- | ---: | ---: | ---: |
| ROI cycles | 878,777 | 858,801 | 843,225 |
| EX0 因 DIV/SQRT 未 ready 而阻塞，排除 flush 當拍 | 107,117 | 109,892 | 103,230 |
| 同拍還有 ready FP IQ 指令被擋 | 56,614 | 62,719 | 46,065 |
| 其中可送往另一個 ready 算術單元的 cycle | 20,535 | 22,200 | 9,990 |
| 上列占 ROI 比例 | 2.337% | 2.585% | 1.185% |
| completion 仲裁衝突 | 0 | 0 | 0 |

這些機會計數互相重疊，包含尚未退休的推測執行，**不是可節省 cycle 或加速上限**。發射改變會改變後續依賴、IQ／ROB 占用與 flush，必須靠實際候選測試判定收益。

三版本的 **FP32 八項均無 EX0 阻塞，也無任何 completion 衝突**。現有算術 FPU 的 accepted issue → first valid／grant 都是 1 cycle；`minver` 確實出現相鄰 cycle 的算術發射。它已有每 cycle 接收一筆的能力，不能將額外 pipeline 描述為把原本「兩拍一筆」變成「一拍一筆」。一般 FDIV 在這批資料是 28 cycle；另有 `minver` 1-cycle 特例。這是單元事件之間的延遲，並非 dispatch 到退休的延遲，也不代表所有 FP 操作的完整延遲表。

六個小型 RV32IF 指令程式，以 FDIV 加上相依 FMUL 鏈實際觸發 **2 個 DIV/SQRT completion 被擋 cycle**，證明觀測器能量到非零仲裁；original/off/on 的完整退休 trace 與 profile 相同，程式也驗證精確的浮點結果。另有 mock packet 正控制及 6 個刻意錯誤的 class／owner／ready／completion 控制。這些診斷不加入 benchmark 分母。

## 原生時序證據

重新解析同流程 baseline／B、TT／SS／FF、每組最差 5 條 setup path，共 **120 條既有 native path**，並與已封存雜湊核對。這是 global-route 寄生估算，沒有新跑 placement／route，也不是完整路徑枚舉。

| 100 MHz setup 餘裕（ps） | baseline TT | B TT | baseline SS | B SS | baseline FF | B FF |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| reg2reg，算術 FPU | 3,735.85 | 3,663.46 | 588.01 | **454.05** | 5,475.72 | 5,428.71 |
| reg2out，LSU → dmem address | 3,381.14 | 3,398.29 | 667.84 | **689.83** | 4,883.17 | 4,889.07 |

B 最慢 corner 的最差路徑是 `fp_ex0_req_q[91]` → `u_fp_execute/cmp_data[107]`，即 operand0 的 exponent 位元到 FP 結果位元。Q 到 D 的報告差值約 **9,360.54 ps**，經過 118 個組合輸出 pin，其中 9 個是 buffer；117 個在 `u_fp_execute` 階層內。這些 pin increments 混合 cell／net 效應，不能由此聲稱 wire／cell 各占幾成，也尚未把匿名 mapped gate 對應到特定 RTL 算式。

SS 的下一條 reg2out 邊界只多約 **235.78 ps** 餘裕。若只縮短 FPU，LSU／記憶體介面可能接手成瓶頸。既有合格時脈仍是 B 9.6 ns、同流程 baseline 9.5 ns；此分析不由 WNS 推算新的合格頻率。固定 10 ns 記憶體也使 9.6 ns CPU 的實際回應取樣達 19.2 ns，既有 B 全集合結果已顯示提頻可能降低系統效能。

## 建議共同選擇的下一個候選

1. **A 的實體資格缺口已補齊。** 共同 100 MHz 比最快合格時脈更適合目前固定記憶體。A+B 是另案，需要獨立驗證，不能把 A／B 收益相加。
2. **第 3 項先測 FP 發射選擇。** 最小候選是在 FP IQ 選擇時考慮單元下一拍的接收能力，避免第二筆 DIV 在共用 EX0 等待而擋住已 ready 的算術指令。只看當拍 DIV ready 不夠：EX0 當拍若正送出一筆 DIV，下一拍單元就會忙碌。須驗證 tag／flush、busy→ready、連續 DIV、同時 completion 與長期進展，最後比較完整兩類分數。這不是已實作或已證明有效的方案；目前沒有實測理由優先改 completion 仲裁公平性。
3. **第 5 項先比較維持 1-cycle 延遲的組合邏輯改善。** 候選包含前導位元定位、shift/sticky 與寬位元算式結構；需先用等價和同一映射確認哪一項縮短實際關鍵路徑。增加 pipeline 的候選另列，因為會增加相依延遲、狀態、flush 驗證與面積；僅有 MHz 改善不足以採納。

本輪沒有合併 A+B、改變 CPU 結構或升格新基線。兩類 ≥1.20× 目標仍未達成。

## 環境恢復與證據保存

10 月 31 日的第一次 A native 嘗試，在 11 月 3 日環境停止後失去未發布的 tmpfs；沒有採認該次實體結果。11 月 5 日的獨立 `attempt-v2` 於乾淨 `8a1c582` 完成，三個階段皆自動壓縮、逐檔核對並 fsync 至主機。發布曾分別被磁碟容量及 Docker daemon 看到的底層 bind view 阻擋，失敗記錄保留。最後使用 **container exec 串流 tar** 讀取實際 mount namespace，核對 104 個檔案及 links 後才卸載 tmpfs；再跑獨立 STA、相鄰失敗點和完整審查。

最快時脈的 27 項測試在後續環境重啟前已保存完整、乾淨來源的成功 summary。完成監督程序曾因映像還原容量而暫停，重啟後程序已不存在；沒有補寫未觀察到的 wrapper exit status，而是重新核對所有 27 項 exit codes、原始輸出及來源後接續環境還原。

已完成歷史工作目錄的 ODB／route guide／文字快取採 lossless gzip 或既有 archive hardlink，逐檔保留 SHA／大小與還原記錄；原封存 bytes 未改動。需要原始檔的舊工具須先解壓。SIM／SYN／FP／ORFS 四個工具映像均已還原為原 image IDs；SIM／SYN／FP 工具與固定子模組檢查通過。僅刪除已可由還原映像取代的重複 gzip 備份，主工作目錄也已恢復完整 checkout。映像暫存策略及容量紀錄隨本輪證據保存。

第一輪觀測證據仍在 [可攜式封裝](evidence/optimization-135-study-2026-10-30.tar.gz)，附 [SHA256](evidence/optimization-135-study-2026-10-30.tar.gz.sha256)，共 721 份已核對 payload。本輪 A 的 [完成證據與重現說明](evidence/2026-11-05/optimization-135-A/README.md) 包含三個 native checkpoint、全部新 STA、兩次完整工作負載、正負控制、來源及環境恢復紀錄；以 32 MiB 分片保存並逐檔核對解碼內容。原 B 的 1,327 筆參考封存也重新核對 stored／decoded bytes。

審查與封存程式位於 [experiments/optimization-135-v1](../experiments/optimization-135-v1/README.md)。本輪完成的是 **global-route 研究比較**，不代表 full ISA／IEEE-754 conformance 或 detailed-route signoff。CPU RTL、原凍結基線與計分政策沒有改動。
