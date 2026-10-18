# LSU 介面修復證據 — 2026-10-18

功能來源 `ec0baa398a02a7dbe1981208aee792c4ea3b71e6`；完整回歸起訖均為乾淨來源。
驗證器後續來源 `e686edd8f222788093072d8130a81f9ac4d3eb5e`：清除 stale summary、增加
中斷負測及固定 ELF STT_FILE 名稱，沒有改動 CPU RTL／sim source／build flags。
後者也由乾淨來源重跑 48 案；兩個 simulator binary SHA-256 與完整回歸完全相同。

本輪修復外部 load 在 ready 背壓下被消耗，以及 store error 被正常 ack／退休的兩個已知缺陷。
未實作 A／B／C，未量測新 PPA，也未宣稱達成 ≥1.20× 或面積 ≤1.10×。
[修復說明](../../../LSU_INTERFACE_FIX.md)列出時序、測試分母與限制。

| 檢查 | 結果／位置 |
| --- | --- |
| 乾淨功能回歸 | `run.json`：lint、介面 48、定向 18、Spike 比對 18、有限 FMA 3,400、FP32 八項、Embench 19、25 項既有 Python 控制通過 |
| 同 ELF 紅燈轉綠 | `interface/before-exact.json`：舊 LSU 42 失敗／6 通過；`interface/after.json`：48/48 |
| 原探針重播 | `interface/original-probes.json`：兩程式 × ready／store-error 共四案轉綠，保留原 request-time write 行為 |
| 正常模式控制 | `interface/default-controls.json`：兩程式在舊、新、assertion 模型完整 stdout 相同 |
| 正常工作負載不變 | `nominal-comparison.json`：FP32 fixture／ELF／checksum／ROI；Embench ELF／ROI／總週期／退休數相同 |
| 工具失敗保護 | 原工具在 compiler failure 後殘留 PASS 的負測為紅；新測試為綠，原始輸出在 `log-index.json` |
| 後續工具重跑 | `verifier/interface.json`：48/48；`verifier/proof.json`：RTL／sim diff 為空、binary 相同、六 ELF 重建逐 byte 相同且 loadable payload 未變 |

`before-exact` 是明確組裝的反事實模型：`2672e3d` 的 LSU 加上與修復版本相同的
C++ environment、core flush assertion 取樣修正及 assertion build helper；不是未修改的舊 checkout。
該 JSON 的 `source_commit` 是 launcher repo 身分；實際模型每個 RTL hash 與舊 LSU commit
在 `context.json`。最後修復測試的相同 ELF bytes 在舊模型重播，排除輸入差異。
歷史失敗封存 [lsu-candidates](../lsu-candidates/README.md)保持原樣。

`run.json` 保留一次 orchestration log 路徑錯誤的恢復紀錄：前九個命令已完成，最後控制命令
尚未執行時檔名含 `/` 而中斷。更正檔名後在相同乾淨來源完成剩餘命令；沒有重試失敗工作負載。
原 traceback 與補完程式均保留。

`log-index.json` 將原 build log／trace 路徑對應到 `raw/*.txt`、SHA-256 與引用位置；
相同 bytes 共用一份 raw，沒有刪除失敗。`SHA256SUMS` 涵蓋全部封存檔案。
ELF、models、VCD 與生成的 C++ 留在 ignored build，這裡保留其身分及可檢視輸出。
編譯／執行命令在 JSON，工具 image ID／來源 hash 在 `run.json`，額外重播程式在 `reproduce/`。

正常重跑入口：

```bash
make check-lsu-interface test diff-test JOBS=4
make check-fma-finite qualify-fp-balanced-dut JOBS=4
make qualify-embench-fp-dut summarize-embench-fp-dut JOBS=4
python3 -m unittest discover -s scripts -p 'test_fp*.py'
python3 scripts/test_lsu_candidates.py
```

完整效能資料／計時／記憶體契約、完整 ISA／FP 覆蓋與 AP5B 實體基線仍未凍結。
