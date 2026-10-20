# LSU A：實體資格與完整雙操作點比較

2026-10-20。A 完成約定的 global-route 研究資格：在 **100 MHz** 時，
Embench19／FP32 八項分別為 **1.045830×／1.078255×**，
標準元件面積 **22,162.24152 µm²（1.003674×）**。
面積符合 ≤1.10×，兩個效能集合都尚未達各自 ≥1.20× 目標。
實際最短已測通過週期 9.9 ns 的完整量測則退步，兩個操作點皆保留。

若保留 100 MHz A 作後續起點，相對它仍需一般嵌入式再改善
1.147414×、FP32 再改善
1.112909× 才能達到原基線的 1.20×。
剩餘標準元件預算約 2,126.99 µm²；B 的實際效益仍須獨立量測。

建議先以 100 MHz 審查 A，再從相同凍結基線做 B 獨立對照。
正式操作點、是否保留 A 及後續組合仍待共同討論；本次不替換
`58a4159da0372b3286758be1e6c1b50f9f28cc27` 的基線，也未實作 B 或 A+B。

## 可比條件與來源

凍結 [AP5B v1](../../../../baselines/ap5b-post-lsu-v1/manifest.json) 不變：
基線 10,000 ps、22,081.118400004027 µm²；Embench19＋均衡 FP32 八項，
DSP／矩陣 ML 兩群各 50%；原 ELF bytes、資料、尺寸、容差及 3,629 筆 FP32
輸出固定。FP32 已含核准的 `fast -fno-fast-math`，不把融合收益再次當成 CPU 收益。
I response／I initiation interval／D response 各固定 10,000 ps；無額外隨機延遲。

A 的唯一功能 RTL 差異是成功且本拍確定消耗的 response buffer 可與下一請求
接受重疊；仍是一筆外部 outstanding、原 load response register、16-slot SQ、
原 B marking 與 store response 後退休，fault／flush 保守排除。
[功能里程碑](../../2026-10-19/lsu-a-functional/README.md) 保留完整介面與數值資格。
其 2026-10-19 的「實體待完成」是當時狀態；本封存補齊後續結果，沒有改寫舊數據。

功能建置與共同時脈量測為乾淨 `39bc12d87f80af2520a72f3a75adb3151a55f4c8`；
後續 `a94132c` 僅封存功能證據，`70727f50db4e77e4904d4d3492979e6a0f4ad2ba`
加入明確的雙操作點 reviewer 與四個控制測試。RTL／模擬器及實體政策輸入不變。
9.9 ns 正式量測在乾淨 70727f5 開始／結束，**27/27** 通過，原 **3,629** 筆數值
符合原容差，durable worker exit 0 且 **231** 個輸入雜湊前後一致。
其實際 normal simulator SHA 為
`ddb1b9dddbc87363c28c3a0d682676774b5696af13515dea3deb2a99f0dddeea`，
可由前一功能封存中的 executable gzip 還原；兩次量測使用相同 binary。
全集合原主機／Spike 輸入資格以 ELF 身分沿用，本次不是新的全集合 Spike 重跑。
`context/source-lineage.json` 直接核對三個 Git revision 的全部候選 RTL、
simulation 與 physical 輸入雜湊相同；相對基線只有 LSU RTL 不同。

兩個操作點的全 27 項退休指令分類及每 PC／instruction／kind 的退休次數均與
基線完全相同。這些是工作量計數對帳，不是完整有序 trace 或完整 ISA 證明。

## 執行時間結果

加速比為 `baseline ROI cycles × 10000 / (candidate ROI cycles × candidate period)`，
各集合完整分母計算幾何平均；沒有按最高頻率比例縮放原 cycles，也沒有混用兩集合時脈。

| 操作點 | Embench19 GM | FP32 GM | DSP GM | 矩陣／ML GM | 記憶體首次可取樣時間 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 100.000000 MHz（10000 ps） | 1.045830× | 1.078255× | 1.051614× | 1.105571× | 10.0 ns |
| 101.010101 MHz（9900 ps） | 0.726601× | 0.700275× | 0.653586× | 0.750300× | 19.8 ns |

在目前的同步取樣契約中，記憶體服務截止時間固定為 10 ns，回應在其後第一個
CPU edge 被看見。100 MHz 是一拍；101.01 MHz 的一拍只有 9.9 ns，所以需兩拍、
19.8 ns 才可取樣，I request 的 10 ns 最短間隔亦跨兩拍。所有 27 項原始
`memory.json` 確認 I／D min=max response 為對應的 10／19.8 ns。
這個離散效果解釋為何提頻約 1% 反而更慢；記憶體政策沒有改動。
request 數含 ROI 外及投機 fetch，不要求等於基線；已退休工作量另有逐項對帳。

