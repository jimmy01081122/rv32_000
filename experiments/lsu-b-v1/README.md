# LSU B v1：ROB 頭端 store marking 同拍送出

2026-10-21，B 獨立實驗已完成：[審查](../../docs/LSU_B_REVIEW.md)與[原始證據](../../docs/evidence/2026-10-21/lsu-b/README.md)已封存。功能／完整同頻 cycle 資料通過；面積0.995585×，但SS setup與FF hold未通過，無完整合格操作點。同頻 cycle GM為Embench 1.029459×／FP32 1.009599×，不作正式PPA通過成績。

後續[時序診斷與選項](../../docs/LSU_B_TIMING_DIAGNOSIS.md)已完成，另行保存
12 次唯讀程序、映射連線核對與原 corner 重現證據；沒有修改本實驗契約或 CPU。

下列保留事前固定的設計與驗收條件。使用者核准進行 B。獨立分支 `codex/lsu-b-marking` 的父版本為
凍結基線 `58a4159da0372b3286758be1e6c1b50f9f28cc27`。沿用 A 已審查的
量測工具與歷史證據（`bf6702c`），CPU 的其餘 17 個 RTL 檔與模擬／實體
輸入仍逐檔匹配基線；唯一 RTL 修改為 LSU。沒有合併 A 的 response-buffer overlap。

事前固定的假設：ROB 頭端 store 已完成、完整 ROB tag（seq 與 idx）匹配有效
SQ entry、地址／資料已由 AGU 同時捕獲、沒有 exception／flush 且處於 RUN，
可在退休 marking 當拍提出記憶體請求。請求背壓時保留 marking；仍等待實際成功
store response 才 ack 退休。保留 16-slot SQ、一筆 external outstanding、
原 registered-response 排除與精確 store fault 回報。新時序風險為 ROB head 到
記憶體 request 的組合路徑。

驗證與判定順序：

1. 原基線與 B 各執行 62 項實際 LSU pin-driven 案例，另要求原基線拒絕 B 的
   同拍節拍。包含 byte／half／word、INT／FP store、seq wrap、完整 tag、
   unresolved address、misalign、flush／recovery、背壓、fault、優先權，及
   3 個 seed 各 128 store 的隨機 ready／response 延遲。保留 A 不存在的控制。
   16-store 理想串流只作機制診斷，不當成完整 CPU 加速比。
2. 乾淨 commit 新建 normal／assert 模型，執行 directed 18、Spike 18、
   assertion interface 48、fixed-time 58、finite-FMA 3,400。
3. 使用原始凍結 ELF／數值／容差完整跑 Embench 19 與 FP32 8，逐筆核對
   3,629 輸出、指令分類與逐 PC／instruction／kind 工作量。
4. CPU 先以 10,000 ps 比較；I response／initiation interval／D response
   固定 10,000 ps。相同 ASAP7 RVT、TT-only、ABC mapping 5,500 ps、backend
   14,000 ps、TT 45% slew／50 ps hold ECO，再做完整 global route。
   不重用 baseline／A 的 netlist／CTS／GRT。獨立 TT／SS／FF 實測 100 ps
   網格，相鄰較快點失敗才界定最快已測通過點；不以 slack 推算宣稱頻率。
5. 100 MHz 與最快合格點不同時各跑完整 27 項；記憶體取樣跨拍須實際量測。
   reviewer 綁定 build／functional proof、binary 與完整輸入、實體資格。
   固定目標：Embench 與 FP32 各 ≥1.20×、標準元件面積 ≤1.10×。

本版已有完整功能／cycle與失敗實體結果；不取代凍結基線，後續調整或組合仍由共同選擇。
