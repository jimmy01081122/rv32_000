# LSU 第一輪優化方案審查

2026-10-18。使用者已核准把 LSU 列為第一優先候選，補一般嵌入式觀測、
記憶體延遲敏感度及具體方案比較，再共同選擇實作。本文件保留事前固定的研究條件並補入結果及候選結構；
尚未選定 A／B／C 效能方案；後續[介面修復](LSU_INTERFACE_FIX.md)已獨立完成。兩類各 ≥1.20×、面積 ≤1.10× 目標不變。

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

## 已完成的診斷結果

乾淨來源 `3513c0c`，正常回應研究 **18/18 通過**；各案例在三種延遲下的
退休指令分類相同。六個 nominal 案例的觀測開／關及既有資格輸出相符，
trace／packed-layout mismatch 全為零。18 項既有與 7 項新 Python 控制通過。
模擬器 binary 與前輪完全相同，RTL／sim source 也未改動。
[封存](evidence/2026-10-18/lsu-candidates/README.md)含事前 protocol 快照、每一案原始
profile／stdout、工具／來源／ELF 身分，以及分開列出的負向環境診斷。

| 案例 | latency 1 cycles | latency 2 cycles | latency 4 cycles | latency 4／1 slowdown |
| --- | ---: | ---: | ---: | ---: |
| crc32 | 5,402,220 | 5,576,480 | 6,098,416 | 1.129× |
| matmult-int | 4,193,163 | 4,651,344 | 5,647,095 | 1.347× |
| wikisort | 2,173,042 | 2,325,955 | 2,662,195 | 1.225× |
| minver | 878,777 | 947,093 | 1,143,155 | 1.301× |
| fir | 74,311 | 83,810 | 109,737 | 1.477× |
| bicg | 23,927 | 28,880 | 39,075 | 1.633× |

這個 slowdown 比較外部回應變慢的影響，沒有量測 A／B／C，也不能反向換算其收益。
例如 `crc32` 與 `BiCG` 的敏感度差異大，不能用單一 FP 個例代替一般嵌入式。

nominal 條件下的兩種互斥等待位置如下；百分比各以該案 ROI cycles 為分母：

| 案例 | store ack 等待 | 頭端 load 自身回應已暫存的等待 | SQ marking 節拍 |
| --- | ---: | ---: | ---: |
| crc32 | 348,516（6.45%） | 174,256（3.23%） | 174,258 |
| matmult-int | 147,318（3.51%） | 55,210（1.32%） | 73,613 |
| wikisort | 209,444（9.64%） | 38,160（1.76%） | 89,561 |
| minver | 149,878（17.06%） | 19,992（2.27%） | 56,624 |
| fir | 1,088（1.46%） | 8,453（11.38%） | 543 |
| bicg | 6,460（27.00%） | 211（0.88%） | 1,676 |

SQ marking 是 store ack 等待的子分類，不能再次相加。其他等待亦很重要：
`minver` 頭端 FDIV 未完成占 185,937 cycles；`matmult-int` 的整數／相依頭端等待
占 793,554 cycles。頭端 opcode 只定位等待位置，不等同功能單元本身的耗時；
後者也可能仍在等 load 或其他依賴。這支持分別實驗 A、B，不能據此保證集合 ≥1.20×。

## 歷史正確性前置項：兩個負向探針及後續修復

以下保留 `3513c0c` 研究時的修復前結果。將環境變更放在獨立 C++ harness，重用相同 Verilated RTL model；正常模式的
`store_forwarding` 與 `rv32i_basic` 完整 stdout 都與基準逐 byte 相同。
下列負測不混入上面的 18/18 正常研究分母：

| 探針 | 環境改動 | 兩個定向 ELF 的實際結果 | 結論 |
| --- | --- | --- | --- |
| 獨立 request-ready 節流 | 空閒時每 4 cycles 開放一次 ready，仍保證持續有接受機會 | 2/2 watchdog；記錄到 blocked load 時 `lsu_ready=1`、`ex0_advance=1` | load 的上游消耗未等外部 request handshake，請求可遺失 |
| 一次 RAM store error response | request-time RAM 寫入行為保持不變，只把一個 store response 的 error 設為 1 | 2/2 確認送出 error，程式仍正常退出，沒有 cause 7 trap | store response error 未轉為 store access fault |

[原始負測與控制](evidence/2026-10-18/lsu-candidates/diagnostics/results.json)保留非零退出與
未發生的 trap，`environment_contract_passed=false`。這些是以前未覆蓋的介面缺口，
不表示正常延遲研究失敗，也不能把正常 PASS 當成介面正確性已成立。

優先修正方向為：外部 load 的 AGU 消耗只在請求真正被接受時前進，等待期間保持
請求身份；內部 forwarding／misalign 仍依各自接受條件處理。store error 則須以
正確 tag／位址回報 cause 7，禁止在錯誤送往 ROB 前先走正常 ack／退休，並確保
SQ／pending 只清除一次。後續已由 `ec0baa3` 的[介面修復](LSU_INTERFACE_FIX.md)完成：48/48 assertion cases、原探針重播及全工作負載功能回歸通過；歷史負測封存維持原樣。正式新基線仍待量測與 PPA 契約。

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
介面修復後，建議先固定新基線，**A 作第一個效能實驗、B 獨立對照**，
之後才評估 A+B；C 的資料／例外 mux 與 completion-to-retire 路徑風險較高，列後續。
A 可同時影響讀／寫交錯，B 有明確的 marking 節拍目標，但相依與外部交易可能遮住收益。
具體方案仍交由使用者共同選定，這裡沒有先實作任何一項。

A 還須正式更新 AP5B 契約：現行架構文字及 LSU assertions 2／6 禁止任何
`rsp_buf_valid` 時接受新請求。新不變條件應是「已有外部 in-flight 時仍禁止；
若本拍 response buffer 將被消耗且舊 metadata 已完成交付，才可接受下一請求」。
不能只刪除原 assertion；應加入交接／未消耗禁止／flush／error 的對應檢查。
目前一般模擬建置未開 `--assert`，候選的驗證模式也須明確開啟並記錄。

在連續獨立請求、無其他瓶頸的理想介面時序下，A 預期能把最短 request 間隔
從 `delay+2` 改為 `delay+1`，latency 1 即 3→2 cycles；B 最多先針對一個
head-store marking 節拍提出消除假設。這是設計推導，須以候選波形確認，
不是本輪量到的 CPU 加速比，也不能當成集合收益預測。

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

上述 ready／store-error 缺口須納入基線資格；不能用「正常 RAM 都 PASS」替代。
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
獨立環境探針的完整 C++ source、build command、模型物件雜湊與執行腳本也在封存中；
它們使用另一個 executable，不替換正式模擬器。前輪 Embench19／FP32 八項的主機與
Spike 證據透過相同 ELF 身分沿用，本輪未重跑完整主集合或主機／Spike。
