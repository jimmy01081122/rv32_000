# FPU 映射修復與驗證

更新：2026-10-27。使用者已核准先修復 FPU；本階段針對
[B 診斷](LSU_B_TIMING_DIAGNOSIS.md)發現的合成映射敏感性，維持原算術、
介面與 latency。已建立共同 FPU 映射，完成映射層形式檢查及三版接線審查；
完整 RTL 等價證明與實體資格仍未完成。

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
| 完整 RTL → mapped 形式證明 | interface-only EQY/PDR 900 s timeout，未證明，未列為 PASS |

OpenDB 原生匯入刪去無可觀察用途的邏輯。審查確認整個刪除子圖不驅動
任何保留元件或 top output；其中包含無用暫存器與 FPU 邏輯，並非全是 buffer。

| 版本 | 連接後 reference cells | OpenDB 保留 cells | 無用子圖移除 |
| --- | ---: | ---: | ---: |
| baseline | 181,422 | 176,210 | 5,212 |
| A | 181,319 | 176,313 | 5,006 |
| B | 178,286 | 172,666 | 5,620 |

CEC 將 ABC 前後同身分、型別與 clock 的 100 個 DFF，轉為共同任意 `state`
輸入與 `nextstate` 輸出，其餘元件及原 port 不變；審查器重建並核對轉換。
這證明映射的狀態轉移等價，尚未形式證明前面的 RTL 降階與算術展開。

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
不能把新資料混入原 v1 PPA 比例。

## 後續關卡

1. 補完 RTL 到映射的形式驗證計畫，或共同明訂下一階段可接受的證據範圍；
   定向與隨機比較不等於完整 ISA／IEEE-754 資格。
2. 校準 TT-only 建置的 hold 修補裕量，維持獨立 SS／FF 零負 slack 門檻。
   本次沒有修復 B 原本兩個 FF hold 端點。
3. 用同一新流程完成 baseline、A、B 實體比較，再共同決定新物理參考或下一項
   架構實驗。原基線與兩類 ≥1.20×、面積 ≤1.10× 目標不變；未導入 A+B 或
   新增 FPU pipeline。

[實作與重播](../experiments/fpu-mapping-v1/README.md)、
[原始紀錄](evidence/2026-10-27/fpu-mapping-repair/README.md)。
