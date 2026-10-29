# B 線完整驗證與結果審查

原生驗證完成於 2026-10-29 UTC；文件整理於 2026-10-30（Asia/Taipei）。
**B 已完成既定實驗契約的完整驗證，取得 global-route 研究資格；
兩類效能各 ≥1.20× 的目標仍未達成。** 本次補完 FPU 實作等價證明、相同流程的
baseline／B 實體資格，以及兩個操作點的完整 27 項量測。原凍結基線不變。

## 量測結論

比較基準為 AP5B v1 的 100 MHz／固定 10 ns 記憶體；全部使用原 ELF、ROI、
尺寸、容差與 `fast -fno-fast-math`。加速比為基線時間除以候選時間，越大越好。

| B 操作點 | Embench19 GM | FP32 八項 GM | DSP 四項 | 矩陣／ML 四項 | 功能／數值 |
| --- | ---: | ---: | ---: | ---: | --- |
| 100 MHz，10,000 ps | **1.029459×** | **1.009599×** | 1.013839× | 1.005376× | 27/27、3,629 筆通過 |
| 104.17 MHz，9,600 ps | 0.748705× | 0.719680× | 0.674466× | 0.767924× | 27/27、3,629 筆通過 |

兩組量測皆由原始輸出重新計分，通過記憶體、stack 餘裕與逐 PC／instruction／kind
退休工作量對帳。工作量 map 是計數，不是完整有序 trace。沒有混用兩集合的時脈。
I response、I initiation interval、D response 始終各為 10,000 ps；9,600 ps CPU
需兩拍，19,200 ps 才能取樣，因此提頻結果較差，不能按同頻 cycles 比例外推。

在已測操作點中，**建議以 100 MHz 評估 B**。同頻收益約為一般嵌入式 +2.95%、
FP32 +0.96%；PID 執行時間仍增加 13.9763%（7,248→8,261 cycles），未排除退步案例。
這個建議不代表選定新基線或核准下一個架構變更。

| 實體版本 | 標準元件面積 µm² | 相對原凍結基線 | 最短已測三 corner 合格週期 |
| --- | ---: | ---: | ---: |
| 原 AP5B v1 | 22,081.118400 | 1.000000× | 10,000 ps |
| 共同 FPU／hold 修復流程的 baseline | 21,545.492940 | 0.975743× | 9,500 ps |
| 相同新流程的 B | **21,309.821820** | **0.965070×** | **9,600 ps** |

B／同流程 baseline 面積為 **0.989062×**，約減少 1.09%；兩種參考下皆低於 1.10×。
相對原基線的減少包含流程變更，不能全歸因於 B 架構。A 尚未以這個新流程重跑，
不能把 A 舊面積／時脈當成同流程對照。新 baseline 的 9.5 ns 是實體點，未另做
該點全 27 項量測；本報告的時間比較固定使用原基線 100 MHz。

## 已完成的驗證邊界

| 關卡 | 可審查證據 | 結果 |
| --- | --- | --- |
| 原 B 功能資格 | baseline／B 各 62 LSU cases、原 RTL 負向節拍控制；directed 18、Spike 18、interface 48、fixed-time 58、有限 FMA 3,400 | 原紀錄與執行檔重新核對通過 |
| 新的完整工作負載 | 100 MHz、104.17 MHz 各 27 項、各 3,629 筆 FP32；原始 stdout／profiles／memory audits | 兩組皆通過 |
| FPU RTL → mapped | reset 建立狀態關係，任意輸入／相關狀態的轉移及全部輸出等價 | 通過，含實際錯誤注入 |
| 形式證明到實體輸入 | 原 FPU body、實際 mapped JSON、Verilog readback、獨立重跑圖、連回核心的 body hashes | 完整證據鏈通過 |
| 同流程實體 | 兩版各自 TT 建置、ECO、單一 ready buffer、完整 global route；獨立 TT／SS／FF | 兩版合格 |
| 最終審查器反例 | 錯版本、改 buffer 政策、overflow、負 hold、電氣違規、原始報告改動、接線計數矛盾 | 7/7 拒收，正向資料通過 |

CPU RTL、B normal／assert simulator 與凍結 ELF 沒有改動，因此沿用並重新驗證
既有功能資格的來源、實際命令、log、執行檔及輸入雜湊。這不是重跑全部 Spike／
定向回歸；此次新跑的是兩組完整 DUT 量測、形式證明與實體流程。
舊 B 712 檔、FPU 修復 771 檔的原封存校驗亦通過。

## FPU 證明如何補完

原 FPU 有 155 個 completion state bits 加 valid，共 156 bits；共同 mapped FPU
有 100 個 FF。只用已註冊輸出的接線建立狀態關係：54 個常數、100 個獨立狀態與
2 個別名。Liberty 的 `DFFHQNx1_ASAP7_75t_R` 是反相 QN，模型明確保留此極性。

先分別證明兩邊從任意、互不相關的初始狀態，經一次同步 reset 上升緣後所有
156 個可觀察狀態都為零。再對任意 100-bit 相關狀態和不受限輸入，證明全部
156 next-state observations 與 157 visible output bits 相等。沒有算術內部切點，
沒有 opcode、運算元或 handshake 假設；因此 reset 建立關係，轉移步驟保持關係。

