# 實體工具探索：未完成作業

2026-10-18。此處全部是 **未完成 global-route 的工具流程探索**，不提供
基線 MHz、閉合週期或標準元件面積；不能將前置 stage 的數字當成正式 PPA。
RTL 仍是修正後的 AP5B；沒有 A／B／C 架構變更。

| 作業 | 有效資訊 | 最終狀態 |
| --- | --- | --- |
| `physical-5500ps-process-clean-v2` | 平台 full-adder extraction；Yosys log 有正常結尾、無 ERROR，完整 mapped netlist | 全流程停止於 placement；原作業未保存最終退出碼，原因未確定 |
| `physical-5500ps-abc-mapping-probe` | 普通 ABC mapping；Yosys log 有正常結尾、無 ERROR，完整 mapped netlist | 全流程停止於 placement；原作業未保存最終退出碼，原因未確定 |
| `physical-14000ps-abc-cached` | 驗證上述 ABC 合成輸入身分，重用 5,500 ps 映射網表；新背景 worker | Make 退出 2：pinned OpenROAD 不支援 placement `-random_seed` |
| `physical-14000ps-abc-compatible-v2` | 修正 seed 旗標後可進入 timing-driven placement | 發現建置載入三視圖而非已約定的 TT-only；明確送 SIGTERM 停止 OpenROAD，Make 退出 2 |
| `physical-14000ps-tt-abc-v3` | TT-only placement／CTS 完成；第一輪繞線無 overflow，普通 post-route setup／hold repair 完成 | 額外 WNS 優化呼叫不支援的 `reroute` move，OpenROAD abort，Make 退出 2；沒有最終 GRT DB |

不為早期作業補造退出碼或停止原因。後兩項保留 durable worker 的原始
`run.json`／`job.json`，記錄真實退出、時間、輸入雜湊與命令。第一項 cached
attempt 的 worker source 尚未 commit，`source_status` 保留其當時狀態；不得
把它稱為乾淨來源量測。

兩份 5,500 ps 的 `mapped-netlist.v.gz` 解壓後 SHA 在 `index.json`，壓縮前後
逐一核對。它們只支持已完成的**合成 stage**快取；建置／映射條件須分別記錄，
14,000 ps backend 不代表重新以 14,000 ps 合成。正常 ABC 是工具映射方式，
不是 CPU 優化；正式基線與候選須使用同一映射政策。

原始 logs／reports、SDC 與每次 run record 保持原內容。較大的中間 OpenDB
在本機 `build/` 可還原壓縮，沒有刪掉 log 或映射網表；壓縮紀錄不是正面
時序證據。`database-compression.json` 只描述相應中止作業的中間資料。

後續 TT-only 作業另開 `physical-14000ps-tt-abc-v3`，不覆寫以上失敗。
它的失敗也保留於此；完成的 `4_cts.odb.gz`／`4_cts.sdc.gz` 僅作 CTS stage
快取，解壓後 SHA 在 `index.json`。另一份 `4_1_cts.odb` 是相同資料庫的複本。
修正設定先通過 [完整 ORFS 小型 API 探針](../global-route-api-validation/README.md)，
再以新標籤 `physical-14000ps-tt-abc-grt-compatible-v4` 從 CTS 重跑繞線。
仍須獨立 TT／SS／FF STA、繞線審查與正式全 27 項量測。
核對本封存：在此目錄執行 `sha256sum -c SHA256SUMS`。
