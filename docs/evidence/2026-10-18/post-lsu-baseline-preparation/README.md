# 修正後基線：固定時間模型與全集合準備量測

2026-10-18。**這是 preparation，尚未完成 global-route 實體基線。**
5,500 ps 是本次模擬探索設定，不是已通過時序的 CPU period。
不得用它發布頻率、實體執行時間加速、面積或規劃目標達標。

- 量測來源：乾淨的 `58220716706da671c04cc98807da71a2e6db81dd`；前後狀態一致。
  18 份 CPU RTL 與 `71c24f5` 一致；A／B／C 均未實作。
- 主集合完整：Embench 19／19，FP32 fast 8／8；3,629 筆數值及原 checksum 全部通過。
  同一批 ELF 的 ROI cycles 逐項等於既有已資格確認的參考；未縮小分母。
- I response、I initiation interval、D response 均為固定 5,500 ps；core period
  亦為 5,500 ps。這一校準點重現先前一拍記憶體行為，未宣稱真實 SRAM 延遲。
- 記憶體 audit、cycle partition、退休 trace／layout 一致性及退休 SP 的
  stack headroom 檢查通過。退休 SP 是診斷觀測，並非所有瞬間 stack 存取的形式證明。
- `memory-time/summary.json`：58／58 檢查，包含八項程式的舊／新 legacy／固定時間
  輸出對照、固定記憶體 5,500 ps 而 CPU period 改為 3,000 ps、無效設定拒絕，
  以及 SW／SB／SH／FSW／LW／FLW 的精確 access fault。
- `environment/time-model-final-gates.log`：本輪 18／18 directed、18 項 FP checker
  控制及 7 項 LSU checker 控制。前輪 Spike／FMA／48 項介面資格確認仍見
  [LSU 修復證據](../lsu-interface-fix/README.md)，不合併成本輪新增次數。
- `environment/baseline-controls-final.log`：5 項輸入契約測試及一組量測證據正反例。
  `measurement-recheck.json` 使用提交 `1223f3a` 的更嚴格 checker，再核對完整
  27 項實際參數、交易計數與原始 log／audit／profile／ELF hashes，全部通過。

`measurement/input-manifest.json` 保留量測當時的原始契約，SHA256 等於 summary
所記錄的 manifest hash；後續實體 I/O min/max 細化不回寫這份歷史輸入。
`runtime-build.json` 記錄 C++ runtime 的實際重編譯環境，包含 ORFS image GCC
11.4.0 與精確 v4.038 headers；不把這次重編譯誤標成全部由原 sim image 產生。
ELF 與 simulator binary 留在 ignored build；本 archive 保存其 hash，原編譯命令
則在 `baselines/ap5b-post-lsu-v1/build-contract.json`。

`environment/` 保存工具／平台 hash、容器來源、Liberty metadata、三 corner 獨立
載入及 lowering hook 正反例。它也包含環境建置過程的 log；只有以上明列檔案
作為本輪正向驗證。`development/` 的失敗嘗試不計為通過；gzip 檔解壓後的 hash
列在 `file-index.json`。部分早期診斷僅留於工具對話紀錄，未捏造遺失的原始 log。

實體工具的版本／corner 舊標籤已依 binary 與 Liberty 實檔修正。最終仍須取得
global-route DB、確認寄生還原、完整 timing constraints、獨立 TT／SS／FF
setup／hold 與電氣檢查，才可凍結 period、記憶體實際 ps 與面積。

在此目錄執行 `sha256sum -c SHA256SUMS` 可核對封存內容。
