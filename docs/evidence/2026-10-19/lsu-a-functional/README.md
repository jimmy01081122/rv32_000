# LSU A：正確性與完整同頻量測

2026-10-19。此里程碑完成 A 的功能與 cycle 研究，**實體面積／時序仍在執行**。
凍結基線 `58a4159` 不變，A 的功能來源是乾淨
`39bc12d87f80af2520a72f3a75adb3151a55f4c8`。本次不將 A 替換為正式基線，
也沒有實作 B 或 A+B。

唯一功能 RTL 變更是 LSU：成功且本拍確定消耗的 response buffer，可與下一
請求接受重疊。單一外部 outstanding、原回應 register、SQ marking、store
response 後退休及 fault／flush 保守排除維持不變。

## 完成證據

- `unit-v4/`：baseline、A 各 20 個 pin-driven assertion cases 全通過，
  並保留原 RTL 無法通過 A 節拍要求的負向對照。理想 16-load stream 原為
  48 cycles／最短間隔 3 拍，A 為 33 cycles／2 拍；completion 延遲都是 2 拍。
  含三個不同 seed 的 128-load stream，response latency 1–10，及 INT／FP、
  tag wrap、背壓、flush、load／store error、forward／misalign、store marking。
  無效外部 response pins 改變不能改變已註冊 completion 或請求資格。
- `build-clean-v1/`：normal／`--assert` 兩種建置均在乾淨 39bc12d 完成，
  前後來源相同；Verilator 4.038、G++ 11.4，完整 command／log／hash 留存。
  `rv32_ooo_sim-normal.gz`、`rv32_ooo_sim-assert.gz` 是實際 executable，
  壓縮後已解壓往返核對 SHA。
- `qualification-clean-v1/`：18 directed 與 18 Spike trace cases、48 個
  assertion-enabled LSU interface cases、58 個固定時間 controls、3,400
  有限 FMA 值／旗標檢查均通過；22 records 是 18 directed＋四個 suite summary。
  固定時間工具中 `old` 標籤在這次表示**同一 A CPU 的 normal 參考執行檔**，
  不是修復前 CPU。完整 ISA／特殊 FP／所有 rounding 的覆蓋仍另列缺口。
- `measurement-10000ps-v1/`：完整 Embench19＋FP32 八項 **27/27 通過**，
  FP32 原 **3,629** 筆輸出與容差不變。每項原 ELF bytes、自我檢查／獨立數值、
  記憶體 audit、退休 SP 餘裕、profile 及原退休指令分類均核對。
  本次沒有重跑全集合 Spike；原輸入資格透過相同 ELF 身分沿用。
- `verification-run.json`：三階段 durable worker exit 0，151 個輸入雜湊
  前後一致。其 `passed:false` 是 worker 保留的資格狀態；實際功能資格在各
  suite 的 summary，研究尚待獨立 PPA 審查。
- `contract-controls-final.log`：17 個契約／量測／worker／closure tests 通過；
  `admission-controls/` 保留 baseline 拒收 A 及候選拒收改動記憶體／mapping 的
  三個實際 CLI 負向控制。`unit-v3/` 是先前開發版本，正式分母使用 v4。

## 完整同頻結果，尚待實體資格

CPU 與基線同為 10,000 ps（100 MHz），I response／I initiation interval／
D response 各固定 10,000 ps。cycles 可直接比較；A 是否能在這個 clock
通過三 corner，仍待獨立實體結果。因此下列是完整同頻 cycle 診斷，尚不是
已資格確認的系統執行時間／PPA 驗收。

| 集合 | 同頻幾何平均加速 |
| --- | ---: |
| Embench19 | 1.045830× |
| FP32 八項（兩群各 50%） | 1.078255× |
| FP32 DSP 四項 | 1.051614× |
| FP32 矩陣／ML 四項 | 1.105571× |

兩個同頻集合目前都低於各自 1.20× 規劃目標；面積尚無結果。
`common-clock-diagnostics.json` 與 `derive-common-clock-diagnostics.py` 保存
完整輸入 hash、計算及逐項等待分類。FIR 頭端等待自身已暫存回應由 8,453
降為 517 cycles；BiCG 的 SQ marking 仍為 1,676 cycles。這些是觀測位置，
不能將重疊事件加總成可省週期，也不能把 B 的未量測效益與 A 相加。

