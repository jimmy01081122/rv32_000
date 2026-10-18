# RTL → sv2v Verilog 身分核對

2026-10-18。此封存核對本次實體作業的 RTL lowering 來源，**不是合成等價性
證明或實體閉合**。原始 `build/baseline-setup/rtl_lowered.v` 保持不變。

固定的 `rv32ooo-syn:g1` image、sv2v 0.0.12，重新讀取 manifest 的完整 18 份
RTL，採 `--top=rv32_ooo_core -DSYNTHESIS -I rtl/pkg`。`v2.lowering.json`
記錄 source／filelist／wrapper／binary 雜湊、命令、真實退出及前後輸入核對。
結果與正在使用的實體輸入 **逐 byte 相同**，SHA256：

`2cbf3fa60c07b6cf21a81c5317e54b28c873bdee050df43793382ae9956d7382`

`verified-lowered.v.gz` 解壓後對應上述 SHA。`image.json` 記錄 Docker image ID；
重建容器沒有使用網路。

第一版重現命令漏掉原合成流程的 `SYNTHESIS` 巨集，因此精確 byte 比對失敗。
`v1-preprocessing-diff.patch` 顯示差異限於三個 `ifndef SYNTHESIS` 區域的
assertion 外框／`$past` scaffolding。補齊原本的巨集後另開 v2 重現，沒有刪改
RTL 或本次實體輸入。v1 失敗紀錄保留，不列為通過。assertion-enabled 模擬
資格確認另見 [fixed-time-assertions](../fixed-time-assertions/README.md)。

在相同 synthesis image 內重跑：

```bash
python3 scripts/lower_baseline_rtl.py --out build/rtl-recheck-fresh.v --compare build/baseline-setup/rtl_lowered.v
```

全新環境產生輸入時，`--out build/baseline-setup/rtl_lowered.v`，不加 `--compare`；
輸出路徑必須不存在。在本封存目錄執行 `sha256sum -c SHA256SUMS` 核對所有檔案。