ABC 的三個正向義務通過；翻轉 next-state bit、移除 valid 更新、reset 強制 valid=1
均實際得到不等價，另外 clock、額外狀態、初始化與 FF 極性錯誤均被模型審查拒收。
原生 frontend 與模型生成重播一致；降階後的功能連線和輸出沒有 X／Z。
ABC 即使不等價也可能 exit 0，審查依精確等價／不等價 log 判斷。

這是**一次同步 reset 後、二態模型下的完整 FPU 實作等價**。golden 是固定 sv2v
輸出的原 FPU；sv2v／Yosys／Liberty／ABC 是明示的工具信任邊界。它保留既有實作
行為，不獨立證明 IEEE-754、完整 RV32F 或全 CPU ISA 正確性。先前 900 秒 EQY
逾時仍保留為失敗紀錄；本次改用已證明的狀態關係完成義務，沒有把逾時列為通過。

## 實體流程與失敗保留

同一 ORFS `8359fde81991e6118b15b8a93fcde606b577794d`、ASAP7 RVT、TT-only 建置，
兩版使用相同 FPU map，各自完成 placement／CTS／global route。建置約束 14,000 ps
不是達成時脈；最終以原 reviewer、I/O、uncertainty、load、nominal wire RC 與
零負 setup／hold、零電氣違規門檻，在獨立 TT／SS／FF processes 檢查。

1. 初次 B 100 ps hold 目標修補超過 9,130 次迭代、25,958 buffers 後仍不收斂，
   明確停止並保留非零退出；pre-ECO 的 FF hold 與 SS slew 失敗也保留。
2. 分別版本化為共同 TT slew 45%／hold 40 ps 修補，設定 3,600 秒上限。
   B 合格，但 baseline FF hold −1.237 ps，故該 baseline 被拒收。
3. 兩版都在 `dmem_req_ready` 加一個相同 `BUFx2_ASAP7_75t_R`，重新合法化與
   完整 global route。Liberty 模型證明 Y=A；每版只增一 cell、0.0729 µm²，無新增狀態。
4. 首次 buffer 名稱檢查誤以為 OpenROAD 接受固定名稱；實際 API 會加數字後綴。
   原失敗紀錄與 `33d566a` 程式保留；改為辨識唯一新增元件並核對 master／prefix，
   在乾淨 `a5cc433` 重新執行兩版，全部通過。

原生接線審查核對 baseline 的 174,140 元件／967,132 pins／523 ports，以及
B 的 171,537 元件／948,537 pins／523 ports。所有原 master、pins、ports 均保持
原接線，唯一差異是 ready input net 被已證明的 wire buffer 分段。兩版最終
overflow、placement failures、antenna net／pin violations 都為零。

| 版本／period | SS setup ps | FF hold ps | TT／SS／FF 完整結果 |
| --- | ---: | ---: | --- |
| baseline 9,400 ps | −11.991 | +9.123 | 失敗 |
| baseline 9,500 ps | +88.009 | +9.123 | 通過 |
| baseline 10,000 ps | +588.009 | +9.123 | 通過 |
| B 9,500 ps | −45.953 | +17.280 | 失敗 |
| B 9,600 ps | +54.047 | +17.280 | 通過 |
| B 10,000 ps | +454.047 | +17.280 | 通過 |

baseline 9,600 ps、B 9,700 ps 也實測通過。邊界是 100 ps 網格的實測結果，
沒有由 slack 推算連續 Fmax。TT hold 40 ps 是修補目標，並非放寬獨立驗收限制。

## 可重播資料與後續決策

[完整封存](evidence/2026-10-29/lsu-b-complete-validation/README.md)包含原始報告、
成功及失敗命令／退出、最終 ODB／SDC、形式模型、兩組完整工作負載、負向控制、
來源快照與 SHA256。流程與審查命令見[實驗入口](../experiments/lsu-b-validation-v2/README.md)。
實體階段固定輸入身分；正式 GRT、hold40、guard 來源分別為 `6493269`、`f2c8b45`、
`a5cc433`。兩組 workload 來源分別為乾淨 `6493269`、`f2c8b45`，scored binary 相同。

本次完成的是已核准的 B 實驗契約。詳細繞線 DRC／LVS、OCV、多 corner 寄生抽取、
功耗、完整 ACT4／ISA／特殊 FP 規格覆蓋，以及多次獨立布局的變異評估仍屬後續工作。
最終工具／平台 204 檔校驗通過後，移除本任務已閒置容器並保留映像；工作區的大型
完成檔採無損壓縮，清理收據與可還原說明隨證據保留。

建議共同審查 B 的小幅整體收益與 PID 退步，並以同頻 A 的較高集合收益作為
下一步方向的輸入；若要比較新流程的 A/B 面積與時脈，須補跑 A。下一項架構、
A+B 組合、物理參考替換或目標變更都待共同決定，本次未自行採用。
