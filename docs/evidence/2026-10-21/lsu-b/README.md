# LSU B v1：功能通過、實體時序未通過

2026-10-21。B 從凍結基線獨立實作，完整功能與同頻 cycle 診斷通過，
但在相同固定實體流程下未取得 TT／SS／FF 全部合格的操作點。
**100 MHz 的 SS setup 為 −2,282.9916 ps；FF hold 為 −0.332734 ps。**
標準元件面積為 **21,983.62194 µm²（0.9955846× 基線）**，符合面積預算。

完整 100 MHz cycle 診斷為 Embench19 **1.029459×**、FP32 八項 **1.009599×**
（DSP 1.013839×、矩陣／ML 1.005376×）。這些是未取得實體操作點資格的
同頻診斷，不能作正式系統執行時間／PPA 通過成績；兩個同頻集合也均低於
各自 ≥1.20× 目標。沒有可定義的「最快合格時脈」，因此未產生第二組正式成績。

結論是 **B v1 的實驗已完成，候選被實體時序關卡拒收**。
凍結基線 `58a4159da0372b3286758be1e6c1b50f9f28cc27` 不變，A 的證據維持原樣；
後續調整／組合仍由使用者共同選擇，本次沒有導入 A+B。

## 來源、範圍與機制

功能／建置／量測來源為乾淨 `95ac0dd6451a1799f9f3fe948c7b74c02f5fccd2`，
其單一父版本就是凍結基線。共用量測工具與 A 歷史證據由 `bf6702c` 帶入；
33 個 RTL／模擬／實體政策輸入逐檔核對，只有 LSU RTL 不同。
[凍結契約](../../../../baselines/ap5b-post-lsu-v1/manifest.json)與
[B 事前實驗契約](../../../../experiments/lsu-b-v1/manifest.json)不變。
`context/source-lineage.json` 綁定實際 Git blobs／父版本／live 檔案，
`context/comparison-provenance-review.json` 核對基線／A／B 的 81 份原始 profile。
原基線 scored executable 也逐 byte 保留。

B 允許完整 ROB tag（seq／idx）匹配、地址與資料已同時由 AGU 捕獲、無例外、
無 flush 且 RUN 的 ROB-head store，在 SQ marking 同拍提出請求。
仍維持 16-slot SQ、一筆 external outstanding、成功 store response 後才 ack，
以及原 AP5B response-buffer 排除。A 的 response-consume overlap 未帶入 B。
原 assertions 2／6 保留，另驗證 B 的授權與下一拍交易追蹤。

`inputs/` 是實際來源快照，包含 95ac 的事前 README；目前討論入口為
[LSU B 審查](../../../LSU_B_REVIEW.md)。

## 功能與同頻資料資格

- `unit-clean-v1/`：基線、B 各 **62** 項 pin-driven／assertion cases；另保留
  原 RTL 無法通過 B 同拍要求的負向控制。涵蓋完整 tag、未解地址、INT／FP、
  byte／half／word 格式、wrap、背壓、flush、fault、forward／misalign、優先權，
  以及三個 seed 各 128 load／store 的延遲串流。這是 LSU 介面案例，非完整 ISA 證明。
  16-store 理想串流 **48→32 cycles**；load 的原 response-buffer 排除維持不變。
  `unit-dev-v1/` 是前一開發跑次，正式分母使用 clean-v1。
- `build-clean-v1/`：Verilator 4.038／G++ 11.4、全新 normal／assert 模型，
  乾淨 95ac 開始與結束。normal SHA
  `359ea89735e630a3c1f2fcd7795ec9598f35d6fb4e9a8b0f448ba3f6ee2c1144`，
  assert SHA `da70e3bd5c695a9d4bea54950746537092a2ffdf69d10367c56a1f45a1dfc860`。
  實際 binary 以 gzip 保存並驗證解壓往返；Verilator 生成命令與 verFiles 也保存。
- `qualification-clean-v1/`：directed **18**、Spike **18**、assertion interface **48**、
  fixed-time controls **58**、finite FMA **3,400** 全通過。
  22 項 summary records 表示 18 directed＋四個 suite，並非 22 個全部覆蓋的 ISA 類別。
- `measurement-10000ps-v1/`：原 Embench **19**＋均衡 FP32 **8** 共 **27/27**，
  原 **3,629** 筆輸出、原 ELF／fixture／尺寸／容差、memory audit、stack 餘裕、
  退休指令分類與逐 PC／instruction／kind 工作量全部核對。
  FP32 沿用已凍結 `fast -fno-fast-math`，未再次計入融合收益。
  全集合主機／Spike 的輸入資格沿用相同 ELF 身分；本次 Spike 重跑是 18 項定向集。
