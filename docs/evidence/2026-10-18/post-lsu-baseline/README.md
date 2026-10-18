# 修正後 AP5B v1：global-route 基線

2026-10-18。實體與正式 27 項量測均通過，v1 研究基線已凍結。
CPU 的 18 份 RTL 與 `71c24f5` 相同，尚未實作 A／B／C。

- 實測週期 **10,000 ps（100 MHz）**：TT／SS／FF 在同一資料庫各自獨立
  通過 setup、hold、電氣及約束涵蓋檢查。相鄰 9,900 ps 在 SS setup 失敗；
  這是最小已測通過的 100 ps 網格點，不是由 WNS 推算的連續 Fmax。
- 標準元件面積 **22,081.118400 µm²**，180,612 CORE instances、18,157
  registers、0 macros。包含 PRF／SQ、commit trace、clock／repair cells；
  外部 RAM 不含在內。
- I response、I initiation interval、D response 固定為 **10,000 ps**。
  候選 CPU 提頻時這些 ps 值不變，於到期後第一個 core edge 取樣。
- ORFS `8359fde81991e6118b15b8a93fcde606b577794d`、ASAP7 RVT，TT-only
  建置；synthesis mapping 原約束 5,500 ps、backend 建置 14,000 ps，最終
  以實際 9,900／10,000 ps STA 定週期，三者分開記錄。普通 ABC mapping。
- 既有 ORFS 相容性 overrides 保留於 `physical/run.json`：使用 pinned
  placement default、停用不支援的額外 `reroute` move，保留一般修復。
  最後從原始 v4 route checkpoint 單次執行 TT 45% slew margin／50 ps hold
  repair 及全設計 global routing，不沿用 v5／v6 混合開發 ECO 結果。
- 175,272 routed nets、wirelength 1,438,123 µm、總 routing demand 29.60%，
  各層 overflow 0；兩次 placement legalization failures 均為 0。

`physical/initial-14000ps/` 保留初次通過的 14 ns 三 corner 報告；
`physical/boundary-9900-10000ps/` 保留實際邊界報告和 closure review。
每個 corner 的報告檔案 inventory 及工具／平台 204-file 前後核對均保留。
`physical/routing-review.json` 記錄完整路由 stdout 與 native placement／antenna
檢查；資料庫、SDC、guide 以 gzip 保存，解壓後 bytes 與原分析輸入一致。
未通過的早期結果在相鄰的 `global-route-initial-review/` 與
`global-route-slew-diagnosis/`，不作正式比較分母。

本結果限於 **global-route 寄生估算的研究基線**，三個 library corners 共用
平台 nominal wire RC。尚無 detailed-route DRC／LVS、多 corner 寄生抽取、
OCV 或 workload activity 功耗量測。Antenna 的模型檢查不能替代製造驗證。
完整 ACT4／FP 架構覆蓋也仍有獨立缺口，詳見 `docs/STATUS.md`。

`input-manifest.json` 是正式量測消耗的精確契約快照，SHA 與
`measurement/summary.json` 相符。正式來源為乾淨
`9769123bceb53142fc425974592eac877b4198ce`，前後狀態一致；
Embench **19/19**、FP32 fast **8/8**，**3,629** 筆獨立數值全通過。
27 項原 ELF／ROI cycles、記憶體 audit、profile 與退休 SP 餘裕均核對；
這輪沒有重跑全集合 Spike，不與既有資格的分母混算。
`environment/frozen-baseline-controls.log` 保存凍結後 20 項契約／量測／worker／
closure 控制的原始輸出，實際命令、退出碼及輸入 hashes 另列於 context JSON。

最終 live manifest 只將 preparing／physical 狀態改為 frozen／qualified，
並增加完成時間與量測證據引用；記憶體、週期、面積、工作負載及原始容差不變。
歷史快照不回寫。`baseline-summary.json` 保留逐項 `cycles × 10,000 ps` 時間；
尚無候選 CPU 加速。退休 SP 是診斷觀測，不是全部瞬間 stack 存取的形式證明。

計分 simulator SHA256：
`fd2049c30c5453a532735eefe6c189bc879ce1220a2c33464573168bf24eae78`。
`rv32_ooo_sim.gz` 保留實際 executable；runtime 使用 GCC 11.4／Ubuntu 22.04，
建置記錄在相鄰 `post-lsu-baseline-preparation/runtime-build.json`。
原 ELF bytes 在各案例 `input.elf`，完整編譯命令在基線的 `build-contract.json`。
`measure_post_lsu_baseline.py` 是基線專用入口，會拒絕不同 RTL；未來候選入口
須讀取固定 10,000 ps 記憶體契約，不能讓記憶體隨候選 core period 加速。

在此目錄執行 `sha256sum -c SHA256SUMS` 核對全部原始資料。
要重做 STA，可把 `physical/` 複製到新的 `build/...` 目錄，將 `5_1_grt.odb.gz`
解壓到該目錄 `results/asap7/rv32_post_lsu_v1/base/5_1_grt.odb`，再用 pinned
image／同一 source helpers 與新的 analysis label 執行分析。原 run records
保留實際路徑與來源，不為重播而改寫。

## 實測時序與完整工作負載

| Corner | 10 ns setup slack ps | Hold slack ps | 電氣／涵蓋違例 |
| --- | ---: | ---: | ---: |
| TT | 2960.541 | 48.437 | 0 |
| SS | 30.871 | 83.926 | 0 |
| FF | 4597.620 | 17.164 | 0 |

SS 最差 setup 位於 `int_ex0_req_q[65]` 至 `dmem_req_addr[12]` 的 reg2out
路徑；最差 reg2reg slack 為 321.03 ps。保留完整 expanded clock paths，
不把所有時序壓成單一內部 datapath 數字。

| 集合 | 工作負載 | ROI cycles | 基線執行時間 µs |
| --- | --- | ---: | ---: |
| fp32 | fir | 74,311 | 743.11 |
| fp32 | iir | 13,523 | 135.23 |
| fp32 | fft | 40,867 | 408.67 |
| fp32 | pid | 7,248 | 72.48 |
| fp32 | gemm | 133,275 | 1,332.75 |
| fp32 | bicg | 23,927 | 239.27 |
| fp32 | cholesky | 194,161 | 1,941.61 |
| fp32 | svm | 43,392 | 433.92 |
| embench | aha-mont64 | 5,356,670 | 53,566.70 |
| embench | crc32 | 5,402,220 | 54,022.20 |
| embench | cubic | 14,490,894 | 144,908.94 |
| embench | edn | 4,754,496 | 47,544.96 |
| embench | huffbench | 3,377,028 | 33,770.28 |
| embench | matmult-int | 4,193,163 | 41,931.63 |
| embench | minver | 878,777 | 8,787.77 |
| embench | nbody | 5,893,151 | 58,931.51 |
| embench | nettle-aes | 5,203,513 | 52,035.13 |
| embench | nettle-sha256 | 4,307,562 | 43,075.62 |
| embench | nsichneu | 7,298,679 | 72,986.79 |
| embench | picojpeg | 5,300,988 | 53,009.88 |
| embench | qrduino | 4,524,180 | 45,241.80 |
| embench | sglib-combined | 4,526,268 | 45,262.68 |
| embench | slre | 4,902,163 | 49,021.63 |
| embench | st | 7,165,107 | 71,651.07 |
| embench | statemate | 3,368,567 | 33,685.67 |
| embench | ud | 2,775,897 | 27,758.97 |
| embench | wikisort | 2,173,042 | 21,730.42 |