| 集合 | 工作負載 | 基線 cycles | A 100 MHz cycles | 同頻時間加速 | A 101.01 MHz cycles | 提頻時間加速 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| fp32 | fir | 74,311 | 66,117 | 1.123932× | 125,393 | 0.598611× |
| fp32 | iir | 13,523 | 13,496 | 1.002001× | 22,777 | 0.599710× |
| fp32 | fft | 40,867 | 37,663 | 1.085070× | 52,375 | 0.788158× |
| fp32 | pid | 7,248 | 7,242 | 1.000829× | 11,352 | 0.644927× |
| fp32 | gemm | 133,275 | 123,175 | 1.081997× | 168,079 | 0.800940× |
| fp32 | bicg | 23,927 | 20,693 | 1.156285× | 33,729 | 0.716555× |
| fp32 | cholesky | 194,161 | 183,250 | 1.059542× | 238,395 | 0.822678× |
| fp32 | svm | 43,392 | 38,501 | 1.127036× | 65,300 | 0.671214× |
| embench | aha-mont64 | 5,356,670 | 5,354,540 | 1.000398× | 9,662,429 | 0.559981× |
| embench | crc32 | 5,402,220 | 5,054,736 | 1.068744× | 8,012,928 | 0.680998× |
| embench | cubic | 14,490,894 | 14,160,446 | 1.023336× | 19,982,172 | 0.732516× |
| embench | edn | 4,754,496 | 4,256,669 | 1.116952× | 6,985,140 | 0.687534× |
| embench | huffbench | 3,377,028 | 3,306,646 | 1.021285× | 4,685,662 | 0.727995× |
| embench | matmult-int | 4,193,163 | 3,825,063 | 1.096234× | 6,173,306 | 0.686102× |
| embench | minver | 878,777 | 858,801 | 1.023260× | 1,080,838 | 0.821264× |
| embench | nbody | 5,893,151 | 5,821,267 | 1.012349× | 8,545,370 | 0.696597× |
| embench | nettle-aes | 5,203,513 | 4,797,126 | 1.084715× | 8,532,971 | 0.615972× |
| embench | nettle-sha256 | 4,307,562 | 4,200,675 | 1.025445× | 7,797,891 | 0.557981× |
| embench | nsichneu | 7,298,679 | 6,913,377 | 1.055733× | 8,455,848 | 0.871870× |
| embench | picojpeg | 5,300,988 | 5,064,804 | 1.046632× | 7,178,562 | 0.745906× |
| embench | qrduino | 4,524,180 | 4,377,993 | 1.033391× | 6,369,911 | 0.717416× |
| embench | sglib-combined | 4,526,268 | 4,332,256 | 1.044783× | 5,859,963 | 0.780208× |
| embench | slre | 4,902,163 | 4,664,230 | 1.051012× | 6,271,141 | 0.789598× |
| embench | st | 7,165,107 | 7,092,839 | 1.010189× | 10,024,750 | 0.721961× |
| embench | statemate | 3,368,567 | 3,100,457 | 1.086474× | 4,079,514 | 0.834068× |
| embench | ud | 2,775,897 | 2,616,256 | 1.061019× | 3,050,831 | 0.919073× |
| embench | wikisort | 2,173,042 | 2,134,990 | 1.017823× | 2,844,370 | 0.771697× |

`context/review-common-clock-v1.json` 與 `context/review-fastest-v1.json` 的
`passed:true` 表示完整性、功能、對應時脈與面積條件核對通過；
`all_planning_targets_met:false` 明確保留兩類效能目標未達。
`context/operating-point-analysis.json` 及其 exact script 保存原始檔案雜湊、
逐項時間、記憶體取樣、工作量及等待位置；等待計數不能相加成可省週期。

## 相同實體流程與實際邊界

使用 pinned `rv32ooo-orfs:8359fde-flat`，image ID
`sha256:92a37abacbbf91494f9a8078b45fe1f6688a533cf5c87d02599d28c5fe229b33`，
ORFS `8359fde81991e6118b15b8a93fcde606b577794d`、OpenROAD
`26Q1-2900-gdf79404cd8`、Yosys `0.63+post`。204 個工具／ASAP7 輸入雜湊在
刪減私有未用平台前後、每次三 corner collection 前後及環境重啟後均核對通過。

ordinary ABC 5,500 ps mapping → 14,000 ps TT-only backend → TT 45% slew／
50 ps hold repair → 最終全設計 global route 與 antenna 模型檢查。
2 threads、placement default、相同相容性 overrides；原 physical Tcl、SDC
政策、I/O、uncertainty、load、RC 與工具皆不變。沒有重用基線或其他 RTL 的
synthesis／CTS／route cache；A 自己的三階段均 exit 0 且輸入身分前後一致。
這兩個建置 period 不是已達成時脈。

同一最終 ODB 分別以新 process 分析 TT／SS／FF，共用 nominal wire RC。
先完成 14 ns 三 corner 審查，再實際執行下列 100 ps grid，而非從 slack 外推：