- `functional-worker-v1/`：實際 exit **0**，**335** 個輸入雜湊前後一致。
  原 outer controller 因環境更新中斷、無最終 exit，容器內 durable 量測持續完成；
  `context/controller-recovery-v2.json` 保留 unknown exit 與接回程序，原 log 未覆寫。
- `admission-controls/`：**31** 契約／review controls 通過；實際 CLI 拒收
  baseline 模式使用 B、改動 mapping period、混用 A build、混用 A functional proof。
  `context/review-common-diagnostics-v1.json` 另獨立重驗全 27 項原始資料與建置／功能證明，
  明確標示 `physical_operating_point_qualified:false`。

同頻 CPU 為 10,000 ps；I response／I initiation interval／D response 永遠各
10,000 ps，random／fault 參數為零。每項為相同 ROI 的 cycle 比，沒有頻率外推。

| 集合 | 案例 | 基線 cycles | A 100 MHz cycles | B 同頻診斷 cycles | B cycle 比 |
| --- | --- | ---: | ---: | ---: | ---: |
| fp32 | fir | 74311 | 66117 | 74303 | 1.000108× |
| fp32 | iir | 13523 | 13496 | 12499 | 1.081927× |
| fp32 | fft | 40867 | 37663 | 36722 | 1.112875× |
| fp32 | pid | 7248 | 7242 | 8261 | 0.877376× |
| fp32 | gemm | 133275 | 123175 | 133870 | 0.995555× |
| fp32 | bicg | 23927 | 20693 | 23720 | 1.008727× |
| fp32 | cholesky | 194161 | 183250 | 190887 | 1.017152× |
| fp32 | svm | 43392 | 38501 | 43383 | 1.000207× |
| embench | aha-mont64 | 5356670 | 5354540 | 5359621 | 0.999449× |
| embench | crc32 | 5402220 | 5054736 | 5402210 | 1.000002× |
| embench | cubic | 14490894 | 14160446 | 14025779 | 1.033161× |
| embench | edn | 4754496 | 4256669 | 4723764 | 1.006506× |
| embench | huffbench | 3377028 | 3306646 | 3217162 | 1.049692× |
| embench | matmult-int | 4193163 | 3825063 | 4138048 | 1.013319× |
| embench | minver | 878777 | 858801 | 843225 | 1.042162× |
| embench | nbody | 5893151 | 5821267 | 5823850 | 1.011900× |
| embench | nettle-aes | 5203513 | 4797126 | 5170824 | 1.006322× |
| embench | nettle-sha256 | 4307562 | 4200675 | 4247681 | 1.014097× |
| embench | nsichneu | 7298679 | 6913377 | 7302368 | 0.999495× |
| embench | picojpeg | 5300988 | 5064804 | 5105271 | 1.038336× |
| embench | qrduino | 4524180 | 4377993 | 4548795 | 0.994589× |
| embench | sglib-combined | 4526268 | 4332256 | 4351929 | 1.040060× |
| embench | slre | 4902163 | 4664230 | 4580842 | 1.070145× |
| embench | st | 7165107 | 7092839 | 7077473 | 1.012382× |
| embench | statemate | 3368567 | 3100457 | 2826412 | 1.191817× |
| embench | ud | 2775897 | 2616256 | 2725595 | 1.018455× |
| embench | wikisort | 2173042 | 2134990 | 2102321 | 1.033639× |

A 的 100 MHz 欄已有[獨立實體資格](../../2026-10-20/lsu-a-physical/README.md)，
B 欄僅為 cycle 診斷。原始數據與計算在 `context/common-clock-diagnostics.json`。
工作量 map 是計數對帳，不是完整有序 trace 或完整 ISA signoff。

PID 執行時間增加 **13.9763%**（7,248→8,261 cycles）；GEMM 也略退步。
BiCG 的 `store_ack_wait` 由 6,460 降到 1,676，但 `head_wait_fp_load` 由 505
升到 5,082，總 ROI 僅減 207 cycles。PID 的 store 等待減 1,027，但 FMA、
FADD 與 store 未完成等待增加，總 ROI 加 1,013。這些是非重疊 cycle_partition
的對帳，不能把 overlapping events 加總成可省週期，也尚未證明所有排程根因。

## 固定實體流程與失敗資料

pinned ORFS `8359fde81991e6118b15b8a93fcde606b577794d`／ASAP7 RVT，
OpenROAD `26Q1-2900-gdf79404cd8`，image
`sha256:92a37abacbbf91494f9a8078b45fe1f6688a533cf5c87d02599d28c5fe229b33`。
2 threads、TT-only construction、ordinary ABC mapping 5,500 ps、backend 14,000 ps，
TT ECO slew 45%／hold 50 ps，再做完整 global route。原 I/O 1,100 ps、uncertainty
50／25 ps、RC、load、checker 與接受門檻均不變。未重用 A／基線 native cache；
B 自己的三階段皆 exit 0 且輸入身分前後一致。建置 period 不代表已達成時脈。

