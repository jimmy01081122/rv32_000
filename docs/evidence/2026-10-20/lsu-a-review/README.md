# LSU A 驗證與審查封存

2026-10-20。[完整審查結論](../../../LSU_A_VERIFICATION_REVIEW.md)記錄兩項
工具漏檢的修正、35 項 baseline／A 單元覆蓋及原數據重新核對。
本輪沒有修改 CPU RTL、simulator inputs 或 physical policy，也沒有開始 B。

- `qualification-clean-v1/`：乾淨 `38107c8` 上的 18 directed、18 Spike、48 interface、
  58 fixed-time、3,400 finite FMA 回歸；normal／assert binary 身分與原建置相同。
- `unit-35-v1/`：baseline、A 各 35 項與原 RTL 負向節拍控制，完整 CSV／stdout／
  build logs、原 baseline LSU、生成旗標與實際單元 binary gzip。壓縮均往返核對。
- `admission-controls-v1/`：四個刻意改動的副本，保留舊版接受與新版拒收結果。
  它們是負向控制，不是 CPU 量測。原始參考 measurement directories 採 symlink
  使用，封存不複製這些 symlink；重播由 `context/admission-controls.py` 以原證據重建。
- `context/review-10000ps-v2.json`、`review-9900ps-v2.json`：以新版工具重新審查
  全部 27 項與既有三 corner 報告，明確綁定原 build 與本輪 clean qualification。
  加速比、面積、目標判定均與前輪相同；`passed:true` 與目標未達分開記錄。
- `context/contract-controls-v1.log`：30 個控制測試通過；`inputs/` 保存相同的
  reviewer／validator／單元測試與相關 RTL 快照，結果中的來源雜湊可直接核對。
- `context/source-and-evidence-integrity.json`：凍結 A inputs 不變，先前三份封存
  各 214／438／369 個索引檔案重新驗證通過。
- `context/runtime-launch-v1.json` 與 driver log 保留啟動 entrypoint 不相容、
  尚未執行驗證的失敗。修正後使用同一 pinned image；完成全部工作、只剩 sleep
  後才移除專用容器，receipt 在 `runtime-cleanup.json`，映像及結果保留。

`copy-inventory.json` 記錄原 path／SHA 與 binary gzip 往返證明。
`SHA256SUMS` 涵蓋全部封存檔案；於本目錄執行 `sha256sum -c SHA256SUMS` 核對。
原命令／path 不為封存改寫；需要時還原原 build paths，再執行審查文件中的命令。
單元擴充測試有實際來源雜湊；它們不是新的完整 core 建置或完整 ISA signoff。