| 集合 | 工作負載 | 基線 ROI cycles | A ROI cycles | 同頻加速 |
| --- | --- | ---: | ---: | ---: |
| fp32 | fir | 74,311 | 66,117 | 1.123932× |
| fp32 | iir | 13,523 | 13,496 | 1.002001× |
| fp32 | fft | 40,867 | 37,663 | 1.085070× |
| fp32 | pid | 7,248 | 7,242 | 1.000829× |
| fp32 | gemm | 133,275 | 123,175 | 1.081997× |
| fp32 | bicg | 23,927 | 20,693 | 1.156285× |
| fp32 | cholesky | 194,161 | 183,250 | 1.059542× |
| fp32 | svm | 43,392 | 38,501 | 1.127036× |
| embench | aha-mont64 | 5,356,670 | 5,354,540 | 1.000398× |
| embench | crc32 | 5,402,220 | 5,054,736 | 1.068744× |
| embench | cubic | 14,490,894 | 14,160,446 | 1.023336× |
| embench | edn | 4,754,496 | 4,256,669 | 1.116952× |
| embench | huffbench | 3,377,028 | 3,306,646 | 1.021285× |
| embench | matmult-int | 4,193,163 | 3,825,063 | 1.096234× |
| embench | minver | 878,777 | 858,801 | 1.023260× |
| embench | nbody | 5,893,151 | 5,821,267 | 1.012349× |
| embench | nettle-aes | 5,203,513 | 4,797,126 | 1.084715× |
| embench | nettle-sha256 | 4,307,562 | 4,200,675 | 1.025445× |
| embench | nsichneu | 7,298,679 | 6,913,377 | 1.055733× |
| embench | picojpeg | 5,300,988 | 5,064,804 | 1.046632× |
| embench | qrduino | 4,524,180 | 4,377,993 | 1.033391× |
| embench | sglib-combined | 4,526,268 | 4,332,256 | 1.044783× |
| embench | slre | 4,902,163 | 4,664,230 | 1.051012× |
| embench | st | 7,165,107 | 7,092,839 | 1.010189× |
| embench | statemate | 3,368,567 | 3,100,457 | 1.086474× |
| embench | ud | 2,775,897 | 2,616,256 | 1.061019× |
| embench | wikisort | 2,173,042 | 2,134,990 | 1.017823× |

## 實體與環境的下一關

A 已新建相同 pinned image／ORFS 的 synthesis；固定 5,500 ps ordinary ABC
mapping、14,000 ps TT backend、45% slew／50 ps hold repair 及最終全 global route。
實際獨立 TT／SS／FF 100 ps grid、標準元件面積及需要時的全 27 項重新量測
尚未完成。最高合格頻率與 100 MHz 觀測點都保留，正式操作點待結果討論。

`runtime-transition.json` 保存全套功能成功後才釋放 FP 容器的檢查與實際 ID。
Docker VFS 會複製大映像，曾有一次平行建立 physical runtime 耗盡磁碟；
`vfs-readonly-diagnosis.json`、兩份 cleanup records 保留精確引用檢查與
回收範圍，沒有刪除任何 registered container 使用中的 layer 或 pinned image。
改為循序 runtime，並僅移除 physical 容器私有副本中未使用的平台與 designs；
保留工具／ASAP7 的 204-file manifest 刪減前後核對通過。
`baseline-storage-compression.json` 保存完成的舊 ODB 快取原 SHA 與 gzip
路徑；每一份在刪除未壓縮副本前均解壓往返核對，原基線封存不變。
第一個 lowering 開發嘗試因 minimal sv2v image 沒有 git 而失敗；第二次使用
已錨定的 baseline hash inventory 成功，未更換工具或改動原 baseline lowered RTL。

## 重現與核對

在此目錄執行 `sha256sum -c SHA256SUMS` 可核對全部封存檔案。
先 checkout 39bc12d，還原原資格 ELF 及 pinned `rv32ooo-fp:p1` runtime，
使用 summary 中的完整命令；輸出改用新的 `build/` 子目錄：

```bash
python3 scripts/build_experiment_sim.py --experiment experiments/lsu-a-v1/manifest.json --out build/experiments/lsu-a-v1/replay-build --jobs 2
python3 scripts/qualify_cpu_experiment.py --experiment experiments/lsu-a-v1/manifest.json --build-summary build/experiments/lsu-a-v1/replay-build/summary.json --out build/experiments/lsu-a-v1/replay-qualification
python3 scripts/measure_cpu_experiment.py --experiment experiments/lsu-a-v1/manifest.json --build-summary build/experiments/lsu-a-v1/replay-build/summary.json --out build/experiments/lsu-a-v1/replay-measurement --period-ps 10000
```

`inputs/` 是這次實際消耗的事前契約快照，沒有回寫後續進度。
原始 paths／commands 保留實際執行位置，不為封存而改寫。
