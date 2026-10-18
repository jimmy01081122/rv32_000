# 修正後 AP5B 基線 v1

2026-10-18。使用者已核准先固定修正後基線，再共同選擇 A／B 獨立實驗。
本目錄先鎖定來源與輸入；`manifest.json` 的 physical／measurement 完成前維持 preparing，
不以舊 AP0／AP5A 報告補入面積或頻率，也不宣稱規劃目標達標。
固定時間模型的 [27 項準備量測](../../docs/evidence/2026-10-18/post-lsu-baseline-preparation/README.md)
已在乾淨 `5822071` 完成，全部通過且 ROI cycles 等於原參考；5,500 ps 尚非實體閉合值。

- CPU：`71c24f5`，含 FMA、FP store 與 LSU 介面修復；18 個 RTL 檔案逐一鎖 hash。
  A／B／C 尚未實作。
- 一般嵌入式：Embench-IoT 1.0 完整 19 項，保留上游資料、精度、暖機與迭代設定。
- FP32：既有 DSP 四項＋矩陣／ML 四項，各組 50%；八份原 fixture／容差不變，
  共核對 3,629 筆。v1 使用現有已驗證資料，擴大資料須另立契約並重建雙方基線。
- 原編譯／連結命令在 `build-contract.json`；主比較固定使用相同 ELF bytes。
  FP32 採 `fast -fno-fast-math`，off 為敏感度附表。
- 計時採原 ELF 的 RDCYCLE ROI，包含既有計時入口開銷，不做事後扣除。
  deterministic 模擬不以主機執行秒數當 CPU 效能。
- 記憶體：1 MiB，I／D 獨立通道，**固定實際時間**。以基線實際通過的 period
  校準原先一拍的 I latency、I initiation interval 及 D latency。候選提頻時 ps 不變；
  response 於到期後第一個 core edge 取樣，量化誤差另記錄。
  這是研究記憶體模型，未宣稱量得真實 SRAM 延遲。
- 延遲附表只改 D response 為基準時間的 2／4 倍，I timing 不變；不併入主分數。
- 實體採 ASAP7 RVT、TT 建置、SS／FF 時序核對與 global-route 寄生估算。
  wire RC 沿用平台 nominal 模型，不宣稱多 corner 詳細抽取或 detailed-route closure。
  I/O delay、slew、load 與 uncertainty 為固定絕對值，不隨掃描 period 改變。
  I/O 最大 delay 為 1,100 ps，最小為 0 ps；最終每個 corner 各自執行 STA。
- 面積邊界是完整核心，包括 PRF／SQ／commit trace；外部 RAM 不含在核心面積內。
  比較 global-route 同階段的標準元件實例面積，包含 clock／repair cells。
- 功能失敗、缺項、hash 不符、超時或不完整量測均使完整集合無效；不得縮小分母。

`make check-baseline-contract` 檢查完整來源／輸入契約；`make check-memory-time`
驗證 legacy 等價、固定時間提頻與精確例外。`measure_post_lsu_baseline.py` 僅在乾淨來源
量測全 27 項，保留 cycle partition、數值及退休 SP 的 stack headroom 診斷。
`--preparation` 輸出明確不能當成已完成的實體基線。

兩個主集合各自驗收 ≥1.20× 執行時間加速、標準元件面積 ≤1.10×。
個別案例及兩個 FP32 子群分別可見；沒有另外增加未核准的退步門檻。
