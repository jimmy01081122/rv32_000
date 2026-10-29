# 可信進度與 AP5B 基線審查

更新：2026-10-30（Asia/Taipei）。修正後 AP5B v1 的 global-route 研究基線已凍結；
使用者已核准 A 先、B 作獨立 CPU 對照；[A 初版](../experiments/lsu-a-v1/README.md)
已完成[雙操作點與實體研究資格](evidence/2026-10-20/lsu-a-physical/README.md)。[B](LSU_B_COMPLETE_VALIDATION.md)已完成修復後的完整實驗契約：功能資格重驗、FPU 實作等價、同流程三 corner 與雙操作點完整 27 項通過。兩類效能目標仍未達，原基線不變。專案沒有硬性時程。

## 目前能證明的進度

| 關卡（對照 [計畫](../PLAN.md)） | 證據 | 狀態 |
| --- | --- | --- |
| 1. 文件整理 | 現行規格、歷史標示、來源與流程入口已整理 | 完成並持續維護 |
| 2. 固定工作負載 | Embench19、均衡 FP32 八項；原 ELF、fixture／尺寸／容差及 3,629 筆輸出固定 | v1 契約凍結 |
| 3. 驗證基礎 | LSU 48 assertion cases、18 directed／Spike、3,400 有限 FMA；固定時間 normal／assert 各 58 controls | 定向資格完成；完整 ISA／FP 覆蓋仍開放 |
| 4. 修正後基線 | 10 ns 三 corner 通過、22,081.1184 µm²；乾淨來源正式 27/27 通過 | global-route 研究層級完成 |
| 5. 目標與第一項 CPU 方案 | 兩類各 ≥1.20×、面積 ≤1.10× 已核准；先 A、B 獨立對照 | 順序已核准 |
| 6. CPU 優化驗收 | A 100 MHz／101.01 MHz 各 27/27、FP3,629；同頻 GM 1.045830×／1.078255×；面積 1.003674×、三 corner 通過 | A、B 研究資格完成；B 新流程面積 0.989062× 同流程 baseline；兩類 ≥1.20× 目標未達 |
| 7. FPU 映射流程修復 | 共同映射、完整 reset／轉移／輸出等價及實際物理圖綁定通過；共同 hold40／ready buffer 完成兩版三 corner | B 契約完成；IEEE-754／完整 ISA 覆蓋仍開放 |

進度以關卡、完整分母和原始證據呈現，不換算成整個專案的完成百分比。
失敗／不完整實體嘗試保留原結果，不併入正向資格。

後續[驗證與審查](LSU_A_VERIFICATION_REVIEW.md)已完成：乾淨來源的定向／Spike／
介面／固定時間／有限 FMA 回歸重跑通過，LSU baseline／A 各 35 項通過。
已補上建置／功能證據身分與逐 PC 工作量的自動審查；四個實際負向案例拒收，
30 個控制通過。兩組原始 27 項重新審查後成績不變；沒有修改 CPU 或重跑實體建置。
B 已於後續核准後完成獨立實驗與時序診斷；完整結果及下一階段選項見下。

## 已固定的比較基線

[契約](../baselines/ap5b-post-lsu-v1/manifest.json)與
[完整證據](evidence/2026-10-18/post-lsu-baseline/README.md)記錄：

- CPU 的 18 份 RTL 與 `71c24f5` 相同，包含 FMA、FP-store 及 LSU 介面修復。
- 完整 Embench-IoT 1.0 的 19 項，以及 FP32 DSP 四項＋矩陣／ML 四項。
  FP32 主設定為 `fast -fno-fast-math`，兩子群各 50%；off 為獨立敏感度。
- 基線 core period 為 **10,000 ps（100 MHz）**。I response、I initiation
  interval、D response 各固定 **10,000 ps**，候選提頻時 ps 不變。
- 面積 **22,081.1184 µm²**：完整 core、PRF／SQ、commit trace 及 clock／repair
  cells，外部 RAM 不含在內。1.10× 預算為 **24,289.23024 µm²**。
- ASAP7 RVT、TT-only 建置；SS／FF 與 TT 各用新 process 分析同一 global-route
  database。三者共用 nominal wire RC，未宣稱多 corner 詳細抽取。
- 在固定 I/O／uncertainty／load 下實測 9.9 ns SS setup 失敗，10.0 ns 三者
  通過。週期是最小已測通過的 100 ps 網格點，不由 WNS 外推連續 Fmax。
- 正式 27 項在乾淨 `9769123` 執行，前後來源狀態一致；原 ELF、ROI cycles、
  計分 simulator hash 不變。數值、記憶體 audit、profile 及 stack headroom 均通過。

執行時間採 `ROI cycles × 合格 core period`。兩個集合各自計算
`GM(time_baseline / time_candidate)`；FP32 的兩群各占 50%。缺項、功能失敗、
hash 不符或未閉合不得縮小分母。沒有以編譯器融合收益當 CPU 架構收益。

## 工具鏈與證據範圍