| CPU period | TT setup／hold ps | SS setup／hold ps | FF setup／hold ps | 結果 |
| --- | ---: | ---: | ---: | --- |
| 9800 ps | 2834.898105／48.803628 | -49.313442／84.647734 | 4421.538264／14.318158 | SS setup 失敗 |
| 9900 ps | 2934.898114／48.803628 | 50.686566／84.647734 | 4521.538273／14.318158 | 三 corner 通過 |
| 10000 ps | 3034.898123／48.803628 | 150.686575／84.647734 | 4621.538282／14.318158 | 三 corner 通過 |

通過點的 constraint coverage、四種 path group、slew／cap／pulse／period
檢查均符合原門檻。全設計最終 route 為 **176,228 nets**、
wirelength **1,441,320 µm**，overflow **0／0／0**；兩次 ECO placement
皆零失敗；antenna net／pin violation 均零。原生 log／JSON／report 均封存。

三 corner 面積皆為 22162.241520003 µm²，標準元件
181,582 顆，register count 18,147，macro 0，已知 library-warning cells 的
實際 instance 0。面積邊界含 core、PRF／SQ、debug／commit trace 及全部
clock／repair cells，不含外部 RAM。物理 register 計數不是架構狀態量的宣稱。
這是單次固定流程結果，未量測重跑變異，也不宣稱 detailed-route、OCV、功耗或完整 ISA signoff。

## 封存與環境紀錄

- `physical/`：三階段 durable run／job／log、原 constraints、全部獨立 timing
  outputs／review，以及已往返解壓核對的 final ODB／SDC／guide、A mapped netlist
  與 sv2v lowered RTL。保留相鄰 9.8 ns timing 失敗。
- `measurement-9900ps-v1/`：完整 27 項 ELF、stdout、profile、memory audit、summary。
  100 MHz 的完整原始量測仍在前一功能封存，這裡以 summary hash 綁定。
- `measurement-9900ps-relaunch-v2/`：真正執行的獨立 worker spec、log、run、lock。
  原先 queued report／spec 與 shared lock 保留在 `context/`；該啟動被原有
  exclusive lock 拒絕。實際負向重播確認非零退出且不覆寫原結果，後以新目錄
  重啟，沒有刪掉鎖檔或假報舊啟動成功。容器跨 session 的退出也另有紀錄。
- `context/operating-point-controls.log`：契約／量測／worker／closure／operating-point
  共 **21 tests** 通過。新增控制拒收未資格時脈、不完整網格與錯綁比較點。
- `context/physical-resources.jsonl`：從 synthesis 中途開始至 boundary 完成的
  唯讀資源樣本，並非完整資源峰值量測。原腳本一併保存。
- `context/` 的 VFS／storage receipts 記錄先前精確清理未引用失敗 layers、
  僅刪除私有映像副本未用平台，以及完成 ODB 的無損壓縮。pinned images 保留；
  活躍工作不並行建立大型 runtime，原基線封存不變。
- `context/runtime-completion-cleanup.json`：兩組量測與審查完成、容器只剩
  `sleep` 後移除該專用容器，回收 8,943,087,616 bytes（約 8.33 GiB），釘選映像保留。
  先前唯讀 preflight 因 Docker 要求 PID 欄位而失敗的紀錄也獨立保留。
- `copy-inventory.json`、`completion-copy-inventory.json` 保留原 source path、
  原 SHA、archive path 與 gzip 往返證明；原始 command／log 路徑未為封存改寫。
  `inputs/` 是實際政策與 reviewer 來源快照。

原始 collection／worker `passed:false` 是故意保留的階段狀態，不能單獨當
成完成資格。實際 native exit、collection completion、independent review 與
27 項量測各自核對後，才得到本報告中的正向研究資格。

## 核對與重現

在本目錄執行 `sha256sum -c SHA256SUMS`。大型檔案採無損 gzip，對照
copy inventory 解壓後原 SHA 必須相同。重新執行 archived review 時，先把
三階段 metadata、原 timing reports 與最終 ODB／SDC／guide 還原至 `run.json`
記錄的 `build/` 位置；不要直接更改原 JSON paths 或 hashes。

checkout 70727f5，使用原 pinned images、工具／platform manifest、原 baseline
輸入資格與原 ELF，執行前一功能封存的 build／qualification 命令，再用兩個
不同新輸出目錄執行 `scripts/measure_cpu_experiment.py --period-ps 10000` 及
`--period-ps 9900`。完整參數在各 worker spec。物理重跑命令與順序在
`context/physical-pipeline.json`／原 script；採新 attempt label，不能混入舊 RTL cache。

最後分別以 `scripts/review_cpu_experiment.py --comparison-point common-clock`
及 `--comparison-point fastest` 綁定各自完整量測及實際三 corner boundary。
此重現需要對應工具環境與還原路徑；僅重算 GM 不等於重新驗證硬體。
