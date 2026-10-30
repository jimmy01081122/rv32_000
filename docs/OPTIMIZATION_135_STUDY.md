# 第 1、3、5 項：第一輪證據研究

更新：2026-10-30（Asia/Taipei）。使用者已選擇架構圖的 1、3、5，這一輪先完成獨立 A 的同流程比較準備、FP 阻塞觀測與 FPU 時序分析，再共同決定 RTL 改動。CPU RTL、凍結工作負載、10 ns 記憶體政策及兩類各 ≥1.20×／面積 ≤1.10× 目標維持原狀。

| 項目 | 本輪狀態 | 尚未完成 |
| --- | --- | --- |
| 1：LSU A 同流程比較 | A linked netlist、共同 FPU、GRT／hold40／ready guard 的輸入與政策預檢通過 | 新 native 建置、獨立 TT／SS／FF 邊界與面積審查 |
| 3：FP EX0／單元 ready／completion | baseline、A、B 的唯讀觀測與獨立對照通過 | 選定並實作發射策略候選，再跑完整工作負載 |
| 5：FPU 路徑／延遲／吞吐 | 既有 native 路徑、實際單元延遲和連續發射證據已核對 | 新組合邏輯或 pipeline 候選的等價、實體與系統時間實驗 |

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

1. **先補完 A 的實體資格缺口。** 已有 100 MHz 全集合結果為 Embench 1.045830×、FP32 1.078255×；B 為 1.029459×、1.009599×。A 的舊面積與最快時脈不能代替這次新共同流程結果。
2. **第 3 項先測 FP 發射選擇。** 最小候選是在 FP IQ 選擇時考慮單元下一拍的接收能力，避免第二筆 DIV 在共用 EX0 等待而擋住已 ready 的算術指令。只看當拍 DIV ready 不夠：EX0 當拍若正送出一筆 DIV，下一拍單元就會忙碌。須驗證 tag／flush、busy→ready、連續 DIV、同時 completion 與長期進展，最後比較完整兩類分數。這不是已實作或已證明有效的方案；目前沒有實測理由優先改 completion 仲裁公平性。
3. **第 5 項先比較維持 1-cycle 延遲的組合邏輯改善。** 候選包含前導位元定位、shift/sticky 與寬位元算式結構；需先用等價和同一映射確認哪一項縮短實際關鍵路徑。增加 pipeline 的候選另列，因為會增加相依延遲、狀態、flush 驗證與面積；僅有 MHz 改善不足以採納。

本輪沒有合併 A+B、改變 CPU 結構或升格新基線。兩類 ≥1.20× 目標仍未達成。

## 環境阻擋與證據保存

建立 `rv32-opt135-native` 的 Docker VFS 可寫副本時發生 ENOSPC；後續 Docker socket 存取請求被取消，無法辨識／清理失敗容器或啟動 A native 流程。未執行 global prune，也未手動刪除不明 Docker layer。

已完成的 B／baseline 工作目錄 ODB 與兩個 route guide 改以既有 gzip payload 的 hardlink 保存；解碼雜湊與回復路徑記在 compaction receipts。**原封存資料未改動**，1327 筆 stored／decoded 記錄再驗證通過。需要舊 raw ODB 的工具須先解壓還原相同 bytes。

工作區可用容量仍為 0，新 archive 目錄建立失敗；改將完整新證據保存為既有目錄內的 [可攜式封裝](evidence/optimization-135-study-2026-10-30.tar.gz)，附 [SHA256](evidence/optimization-135-study-2026-10-30.tar.gz.sha256)。721 份原始／解碼 payload 通過檢查；解壓後可執行 `python3 source/verify_study_archive.py .`。暫存副本仍在 `/tmp/rv32-opt135/archive`。新的 native A 輸入契約與診斷程式位於 [experiments/optimization-135-v1](../experiments/optimization-135-v1/README.md)。本輪 push 狀態以實際 Git 記錄為準。
