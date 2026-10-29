# FPU 映射修復與驗證

更新：2026-10-30（Asia/Taipei）。使用者已核准先修復 FPU；本階段針對
[B 診斷](LSU_B_TIMING_DIAGNOSIS.md)發現的合成映射敏感性，維持原算術、
介面與 latency。已建立共同 FPU 映射，完成映射層形式檢查及三版接線審查；
後續 [B 完整驗證](LSU_B_COMPLETE_VALIDATION.md)已補完 reset 後二態 RTL 實作等價，
並完成同新流程 baseline／B 實體資格；A 的新流程實體重跑仍未進行。

## 修正內容

原流程中，LSU 改動會連帶改變未修改的 FPU 映射。先嘗試 ORFS 原生
`SYNTH_KEEP_MODULES`，三版都完成合成，但元件圖仍不同，故不把保留階層
當成修復成功。

採用的方式是從三份凍結 sv2v 輸出提取完全相同的 FPU，單獨合成，再將
同一份 mapped Verilog 接回 baseline、A、B。每版核心 module body 逐 byte
不變；連接前核對 port 名稱、寬度、方向，之後由原生 ORFS 匯入 OpenDB，
不對共同 FPU 重做映射。

兩次獨立 standalone 合成的圖完全相同：**25,855 cells、100 DFF**。
包含 pin、fanout、共享節點與回授的圖 SHA256 為
`d12b91d198024deff4527b2c1e6217fcc7ca3355bdc09dfb4ebb309192a0fd89`。
實際連接用 Verilog 重新讀回的圖也相同。這是兩次受控重跑的結果，
不代表跨工具版本、平台或所有輸入都保證相同映射。

## 證據與範圍

| 檢查 | 結果與界線 |
| --- | --- |
| 共同來源 | 三版 FPU body 逐 byte 相同；沒有 CPU RTL 改動 |
| 原生執行 | 三版保留階層合成、兩次 standalone 合成、三版匯入均 rc0，輸入 hashes 不變 |
| 接回核心 | 核心 body 不變，三份輸出含相同 FPU body；重播連接結果一致 |
| OpenDB readback | 525,189 個保留元件的 master 與全部 signal pins 核對通過 |
| ABC 前後等價 | 100 bit 的任意狀態／輸入轉移與全部輸出 CEC 通過；nextstate bit 錯誤注入被拒絕 |
| 審查器負向控制 | 對調輸入 bit、加入未支援初始化、改接腳、移除有用元件，4/4 被拒絕 |
| RTL／閘級逐週期回歸 | 116,737 cycles、233,474 次完整輸出比較通過；結果 bit 錯誤注入被拒絕 |
| 完整 RTL → mapped 形式證明 | 後續 reset 建立關係＋任意相關狀態／輸入的轉移及完整輸出證明通過；原 EQY/PDR 900 s timeout 保留為歷史失敗 |

OpenDB 原生匯入刪去無可觀察用途的邏輯。審查確認整個刪除子圖不驅動
任何保留元件或 top output；其中包含無用暫存器與 FPU 邏輯，並非全是 buffer。

| 版本 | 連接後 reference cells | OpenDB 保留 cells | 無用子圖移除 |
| --- | ---: | ---: | ---: |
| baseline | 181,422 | 176,210 | 5,212 |
| A | 181,319 | 176,313 | 5,006 |
| B | 178,286 | 172,666 | 5,620 |

CEC 將 ABC 前後同身分、型別與 clock 的 100 個 DFF，轉為共同任意 `state`
輸入與 `nextstate` 輸出，其餘元件及原 port 不變；審查器重建並核對轉換。
這個早期證據只證明映射的狀態轉移等價。後續完整證明以原 sv2v FPU 為 golden，
從任意初始狀態證明 reset 建立 156-bit／100-FF 關係，再證明全部轉移與可見輸出。
沒有內部算術切點；原生 frontend 重播、X／Z 排除、實際錯誤注入與物理圖綁定通過。
詳見 [證明範圍](LSU_B_COMPLETE_VALIDATION.md)；工具 frontend 是明示信任邊界。

完整 EQY 逾時及早期不適當內部切點、工具／模型缺失均保留。小型 sequential
fixture 曾揭露未明確處理 clock 的 SAT 設定會誤放行負向案例，該設定已拒用。
明確 `clk2fflogic` 的 fixture 才取得正向通過／負向拒絕；問題設定的 pass
不納入正式證據。

閘級回歸採原 canonical RTL 與 Liberty function model 比較，包含 32,768 組
opcode／rounding 編碼與特殊運算元輸入、65,536 組隨機封包，另加入 stall、
flush、reset；共 233,476 次固定 clock 下的輸出穩定性檢查。
所有 155 個 completion bits、valid、ready 均比對。編碼掃描含保留／非法值，
不把 2,048 組編碼當成 2,048 種合法 ISA 行為；NaN／Inf／subnormal 等輸入
也不代表已獨立驗證 IEEE-754 正確性。

早期測試曾在暫存器 commit 後、組合輸出尚未傳播時取樣而失敗，已修正
測試程式並保留原紀錄。最終建置停用 CXXRTL 強制內聯以縮短主機編譯時間，
只在生成模型的 eval 函式加上主機 O0 註記，輔助函式採 O2；移除此註記可
逐 byte 還原原生模型。runtime headers 不變，編譯選項、來源及執行檔 hashes 均封存。

## 時序診斷

相同 SS library、zero-wire、ideal-clock 條件下的最差 FPU 資料到達時間：

| 版本 | 舊 v1 映射，ns | 共同 FPU 映射，ns |
| --- | ---: | ---: |
| baseline | 6.518351 | 6.591387 |
| A | 6.651498 | 6.587407 |
| B | 8.455249 | 6.578693 |

新三版差距約 12.7 ps；相同 FPU 圖仍受邊界 driver、負載與前段核心邏輯影響。
這支持映射差異已被控制，但不是 routed Fmax 或 CPU 加速比。整體流程已改變，
後續 routed 結果另外列出原凍結基線與同新流程 baseline 兩種面積比例，
不把流程修復的收益全部歸因於 B。

## 完成狀態與後續關卡

1. 完整 FPU 實作等價已完成，條件為一次同步 reset 後的二態模型；完整 ISA／
   IEEE-754 規格資格仍需獨立補齊。
2. 共同 TT hold40 修補與單一 ready buffer 已讓 baseline／B 取得三 corner 資格，
   零負 slack 與電氣門檻不變。最終 B 9.6 ns 合格、9.5 ns SS setup 失敗；原失敗保留。
3. B 的 100 MHz／104.17 MHz 完整 27 項均通過，但效能目標未達。若要新流程 A/B
   面積／時脈比較，仍須重跑 A；新的物理參考或下一項架構由使用者共同決定。

[實作與重播](../experiments/fpu-mapping-v1/README.md)、
[原始映射里程碑](evidence/2026-10-27/fpu-mapping-repair/README.md)、
[完整驗證與新實體封存](evidence/2026-10-29/lsu-b-complete-validation/README.md)。
