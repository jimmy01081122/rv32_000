# LSU 第一輪優化方案審查

2026-10-18。使用者已核准把 LSU 列為第一優先候選，補一般嵌入式觀測、
記憶體延遲敏感度及具體方案比較，再共同選擇實作。本文件先記錄研究條件與
候選結構；尚未選定方案或修改 RTL。兩類各 ≥1.20×、面積 ≤1.10× 目標不變。

## 先固定研究分母與條件

| 案例 | 來源／角色 | 選擇理由 |
| --- | --- | --- |
| Embench `crc32` | 已核准 19 項中的整數控制案例 | 整數運算、資料相依、查表與迴圈 |
| Embench `matmult-int` | 整數矩陣 | 陣列讀取、乘加、輸出 store |
| Embench `wikisort` | 排序與資料搬移 | 分支、讀寫交錯及搬移；保留原始精度／函式庫 |
| Embench `minver` | 單精度矩陣反解 | LSU 與 FP／除法相依並存，檢查不同瓶頸 |
| FP32 FIR | 已核准 fast 主設定 | 延續已定位的 load response 等待 |
| FP32 BiCG | 已核准 fast 主設定 | 延續已定位的 store ack 等待 |

選擇在本輪完整量測前固定，不能因為結果不利而移除案例。
使用先前通過主機／Spike／DUT 的相同 ELF 及資料，不改 Embench 編譯政策、
縮放、暖機或數值精度；FP32 固定 `fast -fno-fast-math`。
RAM 為 1 MiB，隨機額外延遲為 0，模擬器設定回應延遲分別為 1、2、4 cycles，
共 6×3＝18 個觀測案例。每項 latency 1 另做觀測關閉重跑及既有輸出比較。

它們是診斷附表，不是把一般嵌入式主集合縮為 4 項或 FP32 主集合縮為 2 項。
不計子集合總分，不據此宣稱 1.20× 達標。延遲比較是同一 CPU 的敏感度，
不是候選 CPU 的效能改善；這些 cycle 參數也不代表已凍結的實際記憶體 ns 契約。

保留每項 CSR／觀測週期對帳、退休指令分類、互斥等待分類、重疊事件、
依 PC 的退休／頭端等待數、ELF／工具／來源雜湊及原始輸出。
任一缺項、程式失敗、超時、指令工作量改變或觀測不一致，研究完整性不通過。
Embench 沿用上游自我檢查；FP32 仍逐筆核對既有獨立參考及原容差。

## 三個具體硬體候選

下列 A／B／C 是待審查的設計選項，目前沒有任何候選 RTL 或效能／PPA 數據。

| 方案 | 實際改動範圍 | 結構與 PPA 代價 | 主要正確性／時序議題 |
| --- | --- | --- | --- |
| A：回應暫存消耗與下一請求重疊 | 保留 AP5B register；當既有 `rsp_buf_valid` 且本拍確定 `rsp_buf_ack` 時，允許下一個已就緒請求送出 | 維持一筆外部 outstanding、一個 load response slot；增加控制與 ready 扇出，實際面積／頻率待量測 | 同拍消耗與新請求的 tag／destination 所有權、flush／error 優先序、request 穩定性；不得形成 ready 組合迴路 |
| B：頭端 store 資格判定與 SQ marking 同拍 | 對已完成、無例外、位於 ROB 頭端且 SQ 完整匹配的 store，允許在更新 `retired` 的同拍成為送出候選 | 保留 16-slot SQ、現行 store 回應後退休及單一 outstanding；增加 head-to-request 控制路徑 | 必須精確匹配 tag、地址／資料有效；不能把分支／trap／flush 後錯誤路徑 store 送出；MMIO 與 store ack 語意維持 |
| C：已暫存 load completion 的 ROB 頭端轉送 | 僅對現有已註冊 completion 做頭端 ready／結果／例外前瞻；先保留其餘執行單元與 IQ 喚醒節拍 | 保留外部 response register；增加頭端結果／例外 mux 與 tag 比對，內部關鍵路徑風險較高 | 資料與 access fault 必須一起轉送；避免重複退休、舊 completion 或錯誤域目的寫入；重新量測 completion-to-retire 時序 |

A 針對 `!rsp_buf_valid` 強制產生的請求轉換空拍；B 針對 store marking 的固定節拍；
C 針對回應已暫存但 ROB `completed` 還未更新的可見等待。等待計數只是暴露位置，
不能把計數直接換成可省週期，或把 A、B、C 的效益相加。
先做 A／B 各自與基線比較，若都值得，再檢查 A+B 交互作用；C 須另外審查時序預算。
正式實作順序須待本輪跨工作負載結果與使用者共同決定。

## 接受候選前的共同門檻

1. **可比性**：同一工具鏈、已核准 fast ELF、資料、記憶體與 PPA 流程。
   保留基線、A、B、必要時 A+B 的獨立提交；每次只驗一項設計假設。
2. **功能**：定向、Spike、有限 FMA 值／旗標、全 Embench19 與 FP32 八項。
   另外專測同拍 response 消耗／新請求、backpressure、forwarding、部分重疊、
   flush／tag wrap、load access fault、store／MMIO 順序及錯誤回應。
3. **實體**：先建立相同 RTL 的新鮮 AP5B 面積／時序基線，再比較候選。
   上表僅是結構風險，沒有預先承諾面積百分比或 MHz。generic synthesis 不能代替標準元件面積。
4. **效能**：完整 19 項與八項集合分別驗收；診斷六項只用來解釋機制。
   若實體頻率改變，需按已凍結的記憶體時間契約重新算系統時間。

現行 source review 亦發現：LSU 的 store response 分支直接清除 SQ，沒有像 load
分支一樣把 `dmem_rsp_error` 轉成 exception。這是既有驗證／錯誤回應契約缺口；
本輪正常回應的模擬無法覆蓋它。候選不能把「正常 RAM 都 PASS」當成完整錯誤語意正確。
本輪不提出 store 在回應前退休的 committed-store buffer，避免先改動尚未界定的錯誤模型。

## 重現診斷

先準備既有資格輸出（缺少時重跑對應資格命令）：

```bash
make qualify-embench-fp-dut JOBS=4
make qualify-fp-balanced-dut JOBS=4
python3 -m unittest discover -s scripts -p 'test_fp*.py'
python3 scripts/test_lsu_candidates.py
make profile-lsu-candidates JOBS=4
```

上面兩個 qualify 命令只在需要建立／重新驗證輸入時使用；研究會核對 ELF 與
已封存資格記錄的雜湊，不能默默接受不同的輸入。
完整研究結果與可審查證據完成後補入本文件。