最終 route：174,439 nets、wirelength 1,482,175 µm、overflow **0／0／0**，
兩次 ECO placement **0** failures，antenna net／pin violations **0／0**。
標準元件 179,774、physical register count 18,162、macro 0、已知 warning cells 的
實例 0。面積含 core／PRF／SQ／commit trace 與所有 clock／repair cells，排除外部 RAM。
ECO 的 slew buffers 為 1,249、hold buffers 4,662；A 分別為 1,203／4,257。
這些已包含在面積中，不能再額外相加。

同一最終 ODB 在各 corner 的獨立新 process 實測如下：

| period ps | TT setup／hold ps | SS setup／hold ps | FF setup／hold ps | 完整資格 |
| ---: | ---: | ---: | ---: | --- |
| 14000 | 5828.409／48.856 | 1717.009／85.209 | 8094.052／-0.333 | 未通過 |
| 10000 | 1828.409／48.856 | -2282.992／85.209 | 4094.051／-0.333 | 未通過 |
| 12200 | 4028.409／48.856 | -82.991／85.209 | 6294.051／-0.333 | 未通過 |
| 12300 | 4128.409／48.856 | 17.009／85.209 | 6394.051／-0.333 | 未通過 |

12.2／12.3 ns 是相鄰 100 ps 的 **setup-only** 實測邊界；FF hold 在所有點失敗，
所以 12.3 ns 也不是合格操作點。14 ns 失敗及原控制器的非零退出都保留，
沒有覆寫成「成功」。`context/physical-pipeline.json`／`completion-pipeline.json`
的 incomplete／error 反映自動資格關卡停止；`context/experiment-result.json`
則明確區分「實驗已完成」與「候選未合格」。

`context/review-unqualified-common-clock-v1.json` 是真實的完整資格拒收：
`measurement clock is not independently qualified`。沒有降低 hold 門檻、改 ECO margin、
延用 A 的物理資料，或用 cycle 比縮放出一個正式得分。

最差 SS setup 是 `fp_ex0_req_q[89]`→`u_fp_execute.cmp_data[115]` 的 reg2reg 路徑；
FF hold 是 `dmem_req_ready`→LSU in-flight tracking 暫存器的 in2reg 路徑。
原始路徑與基線／A 對照在 `context/physical-failure-path-review.json` 及提取的 rpt。
FPU RTL 未改；單次完整映射／布局的結果不能證明 B 頭端 store 邏輯必然造成全部
時序退步。後續若診斷映射、調整流程或另做 B／A+B，需共同決定並維持可比條件。
這是 global-route nominal-RC 研究，沒有 detailed-route、OCV、功耗或多跑次變異資格。

## 封存、空間與重播

`copy-inventory.json` 保存原路徑、SHA、mode、archive path 及 gzip 往返驗證。
`physical/` 含三階段 metadata／log／constraint、兩輪全部 corner reports、mapped
netlist 與最終 ODB／SDC／可用 guide；`inputs/` 含實際 CPU／政策／checker 快照。
原始 JSON paths／hashes 均未為封存改寫。`SHA256SUMS` 對應封存實際 bytes。

`context/` 的 runtime／storage receipts 記錄：FP 工作完成後才釋放其 runtime，
工具／ASAP7 204 個 hash 在刪減私有未用平台、headers／docs 前後及 corner 收集
前後皆核對；舊 A／基線的相同閒置快取採 hardlink，路徑與 bytes 保留，應保持不可變。
兩份 A 其他閒置 ODB 採往返核對 gzip；A／基線原始證據 indexes 均未修改。
B 的所有 native／diagnostic 工作結束且只剩 sleep 後，才移除專用 physical runtime；
pinned images 與 host bind outputs 保留。resource samples 從功能量測中途到第一輪
時序拒收為止，不代表整個 session 的完整資源峰值。

核對：在本目錄執行 `sha256sum -c SHA256SUMS`。
重播來源使用 95ac、原 pinned images 及 baseline frozen ELFs；用全新輸出 labels 執行
`build-clean-v1/summary.json` 的建置命令及 `context/functional-pipeline.py` 的
unit／qualification／measurement 命令，
以及 `context/physical-pipeline.json`／`diagnostic-boundary-driver.log` 所對應的分析命令。
`context/finish-measurements.py` 保留資格失敗後停止的真實紀錄；沒有第二組合格成績。
若只重驗原始證據，先依 copy inventory 解壓至原 `build/` 路徑，恢復原 mode（binary
需可執行），包含 baseline／A 的既有封存與 B 的 generated verFiles／suite logs。
執行 `context/review-common-diagnostics.py` 可重驗功能／cycle；完整
`review_cpu_experiment.py --comparison-point common-clock` 應再次拒收這份 timing。
詳細命令與實際退出均在原 job spec／driver logs，不應手動改 hashes 使失敗變通過。
