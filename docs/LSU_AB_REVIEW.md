# A+B 合併實驗與整數除法診斷

更新：2026-11-09（Asia/Taipei）。A+B 功能與完整共同時脈量測通過；
獨立實體面積、時序與最快合格時脈量測尚未完成。原始基線不變。

## 共同時脈結果

CPU 與 I/D 記憶體時間均為 10 ns；使用原始固定 ELF、完整 Embench 19 與
FP32 八項。FP32 的 DSP、矩陣／ML 子群各占 50%。

| 候選 | Embench 加速比 | FP32 加速比 | 此表證據範圍 |
| --- | ---: | ---: | --- |
| A | 1.045830× | 1.078255× | 已有共同流程實體資格 |
| B | 1.029459× | 1.009599× | 已有共同流程實體資格 |
| A+B | **1.073943×** | **1.088248×** | 新功能／週期量測；實體資格待完成 |

A+B 相對 A 的集合增益為 Embench 2.69%、FP32 0.93%；27 項中 22 項較快、
五項較慢。相對 B 則 27 項均較快。以上是實測，沒有將 A、B 增益相乘。

**PID 仍是重要退化：A+B 需要 8,256 cycles，A 為 7,242 cycles，增加 14.00%。**
其餘較 A 慢的項目為 GEMM、aha-mont64、nsichneu、qrduino。
因此集合平均改善不代表每項均改善，也不自動將 A+B 升為新基線。
兩個集合仍未達到各自 1.20× 的目標。

## 實作與驗證

實作提交為 `3f079c1c3d7b53c50beb13bc2d8bf366ac42999f`，CPU 只修改 LSU：
成功且被消耗的 registered response 可同拍交接下一個請求；完整 tag 匹配、
無例外的 ROB 頭部 store 可在退休標記當拍發送。仍只有一個外部 outstanding。

- 基線、A、B、A+B 各 83 項 pin-driven 測試，合計 332 項通過；三個負向對照通過。
- 新增 21 項交互情境，涵蓋同拍 load completion／store marking、較年輕 load 競爭、
  回壓、序號環繞、INT/FP、錯誤、flush、recovery 與完整 tag。
- 原 B assertion 對 response buffer 的絕對排除與 A 衝突；測試抓到後改為驗證
  成功且確實消耗的回應。失敗來源與記錄保留，未計入通過數。
- 乾淨提交建置 normal/assert 模型；18 項定向、18 項 Spike、48 項介面、
  58 項記憶體控制與 3,400 個有限值 FMA 全部通過。
- 27 項工作負載全部通過；3,629 個數值輸出及逐 PC 退休工作量與基線一致。

這些測試沒有宣稱完整 ISA／IEEE-754 覆蓋。

## 整數除法的下一步依據

[唯讀診斷](../experiments/divider-diagnosis-v1/README.md)核對了 27 項既有 profile、
六組 observer 開／關對照，以及 48 個實際指令控制案例。一般 DIV/REM 接受至
結果有效為 33 cycles，除以零／有號溢位控制為 1 cycle；未觀測到 divider 完成仲裁等待。

提前產生結果的運算元占比在 `ud` 為 85.71%、`cubic` 為 32.23%，
`nettle-aes` 為 100%；`st`、`nbody` 為零，`wikisort` 為 2.53%。
占比分母是接受的請求，包含可能被 flush 取消的工作，不能當成可節省 CPU 週期。
`nettle-aes` 有 546 次取消、`wikisort` 有四次；生命週期計數均核對一致。

建議先完成 A+B 獨立 PPA，再共同評估：針對 `ud` 的低成本提前結果路徑，
或覆蓋較廣的每拍兩個商位元迭代。Leading-zero skipping 的機會與提前結果重疊，
需分開量測。固定 FP32 八項沒有退休的整數 DIV/REM，這條路徑不能單獨完成 FP32 目標。

原始記錄、模型、ELF、來源及獨立審查見
[功能與診斷證據](evidence/2026-11-09/lsu-ab-functional/README.md)。
