# ASAP7 RVT 加法器模型警告核對

2026-10-18。這是工具／library 資格確認，**不是 CPU 實體時序閉合**。
固定的 ASAP7 `SIMPLE` Liberty 在 FAx1／HAxp5 的額外 CON→SN output-port
timing groups 產生 `STA-1212`。不修改 PDK，也不隱藏警告。

`summary.json`、`raw-arcs.json` 與逐 corner STA 報告記錄：

- TT／SS／FF 的 FA／HA Boolean functions 全部符合反相 carry／sum 真值表。
- 144 種會改變輸出的單一輸入轉換，均有符合條件、極性與方向的 input→output
  延遲表。額外的 CON→SN groups 不用作功能 input→output coverage。
- 每個 corner 在新 OpenSTA process 載入原始 libraries，以一個 FA、一個 HA
  的小電路檢查全部十組功能路徑；共 30 組，每組 min／max 報告都存在。
- 缺少 arc、缺少延遲表及錯誤 Boolean function 的三個反例均被拒絕。
- binary、三份 SIMPLE libraries、checker／Tcl／Verilog 都有 hash；完整核心的
  分析工具會核對 live binary／libraries 與這份核對結果一致後，才允許這一範圍的警告。

完整核心仍須另行檢查實際 cell 使用量、寄生還原、約束完整性、setup／hold、
電氣限制與繞線狀態。本核對沒有驗證類比 characterization、OCV 或整套 Liberty
品質；它只支持這個研究流程對已知 output-port 警告的有限判讀。
不同 corner 的 XOR timing groups 不完全相同，最終核心 STA 分別執行，避免
共用 reference graph 時漏掉 FF 額外的 non-unate arcs。

在固定 runtime 內執行 `python3 scripts/audit_asap7_adders.py --out build/asap7-adders-fresh`
可重跑；輸出目錄必須不存在。核對封存內容：`sha256sum -c SHA256SUMS`。
