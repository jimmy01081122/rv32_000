# LSU 介面缺口修正與驗證

2026-10-18。功能來源 `ec0baa3`；這是 correctness 修正，A／B／C 效能方案尚未實作。
[封存證據](evidence/2026-10-18/lsu-interface-fix/README.md)保留乾淨來源、工具／模型身分、
修正前失敗、修正後結果與原始輸出。兩類各 ≥1.20×、標準元件面積 ≤1.10× 的規劃目標不變。

## 修正行為

**外部 load 的消耗與 request handshake 一致。** 原本 AGU 在 request-ready 為 0 時
仍可被 LSU 接受，卻沒有建立 in-flight 所有權，導致 load 遺失及 watchdog。
現在外部 load 的 `lsu_ready` 須同時滿足 `can_issue_load && dmem_req_ready`。
`dmem_req_valid` 仍獨立於 ready，forwarding／misalignment 的內部接受條件沿用原路徑。

**store access fault 先寫回 ROB，禁止正常退休。** 原本 store response 不論 error
都 ack 並清除 SQ。現在成功 store 的 ack 時序維持原樣；error response 則禁止 ack，
釋放 SQ 並把 tag、原始地址及 cause 7 放入既有 AP5B response buffer。
新增一個 store/load 分類位元，store fault 不產生 PRF result，`dmem_pending` 持續包含
buffer 中的 store 所有權。未增加 SQ、LQ 或 external outstanding 數。

| 時點 | 失敗 store 的行為 |
| --- | --- |
| error response 握手 | `sq_retire_ack=0`；SQ 釋放，buffer 接手 tag／地址 |
| 下一拍 | registered exception completion 交給 ROB；buffer 仍阻擋新外部 request |
| ROB exception 可見 | cause 7 trap，mepc 為故障 store PC、mtval 為原始地址；故障 store 不退休 |

主測環境的 error write 不更新 RAM；另重播原探針保留 request-time 寫入、只改 response error。
兩種環境均觀察到 cause 7。CPU 不回復匯流排上已發生的寫入。

## 驗證矩陣與紅燈轉綠

`make check-lsu-interface JOBS=4` 建立獨立 `build/sim-assert`，在固定 Verilator 4.038
下開啟 `--assert`，再執行 48 個檢查：

- 6 項既有程式 × ready 每 4 cycles 開放一次 × 回應延遲 1／4，共 12 案；涵蓋
  forwarding、partial overlap、unresolved store、wrong-path store 及 redirect。
- SW／SB／SH／FSW／LW／FLW × ready period 1／4 × 回應延遲 1／2／4，共 36 案。
  每案核對唯一 fault request／response、唯一精確 trap，以及故障指令和指定年輕指令未退休。
  韌體核對 mcause／mepc／mtval、整數／FP 目的暫存器 rollback、年輕 store 無副作用，
  並在 MRET 後完成新的 store／load。
- SB／SH 以對齊 word 的 bus address 注入錯誤，mtval 分別核對原始 +1／+2 byte address。

修正後 **48/48 通過**。以相同最終 ELF bytes 重播修正前 LSU，得到 **42 失敗／6 通過**；
原本正常的 6 個無 ready 背壓 load-fault 案例仍通過。before model 使用 `2672e3d` 的 LSU，
搭配相同新環境及修正後的 core assertions；這是明確組裝的反事實模型，並非未修改的舊 checkout。

另有兩組正常模式對照：`store_forwarding`／`rv32i_basic` 在舊模型、新模型、assertion
模型上的完整 stdout 逐 byte 相同。原始 ready／store-error 四個探針也轉綠；它們僅作原缺陷
重播，精確 trap／恢復由上述專用韌體證明。

啟用 assertions 也補齊兩項驗證基礎：Verilator 4.x 的模擬時間回呼，以及既有 core flush
assertions 的取樣時點。後者原先在 flush 邊緣檢查清除前舊值；現在於下一拍檢查 INT／FP EX0
與 FP completion 已清除。此處沒有改動 flush 功能 RTL，也沒有刪除該檢查。

## 整體回歸與基線狀態

乾淨 `ec0baa3` 上的結果：lint、介面 48/48、既有定向 18/18、Spike commit 比對 18/18、
有限 FMA 3,400 筆結果／旗標及 cancellation probe、FP32 fast 8/8（逐筆 3,629 筆）、
Embench 19/19 主機／Spike／DUT 自我檢查，以及 25 項 Python 控制均通過。
FP32 的 fixture、ELF、checksum、ROI cycles 與修正前相符；Embench 19 項的 ELF、ROI／總週期、
退休數亦相同。正常環境下未觀察到效能變化，沒有以本次修復宣稱 CPU 加速。

驗證工具後續提交 `e686edd` 補上 compiler failure 中斷時清除舊 PASS summary 的保護，
新增一項先紅後綠的失敗保護測試，並固定測試 ELF 的 STT_FILE 名稱。
該提交沒有改動 RTL／sim／build flags；乾淨來源再次通過 48/48，兩個 simulator binary
與完整回歸相同。六個 ELF 重建逐 byte 相同，loadable payload 與原測試相同。

這建立介面修復的功能參考點，仍非正式 AP5B 效能／實體基線。正式資料尺寸、計時／記憶體契約、
完整 ACT4／FP 覆蓋及新鮮 PPA 尚待補齊。舊六案例敏感度 runner 有來源鎖，會拒絕新 RTL；
後續量測須另立修正後來源與協議，保留舊研究原始證據，不放寬其鎖定條件。