裸機 FP32 工具鏈固定 xPack GCC 15.2.0／newlib 4.5.0，ISA／ABI 為
`rv32imf_zicsr / ilp32f`。來源與建置命令在 `toolchain.lock`、
`baselines/ap5b-post-lsu-v1/build-contract.json`；凍結 ELF bytes 是主比較輸入。
原資格分別見 [Embench19](evidence/2026-10-17/embench-approved-rerun/README.md)、
[FP32 八項](evidence/2026-10-17/fp32-balanced-qualification/README.md)與
[LSU 修復](evidence/2026-10-18/lsu-interface-fix/README.md)。正式量測沿用相同
ELF 與既有獨立參考，不把此次 DUT 重跑誤報成新的全集合 Spike 重跑。

實體 OpenROAD／Yosys／platform 的 204-file 雜湊、映像來源、精確 source
checkout 與相容性 overrides 均封存。報告工具有 49 個實際控制，完整 ORFS
小型 fixture 通過三 corner，baseline／worker／closure 控制共 20 項。
`SYNTHESIS` 定義下的 sv2v 輸出已逐 byte 重現；未更改 Liberty 模型或放寬限制。

這是指定模型下的研究結果。尚未完成 detailed-route DRC／LVS、OCV、
多 corner parasitic extraction、workload activity 功耗，或第二次全流程重跑
的 repeatability 量測。原 tool-flow 退出 0 與 timing collection 完成各自保留，
只有獨立審查及全 27 項通過才完成這個研究基線。

完整 ACT4／RV32F rounding、NaN／Inf、flags、trap 覆蓋仍須補齊；
現有 Spike parser 沒有完整 cause／tval 比對。退休 SP 餘裕是診斷觀測，
不是所有瞬間 stack 存取的形式證明。詳見 [缺口清單](STATUS.md)。

## 已核准的實驗順序

[LSU 方案審查](LSU_OPTIMIZATION_REVIEW.md)保留六案例診斷與事前假設：

| 方案 | 假設 | 主要風險 |
| --- | --- | --- |
| A：response buffer 消耗與下一請求重疊 | 減少請求轉換空拍，維持一筆外部 outstanding | 同拍 metadata 交接、backpressure、flush／error 與 ready 路徑 |
| B：head-store 資格與 SQ marking 同拍 | 減少 store marking 的固定節拍 | 頭端 tag／地址／資料匹配、錯誤路徑 store、head-to-request 時序 |

建議 A 作第一個獨立實驗、B 另立對照，之後才決定是否組合；C 暫列後續。
此順序已由使用者核准。A 的[完整功能與同頻證據](evidence/2026-10-19/lsu-a-functional/README.md)
已封存；在固定 100 MHz／10 ns memory 下，兩個集合仍低於各自 1.20×。
A 已更新 AP5B 交接契約與 assertions，包含新請求 tag／地址的下一拍所有權檢查。
實體流程使用相同 pinned 工具、TT-only、5,500 ps mapping、14,000 ps backend、
45% slew／50 ps hold repair 與最後全 global route。實測 9.8 ns SS setup 失敗、
9.9 ns 與 10 ns 三 corner 通過，面積為 22,162.24152 µm²（增加約 0.3674%）。
9.9 ns 的完整集合為 Embench 0.726601×、FP32 0.700275×；固定 10 ns
記憶體跨兩拍、19.8 ns 才可取樣，不能用同頻 cycles 按比例推算提頻成績。
兩個操作點與不利結果均封存，不混用集合時脈。建議先以 100 MHz 評估 A，
B 已從相同凍結基線完成獨立對照（結果見下）；操作點與後續取捨共同討論，未導入 A+B。
架構、集合、目標或驗收條件變更都先討論；可比條件內的檢查與修復持續進行。


B 的[原 v1 封存](evidence/2026-10-21/lsu-b/README.md)保留當時的完整功能通過與
原流程時序失敗。後續[時序診斷](LSU_B_TIMING_DIAGNOSIS.md)確認未改 FPU 的映射
差距在布局前已存在；[共同 FPU 修復](FPU_MAPPING_REPAIR.md)及 B 完整驗證已接續完成。

[B 最終審查](LSU_B_COMPLETE_VALIDATION.md)確認完整 FPU reset 後二態實作等價，
同流程 baseline／B 三 corner 分別自 9.5／9.6 ns 合格，均有實際相鄰較快失敗點。
B 在 100 MHz 為 Embench 1.029459×／FP32 1.009599×，104.17 MHz 為
0.748705×／0.719680×；每點 27/27、3,629 數值與逐 PC 計數通過。
B 面積 21,309.821820 µm²，為原基線 0.965070×、同新流程 baseline 的 0.989062×。
建議以 100 MHz 評估，PID +13.9763% 的時間退步仍列入討論。最終審查器 7 個
反例全數拒收，正向通過；失敗修補嘗試與舊 EQY timeout 未改寫。

[新封存](evidence/2026-10-29/lsu-b-complete-validation/README.md)區分原功能資格
重新核對與新跑的工作負載／形式／實體。完成驗證不代表達成效能目標；A 尚未以
新物理流程重跑，也沒有選定新基線或導入 A+B。下一步架構方向由使用者共同選擇。
