# 目前已驗證的 critical paths

候選通過 ASAP7 global-route 的三個 corner。在 100 ps 試驗網格上，最短合格週期是 **9.8 ns**（102.04 MHz）。A+B 父版為 9.4 ns。

| Corner | 9.8 ns setup | 9.8 ns hold | 10 ns setup | 10 ns hold |
| --- | ---: | ---: | ---: | ---: |
| TT | +2,950.70 ps | +39.49 ps | +3,150.70 ps | +39.49 ps |
| SS | +57.09 ps | +71.30 ps | +257.09 ps | +71.30 ps |
| FF | +4,547.99 ps | +16.16 ps | +4,747.99 ps | +16.16 ps |

相鄰的 9.7 ns 實測在 SS 的 setup slack 為 **-42.91 ps**。標準元件面積為 **21,498.75 µm²**，相對原基線為 **0.973626×**，相對 A+B 為 **0.992416×**。

## Critical paths

以下是 9.8 ns 各 path group 抽樣中最緊的一條。每組含五條實際路徑，表中 slack 已與獨立時序報告對帳。

| Corner／檢查 | 路徑類型 | 起點 → 終點 | Slack |
| --- | --- | --- | ---: |
| SS setup | reg2out | `int_ex0_req_q[64]` → `dmem_req_byte_en[1]` | +57.09 ps |
| SS setup | reg2reg | `fp_ex0_req_q[94]` → `u_fp_execute/cmp_data[107]` | +439.78 ps |
| SS setup | in2out | `dmem_rsp_valid` → `dmem_req_wdata[2]` | +4,574.66 ps |
| SS setup | in2reg | `dmem_rsp_valid` → `u_rob.entries[13][64]` | +4,982.71 ps |
| FF hold | reg2reg | `fp_ex0_req_q[284]` → `u_fp_simple.cmp_data[138]` | +16.16 ps |
| FF hold | in2reg | `imem_rsp_rdata[26]` → `u_frontend.iq_mem[5][101]` | +19.67 ps |
| FF hold | reg2out | `u_rob.commit_trace[246]` → `commit_trace[246]` | +314.07 ps |
| FF hold | in2out | `rst` → `dmem_req_valid` | +375.59 ps |

在 SS 9.8 ns，最緊 byte-enable 路徑的資料到達時間是 8,592.91 ps。9,800 ps 扣除 50 ps 的 setup 不確定度及 1,100 ps 的輸出預算，要求到達時間為 8,650 ps，得到 +57.09 ps 餘裕。

在 100 MHz 的 SS 報告中，全核心最小 setup 為 **+257.09 ps**。另將起點限制為五個 `rob_count` 暫存器、終點限制為 32 個 `dmem_req_addr` 位元，最緊為 **+6385.70 ps**。兩次查詢使用同一份 global-route 資料庫與 10 ns 約束。

[ROB 空間限制完整實體結果](LSU_ROB_ROOM_PHYSICAL.md)。

## 歷史對照：A+B 父版

CPU `3f079c1`，實體來源 `f66e12b`。

## Setup：SS、9.4 ns

| 排序 | 起點 | 終點 | 類型 | Slack |
| --- | --- | --- | --- | ---: |
| 1 | `int_ex0_req_q[65]` | `dmem_req_addr[2]` | reg → output | **+8.20 ps** |
| 2 | 同上 | `dmem_req_addr[9]` | reg → output | +8.36 ps |
| 3 | 同上 | `dmem_req_addr[13]` | reg → output | +8.76 ps |
| 4 | 同上 | `dmem_req_addr[4]` | reg → output | +9.69 ps |
| 5 | 同上 | `dmem_req_addr[6]` | reg → output | +10.48 ps |
| 6 | `fp_ex0_req_q[62]` | `u_fp_execute/cmp_data[107]` | reg → reg | **+59.46 ps** |
| 7 | 同上 | `u_fp_execute/cmp_data[101]` | reg → reg | +82.12 ps |
| 8 | 同上 | `u_fp_execute/cmp_data[111]` | reg → reg | +83.10 ps |

第一組經過 INT EX0／LSU 到資料埠位址輸出；第二組是 FPU 算術到已註冊 completion。
表中省略 mapped flop 型別後綴，原始報告保留完整名稱。每個 path group 各抽樣五條，
表格是這些抽樣的排序，不宣稱列出全設計任意前八條，也未將匿名 gates 全部對回 RTL 算式。
這些 slack 包含實際 constraints、clock tree 與 I/O budget，不能直接視為純組合延遲。

| SS 各類最緊路徑（9.4 ns） | 起點 → 終點 | Slack |
| --- | --- | ---: |
| reg → output | INT EX0 → `dmem_req_addr[2]` | +8.20 ps |
| reg → reg | FP EX0 → FPU completion | +59.46 ps |
| input → output | `dmem_rsp_error` → `dmem_req_wdata[20]` | +4,430.70 ps |
| input → reg | `dmem_rsp_error` → `u_rob.entries[9][110]` | +5,317.92 ps |

## Corner 與 hold

| Corner | 9.4 ns 最小 setup | 最小 hold |
| --- | ---: | ---: |
| TT | +2,719.23 ps | +39.98 ps |
| SS | +8.20 ps | +71.31 ps |
| FF | +4,225.69 ps | **+17.58 ps** |

FF 最緊 hold 是 `u_rob.event_counter[26] → u_rob.commit_trace[304]`（reg → reg），
另一個較緊 I/O hold 是 `dmem_rsp_error → u_lsu.rsp_buf_error`，**+24.67 ps**。
Hold 的約束須獨立維持，不能只追 setup 或 MHz。

9.3 ns 已實測在 SS setup **−91.80 ps** 失敗；9.4 ns 是 100 ps 試驗網格中的最短合格點。
100 MHz／10 ns 的 SS setup 為 **+608.20 ps**。固定 10 ns 記憶體下，已測全集合以
100 MHz 較快，故新仲裁先在此比較週期數；這不免除候選的重新實體資格。

## 與 LSU 仲裁的關係

新實驗先給安全 load 一次 head-store 首次 marking 的機會，再恢復 store 優先；
回壓期間保留已選 load。它加入選擇邏輯的位置接近上述最緊 LSU 輸出路徑，
因此要同時看 PID／完整兩集合的週期結果與後續路徑變化，不能用父版本的餘裕替新 RTL 保證時序。

[A+B 完整報告](LSU_AB_REVIEW.md) · [既有原始證據](evidence/2026-11-13/lsu-ab-complete/README.md) ·
[新仲裁契約](../experiments/lsu-load-arb-v1/README.md) · [仲裁功能結果](LSU_ARBITRATION_REVIEW.md)。
`report_parent_timing.py` 逐一核對封存與 collector hashes，重新整理三個 corner、兩個週期、
setup／hold 共 240 條抽樣路徑，並與獨立 closure 的最小 slack 對照。
