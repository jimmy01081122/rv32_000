# 固定時間模型：RTL assertions 建置

2026-10-18。與正常建置分開重跑，58／58 通過；CPU RTL 仍等於 `71c24f5`。
八項程式涵蓋舊／新 legacy、固定時間與 CPU 提頻而記憶體時間不變的對照，
另含六種無效參數及 SW／SB／SH／FSW／LW／FLW 的兩種 core period 精確 fault。
排程器的 deadline、背壓、信用額與 overflow 單元控制亦通過。

`cases/` 保存本次 log、audit 與全部 12 份 fault trace；它們的 trace hashes
逐份等於[先前正常建置準備量測](../post-lsu-baseline-preparation/memory-time/summary.json)。
因此本目錄也提供該準備報告所引用、未複製到舊封存目錄的原始 trace bytes；
不回寫已封存的舊證據。

`assert-model-generation.dat` 證明重用的 Verilated RTL model 以 `--assert` 產生。
本次使用固定 ORFS runtime 的 GCC 11.4.0 與 v4.038 headers 重新編譯 C++；
實際命令、source／binary hashes 見 `context.json` 與 build log。
正常建置的 scored simulator 沒有更動，完整 27 項歷史量測保持原樣。

這項核對不代表物理 clock、面積或完整 ISA signoff；基線的實體欄位仍待完成。
核對封存：`sha256sum -c SHA256SUMS`。
